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

        Prioridad: Admin > VIP Channel > VIP Subscription > Free (primer match wins)

        IMPORTANTE: VIP Channel tiene PRIORIDAD sobre VIP Subscription.
        Si el usuario está en el canal VIP, es VIP sin importar el estado de suscripción.

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            UserRole: Rol detectado (ADMIN, VIP, or FREE)
        """
        # 1. Check Admin (highest priority)
        if Config.is_admin(user_id):
            logger.debug(f"👑 User {user_id} detectado como ADMIN")
            return UserRole.ADMIN

        # 2. Check VIP Channel membership (HIGHEST PRIORITY for VIP detection)
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
                    logger.debug(f"⭐ User {user_id} detectado como VIP (canal VIP)")
                    return UserRole.VIP
            except Exception as e:
                logger.debug(f"⚠️ No se pudo verificar membresía VIP channel para user {user_id}: {e}")
                # Continue to check subscription

        # 3. Check VIP Subscription (if not in VIP channel)
        from bot.services.subscription import SubscriptionService

        subscription_service = SubscriptionService(self.session, bot=self.bot)

        is_vip = await subscription_service.is_vip_active(user_id)
        if is_vip:
            logger.debug(f"⭐ User {user_id} detectado como VIP (suscripción)")
            return UserRole.VIP

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

    def is_admin(self, user_id: int) -> bool:
        """
        Verifica si un usuario es admin (método helper síncrono).

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            True si es admin, False en caso contrario
        """
        return Config.is_admin(user_id)
