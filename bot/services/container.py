"""
Service Container con Dependency Injection y Lazy Loading.
Optimizado para consumo mínimo de memoria en Termux.
"""
import logging
from typing import Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Contenedor de servicios con lazy loading.

    Los servicios se instancian solo cuando se acceden por primera vez.
    Esto reduce el consumo de memoria inicial en Termux.

    Patrón: Dependency Injection + Lazy Initialization

    Uso:
        container = ServiceContainer(session, bot)

        # Primera vez: carga el service
        token = await container.subscription.generate_token(...)

        # Segunda vez: reutiliza instancia
        result = await container.subscription.validate_token(...)
    """

    def __init__(self, session: AsyncSession, bot: Bot):
        """
        Inicializa el container con dependencias base.

        Args:
            session: Sesión de base de datos SQLAlchemy
            bot: Instancia del bot de Telegram
        """
        assert session is not None, "session no puede ser None"
        assert bot is not None, "bot no puede ser None"

        self._session = session
        self._bot = bot

        # Services (cargados lazy)
        self._subscription_service = None
        self._channel_service = None
        self._config_service = None
        self._stats_service = None
        self._pricing_service = None
        self._user_service = None
        self._lucien_voice_service = None
        self._session_history = None
        self._role_detection_service = None
        self._content_service = None
        self._role_change_service = None
        self._interest_service = None
        self._user_management_service = None
        self._vip_entry_service = None
        self._wallet_service = None
        self._reaction_service = None
        self._streak_service = None
        self._shop_service = None
        self._reward_service = None
        self._narrative_service = None
        self._story_editor_service = None

        logger.debug("🏭 ServiceContainer inicializado (modo lazy)")

    # ===== SUBSCRIPTION SERVICE =====

    @property
    def subscription(self):
        """
        Service de gestión de suscripciones VIP/Free.

        Se carga lazy (solo en primer acceso).

        Returns:
            SubscriptionService: Instancia del service
        """
        if self._subscription_service is None:
            from bot.services.subscription import SubscriptionService
            logger.debug("🔄 Lazy loading: SubscriptionService")
            self._subscription_service = SubscriptionService(self._session, self._bot)

        return self._subscription_service

    # ===== CHANNEL SERVICE =====

    @property
    def channel(self):
        """
        Service de gestión de canales Telegram.

        Se carga lazy (solo en primer acceso).

        Returns:
            ChannelService: Instancia del service
        """
        if self._channel_service is None:
            from bot.services.channel import ChannelService
            logger.debug("🔄 Lazy loading: ChannelService")
            self._channel_service = ChannelService(self._session, self._bot)

        return self._channel_service

    # ===== CONFIG SERVICE =====

    @property
    def config(self):
        """
        Service de configuración del bot.

        Se carga lazy (solo en primer acceso).

        Returns:
            ConfigService: Instancia del service
        """
        if self._config_service is None:
            from bot.services.config import ConfigService
            logger.debug("🔄 Lazy loading: ConfigService")
            self._config_service = ConfigService(self._session)

        return self._config_service

    # ===== STATS SERVICE =====

    @property
    def stats(self):
        """
        Service de estadísticas.

        Se carga lazy (solo en primer acceso).

        Returns:
            StatsService: Instancia del service
        """
        if self._stats_service is None:
            from bot.services.stats import StatsService
            logger.debug("🔄 Lazy loading: StatsService")
            self._stats_service = StatsService(self._session)

        return self._stats_service

    # ===== PRICING SERVICE =====

    @property
    def pricing(self):
        """
        Service de gestión de planes de suscripción/tarifas.

        Se carga lazy (solo en primer acceso).

        Returns:
            PricingService: Instancia del service
        """
        if self._pricing_service is None:
            from bot.services.pricing import PricingService
            logger.debug("🔄 Lazy loading: PricingService")
            self._pricing_service = PricingService(self._session)

        return self._pricing_service

    # ===== USER SERVICE =====

    @property
    def user(self):
        """
        Service de gestión de usuarios y roles.

        Se carga lazy (solo en primer acceso).

        Returns:
            UserService: Instancia del service
        """
        if self._user_service is None:
            from bot.services.user import UserService
            logger.debug("🔄 Lazy loading: UserService")
            self._user_service = UserService(self._session)

        return self._user_service

    # ===== LUCIEN VOICE SERVICE =====

    @property
    def message(self):
        """
        Servicio de mensajes con la voz de Lucien.

        Se carga lazy (solo en primer acceso).

        Returns:
            LucienVoiceService: Instancia del servicio de mensajes

        Usage:
            # Generate error message
            error_msg = container.message.common.error('al generar token')

            # Generate success message
            success_msg = container.message.common.success('canal configurado')
        """
        if self._lucien_voice_service is None:
            from bot.services.message import LucienVoiceService
            logger.debug("🔄 Lazy loading: LucienVoiceService")
            self._lucien_voice_service = LucienVoiceService()

        return self._lucien_voice_service

    # ===== SESSION HISTORY =====

    @property
    def session_history(self):
        """
        Servicio de historial de sesión para selección de variantes consciente del contexto.

        Se carga lazy (solo en primer acceso).

        Returns:
            SessionMessageHistory: Instancia del servicio de historial

        Usage:
            # Handlers pasan user_id a message providers
            text, kb = container.message.user.start.greeting(
                user_name="Juan",
                user_id=message.from_user.id,
                is_vip=True
            )
            # Provider internamente llama _choose_variant con session_history
        """
        if self._session_history is None:
            from bot.services.message.session_history import SessionMessageHistory
            logger.debug("🔄 Lazy loading: SessionMessageHistory")
            # TTL 5 minutos, máximo 5 entradas por usuario
            self._session_history = SessionMessageHistory(ttl_seconds=300, max_entries=5)

        return self._session_history

    # ===== ROLE DETECTION SERVICE =====

    @property
    def role_detection(self):
        """
        Service de detección de roles (Admin/VIP/Free).

        Se carga lazy (solo en primer acceso).

        Returns:
            RoleDetectionService: Instancia del service
        """
        if self._role_detection_service is None:
            from bot.services.role_detection import RoleDetectionService
            logger.debug("🔄 Lazy loading: RoleDetectionService")
            self._role_detection_service = RoleDetectionService(self._session, self._bot)

        return self._role_detection_service

    # ===== CONTENT SERVICE =====

    @property
    def content(self):
        """
        Service de gestión de paquetes de contenido.

        Se carga lazy (solo en primer acceso).

        Returns:
            ContentService: Instancia del service
        """
        if self._content_service is None:
            from bot.services.content import ContentService
            logger.debug("🔄 Lazy loading: ContentService")
            self._content_service = ContentService(self._session)

        return self._content_service

    # ===== ROLE CHANGE SERVICE =====

    @property
    def role_change(self):
        """
        Service de registro de cambios de rol (auditoría).

        Se carga lazy (solo en primer acceso).

        Returns:
            RoleChangeService: Instancia del service
        """
        if self._role_change_service is None:
            from bot.services.role_change import RoleChangeService
            logger.debug("🔄 Lazy loading: RoleChangeService")
            self._role_change_service = RoleChangeService(self._session)

        return self._role_change_service

    # ===== INTEREST SERVICE =====

    @property
    def interest(self):
        """
        Service de gestión de intereses de usuarios en paquetes.

        Se carga lazy (solo en primer acceso).

        Returns:
            InterestService: Instancia del service

        Usage:
            # Registrar interés (con debounce)
            success, status, interest = await container.interest.register_interest(
                user_id=123, package_id=456
            )
            if success and status != "debounce":
                # Notificar al admin
                pass

            # Listar intereses pendientes
            interests, total = await container.interest.get_interests(is_attended=False)

            # Marcar como atendido
            success, msg = await container.interest.mark_as_attended(interest_id=789)
        """
        if self._interest_service is None:
            from bot.services.interest import InterestService
            logger.debug("🔄 Lazy loading: InterestService")
            self._interest_service = InterestService(self._session, self._bot)

        return self._interest_service

    # ===== USER MANAGEMENT SERVICE =====

    @property
    def user_management(self):
        """
        Service de gestión de usuarios y acciones administrativas.

        Se carga lazy (solo en primer acceso).

        Returns:
            UserManagementService: Instancia del service

        Usage:
            # Get user info
            info = await container.user_management.get_user_info(user_id=123)

            # Change role
            success, msg = await container.user_management.change_user_role(
                user_id=123, new_role=UserRole.VIP, changed_by=456
            )

            # Expel from channels
            success, msg = await container.user_management.expel_user_from_channels(
                user_id=123, expelled_by=456
            )
        """
        if self._user_management_service is None:
            from bot.services.user_management import UserManagementService
            logger.debug("🔄 Lazy loading: UserManagementService")
            self._user_management_service = UserManagementService(self._session, self._bot)

        return self._user_management_service

    # ===== VIP ENTRY SERVICE =====

    @property
    def vip_entry(self):
        """
        Service de gestión de flujo ritualizado de entrada VIP.

        Se carga lazy (solo en primer acceso).

        Returns:
            VIPEntryService: Instancia del service

        Usage:
            # Get current stage
            stage = await container.vip_entry.get_current_stage(user_id=123)

            # Advance stage
            success = await container.vip_entry.advance_stage(user_id=123, from_stage=1)

            # Create 24h invite link
            link = await container.vip_entry.create_24h_invite_link(user_id=123)

            # Cancel on expiry
            await container.vip_entry.cancel_entry_on_expiry(user_id=123)
        """
        if self._vip_entry_service is None:
            from bot.services.vip_entry import VIPEntryService
            logger.debug("🔄 Lazy loading: VIPEntryService")
            self._vip_entry_service = VIPEntryService(self._session, self._bot)

        return self._vip_entry_service

    # ===== WALLET SERVICE =====

    @property
    def wallet(self):
        """
        Service de economía (besitos, transacciones, niveles).

        Se carga lazy (solo en primer acceso).

        Returns:
            WalletService: Instancia del service

        Usage:
            # Credit user
            success, msg, tx = await container.wallet.earn_besitos(...)

            # Check balance
            balance = await container.wallet.get_balance(user_id)

            # Get transaction history
            txs, total = await container.wallet.get_transaction_history(user_id)
        """
        if self._wallet_service is None:
            from bot.services.wallet import WalletService
            logger.debug("🔄 Lazy loading: WalletService")
            self._wallet_service = WalletService(self._session)

        return self._wallet_service

    # ===== REACTION SERVICE =====

    @property
    def reaction(self):
        """
        Service de gestión de reacciones a contenido.

        Se carga lazy (solo en primer acceso).

        Returns:
            ReactionService: Instancia del service

        Usage:
            # Add reaction
            success, code, data = await container.reaction.add_reaction(
                user_id=123,
                content_id=456,
                channel_id="-1001234567890",
                emoji="❤️",
                content_category=ContentCategory.VIP_CONTENT
            )

            # Get content reaction counts
            counts = await container.reaction.get_content_reactions(
                content_id=456,
                channel_id="-1001234567890"
            )
        """
        if self._reaction_service is None:
            from bot.services.reaction import ReactionService
            logger.debug("🔄 Lazy loading: ReactionService")
            # Inject wallet service for besitos earning and streak service for tracking
            self._reaction_service = ReactionService(
                self._session,
                wallet_service=self.wallet,
                streak_service=self.streak
            )

        return self._reaction_service

    # ===== STREAK SERVICE =====

    @property
    def streak(self):
        """
        Service de gestión de rachas diarias y recompensas.

        Se carga lazy (solo en primer acceso).

        Returns:
            StreakService: Instancia del service

        Usage:
            # Check if user can claim daily gift
            can_claim, status = await container.streak.can_claim_daily_gift(user_id)

            # Claim daily gift
            success, result = await container.streak.claim_daily_gift(user_id)

            # Get streak info
            info = await container.streak.get_streak_info(user_id, StreakType.DAILY_GIFT)
        """
        if self._streak_service is None:
            from bot.services.streak import StreakService
            logger.debug("🔄 Lazy loading: StreakService")
            # Inject wallet service for besitos crediting
            self._streak_service = StreakService(
                self._session,
                wallet_service=self.wallet
            )

        return self._streak_service

    # ===== SHOP SERVICE =====

    @property
    def shop(self):
        """
        Service de tienda (shop) para compra de contenido.

        Se carga lazy (solo en primer acceso).

        Returns:
            ShopService: Instancia del service

        Usage:
            # Browse catalog
            products, total = await container.shop.browse_catalog(user_role="VIP")

            # Purchase product
            success, code, result = await container.shop.purchase_product(
                user_id=123, product_id=456, user_role="VIP"
            )

            # Get purchase history
            history, total = await container.shop.get_purchase_history(user_id=123)
        """
        if self._shop_service is None:
            from bot.services.shop import ShopService
            logger.debug("🔄 Lazy loading: ShopService")
            # Inject wallet service for payments
            self._shop_service = ShopService(
                self._session,
                wallet_service=self.wallet
            )

        return self._shop_service

    # ===== REWARD SERVICE =====

    @property
    def reward(self):
        """
        Service de recompensas y logros.

        Se carga lazy (solo en primer acceso).

        Returns:
            RewardService: Instancia del service

        Usage:
            # Check rewards on event
            unlocked = await container.reward.check_rewards_on_event(
                user_id=123, event_type="daily_gift_claimed"
            )

            # Get available rewards
            rewards = await container.reward.get_available_rewards(user_id=123)

            # Claim a reward
            success, msg, details = await container.reward.claim_reward(
                user_id=123, reward_id=456
            )
        """
        if self._reward_service is None:
            from bot.services.reward import RewardService
            logger.debug("🔄 Lazy loading: RewardService")
            # Inject wallet and streak services
            self._reward_service = RewardService(
                self._session,
                wallet_service=self.wallet,
                streak_service=self.streak
            )

        return self._reward_service

    # ===== NARRATIVE SERVICE =====

    @property
    def narrative(self):
        """
        Service de narrativa interactiva para usuarios.

        Se carga lazy (solo en primer acceso).

        Returns:
            NarrativeService: Instancia del service

        Usage:
            # Get available stories
            stories, total = await container.narrative.get_available_stories(
                user_tier=1, is_premium_user=False
            )

            # Start a story
            success, msg, progress = await container.narrative.start_story(
                user_id=123, story_id=456
            )

            # Make a choice
            success, msg, node, progress = await container.narrative.make_choice(
                user_id=123, progress=progress, choice_id=789
            )
        """
        if self._narrative_service is None:
            from bot.services.narrative import NarrativeService
            logger.debug("🔄 Lazy loading: NarrativeService")
            self._narrative_service = NarrativeService(
                self._session,
                wallet_service=self.wallet,
                reward_service=self.reward,
                shop_service=self.shop,
                streak_service=self.streak
            )

        return self._narrative_service

    # ===== STORY EDITOR SERVICE =====

    @property
    def story_editor(self):
        """
        Service de gestión de historias para administradores.

        Se carga lazy (solo en primer acceso).

        Returns:
            StoryEditorService: Instancia del service

        Usage:
            # Create a story
            success, msg, story = await container.story_editor.create_story(
                title="Mi Historia", description="...", is_premium=False
            )

            # Create nodes
            success, msg, node = await container.story_editor.create_node(
                story_id=story.id, node_type=NodeType.START, content_text="..."
            )

            # Publish story
            success, msg = await container.story_editor.publish_story(story.id)
        """
        if self._story_editor_service is None:
            from bot.services.story_editor import StoryEditorService
            logger.debug("🔄 Lazy loading: StoryEditorService")
            self._story_editor_service = StoryEditorService(self._session)

        return self._story_editor_service

    # ===== UTILIDADES =====

    def get_loaded_services(self) -> list[str]:
        """
        Retorna lista de servicios ya cargados en memoria.

        Útil para debugging y monitoring de uso de memoria.

        Returns:
            Lista de nombres de services cargados
        """
        loaded = []

        if self._subscription_service is not None:
            loaded.append("subscription")
        if self._channel_service is not None:
            loaded.append("channel")
        if self._config_service is not None:
            loaded.append("config")
        if self._stats_service is not None:
            loaded.append("stats")
        if self._pricing_service is not None:
            loaded.append("pricing")
        if self._user_service is not None:
            loaded.append("user")
        if self._lucien_voice_service is not None:
            loaded.append("message")
        if self._session_history is not None:
            loaded.append("session_history")
        if self._role_detection_service is not None:
            loaded.append("role_detection")
        if self._content_service is not None:
            loaded.append("content")
        if self._role_change_service is not None:
            loaded.append("role_change")
        if self._interest_service is not None:
            loaded.append("interest")
        if self._user_management_service is not None:
            loaded.append("user_management")
        if self._vip_entry_service is not None:
            loaded.append("vip_entry")
        if self._wallet_service is not None:
            loaded.append("wallet")
        if self._reaction_service is not None:
            loaded.append("reaction")
        if self._streak_service is not None:
            loaded.append("streak")
        if self._shop_service is not None:
            loaded.append("shop")
        if self._reward_service is not None:
            loaded.append("reward")
        if self._narrative_service is not None:
            loaded.append("narrative")
        if self._story_editor_service is not None:
            loaded.append("story_editor")

        return loaded

    async def preload_critical_services(self):
        """
        Precarga servicios críticos de forma explícita.

        Se puede llamar en background después del startup
        para "calentar" los services más usados.

        Críticos: subscription, config (usados frecuentemente)
        No críticos: channel, stats (usados ocasionalmente)
        """
        logger.info("🔥 Precargando services críticos...")

        # Trigger lazy load accediendo a las properties
        _ = self.subscription
        _ = self.config

        logger.info(f"✅ Services precargados: {self.get_loaded_services()}")
