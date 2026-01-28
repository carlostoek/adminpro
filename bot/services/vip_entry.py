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
from bot.services.subscription import SubscriptionService

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


    async def advance_stage(self, user_id: int, from_stage: int) -> bool:
        """
        Avanza a la siguiente etapa del flujo VIP.

        Valida:
        - Suscripción no expirada
        - from_stage coincide con etapa actual en BD
        - Progresión secuencial (no saltos)

        Args:
            user_id: ID del usuario
            from_stage: Etapa actual (para validación)

        Returns:
            True si etapa avanzó correctamente, False si error
        """
        # Get subscriber
        result = await self.session.execute(
            select(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
        )
        subscriber = result.scalar_one_or_none()

        if not subscriber:
            logger.error(f"❌ VIPSubscriber not found for user {user_id}")
            return False

        # Validate subscription not expired
        if subscriber.is_expired():
            logger.warning(
                f"⚠️ Cannot advance stage: User {user_id} subscription expired"
            )
            return False

        # Validate from_stage matches current stage
        current_stage = subscriber.vip_entry_stage if subscriber.vip_entry_stage else 0

        if from_stage != current_stage:
            logger.warning(
                f"⚠️ Stage mismatch: expected {current_stage}, got {from_stage} "
                f"for user {user_id}"
            )
            return False

        # Validate sequential progression (no skips)
        if from_stage not in (1, 2):  # Only advance from stage 1 or 2
            logger.warning(f"⚠️ Cannot advance from stage {from_stage}")
            return False

        # Advance to next stage
        next_stage = from_stage + 1
        subscriber.vip_entry_stage = next_stage

        logger.info(
            f"✅ User {user_id} VIP entry advanced: stage {from_stage} → {next_stage}"
        )

        return True

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


    async def is_entry_token_valid(self, token: str) -> bool:
        """
        Verifica si un token de entrada es válido.

        Args:
            token: Token a verificar

        Returns:
            True si token existe y corresponde a usuario en etapa 3
        """
        result = await self.session.execute(
            select(VIPSubscriber).where(
                VIPSubscriber.vip_entry_token == token,
                VIPSubscriber.vip_entry_stage == 3
            )
        )
        subscriber = result.scalar_one_or_none()

        if subscriber and not subscriber.is_expired():
            return True

        return False

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
            subscriber.invite_link_sent_at = datetime.utcnow()

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
