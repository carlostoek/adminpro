"""
User Start Messages Provider - User-facing /start command messages.

Provides messages for user greetings, deep link activation, and role-based welcome.
All messages maintain Lucien's sophisticated mayordomo voice from docs/guia-estilo.md.

User messages differ from admin:
- Warmer, more welcoming tone (users need reassurance)
- Time-of-day awareness (users interact repeatedly)
- Role-based adaptation (single method handles admin/VIP/free)
- Deep link celebration (auto-activation feels special)
"""
from datetime import datetime
from typing import Tuple, Optional

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.markdown import escape_html

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard


class UserStartMessages(BaseMessageProvider):
    """
    User start messages provider for /start command.

    Voice Characteristics (from docs/guia-estilo.md):
    - Warmer than admin messages (users need reassurance)
    - Time-of-day greetings (morning/afternoon/evening)
    - Role-based adaptation (admin redirect, VIP status, free options)
    - Deep link celebration (distinct from manual redemption)
    - Uses "usted", never "tú"
    - Emoji 🎩 always present
    - References Diana for authority/mystique

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI or str for text-only

    Examples:
        >>> provider = UserStartMessages()
        >>> text, keyboard = provider.greeting("Juan", is_vip=True, vip_days_remaining=15)
        >>> '🎩' in text and 'Juan' in text
        True
        >>> keyboard is None  # VIP users don't get action keyboard
        True
    """

    def __init__(self):
        """
        Initialize UserStartMessages provider.

        Stateless: no session or bot stored.
        """
        super().__init__()

    def greeting(
        self,
        user_name: str,
        is_admin: bool = False,
        is_vip: bool = False,
        vip_days_remaining: int = 0
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Generate time-of-day greeting adapted to user role.

        Time periods:
        - Morning (6-12): "Buenos días", "Buen día", "Bienvenido esta mañana"
        - Afternoon (12-20): "Buenas tardes", "Bienvenido", "Buena tarde"
        - Evening (20-6): "Buenas noches", "Buena noche", "Bienvenido esta noche"

        Role adaptation:
        - Admin: Concise redirect to /admin, no keyboard
        - VIP: Show days remaining, no keyboard
        - Free: Warm welcome + options keyboard (redeem token, request free)

        Args:
            user_name: User's first name (will be HTML-escaped)
            is_admin: Whether user is admin (redirects to /admin)
            is_vip: Whether user has active VIP subscription
            vip_days_remaining: Days remaining in VIP subscription

        Returns:
            Tuple of (message_text, keyboard)
            - Admin/VIP: keyboard is None
            - Free: keyboard with redeem/request options

        Examples:
            Admin redirect:
                >>> provider = UserStartMessages()
                >>> text, kb = provider.greeting("María", is_admin=True)
                >>> '/admin' in text and kb is None
                True

            VIP status:
                >>> text, kb = provider.greeting("Carlos", is_vip=True, vip_days_remaining=15)
                >>> '15 días' in text and kb is None
                True

            Free user with options:
                >>> text, kb = provider.greeting("Ana")
                >>> kb is not None  # Has action keyboard
                True
        """
        safe_name = escape_html(user_name)

        # Time-of-day detection
        hour = datetime.now().hour

        # Determine time period and select weighted greeting
        if 6 <= hour < 12:
            # Morning (6-12)
            greeting_variants = [
                "Buenos días",
                "Buen día",
                "Bienvenido esta mañana"
            ]
            greeting_weights = [0.5, 0.3, 0.2]
        elif 12 <= hour < 20:
            # Afternoon (12-20)
            greeting_variants = [
                "Buenas tardes",
                "Bienvenido",
                "Buena tarde"
            ]
            greeting_weights = [0.5, 0.3, 0.2]
        else:
            # Evening (20-6)
            greeting_variants = [
                "Buenas noches",
                "Buena noche",
                "Bienvenido esta noche"
            ]
            greeting_weights = [0.5, 0.3, 0.2]

        greeting = self._choose_variant(greeting_variants, greeting_weights)

        # Role-based adaptation
        if is_admin:
            # Admin: Concise redirect to /admin
            text = self._compose(
                f"🎩 {greeting}, <b>{safe_name}</b>",
                "Usted es administrador. Use /admin para gestionar los dominios de Diana."
            )
            return (text, None)

        elif is_vip:
            # VIP: Show days remaining
            text = self._compose(
                f"🎩 {greeting}, <b>{safe_name}</b>",
                f"Su membresía en el círculo exclusivo está activa.\n"
                f"<b>Tiempo restante:</b> {vip_days_remaining} días",
                "Diana lo espera en el canal privado."
            )
            return (text, None)

        else:
            # Free: Warm welcome + options
            text = self._compose(
                f"🎩 {greeting}, <b>{safe_name}</b>",
                "Soy Lucien, mayordomo de Diana.\n\n"
                "Puedo asistirle con:\n"
                "• Canjear una invitación al círculo exclusivo\n"
                "• Solicitar acceso temporal al vestíbulo",
                "¿En qué puedo ayudarle?"
            )

            # Keyboard with redeem token and request free options
            keyboard = create_inline_keyboard([
                [("🎫 Canjear Invitación VIP", "user:redeem_token")],
                [("🕐 Solicitar Acceso Free", "user:request_free")]
            ])

            return (text, keyboard)

    def deep_link_activation_success(
        self,
        user_name: str,
        plan_name: str,
        duration_days: int,
        price: str,
        days_remaining: int,
        invite_link: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate celebratory message for successful deep link activation.

        Distinct from manual redemption - deep link feels more automatic/special.

        Args:
            user_name: User's first name (will be HTML-escaped)
            plan_name: Name of subscription plan (e.g., "Plan Mensual")
            duration_days: Duration of plan in days
            price: Formatted price string (e.g., "$9.99")
            days_remaining: Total days remaining after activation
            invite_link: URL for joining VIP channel (expires in 5 hours)

        Returns:
            Tuple of (message_text, keyboard with join button)

        Voice Rationale:
            Celebratory tone different from manual redemption creates
            UX distinction between clicking deep link vs typing token.

        Examples:
            >>> provider = UserStartMessages()
            >>> text, kb = provider.deep_link_activation_success(
            ...     "Pedro",
            ...     "Plan Mensual",
            ...     30,
            ...     "$9.99",
            ...     30,
            ...     "https://t.me/+ABC123"
            ... )
            >>> '🎩' in text and 'Pedro' in text
            True
            >>> kb is not None  # Has join button
            True
        """
        safe_name = escape_html(user_name)

        # Two equal-weight celebration variants
        celebration_variants = [
            "¡Excelente! Su suscripción VIP ha sido activada.",
            "¡Bienvenido al círculo exclusivo! Todo está listo."
        ]
        celebration = self._choose_variant(celebration_variants)

        text = self._compose(
            f"🎩 {celebration}",
            f"<b>Plan:</b> {plan_name}\n"
            f"<b>Precio:</b> {price}\n"
            f"<b>Duración:</b> {duration_days} días\n"
            f"<b>Tiempo restante:</b> {days_remaining} días\n\n"
            f"Haga click en el botón para unirse ahora.",
            f"⏰ <i>El acceso expira en 5 horas</i>"
        )

        # Single button with URL to VIP channel
        keyboard = create_inline_keyboard([
            [("⭐ Unirse al Canal VIP", invite_link, "url")]
        ])

        return (text, keyboard)

    def deep_link_activation_error(
        self,
        error_type: str,
        details: str = ""
    ) -> str:
        """
        Generate error message for failed deep link activation.

        Error types:
        - "invalid": Token format incorrect or doesn't exist
        - "used": Token already redeemed
        - "expired": Token expired
        - "no_plan": Token has no plan associated

        Args:
            error_type: Type of error (invalid, used, expired, no_plan)
            details: Optional additional details to append

        Returns:
            Error message text (no keyboard, errors don't need actions)

        Voice Rationale:
            Polite but clear error explanations maintain Lucien's voice
            while providing actionable guidance.

        Examples:
            >>> provider = UserStartMessages()
            >>> error = provider.deep_link_activation_error("used")
            >>> '🎩' in error and 'Diana' in error
            True

            >>> error = provider.deep_link_activation_error("expired", "Token ABC123")
            >>> 'expiró' in error and 'ABC123' in error
            True
        """
        error_messages = {
            "invalid": (
                "🎩 Lucien:\n\n"
                "La invitación proporcionada no es válida.\n\n"
                "Posibles causas:\n"
                "• El código fue ingresado incorrectamente\n"
                "• La invitación ya fue utilizada\n"
                "• La invitación ha expirado\n\n"
                "Consulte con quien le proporcionó el acceso."
            ),
            "used": (
                "🎩 Lucien:\n\n"
                "Esta invitación ya fue utilizada.\n\n"
                "Diana no permite el uso múltiple de invitaciones.\n\n"
                "Si necesita acceso, solicite una nueva invitación."
            ),
            "expired": (
                "🎩 Lucien:\n\n"
                "La invitación ha expirado.\n\n"
                "Las invitaciones tienen validez limitada por seguridad.\n\n"
                "Solicite una nueva invitación al administrador."
            ),
            "no_plan": (
                "🎩 Lucien:\n\n"
                "La invitación no tiene un plan asociado.\n\n"
                "Esto puede ocurrir con invitaciones antiguas.\n\n"
                "Consulte con el administrador para obtener una invitación actualizada."
            )
        }

        base_message = error_messages.get(
            error_type,
            "🎩 Lucien:\n\n"
            "Ocurrió un error procesando la invitación.\n\n"
            "Consulte con el administrador."
        )

        # Append details if provided
        if details:
            return f"{base_message}\n\n<i>Detalles: {details}</i>"

        return base_message
