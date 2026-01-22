"""
Subscription Service - Gestión de suscripciones VIP/Free.

Responsabilidades:
- Generación de tokens de invitación
- Validación y canje de tokens
- Gestión de suscriptores VIP (crear, extender, expirar)
- Gestión de solicitudes Free (crear, procesar)
- Limpieza automática de datos antiguos
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from aiogram import Bot
from aiogram.types import ChatInviteLink
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config
from bot.database.models import (
    InvitationToken,
    VIPSubscriber,
    FreeChannelRequest,
    BotConfig
)

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service para gestionar suscripciones VIP y Free.

    VIP Flow:
    1. Admin genera token → generate_vip_token()
    2. Usuario canjea token → redeem_vip_token()
    3. Usuario recibe invite link → create_invite_link()
    4. Suscripción expira automáticamente → expire_vip_subscribers() (background)

    Free Flow:
    1. Usuario solicita acceso → create_free_request()
    2. Espera N minutos
    3. Sistema procesa cola → process_free_queue() (background)
    4. Usuario recibe invite link
    """

    def __init__(self, session: AsyncSession, bot: Bot):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos
            bot: Instancia del bot de Telegram
        """
        self.session = session
        self.bot = bot
        logger.debug("✅ SubscriptionService inicializado")

    # ===== TOKENS VIP =====

    async def generate_vip_token(
        self,
        generated_by: int,
        duration_hours: int = 24,
        plan_id: Optional[int] = None
    ) -> InvitationToken:
        """
        Genera un token de invitación único para canal VIP.

        El token:
        - Tiene 16 caracteres alfanuméricos
        - Es único (verifica duplicados)
        - Expira después de duration_hours
        - Puede usarse solo 1 vez
        - Opcionalmente vinculado a un plan de suscripción

        Args:
            generated_by: User ID del admin que genera el token
            duration_hours: Duración del token en horas (default: 24h)
            plan_id: ID del plan de suscripción (opcional)

        Returns:
            InvitationToken: Token generado

        Raises:
            ValueError: Si duration_hours es inválido
            RuntimeError: Si no se puede generar token único después de 10 intentos
        """
        if duration_hours < 1:
            raise ValueError("duration_hours debe ser al menos 1")

        # Generar token único
        max_attempts = 10
        token_str = None

        for attempt in range(max_attempts):
            # secrets.token_urlsafe(12) genera ~16 chars después de strip
            token_str = secrets.token_urlsafe(12)[:16]

            # Verificar que no exista
            result = await self.session.execute(
                select(InvitationToken).where(
                    InvitationToken.token == token_str
                )
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                # Token único encontrado
                break

            logger.warning(f"⚠️ Token duplicado generado (intento {attempt + 1})")
        else:
            # No se encontró token único después de max_attempts
            raise RuntimeError(
                "No se pudo generar token único después de 10 intentos"
            )

        # Crear token
        token = InvitationToken(
            token=token_str,
            generated_by=generated_by,
            created_at=datetime.utcnow(),
            duration_hours=duration_hours,
            used=False,
            plan_id=plan_id  # Vincular con plan (opcional)
        )

        self.session.add(token)
        # No commit - dejar que el handler maneje la transacción

        logger.info(
            f"✅ Token VIP generado: {token.token} "
            f"(válido por {duration_hours}h, plan_id: {plan_id}, generado por {generated_by})"
        )

        return token

    async def validate_token(
        self,
        token_str: str
    ) -> Tuple[bool, str, Optional[InvitationToken]]:
        """
        Valida un token de invitación.

        Un token es válido si:
        - Existe en la base de datos
        - No ha sido usado (used=False)
        - No ha expirado (created_at + duration_hours > now)

        Args:
            token_str: String del token (16 caracteres)

        Returns:
            Tuple[bool, str, Optional[InvitationToken]]:
                - bool: True si válido, False si inválido
                - str: Mensaje de error/éxito
                - Optional[InvitationToken]: Token si existe, None si no
        """
        # Buscar token
        result = await self.session.execute(
            select(InvitationToken).where(
                InvitationToken.token == token_str
            )
        )
        token = result.scalar_one_or_none()

        if token is None:
            return False, "❌ Token no encontrado", None

        if token.used:
            return False, "❌ Este token ya fue usado", token

        if token.is_expired():
            return False, "❌ Token expirado", token

        return True, "✅ Token válido", token

    async def redeem_vip_token(
        self,
        token_str: str,
        user_id: int
    ) -> Tuple[bool, str, Optional[VIPSubscriber]]:
        """
        Canjea un token VIP y crea/extiende suscripción.

        Si el usuario ya es VIP:
        - Extiende su suscripción (no crea nueva)

        Si el usuario es nuevo:
        - Crea nueva suscripción VIP

        Args:
            token_str: String del token
            user_id: ID del usuario que canjea

        Returns:
            Tuple[bool, str, Optional[VIPSubscriber]]:
                - bool: True si éxito, False si error
                - str: Mensaje descriptivo
                - Optional[VIPSubscriber]: Suscriptor creado/actualizado
        """
        # Validar token
        is_valid, message, token = await self.validate_token(token_str)

        if not is_valid:
            return False, message, None

        # Marcar token como usado
        token.used = True
        token.used_by = user_id
        token.used_at = datetime.utcnow()

        # Verificar si usuario ya es VIP
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.user_id == user_id
            )
        )
        existing_subscriber = result.scalar_one_or_none()

        if existing_subscriber:
            # Usuario ya es VIP: extender suscripción
            # Agregar token.duration_hours a la fecha de expiración actual
            extension = timedelta(hours=token.duration_hours)

            # Si ya expiró, partir desde ahora
            if existing_subscriber.is_expired():
                existing_subscriber.expiry_date = datetime.utcnow() + extension
            else:
                # Si aún está activo, extender desde la fecha actual de expiración
                existing_subscriber.expiry_date += extension

            existing_subscriber.status = "active"

            # No commit - dejar que el handler maneje la transacción

            logger.info(
                f"✅ Suscripción VIP extendida: user {user_id} "
                f"(nueva expiración: {existing_subscriber.expiry_date})"
            )

            return True, "✅ Suscripción VIP extendida exitosamente", existing_subscriber

        # Usuario nuevo: crear suscripción
        expiry_date = datetime.utcnow() + timedelta(hours=token.duration_hours)

        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow(),
            expiry_date=expiry_date,
            status="active",
            token_id=token.id
        )

        self.session.add(subscriber)
        # No commit - dejar que el handler maneje la transacción

        logger.info(
            f"✅ Nuevo suscriptor VIP: user {user_id} "
            f"(expira: {expiry_date})"
        )

        return True, "✅ Suscripción VIP activada exitosamente", subscriber

    # ===== GESTIÓN VIP =====

    async def get_vip_subscriber(self, user_id: int) -> Optional[VIPSubscriber]:
        """
        Obtiene el suscriptor VIP por user_id.

        Args:
            user_id: ID del usuario

        Returns:
            VIPSubscriber si existe, None si no
        """
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def is_vip_active(self, user_id: int) -> bool:
        """
        Verifica si un usuario tiene suscripción VIP activa.

        Args:
            user_id: ID del usuario

        Returns:
            True si VIP activo, False si no
        """
        subscriber = await self.get_vip_subscriber(user_id)

        if subscriber is None:
            return False

        if subscriber.status != "active":
            return False

        if subscriber.is_expired():
            return False

        return True

    async def activate_vip_subscription(
        self,
        user_id: int,
        token_id: int,
        duration_hours: int
    ) -> VIPSubscriber:
        """
        Activa una suscripción VIP para un usuario (método privado de deep link).

        NUEVO: Usado por el flujo de deep link para activar automáticamente
        la suscripción sin pasar por el flujo de canje manual.

        Args:
            user_id: ID del usuario que activa
            token_id: ID del token a usar
            duration_hours: Duración de la suscripción en horas

        Returns:
            VIPSubscriber: Suscriptor creado o actualizado

        Raises:
            ValueError: Si el usuario ya es VIP o token inválido
        """
        # Verificar si usuario ya es VIP
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.user_id == user_id
            )
        )
        existing_subscriber = result.scalar_one_or_none()

        if existing_subscriber:
            # Usuario ya es VIP: extender suscripción
            extension = timedelta(hours=duration_hours)

            # Si ya expiró, partir desde ahora
            if existing_subscriber.is_expired():
                existing_subscriber.expiry_date = datetime.utcnow() + extension
            else:
                # Si aún está activo, extender desde la fecha actual de expiración
                existing_subscriber.expiry_date += extension

            existing_subscriber.status = "active"

            # No commit - dejar que el handler maneje la transacción
            logger.info(
                f"✅ Suscripción VIP extendida vía deep link: user {user_id} "
                f"(nueva expiración: {existing_subscriber.expiry_date})"
            )

            return existing_subscriber

        # Usuario nuevo: crear suscripción
        expiry_date = datetime.utcnow() + timedelta(hours=duration_hours)

        subscriber = VIPSubscriber(
            user_id=user_id,
            join_date=datetime.utcnow(),
            expiry_date=expiry_date,
            status="active",
            token_id=token_id
        )

        self.session.add(subscriber)
        # No commit - dejar que el handler maneje la transacción

        logger.info(
            f"✅ Nuevo suscriptor VIP vía deep link: user {user_id} "
            f"(expira: {expiry_date})"
        )

        return subscriber

    async def expire_vip_subscribers(self) -> int:
        """
        Marca como expirados los suscriptores VIP cuya fecha pasó.

        Esta función se ejecuta periódicamente en background.

        Returns:
            Cantidad de suscriptores expirados
        """
        # Buscar suscriptores activos con fecha de expiración pasada
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.status == "active",
                VIPSubscriber.expiry_date < datetime.utcnow()
            )
        )
        expired_subscribers = result.scalars().all()

        count = 0
        for subscriber in expired_subscribers:
            subscriber.status = "expired"
            count += 1
            logger.info(f"⏱️ VIP expirado: user {subscriber.user_id}")

        if count > 0:
            await self.session.commit()
            logger.info(f"✅ {count} suscriptor(es) VIP marcados como expirados")

        return count

    async def kick_expired_vip_from_channel(self, channel_id: str) -> int:
        """
        Expulsa suscriptores expirados del canal VIP.

        Esta función se ejecuta después de expire_vip_subscribers()
        en el background task.

        Args:
            channel_id: ID del canal VIP (ej: "-1001234567890")

        Returns:
            Cantidad de usuarios expulsados
        """
        # Buscar suscriptores expirados
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.status == "expired"
            )
        )
        expired_subscribers = result.scalars().all()

        kicked_count = 0
        for subscriber in expired_subscribers:
            try:
                # Intentar expulsar del canal
                await self.bot.ban_chat_member(
                    chat_id=channel_id,
                    user_id=subscriber.user_id
                )

                # Desbanear inmediatamente (solo expulsar, no banear permanente)
                await self.bot.unban_chat_member(
                    chat_id=channel_id,
                    user_id=subscriber.user_id
                )

                kicked_count += 1
                logger.info(f"👢 Usuario expulsado de VIP: {subscriber.user_id}")

            except Exception as e:
                logger.warning(
                    f"⚠️ No se pudo expulsar a user {subscriber.user_id}: {e}"
                )

        if kicked_count > 0:
            logger.info(f"✅ {kicked_count} usuario(s) expulsados del canal VIP")

        return kicked_count

    async def get_all_vip_subscribers(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[VIPSubscriber]:
        """
        Obtiene lista de suscriptores VIP con paginación.

        Args:
            status: Filtrar por status ("active", "expired", None=todos)
            limit: Máximo de resultados (default: 100)
            offset: Offset para paginación (default: 0)

        Returns:
            Lista de suscriptores
        """
        query = select(VIPSubscriber).order_by(
            VIPSubscriber.expiry_date.desc()
        )

        if status:
            query = query.where(VIPSubscriber.status == status)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ===== CANAL FREE =====

    async def create_free_request(self, user_id: int) -> FreeChannelRequest:
        """
        Crea una solicitud de acceso al canal Free.

        Si el usuario ya tiene una solicitud pendiente, la retorna.

        Args:
            user_id: ID del usuario

        Returns:
            FreeChannelRequest: Solicitud creada o existente
        """
        # Verificar si ya tiene solicitud pendiente
        result = await self.session.execute(
            select(FreeChannelRequest).where(
                FreeChannelRequest.user_id == user_id,
                FreeChannelRequest.processed == False
            ).order_by(FreeChannelRequest.request_date.desc())
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                f"ℹ️ Usuario {user_id} ya tiene solicitud Free pendiente "
                f"(hace {existing.minutes_since_request()} min)"
            )
            return existing

        # Crear nueva solicitud
        request = FreeChannelRequest(
            user_id=user_id,
            request_date=datetime.utcnow(),
            processed=False
        )

        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)

        logger.info(f"✅ Solicitud Free creada: user {user_id}")

        return request

    async def get_free_request(self, user_id: int) -> Optional[FreeChannelRequest]:
        """
        Obtiene la solicitud Free pendiente de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            FreeChannelRequest si existe pendiente, None si no
        """
        result = await self.session.execute(
            select(FreeChannelRequest).where(
                FreeChannelRequest.user_id == user_id,
                FreeChannelRequest.processed == False
            ).order_by(FreeChannelRequest.request_date.desc())
        )
        return result.scalar_one_or_none()

    async def create_free_request_from_join_request(
        self,
        user_id: int,
        from_chat_id: str
    ) -> Tuple[bool, str, Optional[FreeChannelRequest]]:
        """
        Crea solicitud Free desde ChatJoinRequest de Telegram.

        Limpia solicitudes antiguas y crea una nueva solicitud limpia.
        Esto permite que usuarios que salieron del canal puedan volver a solicitar.

        Args:
            user_id: ID del usuario que solicita
            from_chat_id: ID del canal desde donde se solicita

        Returns:
            Tuple[bool, str, Optional[FreeChannelRequest]]:
                - bool: True si nueva, False si duplicada
                - str: Mensaje descriptivo
                - Optional[FreeChannelRequest]: Solicitud creada o existente
        """
        # Verificar si ya tiene solicitud pendiente RECIENTE (últimos 5 minutos)
        # Esto previene spam pero permite reintentos después de salir del canal
        recent_cutoff = datetime.utcnow() - timedelta(minutes=Config.FREE_REQUEST_SPAM_WINDOW_MINUTES)

        result = await self.session.execute(
            select(FreeChannelRequest).where(
                FreeChannelRequest.user_id == user_id,
                FreeChannelRequest.processed == False,
                FreeChannelRequest.request_date >= recent_cutoff
            ).order_by(FreeChannelRequest.request_date.desc())
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(
                f"ℹ️ Usuario {user_id} ya tiene solicitud Free reciente "
                f"(hace {existing.minutes_since_request()} min)"
            )
            return False, "Ya existe solicitud pendiente", existing

        # ESTRATEGIA DE LIMPIEZA: Eliminar TODAS las solicitudes antiguas del usuario
        #
        # RAZÓN: Garantizar un estado limpio cuando el usuario vuelve a solicitar.
        # Este enfoque se implementa porque:
        #
        # 1. CASOS DE USO LEGÍTIMOS:
        #    - Usuario salió del canal Free y quiere volver a entrar
        #    - Usuario tuvo una solicitud antigua que nunca procesó
        #    - Usuario quiere "resetear" su solicitud después de mucho tiempo
        #
        # 2. PREVENCIÓN DE INCONSISTENCIAS:
        #    - Evita tener múltiples solicitudes del mismo usuario en BD
        #    - Evita confusión sobre cuál solicitud es la "actual"
        #    - Simplifica la lógica de procesamiento (siempre hay máximo 1 solicitud)
        #
        # 3. TRADE-OFFS CONSIDERADOS:
        #    - ⚠️ RIESGO: Si falla la creación de nueva solicitud, se pierden datos antiguos
        #    - ✅ MITIGACIÓN: La ventana anti-spam (5 min) evita pérdida de datos recientes
        #    - ✅ BENEFICIO: Estado consistente, sin duplicados, fácil de razonar
        #
        # 4. ALTERNATIVAS DESCARTADAS:
        #    - Soft delete: Aumenta complejidad sin beneficio claro
        #    - Mantener historial: No es requerido para el caso de uso actual
        #    - Eliminar solo después de crear: Más transacciones, más complejo
        #
        # CONCLUSIÓN: La limpieza total es intencional y apropiada para este caso de uso.
        delete_result = await self.session.execute(
            delete(FreeChannelRequest).where(
                FreeChannelRequest.user_id == user_id
            )
        )
        deleted_count = delete_result.rowcount

        if deleted_count > 0:
            logger.info(
                f"🧹 Limpiadas {deleted_count} solicitud(es) antigua(s) de user {user_id}"
            )

        # Crear nueva solicitud limpia
        request = FreeChannelRequest(
            user_id=user_id,
            request_date=datetime.utcnow(),
            processed=False
        )

        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)

        logger.info(f"✅ Solicitud Free creada desde ChatJoinRequest: user {user_id}")

        return True, "Solicitud creada exitosamente", request

    async def process_free_queue(self, wait_time_minutes: int) -> List[FreeChannelRequest]:
        """
        Procesa la cola de solicitudes Free que cumplieron el tiempo de espera.

        Esta función se ejecuta periódicamente en background.

        Args:
            wait_time_minutes: Tiempo mínimo de espera requerido

        Returns:
            Lista de solicitudes procesadas
        """
        # Calcular timestamp límite
        cutoff_time = datetime.utcnow() - timedelta(minutes=wait_time_minutes)

        # Buscar solicitudes listas para procesar
        result = await self.session.execute(
            select(FreeChannelRequest).where(
                FreeChannelRequest.processed == False,
                FreeChannelRequest.request_date <= cutoff_time
            ).order_by(FreeChannelRequest.request_date.asc())
        )
        ready_requests = result.scalars().all()

        if not ready_requests:
            return []

        # Marcar como procesadas
        for request in ready_requests:
            request.processed = True
            request.processed_at = datetime.utcnow()

        await self.session.commit()

        logger.info(f"✅ {len(ready_requests)} solicitud(es) Free procesadas")

        return list(ready_requests)

    async def cleanup_old_free_requests(self, days_old: int = 30) -> int:
        """
        Elimina solicitudes Free antiguas (ya procesadas).

        Args:
            days_old: Eliminar solicitudes procesadas hace más de N días

        Returns:
            Cantidad de solicitudes eliminadas
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        result = await self.session.execute(
            delete(FreeChannelRequest).where(
                FreeChannelRequest.processed == True,
                FreeChannelRequest.processed_at < cutoff_date
            )
        )

        deleted_count = result.rowcount
        await self.session.commit()

        if deleted_count > 0:
            logger.info(f"🗑️ {deleted_count} solicitud(es) Free antiguas eliminadas")

        return deleted_count

    async def approve_ready_free_requests(
        self,
        wait_time_minutes: int,
        free_channel_id: str
    ) -> Tuple[int, int]:
        """
        Aprueba solicitudes Free que cumplieron tiempo de espera.

        Usa approve_chat_join_request() de Telegram API en lugar de invite links.
        Este es el método moderno recomendado por Telegram.

        Args:
            wait_time_minutes: Tiempo mínimo de espera requerido
            free_channel_id: ID del canal Free

        Returns:
            Tuple[int, int]: (success_count, error_count)
        """
        # Calcular timestamp límite
        cutoff_time = datetime.utcnow() - timedelta(minutes=wait_time_minutes)

        # Buscar solicitudes listas para aprobar
        result = await self.session.execute(
            select(FreeChannelRequest).where(
                FreeChannelRequest.processed == False,
                FreeChannelRequest.request_date <= cutoff_time
            ).order_by(FreeChannelRequest.request_date.asc())
        )
        ready_requests = result.scalars().all()

        if not ready_requests:
            logger.debug("✓ No hay solicitudes Free listas para aprobar")
            return 0, 0

        success_count = 0
        error_count = 0

        # Obtener info del canal una vez (evita N+1 queries)
        try:
            channel_info = await self.bot.get_chat(free_channel_id)
            channel_name = channel_info.title or "Canal Free"
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener info del canal Free: {e}")
            channel_name = "Canal Free"

        # Aprobar cada solicitud usando Telegram API
        for request in ready_requests:
            try:
                # 1. Aprobar ChatJoinRequest directamente
                await self.bot.approve_chat_join_request(
                    chat_id=free_channel_id,
                    user_id=request.user_id
                )

                # 2. Crear invite link personalizado (1 uso, 24h)
                invite_link = await self.create_invite_link(
                    channel_id=free_channel_id,
                    user_id=request.user_id,
                    expire_hours=24
                )

                # 3. Enviar mensaje de confirmación al usuario
                try:
                    confirmation_message = (
                        f"🎉 <b>¡Acceso Free Aprobado!</b>\n\n"
                        f"Tu solicitud ha sido aprobada exitosamente.\n\n"
                        f"📺 Canal: <b>{channel_name}</b>\n\n"
                        f"👇 <b>Haz click aquí para ingresar:</b>\n"
                        f"{invite_link.invite_link}\n\n"
                        f"⚠️ <b>Importante:</b>\n"
                        f"• El link expira en 24 horas\n"
                        f"• Solo puedes usarlo 1 vez\n"
                        f"• No lo compartas con otros\n\n"
                        f"¡Disfruta del contenido! 🎯"
                    )

                    await self.bot.send_message(
                        chat_id=request.user_id,
                        text=confirmation_message,
                        parse_mode="HTML"
                    )

                    logger.info(
                        f"✅ Confirmación enviada a user {request.user_id} con invite link"
                    )

                except Exception as notify_error:
                    # Distinguir entre usuario que bloqueó el bot vs otros errores
                    error_type = type(notify_error).__name__
                    if "Forbidden" in error_type or "blocked" in str(notify_error).lower():
                        logger.warning(
                            f"⚠️ Usuario {request.user_id} bloqueó el bot, no se envió confirmación"
                        )
                    else:
                        logger.error(
                            f"❌ Error inesperado enviando confirmación a {request.user_id}: {notify_error}"
                        )
                    # No falla la aprobación si el mensaje no se envía

                # 4. Marcar como procesada
                request.processed = True
                request.processed_at = datetime.utcnow()

                success_count += 1
                logger.info(f"✅ Solicitud Free aprobada: user {request.user_id}")

            except Exception as e:
                error_count += 1
                logger.error(
                    f"❌ Error aprobando solicitud de user {request.user_id}: {e}"
                )

        # Commit todos los cambios
        await self.session.commit()

        logger.info(
            f"📊 Procesamiento Free completado: {success_count} aprobadas, "
            f"{error_count} errores"
        )

        return success_count, error_count

    # ===== INVITE LINKS =====

    async def create_invite_link(
        self,
        channel_id: str,
        user_id: int,
        expire_hours: int = 1
    ) -> ChatInviteLink:
        """
        Crea un invite link único para un usuario.

        El link:
        - Es de un solo uso (member_limit=1)
        - Expira después de expire_hours
        - Es específico para el usuario (se puede trackear)

        Args:
            channel_id: ID del canal (ej: "-1001234567890")
            user_id: ID del usuario
            expire_hours: Horas hasta que expira el link

        Returns:
            ChatInviteLink: Link de invitación creado

        Raises:
            TelegramAPIError: Si el bot no tiene permisos en el canal
        """
        expire_date = datetime.utcnow() + timedelta(hours=expire_hours)

        invite_link = await self.bot.create_chat_invite_link(
            chat_id=channel_id,
            name=f"User {user_id}",
            expire_date=expire_date,
            member_limit=1  # Solo 1 persona puede usar este link
        )

        logger.info(
            f"🔗 Invite link creado para user {user_id}: "
            f"{invite_link.invite_link[:30]}..."
        )

        return invite_link
