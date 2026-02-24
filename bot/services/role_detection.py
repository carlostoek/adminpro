"""
Role Detection Service - Detecta automáticamente el rol del usuario (Admin/VIP/Free).

Responsabilidades:
- Detectar rol basándose en prioridad: Admin > VIP > Free
- Cálculo stateless (sin caché) para evitar roles stale
- Integración con Config.is_admin() y SubscriptionService.is_vip_active()

Pattern: Stateless service following SubscriptionService architecture
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import UserRole
from config import Config

logger = logging.getLogger(__name__)


class RoleDetectionService:
    """
    Servicio para detectar el rol de un usuario.

    Prioridad de detección:
    1. Admin (Config.is_admin() - highest priority)
    2. VIP (SubscriptionService.is_vip_active() - active subscription)
    3. Free (default fallback)

    El servicio es stateless - no cachea resultados.
    Esto garantiza que el rol siempre se recalcule desde fuentes frescas.
    """

    def __init__(self, session: AsyncSession, bot: Optional["Bot"] = None):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos SQLAlchemy
            bot: Instancia del Bot de Aiogram (opcional, para SubscriptionService)
        """
        self.session = session
        self.bot = bot
        logger.debug("✅ RoleDetectionService inicializado")

    async def get_user_role(self, user_id: int) -> UserRole:
        """
        Detecta el rol actual del usuario.

        Prioridad: Admin (env o canal) > VIP Subscription (activa) > VIP Channel > Free (primer match wins)

        IMPORTANTE: VIP Subscription ACTIVA tiene PRIORIDAD sobre VIP Channel.
        Solo es VIP si tiene suscripción activa. Estar en el canal sin suscripción
        activa no convierte al usuario en VIP.

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            UserRole: Rol detectado (ADMIN, VIP, or FREE)
        """
        # 1. Check Admin from environment variables (highest priority)
        if Config.is_admin(user_id):
            logger.debug(f"👑 User {user_id} detectado como ADMIN (env var)")
            return UserRole.ADMIN

        # 2. Check Admin from channel membership (same priority as env admin)
        if self.bot:
            from bot.services.channel import ChannelService
            channel_service = ChannelService(self.session, self.bot)
            if await channel_service.is_user_channel_admin(user_id):
                logger.info(f"👑 User {user_id} detectado como ADMIN (canal)")
                return UserRole.ADMIN

        # 3. Check VIP Subscription FIRST (HIGHEST PRIORITY for VIP detection)
        # Verificar suscripción activa antes de verificar canal
        from bot.services.subscription import SubscriptionService

        subscription_service = SubscriptionService(self.session, bot=self.bot)

        is_vip = await subscription_service.is_vip_active(user_id)
        if is_vip:
            logger.debug(f"⭐ User {user_id} detectado como VIP (suscripción activa)")
            return UserRole.VIP

        # 3. Check VIP Channel membership (SECONDARY - solo si no hay suscripción activa)
        # Import local para evitar circular dependency
        from bot.services.channel import ChannelService

        channel_service = ChannelService(self.session, bot=self.bot)
        vip_channel_id = await channel_service.get_vip_channel_id()

        if vip_channel_id:
            try:
                # Check if user is member of VIP channel
                member = await self.bot.get_chat_member(
                    chat_id=vip_channel_id,
                    user_id=user_id
                )
                # User is member if status is member, administrator, or creator
                if member.status in ["member", "administrator", "creator"]:
                    logger.warning(f"⚠️ User {user_id} está en canal VIP pero sin suscripción activa")
                    logger.debug(f"🆓 User {user_id} tratado como FREE (sin suscripción activa)")
                    # No devolver VIP - suscripción expiró o no existe
                    return UserRole.FREE
            except Exception as e:
                logger.debug(f"⚠️ No se pudo verificar membresía VIP channel para user {user_id}: {e}")

        # 4. Default to Free
        logger.debug(f"🆓 User {user_id} detectado como FREE")
        return UserRole.FREE

    async def refresh_user_role(self, user_id: int) -> UserRole:
        """
        Alias de get_user_role para consistencia de API.

        Este método existe por claridad semántica:
        - get_user_role: Obtener rol (no implica caché)
        - refresh_user_role: Recalcular rol (explícito que es fresco)

        Ambos retornan el mismo resultado (cálculo stateless).
        """
        return await self.get_user_role(user_id)

    async def is_admin(self, user_id: int) -> bool:
        """
        Verifica si un usuario es admin (incluye variables de entorno y canales).

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            True si es admin (env o canal), False en caso contrario
        """
        # Check env vars first
        if Config.is_admin(user_id):
            return True

        # Check channel admins
        if self.bot:
            from bot.services.channel import ChannelService
            channel_service = ChannelService(self.session, self.bot)
            return await channel_service.is_user_channel_admin(user_id)

        return False
