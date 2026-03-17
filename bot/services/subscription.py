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
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot
from aiogram.types import ChatInviteLink
from sqlalchemy import select, delete, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import Config
from bot.database.models import (
    InvitationToken,
    VIPSubscriber,
    FreeChannelRequest,
    BotConfig,
    User,
    UserInterest,
    UserRoleChangeLog
)
from bot.services.container import ServiceContainer
from bot.database.enums import UserRole, RoleChangeReason

logger = logging.getLogger(__name__)


def _mask_token(token: str) -> str:
    """Enmascara un token mostrando solo los primeros 4 caracteres.

    Args:
        token: Token completo a enmascarar

    Returns:
        Token enmascarado (ej: "abcd****")
    """
    if not token or len(token) < 4:
        return "****"
    return f"{token[:4]}****"


def _mask_user_id(user_id: int) -> str:
    """Enmascara un user ID mostrando solo primeros y últimos 2 dígitos.

    Args:
        user_id: ID de usuario de Telegram

    Returns:
        ID enmascarado (ej: "12****89")
    """
    user_str = str(user_id)
    if len(user_str) <= 4:
        return "****"
    return f"{user_str[:2]}****{user_str[-2:]}"


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
            f"✅ Token VIP generado: {_mask_token(token.token)} "
            f"(válido por {duration_hours}h, plan_id: {plan_id}, generado por admin_id={generated_by})"
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

        ATÓMICO: Usa UPDATE con WHERE y rowcount check para prevenir
        race conditions (C-001). Múltiples requests concurrentes resultan
        en solo un canje exitoso.

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
        # ATOMIC UPDATE: Marcar token como usado SOLO si no está usado y no expiró
        # El rowcount indica si el UPDATE afectó alguna fila
        result = await self.session.execute(
            update(InvitationToken)
            .where(
                InvitationToken.token == token_str,
                InvitationToken.used == False,
                InvitationToken.expires_at > datetime.utcnow()
            )
            .values(
                used=True,
                used_by=user_id,
                used_at=datetime.utcnow()
            )
        )

        if result.rowcount == 0:
            # Token ya fue usado, expiró, o no existe
            # Esto previene race conditions: solo el primer UPDATE exitoso pasa
            logger.warning(
                f"⚠️ Token {_mask_token(token_str)} race condition o inválido "
                f"para user {_mask_user_id(user_id)}"
            )
            return False, "❌ Token inválido, expirado o ya fue usado", None

        # Token marcado como usado exitosamente - obtener datos para la suscripción
        token_result = await self.session.execute(
            select(InvitationToken).where(InvitationToken.token == token_str)
        )
        token = token_result.scalar_one()

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

            # Check if subscription was expired (needs unban)
            was_expired = existing_subscriber.is_expired() or existing_subscriber.status == "expired"

            # Si ya expiró, partir desde ahora
            if existing_subscriber.is_expired():
                existing_subscriber.expiry_date = datetime.utcnow() + extension
            else:
                # Si aún está activo, extender desde la fecha actual de expiración
                existing_subscriber.expiry_date += extension

            existing_subscriber.status = "active"

            # Unban from VIP channel if subscription was expired
            if was_expired:
                from bot.services.channel import ChannelService
                channel_service = ChannelService(self.session, self.bot)
                vip_channel_id = await channel_service.get_vip_channel_id()
                if vip_channel_id:
                    await self.unban_from_vip_channel(user_id, vip_channel_id)

            # No commit - dejar que el handler maneje la transacción

            logger.info(
                f"✅ Suscripción VIP extendida: user {_mask_user_id(user_id)} "
                f"(nueva expiración: {existing_subscriber.expiry_date}, was_expired={was_expired})"
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
            f"✅ Nuevo suscriptor VIP: user {_mask_user_id(user_id)} "
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

    async def get_vip_subscriber_with_relations(
        self,
        user_id: int,
        load_user: bool = True,
        load_token: bool = True
    ) -> Optional[VIPSubscriber]:
        """
        Obtiene el suscriptor VIP con relaciones eager loaded.

        Use este método cuando necesite acceder a:
        - subscriber.user (User model)
        - subscriber.token (InvitationToken)
        - subscriber.token.plan (SubscriptionPlan)

        Args:
            user_id: ID del usuario
            load_user: Cargar relación user (default: True)
            load_token: Cargar relación token y plan (default: True)

        Returns:
            VIPSubscriber con relaciones cargadas, None si no existe

        Example:
            subscriber = await service.get_vip_subscriber_with_relations(123)
            print(subscriber.user.full_name)  # No N+1 query
            print(subscriber.token.plan.name)  # No N+1 query
        """
        query = select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)

        # Aplicar eager loading según parámetros
        if load_user:
            query = query.options(selectinload(VIPSubscriber.user))
        if load_token:
            query = query.options(
                selectinload(VIPSubscriber.token).selectinload(InvitationToken.plan)
            )

        result = await self.session.execute(query)
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

        Phase 13: Inicializa vip_entry_stage=1 para nuevos suscriptores,
        iniciando el flujo ritualizado de entrada en 3 etapas.

        Args:
            user_id: ID del usuario que activa
            token_id: ID del token a usar
            duration_hours: Duración de la suscripción en horas

        Returns:
            VIPSubscriber: Suscriptor creado o actualizado

        Raises:
            ValueError: Si el usuario ya es VIP o token inválido
        """
        # Calculate expiry
        expiry_date = datetime.utcnow() + timedelta(hours=duration_hours)

        # Check if subscriber already exists (renewal)
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.user_id == user_id
            )
        )
        existing_subscriber = result.scalar_one_or_none()

        if existing_subscriber:
            # Renew existing subscription
            extension = timedelta(hours=duration_hours)

            # Check if subscription was expired (needs unban)
            was_expired = existing_subscriber.is_expired() or existing_subscriber.status == "expired"

            # Si ya expiró, partir desde ahora
            if existing_subscriber.is_expired():
                existing_subscriber.expiry_date = datetime.utcnow() + extension
            else:
                # Si aún está activo, extender desde la fecha actual de expiración
                existing_subscriber.expiry_date += extension

            existing_subscriber.status = "active"
            existing_subscriber.token_id = token_id

            # Phase 13: Restart ritual ONLY if subscription was expired/kicked
            # This ensures re-entering users get a fresh invite link via the ritual
            # Users extending active subscriptions keep their current access (stage=None)
            if was_expired:
                existing_subscriber.vip_entry_stage = 1  # Restart ritual for re-entry
                logger.info(f"🔄 Ritual restarted for expired user {_mask_user_id(user_id)}")

            # Unban from VIP channel if subscription was expired
            if was_expired:
                from bot.services.channel import ChannelService
                channel_service = ChannelService(self.session, self.bot)
                vip_channel_id = await channel_service.get_vip_channel_id()
                if vip_channel_id:
                    await self.unban_from_vip_channel(user_id, vip_channel_id)

            subscriber = existing_subscriber
            logger.info(
                f"🔄 Suscripción VIP renovada para user {_mask_user_id(user_id)} "
                f"(stage={subscriber.vip_entry_stage}, was_expired={was_expired})"
            )
        else:
            # Create new subscription with vip_entry_stage=1
            subscriber = VIPSubscriber(
                user_id=user_id,
                token_id=token_id,
                join_date=datetime.utcnow(),
                expiry_date=expiry_date,
                status="active",
                vip_entry_stage=1  # Phase 13: Start ritual at stage 1
            )
            self.session.add(subscriber)
            logger.info(
                f"✅ Nueva suscripción VIP creada para user {_mask_user_id(user_id)} (stage=1)"
            )

        return subscriber

    async def expire_vip_subscribers(self, container: Optional[ServiceContainer] = None) -> int:
        """
        Marca como expirados los suscriptores VIP cuya fecha pasó.

        Si se proporciona container, también loguea cambios de rol.

        Esta función se ejecuta periódicamente en background.

        Args:
            container: ServiceContainer opcional para logging de cambios de rol

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
            logger.info(f"⏱️ VIP expirado: user {_mask_user_id(subscriber.user_id)}")

            # Phase 13: Cancel entry flow if incomplete (stages 1 or 2)
            if container and subscriber.vip_entry_stage in (1, 2):
                try:
                    await container.vip_entry.cancel_entry_on_expiry(
                        user_id=subscriber.user_id
                    )
                    logger.info(
                        f"🚫 Cancelled VIP entry flow for user {_mask_user_id(subscriber.user_id)} "
                        f"(subscription expired at stage {subscriber.vip_entry_stage})"
                    )
                except Exception as e:
                    logger.error(
                        f"Error cancelling VIP entry flow for user {_mask_user_id(subscriber.user_id)}: {e}"
                    )

            # Log role change if container provided
            if container and container.role_change:
                try:
                    await container.role_change.log_role_change(
                        user_id=subscriber.user_id,
                        new_role=UserRole.FREE,
                        changed_by=0,  # SYSTEM
                        reason=RoleChangeReason.VIP_EXPIRED,
                        change_source="SYSTEM",
                        previous_role=UserRole.VIP,
                        change_metadata={
                            "vip_subscriber_id": subscriber.id,
                            "expired_at": datetime.utcnow().isoformat(),
                            "original_expiry": subscriber.expiry_date.isoformat() if subscriber.expiry_date else None
                        }
                    )
                    logger.debug(f"✅ Role change logged for expired VIP user {_mask_user_id(subscriber.user_id)}")
                except Exception as e:
                    logger.error(f"Error logging role change for user {_mask_user_id(subscriber.user_id)}: {e}")

        if count > 0:
            await self.session.commit()
            logger.info(f"✅ {count} suscriptor(es) VIP marcados como expirados")

        return count

    async def kick_expired_vip_from_channel(self, channel_id: str) -> Tuple[int, int, int]:
        """
        Expulsa suscriptores expirados del canal VIP con ban permanente.

        Esta función se ejecuta después de expire_vip_subscribers()
        en el background task.

        El ban es PERMANENTE - el usuario permanece baneado hasta que
        active un nuevo token (cuando se llama a unban_from_vip_channel).

        Usa kicked_from_channel_at para trackear progreso y permitir reintentos.

        Args:
            channel_id: ID del canal VIP (ej: "-1001234567890")

        Returns:
            Tuple[int, int, int]: (kicked_count, already_kicked_count, failed_count)
        """
        # Buscar suscriptores expirados que aún no han sido expulsados
        result = await self.session.execute(
            select(VIPSubscriber)
            .where(
                VIPSubscriber.status == "expired",
                VIPSubscriber.kicked_from_channel_at.is_(None)  # Not yet kicked
            )
            .order_by(VIPSubscriber.expiry_date)
            .limit(100)  # Batch processing
        )
        expired_subscribers = result.scalars().all()

        if not expired_subscribers:
            return (0, 0, 0)

        kicked_count = 0
        failed_count = 0

        for subscriber in expired_subscribers:
            try:
                # Intentar banear del canal
                await self.bot.ban_chat_member(
                    chat_id=channel_id,
                    user_id=subscriber.user_id
                )

                # Marcar como expulsado exitosamente
                subscriber.kicked_from_channel_at = datetime.utcnow()
                kicked_count += 1

                logger.info(f"🚫 Usuario baneado de VIP (suscripción expirada): {_mask_user_id(subscriber.user_id)}")

            except Exception as e:
                error_str = str(e).lower()

                # Verificar si el usuario ya no está en el canal (éxito parcial)
                if "user not found" in error_str or "user is not a member" in error_str:
                    # Usuario ya no está en el canal - marcar como hecho
                    subscriber.kicked_from_channel_at = datetime.utcnow()
                    logger.info(f"✅ Usuario {_mask_user_id(subscriber.user_id)} ya no estaba en el canal")
                else:
                    # Error real - se reintentará en la próxima ejecución
                    failed_count += 1
                    logger.warning(
                        f"⚠️ No se pudo banear a user {_mask_user_id(subscriber.user_id)}: {e}"
                    )

        # Flush para persistir los cambios de kicked_from_channel_at
        await self.session.flush()

        # Contar cuántos ya fueron expulsados en total (para reporting)
        already_kicked_result = await self.session.execute(
            select(func.count(VIPSubscriber.id))
            .where(
                VIPSubscriber.status == "expired",
                VIPSubscriber.kicked_from_channel_at.isnot(None)
            )
        )
        total_kicked = already_kicked_result.scalar_one()

        if kicked_count > 0 or failed_count > 0:
            logger.info(
                f"✅ VIP kick results: {kicked_count} newly kicked, "
                f"{total_kicked - kicked_count} already out, {failed_count} failed (will retry)"
            )

        return (kicked_count, total_kicked - kicked_count, failed_count)

    async def unban_from_vip_channel(
        self,
        user_id: int,
        channel_id: str
    ) -> bool:
        """
        Desbanea a un usuario del canal VIP al renovar su suscripción.

        Se llama cuando un usuario expulsado activa un nuevo token,
        permitiéndole reingresar al canal con el nuevo enlace.

        Args:
            user_id: ID del usuario a desbanear
            channel_id: ID del canal VIP

        Returns:
            True si se desbaneó correctamente, False si hubo error
        """
        try:
            await self.bot.unban_chat_member(
                chat_id=channel_id,
                user_id=user_id,
                only_if_banned=True  # Solo desbanear si está baneado
            )
            logger.info(f"✅ Usuario desbaneado de VIP (renovación): {_mask_user_id(user_id)}")
            return True
        except Exception as e:
            logger.warning(
                f"⚠️ No se pudo desbanear a user {_mask_user_id(user_id)}: {e}"
            )
            return False

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

    async def get_all_vip_subscribers_with_users(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        load_tokens: bool = False
    ) -> List[VIPSubscriber]:
        """
        Obtiene lista de suscriptores VIP con eager loading de usuarios.

        Use este método cuando necesite acceder a subscriber.user
        para evitar N+1 queries en loops.

        Args:
            status: Filtrar por status ("active", "expired", None=todos)
            limit: Máximo de resultados (default: 100)
            offset: Offset para paginación (default: 0)
            load_tokens: También cargar tokens y planes (default: False)

        Returns:
            Lista de suscriptores con usuarios cargados

        Example:
            subscribers = await service.get_all_vip_subscribers_with_users()
            for sub in subscribers:
                print(sub.user.full_name)  # No N+1 query
        """
        query = select(VIPSubscriber).order_by(
            VIPSubscriber.expiry_date.desc()
        )

        # Aplicar eager loading
        query = query.options(selectinload(VIPSubscriber.user))

        if load_tokens:
            query = query.options(
                selectinload(VIPSubscriber.token).selectinload(InvitationToken.plan)
            )

        if status:
            query = query.where(VIPSubscriber.status == status)

        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ===== CANAL FREE =====

    async def create_free_request(
        self, user_id: int
    ) -> Tuple[bool, str, Optional[FreeChannelRequest]]:
        """
        Crea una solicitud de acceso al canal Free con protección contra race conditions.

        ATÓMICO: Usa INSERT con unique constraint y IntegrityError handling (C-002).
        SQLite-compatible: no requiere SELECT FOR UPDATE.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, str, Optional[FreeChannelRequest]]:
                - bool: True si éxito, False si ya existe solicitud pendiente
                - str: Mensaje descriptivo
                - Optional[FreeChannelRequest]: Solicitud creada o None si error
        """
        # Intentar INSERT directo - la base de datos fuerza unicidad via constraint
        try:
            request = FreeChannelRequest(
                user_id=user_id,
                request_date=datetime.utcnow(),
                processed=False,
                pending_request=True  # Para el unique constraint
            )
            self.session.add(request)
            await self.session.flush()  # Forzar el INSERT sin commit completo

            logger.info(f"✅ Solicitud Free creada: user {_mask_user_id(user_id)}")
            return True, "✅ Solicitud creada exitosamente", request

        except IntegrityError:
            # Violación de constraint único - usuario ya tiene solicitud pendiente
            # SQLite requiere rollback después de IntegrityError
            await self.session.rollback()

            # Obtener solicitud existente para mensaje detallado
            result = await self.session.execute(
                select(FreeChannelRequest).where(
                    FreeChannelRequest.user_id == user_id,
                    FreeChannelRequest.processed == False
                ).order_by(FreeChannelRequest.request_date.desc())
            )
            existing = result.scalar_one_or_none()

            if existing:
                wait_msg = f" (tiempo en cola: {existing.minutes_since_request()} min)"
                logger.info(
                    f"⚠️ Usuario {_mask_user_id(user_id)} intentó crear solicitud duplicada{wait_msg}"
                )
                return (
                    False,
                    f"❌ Ya tienes una solicitud pendiente{wait_msg}",
                    existing
                )

            logger.warning(
                f"⚠️ IntegrityError en solicitud Free para user {_mask_user_id(user_id)} "
                f"pero no se encontró solicitud existente"
            )
            return False, "❌ Ya tienes una solicitud pendiente", None

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
        from_chat_id: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[FreeChannelRequest]]:
        """
        Crea solicitud Free desde ChatJoinRequest de Telegram.

        Limpia solicitudes antiguas y crea una nueva solicitud limpia.
        Esto permite que usuarios que salieron del canal puedan volver a solicitar.

        Args:
            user_id: ID del usuario que solicita
            from_chat_id: ID del canal desde donde se solicita
            username: Username de Telegram (opcional)
            first_name: Nombre del usuario (opcional)
            last_name: Apellido del usuario (opcional)

        Returns:
            Tuple[bool, str, Optional[FreeChannelRequest]]:
                - bool: True si nueva, False si duplicada
                - str: Mensaje descriptivo
                - Optional[FreeChannelRequest]: Solicitud creada o existente
        """
        # ===== CREAR/VERIFICAR USUARIO PRIMERO =====
        # El usuario debe existir antes de crear la solicitud (FK constraint)
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Crear usuario nuevo con datos disponibles
            user = User(
                user_id=user_id,
                username=username,
                first_name=first_name or "Usuario",
                last_name=last_name,
                role=UserRole.FREE
            )
            self.session.add(user)
            await self.session.flush()  # Flush para crear el usuario sin commit aún
            logger.info(f"✅ Usuario creado desde ChatJoinRequest: {_mask_user_id(user_id)}")
        else:
            # Actualizar datos del usuario si han cambiado
            updated = False
            if username is not None and user.username != username:
                user.username = username
                updated = True
            if first_name is not None and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name is not None and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                await self.session.flush()
                logger.debug(f"📝 Datos de usuario actualizados: {_mask_user_id(user_id)}")

        # ===== BUSCAR SOLICITUD EXISTENTE =====
        # Buscar CUALQUIER solicitud pendiente del usuario (no solo recientes)
        result = await self.session.execute(
            select(FreeChannelRequest).where(
                FreeChannelRequest.user_id == user_id,
                FreeChannelRequest.processed == False
            ).order_by(FreeChannelRequest.request_date.desc())
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Verificar si la solicitud ya cumplió el tiempo de espera
            wait_time = Config.DEFAULT_WAIT_TIME_MINUTES
            minutes_since = existing.minutes_since_request()

            if minutes_since >= wait_time:
                # La solicitud ya cumplió el tiempo pero no fue procesada
                # (probablemente la ChatJoinRequest de Telegram expiró)
                # Eliminarla y crear una nueva para que el usuario pueda reintentar
                logger.info(
                    f"🔄 Solicitud Free de user {_mask_user_id(user_id)} ya cumplió tiempo "
                    f"({minutes_since} min >= {wait_time} min) pero no fue aprobada. "
                    f"Creando nueva solicitud..."
                )
                await self.session.delete(existing)
                await self.session.commit()
                # Continuar con la creación de nueva solicitud abajo
            else:
                # Solicitud aún dentro del tiempo de espera - verificar anti-spam
                spam_cutoff = datetime.utcnow() - timedelta(minutes=Config.FREE_REQUEST_SPAM_WINDOW_MINUTES)

                if existing.request_date >= spam_cutoff:
                    # Solicitud muy reciente - rechazar duplicado
                    logger.info(
                        f"ℹ️ Usuario {_mask_user_id(user_id)} ya tiene solicitud Free reciente "
                        f"(hace {minutes_since} min, quedan {wait_time - minutes_since} min)"
                    )
                    return False, "Ya existe solicitud pendiente", existing
                else:
                    # Solicitud antigua pero aún no cumple tiempo de espera
                    # Actualizar el request_date para "reanimar" la solicitud
                    # (el usuario reactivó su solicitud antes de que expirara)
                    existing.request_date = datetime.utcnow()
                    await self.session.commit()
                    await self.session.refresh(existing)
                    logger.info(
                        f"🔄 Solicitud Free reactivada para user {_mask_user_id(user_id)} "
                        f"(tiempo reseteado, protegida de expiración)"
                    )
                    return False, "Solicitud reactivada", existing

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
                f"🧹 Limpiadas {deleted_count} solicitud(es) antigua(s) de user {_mask_user_id(user_id)}"
            )

        # Crear nueva solicitud limpia
        request = FreeChannelRequest(
            user_id=user_id,
            request_date=datetime.utcnow(),
            processed=False,
            pending_request=True  # Para el unique constraint
        )

        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)

        logger.info(f"✅ Solicitud Free creada desde ChatJoinRequest: user {_mask_user_id(user_id)}")

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
            request.pending_request = False  # Remove from unique constraint

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

        Usa UPDATE atómico con rowcount check para prevenir race conditions.
        SQLite-compatible (no usa SKIP LOCKED).

        Flujo seguro:
        1. SELECT para obtener candidatos (con LIMIT para batching)
        2. UPDATE atómico marca solicitudes como procesadas
        3. Commit para liberar locks
        4. Llamadas a Telegram API (fuera de transacción)

        Args:
            wait_time_minutes: Tiempo mínimo de espera requerido
            free_channel_id: ID del canal Free

        Returns:
            Tuple[int, int]: (success_count, error_count)
        """
        # Calcular timestamp límite
        cutoff_time = datetime.utcnow() - timedelta(minutes=wait_time_minutes)

        # Step 1: Obtener IDs de solicitudes candidatas (con LIMIT para batching)
        select_result = await self.session.execute(
            select(FreeChannelRequest.id, FreeChannelRequest.user_id)
            .where(
                FreeChannelRequest.processed == False,
                FreeChannelRequest.request_date <= cutoff_time
            )
            .order_by(FreeChannelRequest.request_date)
            .limit(100)  # Batch processing para evitar memory issues
        )
        candidates = select_result.all()  # List of (id, user_id) tuples

        if not candidates:
            logger.debug("✓ No hay solicitudes Free listas para aprobar")
            return 0, 0

        # Step 2: Atomically mark estas solicitudes específicas como procesadas
        candidate_ids = [row[0] for row in candidates]
        user_id_map = {row[0]: row[1] for row in candidates}

        update_result = await self.session.execute(
            update(FreeChannelRequest)
            .where(
                FreeChannelRequest.id.in_(candidate_ids),
                FreeChannelRequest.processed == False  # Still unprocessed (race check)
            )
            .values(
                processed=True,
                processed_at=datetime.utcnow(),
                pending_request=False  # Remove from unique constraint
            )
        )

        # Verificar si hubo race condition (otro worker procesó algunas)
        if update_result.rowcount != len(candidate_ids):
            logger.warning(
                f"⚠️ Race condition detectado: esperado {len(candidate_ids)} updates, "
                f"obtenido {update_result.rowcount}. Algunas solicitudes fueron procesadas por otro worker."
            )

        # Commit para liberar locks antes de llamadas API
        await self.session.commit()

        logger.info(f"🔒 Claimed {update_result.rowcount} solicitudes para procesamiento")

        # Step 3: Procesar solicitudes reclamadas (no DB locks held during API calls)
        success_count = 0
        error_count = 0

        # Obtener info del canal una vez (evita N+1 queries)
        try:
            channel_info = await self.bot.get_chat(free_channel_id)
            channel_name = channel_info.title or "Canal Free"
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener info del canal Free: {e}")
            channel_name = "Canal Free"

        # Procesar solo las solicitudes que fueron efectivamente reclamadas
        # Re-query para obtener las que realmente fueron marcadas por este worker
        claimed_result = await self.session.execute(
            select(FreeChannelRequest.id, FreeChannelRequest.user_id)
            .where(
                FreeChannelRequest.id.in_(candidate_ids),
                FreeChannelRequest.processed == True,
                FreeChannelRequest.pending_request == False  # Recién procesadas
            )
        )
        claimed_requests = claimed_result.all()

        for request_id, user_id in claimed_requests:
            try:
                # 1. Aprobar ChatJoinRequest directamente
                await self.bot.approve_chat_join_request(
                    chat_id=free_channel_id,
                    user_id=user_id
                )

                # 2. Obtener enlace del canal
                from bot.services.message.user_flows import UserFlowMessages
                from bot.services.channel import ChannelService

                channel_service = ChannelService(self.session, self.bot)
                channel_link = await channel_service.get_or_create_free_channel_invite_link()

                if not channel_link:
                    config_result = await self.session.execute(
                        select(BotConfig).where(BotConfig.id == 1)
                    )
                    bot_config = config_result.scalar_one_or_none()

                    if bot_config and bot_config.free_channel_invite_link:
                        channel_link = bot_config.free_channel_invite_link
                    elif free_channel_id.startswith('@'):
                        channel_link = f"t.me/{free_channel_id[1:]}"
                        logger.warning("⚠️ Usando fallback t.me URL para canal público")

                # 3. Enviar mensaje de aprobación
                if channel_link:
                    try:
                        flows = UserFlowMessages()
                        approval_text, keyboard = flows.free_request_approved(
                            channel_name=channel_name,
                            channel_link=channel_link
                        )

                        await self.bot.send_message(
                            chat_id=user_id,
                            text=approval_text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )

                        logger.info(
                            f"✅ Aprobación enviada a user {_mask_user_id(user_id)} con enlace al canal"
                        )
                    except Exception as notify_error:
                        error_type = type(notify_error).__name__
                        if "Forbidden" in error_type or "blocked" in str(notify_error).lower():
                            logger.warning(
                                f"⚠️ Usuario {_mask_user_id(user_id)} bloqueó el bot"
                            )
                        else:
                            logger.error(
                                f"❌ Error enviando confirmación a {_mask_user_id(user_id)}: {notify_error}"
                            )

                success_count += 1
                logger.info(f"✅ Solicitud Free aprobada: user {_mask_user_id(user_id)}")

            except Exception as e:
                error_count += 1
                error_msg = str(e).lower()

                # Verificar si es error de solicitud expirada
                is_expired_error = any(
                    keyword in error_msg
                    for keyword in ["expired", "not found", "no pending", "request expired",
                                   "user_not_participant", "user_already_participant"]
                )

                if is_expired_error:
                    logger.warning(
                        f"⚠️ Solicitud de user {_mask_user_id(user_id)} expiró o fue cancelada. "
                        f"Ya marcada como procesada para evitar reintentos."
                    )
                else:
                    logger.error(
                        f"❌ Error aprobando solicitud de user {_mask_user_id(user_id)}: {e}"
                    )

        logger.info(
            f"📊 Procesamiento Free completado: {success_count} aprobadas, "
            f"{error_count} errores (batch: {len(candidates)}, claimed: {update_result.rowcount})"
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
            name=f"User {_mask_user_id(user_id)}",
            expire_date=expire_date,
            member_limit=1  # Solo 1 persona puede usar este link
        )

        logger.info(
            f"🔗 Invite link creado para user {_mask_user_id(user_id)}: "
            f"{invite_link.invite_link[:30]}..."
        )

        return invite_link

    # ===== USER DELETION =====

    # ===== BULK FREE REQUESTS MANAGEMENT =====

    async def get_pending_free_requests(
        self,
        limit: int = 100
    ) -> List[FreeChannelRequest]:
        """
        Obtiene todas las solicitudes Free pendientes.

        Args:
            limit: Máximo de solicitudes a retornar (default: 100)

        Returns:
            Lista de FreeChannelRequest pendientes, ordenadas por fecha (más antiguas primero)
        """
        result = await self.session.execute(
            select(FreeChannelRequest)
            .where(FreeChannelRequest.processed == False)
            .order_by(FreeChannelRequest.request_date.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_free_requests_count(self) -> int:
        """
        Obtiene la cantidad de solicitudes Free pendientes.

        Returns:
            int: Cantidad de solicitudes pendientes
        """
        result = await self.session.execute(
            select(func.count(FreeChannelRequest.id))
            .where(FreeChannelRequest.processed == False)
        )
        return result.scalar_one_or_none() or 0

    async def approve_all_free_requests(
        self,
        free_channel_id: str
    ) -> Tuple[int, int]:
        """
        Aprueba todas las solicitudes Free pendientes en lotes.

        Args:
            free_channel_id: ID del canal Free

        Returns:
            Tuple[int, int]: (success_count, error_count)
        """
        success_count = 0
        error_count = 0

        # Obtener info del canal una vez (evita N+1 queries)
        try:
            channel_info = await self.bot.get_chat(free_channel_id)
            channel_name = channel_info.title or "Canal Free"
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener info del canal Free: {e}")
            channel_name = "Canal Free"

        # Obtener enlace del canal (dinámicamente generado si no existe)
        from bot.services.message.user_flows import UserFlowMessages
        from bot.services.channel import ChannelService

        # Usar ChannelService para obtener o crear el enlace dinámicamente
        channel_service = ChannelService(self.session, self.bot)
        channel_link = await channel_service.get_or_create_free_channel_invite_link()

        if not channel_link:
            # Fallback: intentar obtener desde BotConfig (legacy) o construir URL pública
            config_result = await self.session.execute(
                select(BotConfig).where(BotConfig.id == 1)
            )
            bot_config = config_result.scalar_one_or_none()

            if bot_config and bot_config.free_channel_invite_link:
                channel_link = bot_config.free_channel_invite_link
            elif free_channel_id.startswith('@'):
                channel_link = f"t.me/{free_channel_id[1:]}"
                logger.warning("⚠️ Usando fallback t.me URL para canal público")
            else:
                channel_link = None
                logger.error("❌ No se pudo obtener ni crear enlace de invitación")

        while True:
            pending_requests = await self.get_pending_free_requests(limit=100)
            if not pending_requests:
                logger.debug("No hay más solicitudes Free pendientes para aprobar")
                break

            for request in pending_requests:
                try:
                    # Aprobar solicitud en Telegram
                    await self.bot.approve_chat_join_request(
                        chat_id=free_channel_id,
                        user_id=request.user_id
                    )

                    # Marcar como procesada
                    request.processed = True
                    request.processed_at = datetime.utcnow()
                    request.pending_request = False  # Remove from unique constraint

                    # Enviar mensaje de aprobación con Lucien's voice
                    if channel_link:
                        try:
                            flows = UserFlowMessages()
                            approval_text, keyboard = flows.free_request_approved(
                                channel_name=channel_name,
                                channel_link=channel_link
                            )

                            await self.bot.send_message(
                                chat_id=request.user_id,
                                text=approval_text,
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )

                            logger.info(
                                f"✅ Aprobación enviada a user {_mask_user_id(request.user_id)} con enlace al canal"
                            )
                        except Exception as notify_error:
                            # Distinguir entre usuario que bloqueó el bot vs otros errores
                            error_type = type(notify_error).__name__
                            if "Forbidden" in error_type or "blocked" in str(notify_error).lower():
                                logger.warning(
                                    f"⚠️ Usuario {_mask_user_id(request.user_id)} bloqueó el bot, no se envió confirmación"
                                )
                            else:
                                logger.warning(
                                    f"⚠️ No se pudo enviar confirmación a user {_mask_user_id(request.user_id)}: {notify_error}"
                                )

                    success_count += 1
                    logger.info(f"✅ Solicitud Free aprobada (bulk): user {_mask_user_id(request.user_id)}")

                except Exception as e:
                    error_count += 1
                    error_msg = str(e).lower()

                    # Verificar si es un error que indica que la solicitud ya no es válida
                    # (expirada, usuario ya en canal, etc.)
                    is_final_error = any(
                        keyword in error_msg
                        for keyword in ["expired", "not found", "no pending", "request expired", "user_not_participant", "user_already_participant"]
                    )

                    if is_final_error:
                        # Marcar como procesada para no volver a intentar
                        request.processed = True
                        request.processed_at = datetime.utcnow()
                        request.pending_request = False  # Remove from unique constraint
                        logger.warning(
                            f"⚠️ Solicitud de user {_mask_user_id(request.user_id)} no se pudo aprobar "
                            f"({e}). Marcada como procesada para evitar reintentos."
                        )
                    else:
                        logger.warning(
                            f"⚠️ Error aprobando solicitud de user {_mask_user_id(request.user_id)}: {e}"
                        )

            await self.session.commit()

        logger.info(
            f"📊 Aprobación masiva completada: {success_count} aprobadas, "
            f"{error_count} errores"
        )

        return success_count, error_count

    async def reject_all_free_requests(
        self,
        free_channel_id: str
    ) -> Tuple[int, int]:
        """
        Rechaza todas las solicitudes Free pendientes en lotes.

        Args:
            free_channel_id: ID del canal Free

        Returns:
            Tuple[int, int]: (success_count, error_count)
        """
        success_count = 0
        error_count = 0

        while True:
            pending_requests = await self.get_pending_free_requests(limit=100)
            if not pending_requests:
                logger.debug("No hay más solicitudes Free pendientes para rechazar")
                break

            for request in pending_requests:
                try:
                    # Rechazar solicitud en Telegram
                    await self.bot.decline_chat_join_request(
                        chat_id=free_channel_id,
                        user_id=request.user_id
                    )

                    # Marcar como procesada
                    request.processed = True
                    request.processed_at = datetime.utcnow()
                    request.pending_request = False  # Remove from unique constraint

                    success_count += 1
                    logger.info(f"🚫 Solicitud Free rechazada (bulk): user {_mask_user_id(request.user_id)}")

                except Exception as e:
                    error_count += 1
                    logger.warning(
                        f"⚠️ Error rechazando solicitud de user {_mask_user_id(request.user_id)}: {e}"
                    )

            await self.session.commit()

        logger.info(
            f"📊 Rechazo masivo completado: {success_count} rechazadas, "
            f"{error_count} errores"
        )

        return success_count, error_count

    async def delete_user_completely(
        self,
        user_id: int,
        deleted_by: int
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Elimina completamente un usuario y todas sus entidades relacionadas.

        Esta operación es irreversible y elimina:
        - UserInterest (intereses en paquetes)
        - UserRoleChangeLog (historial de cambios de rol)
        - FreeChannelRequest (solicitudes al canal Free)
        - VIPSubscriber (suscripción VIP y tokens relacionados)
        - InvitationToken (tokens generados o usados por el usuario)
        - User (el usuario mismo)

        Args:
            user_id: ID del usuario a eliminar
            deleted_by: ID del admin que realiza la eliminación

        Returns:
            Tuple[bool, str, Optional[User]]:
                - bool: True si éxito, False si error
                - str: Mensaje descriptivo
                - Optional[User]: Info del usuario eliminado (para notificación)
        """
        # Obtener info del usuario antes de eliminar
        result = await self.session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return False, "❌ Usuario no encontrado", None

        # Guardar info para retornar
        deleted_user_info = user

        try:
            # Eliminar en orden correcto para evitar FK constraint errors
            # 1. UserInterest (user_id FK)
            await self.session.execute(
                delete(UserInterest).where(UserInterest.user_id == user_id)
            )
            logger.debug(f"🗑️ Eliminados intereses de usuario {_mask_user_id(user_id)}")

            # 2. UserRoleChangeLog (user_id FK)
            await self.session.execute(
                delete(UserRoleChangeLog).where(UserRoleChangeLog.user_id == user_id)
            )
            logger.debug(f"🗑️ Eliminado historial de cambios de rol de usuario {_mask_user_id(user_id)}")

            # 3. FreeChannelRequest (user_id FK)
            await self.session.execute(
                delete(FreeChannelRequest).where(FreeChannelRequest.user_id == user_id)
            )
            logger.debug(f"🗑️ Eliminadas solicitudes Free de usuario {_mask_user_id(user_id)}")

            # 4. VIPSubscriber (user_id FK) - cascada a través de relación subscribers
            # Primero obtener los token_ids asociados para limpiar después
            result = await self.session.execute(
                select(VIPSubscriber.token_id).where(VIPSubscriber.user_id == user_id)
            )
            token_ids = result.scalars().all()

            await self.session.execute(
                delete(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
            )
            logger.debug(f"🗑️ Eliminada suscripción VIP de usuario {_mask_user_id(user_id)}")

            # 5. InvitationToken donde generated_by=user_id OR used_by=user_id
            await self.session.execute(
                delete(InvitationToken).where(
                    (InvitationToken.generated_by == user_id) |
                    (InvitationToken.used_by == user_id)
                )
            )
            logger.debug(f"🗑️ Eliminados tokens asociados a usuario {_mask_user_id(user_id)}")

            # 6. Finalmente, eliminar el usuario
            await self.session.execute(
                delete(User).where(User.user_id == user_id)
            )

            # Commit de la transacción
            await self.session.commit()

            logger.info(
                f"✅ Usuario {_mask_user_id(user_id)} eliminado completamente por admin {_mask_user_id(deleted_by)}"
            )

            return True, "✅ Usuario eliminado completamente", deleted_user_info

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Error eliminando usuario {_mask_user_id(user_id)}: {e}")
            # No exponer detalles del error interno al usuario
            return False, "❌ Error interno al eliminar usuario. Contacte al administrador.", None
