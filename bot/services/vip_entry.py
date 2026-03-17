"""
VIP Entry Service - Gestión de flujo ritualizado de entrada VIP.

Responsabilidades:
- Validación de etapa actual del usuario
- Avance de etapas (1 → 2 → 3 → NULL)
- Generación de token único para enlace de etapa 3
- Creación de enlace de invitación con validez de 24 horas
- Cancelación de flujo cuando suscripción expira

Phase 13: Ritualized VIP entry flow replacing immediate link delivery.
"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from aiogram import Bot
from aiogram.types import ChatInviteLink
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import VIPSubscriber, User
from bot.services.subscription import SubscriptionService, utc_now

logger = logging.getLogger(__name__)


class VIPEntryService:
    """
    Service para gestionar flujo ritualizado de entrada VIP.

    Flujo:
    1. Usuario activa token → vip_entry_stage=1
    2. Usuario pulsa "Continuar" → vip_entry_stage=2
    3. Usuario pulsa "Estoy listo" → vip_entry_stage=3 + token generado
    4. Usuario accede al canal → vip_entry_stage=NULL (completo)

    Expiración:
    - Si suscripción expira durante etapas 1-2:
      - Cancelar flujo (vip_entry_stage=NULL)
      - Remover usuario del canal (si ya se unió)
      - Bloquear continuación

    Métodos:
    - get_current_stage(): Obtiene etapa actual del usuario
    - advance_stage(): Avanza a siguiente etapa (validaciones)
    - generate_entry_token(): Genera token único para etapa 3
    - create_24h_invite_link(): Crea enlace de 24 horas
    - cancel_entry_on_expiry(): Cancela flujo por expiración
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
        self.subscription = SubscriptionService(session, bot)
        logger.debug("✅ VIPEntryService inicializado")

    # ===== STAGE VALIDATION =====

    async def get_current_stage(self, user_id: int) -> Optional[int]:
        """
        Obtiene la etapa actual del flujo VIP de entrada.

        Args:
            user_id: ID del usuario

        Returns:
            Etapa actual (1, 2, 3) o NULL si flujo completado/no iniciado
        """
        result = await self.session.execute(
            select(VIPSubscriber.vip_entry_stage).where(
                VIPSubscriber.user_id == user_id
            )
        )
        stage = result.scalar_one_or_none()
        return stage


    async def advance_stage(self, user_id: int, from_stage: int) -> Tuple[bool, str]:
        """
        Avanza a la siguiente etapa del flujo VIP con protección contra race conditions.

        Usa UPDATE atómico con cláusula WHERE condicional para prevenir
        condiciones de carrera donde múltiples requests intentan avanzar la etapa.

        Valida:
        - Suscripción no expirada
        - from_stage coincide con etapa actual en BD
        - Progresión secuencial (no saltos)

        Args:
            user_id: ID del usuario
            from_stage: Etapa actual esperada (para validación)

        Returns:
            Tuple de (success, message):
            - success: True si la etapa fue avanzada exitosamente
            - message: Mensaje de éxito o error detallado
        """
        # Validate stage progression logic first
        if from_stage not in (1, 2):
            return (False, f"No se puede avanzar desde la etapa {from_stage}")

        next_stage = from_stage + 1

        # Atomic UPDATE: only update if conditions match
        # This prevents race conditions where another request already advanced the stage
        result = await self.session.execute(
            update(VIPSubscriber)
            .where(
                VIPSubscriber.user_id == user_id,
                VIPSubscriber.vip_entry_stage == from_stage,  # Must match expected stage
                VIPSubscriber.expiry_date > utc_now(),  # Subscription not expired
                VIPSubscriber.status == "active"  # Subscription active
            )
            .values(vip_entry_stage=next_stage)
        )

        if result.rowcount == 0:
            # UPDATE failed - check why for better error message
            subscriber_result = await self.session.execute(
                select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
            )
            subscriber = subscriber_result.scalar_one_or_none()

            if not subscriber:
                return (False, "Suscripción VIP no encontrada")

            if subscriber.is_expired():
                return (False, "Tu suscripción VIP ha expirado")

            current = subscriber.vip_entry_stage or 0
            if current != from_stage:
                if current > from_stage:
                    return (False, f"Ya has avanzado a la etapa {current}")
                else:
                    return (False, f"Etapa incorrecta. Actual: {current}, Esperada: {from_stage}")

            return (False, "No se pudo avanzar la etapa")

        logger.info(f"User {user_id} VIP entry advanced: stage {from_stage} -> {next_stage}")
        return (True, f"Etapa {next_stage} desbloqueada")

    # ===== TOKEN GENERATION =====

    async def generate_entry_token(self, user_id: int) -> str:
        """
        Genera token único para enlace de invitación de etapa 3.

        El token:
        - Tiene 64 caracteres (token_urlsafe)
        - Es único (verifica duplicados)
        - Se almacena en vip_entry_token field
        - Se usa para validar enlace de un solo uso

        Args:
            user_id: ID del usuario

        Returns:
            Token generado (64 caracteres)

        Raises:
            RuntimeError: Si no se puede generar token único después de 10 intentos
        """
        max_attempts = 10

        for attempt in range(max_attempts):
            # Generate random token (64 characters from token_urlsafe(48))
            token = secrets.token_urlsafe(48)

            # Check uniqueness
            result = await self.session.execute(
                select(VIPSubscriber).where(VIPSubscriber.vip_entry_token == token)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                # Token is unique - store it
                subscriber_result = await self.session.execute(
                    select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
                )
                subscriber = subscriber_result.scalar_one_or_none()

                if subscriber:
                    subscriber.vip_entry_token = token
                    logger.info(f"✅ Entry token generated for user {user_id}")
                    return token
                else:
                    logger.error(f"❌ VIPSubscriber not found for user {user_id}")
                    raise RuntimeError("Subscriber not found")

        # Could not generate unique token
        logger.error(f"❌ Failed to generate unique token after {max_attempts} attempts")
        raise RuntimeError("Could not generate unique entry token")


    async def validate_and_consume_entry_token(self, token: str) -> Tuple[bool, str, Optional[int]]:
        """
        Valida y consume atómicamente un token de entrada.

        Esto previene condiciones de carrera donde el mismo token es usado múltiples veces.

        Args:
            token: Token de entrada a validar y consumir

        Returns:
            Tuple de (success, message, user_id):
            - success: True si el token es válido y fue consumido
            - message: Mensaje de éxito o error
            - user_id: ID del usuario si exitoso, None si falló
        """
        # Step 1: Get user_id BEFORE consuming token (avoids race condition in lookup)
        # This is read-only, no locks needed
        subscriber_result = await self.session.execute(
            select(VIPSubscriber.user_id, VIPSubscriber.vip_entry_stage, VIPSubscriber.expiry_date)
            .where(VIPSubscriber.vip_entry_token == token)
        )
        subscriber_data = subscriber_result.one_or_none()

        if not subscriber_data:
            return (False, "Token de entrada inválido", None)

        user_id, current_stage, expiry_date = subscriber_data

        # Validate pre-conditions before attempting UPDATE
        if expiry_date and expiry_date < utc_now():
            return (False, "Tu suscripción VIP ha expirado", None)

        if current_stage != 3:
            if current_stage is None:
                return (False, "El acceso ya fue completado anteriormente", None)
            return (False, f"Completa la etapa {current_stage} primero", None)

        # Step 2: Atomic UPDATE to consume token
        # This ensures only one request can successfully consume the token
        result = await self.session.execute(
            update(VIPSubscriber)
            .where(
                VIPSubscriber.vip_entry_token == token,
                VIPSubscriber.vip_entry_stage == 3  # Double-check stage hasn't changed
            )
            .values(
                vip_entry_stage=None,  # Flow complete
                vip_entry_token=None   # Token consumed
            )
        )

        if result.rowcount == 0:
            # Another request consumed the token between our read and UPDATE
            return (False, "El token ya fue utilizado. Inténtalo de nuevo.", None)

        # Success - we already have user_id from Step 1, no race condition here
        logger.info(f"Entry token consumed for user {user_id}")
        return (True, "Acceso VIP confirmado", user_id)


    async def is_entry_token_valid(self, token: str) -> bool:
        """
        Verifica si un token de entrada es válido (chequeo no destructivo para UI).

        Nota: Esto NO consume el token. Use validate_and_consume_entry_token
        para validación de acceso real.

        Args:
            token: Token a verificar

        Returns:
            True si token existe, corresponde a usuario en etapa 3, y no ha expirado
        """
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.vip_entry_token == token,
                VIPSubscriber.vip_entry_stage == 3,
                VIPSubscriber.expiry_date > utc_now()
            )
        )
        subscriber = result.scalar_one_or_none()
        return subscriber is not None

    # ===== INVITE LINK CREATION =====

    async def create_24h_invite_link(self, user_id: int) -> Optional[ChatInviteLink]:
        """
        Crea enlace de invitación al canal VIP con validez de 24 horas.

        Características:
        - Validez: 24 horas desde generación
        - Uso: member_limit=1 (un solo uso)
        - Timestamp: invite_link_sent_at actualizado

        Args:
            user_id: ID del usuario

        Returns:
            ChatInviteLink si se creó correctamente, None si error
        """
        # Get subscriber
        result = await self.session.execute(
            select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
        )
        subscriber = result.scalar_one_or_none()

        if not subscriber:
            logger.error(f"❌ VIPSubscriber not found for user {user_id}")
            return None

        # Get VIP channel ID from ConfigService
        from bot.services.config import ConfigService
        config_service = ConfigService(self.session)
        vip_channel_id = await config_service.get_vip_channel_id()

        if not vip_channel_id:
            logger.error("❌ VIP channel not configured")
            return None

        # Create invite link via SubscriptionService
        try:
            invite_link = await self.subscription.create_invite_link(
                channel_id=vip_channel_id,
                user_id=user_id,
                expire_hours=24  # 24-hour validity
            )

            # Update invite_link_sent_at timestamp
            subscriber.invite_link_sent_at = utc_now()

            logger.info(f"✅ 24h invite link created for user {user_id}")
            return invite_link

        except Exception as e:
            logger.error(f"❌ Error creating invite link for user {user_id}: {e}")
            return None

    # ===== EXPIRY CANCELLATION =====

    async def cancel_entry_on_expiry(self, user_id: int) -> None:
        """
        Cancela flujo de entrada VIP por expiración de suscripción.

        Acciones:
        - Set vip_entry_stage = NULL (cancelar flujo)
        - Remover usuario del canal VIP (si ya se unió)
        - Log evento de cancelación

        Llamado por: Background task expire_vip_subscribers()

        Args:
            user_id: ID del usuario
        """
        # Get subscriber
        result = await self.session.execute(
            select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
        )
        subscriber = result.scalar_one_or_none()

        if not subscriber:
            logger.warning(f"⚠️ VIPSubscriber not found for user {user_id}")
            return

        # Only cancel if flow is incomplete (stage 1 or 2)
        if subscriber.vip_entry_stage not in (1, 2):
            return

        # Cancel flow
        old_stage = subscriber.vip_entry_stage
        subscriber.vip_entry_stage = None  # NULL = cancelled

        logger.info(
            f"🚫 VIP entry flow cancelled for user {user_id} "
            f"(was at stage {old_stage}, subscription expired)"
        )

        # Kick from VIP channel if already joined
        try:
            vip_channel_id = await self._get_vip_channel_id()

            if vip_channel_id:
                removed = await self.subscription.kick_expired_vip_from_channel(
                    channel_id=vip_channel_id
                )
                logger.info(f"👞 User {user_id} removed from VIP channel (entry cancelled)")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove user {user_id} from VIP channel: {e}")

    async def _get_vip_channel_id(self) -> Optional[str]:
        """Helper: Get VIP channel ID from ConfigService."""
        from bot.services.config import ConfigService
        config_service = ConfigService(self.session)
        return await config_service.get_vip_channel_id()
