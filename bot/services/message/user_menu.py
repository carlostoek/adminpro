"""
User Menu Messages Provider - VIP and Free user menu messages.

Provides messages for VIP and Free user menus with Diana's direct voice.
User-facing menus use Diana's personal voice for direct connection.

Voice Architecture:
- User menus (this module): Diana's voice (🫦) - direct, personal, empowering
- Admin interfaces: Lucien's voice (🎩) - formal, mayordomo, elegant
- System/flow messages: Lucien's voice (🎩) - service-oriented

VIP users: "Ya no estás afuera. Aquí el juego cambia."
Free users: "Sí… ya eres Kinky. Aquí empieza el juego."
"""
import random
from datetime import datetime
from typing import Tuple, List, Optional, Dict, Any

from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard, create_menu_navigation, create_content_with_navigation
from bot.utils.formatters import escape_html
from bot.database.models import ContentPackage


class UserMenuMessages(BaseMessageProvider):
    """
    User menu messages provider for VIP and Free user menus.

    Voice Characteristics (Diana's Voice 🫦):
    - User menus use Diana's direct, personal voice (not Lucien's mayordomo voice)
    - VIP menu: "Ya no estás afuera. Aquí el juego cambia."
    - Free menu: "Sí… ya eres Kinky. Aquí empieza el juego."
    - Content browsing: "Lo que no publico… lo dejo aquí."
    - Direct, empowering, intimate tone
    - Second person ("tú/eres/estás") for personal connection
    - Emoji 🫦 for Diana's voice signature

    Voice Architecture (System-wide):
    - User menus (this module): Diana's voice (🫦)
    - Admin interfaces: Lucien's voice (🎩)
    - System/flow messages: Lucien's voice (🎩)

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI
    - Uses create_content_with_navigation for consistent navigation buttons

    Examples:
        >>> provider = UserMenuMessages()
        >>> text, kb = provider.vip_menu_greeting("Juan", vip_expires_at=datetime.now())
        >>> '🫦' in text  # Diana's voice for user menus
        True
        >>> text, kb = provider.free_menu_greeting("Ana", free_queue_position=5)
        >>> '🫦' in text  # Diana's voice for user menus
        True
    """

    def __init__(self):
        """
        Initialize UserMenuMessages provider.

        Stateless: no session or bot stored.
        """
        super().__init__()

    def _format_streak_display(self, streak_count: int) -> str:
        """
        Format streak count for display with fire emoji.

        Args:
            streak_count: Current streak day count

        Returns:
            str: Formatted streak string with fire emoji

        Voice (Diana 🫦):
            - Direct, empowering tone
            - "Sin racha" for zero streak (encouraging start)
            - "{count} días" for active streak
        """
        if streak_count > 0:
            return f"🔥 {streak_count} días"
        return "🔥 Sin racha"

    def _format_time_until_next_claim(self, next_claim_time: Optional[datetime]) -> str:
        """
        Format time remaining until next claim.

        Args:
            next_claim_time: Datetime when next claim is available

        Returns:
            str: Formatted time string (e.g., "5h 30m")
        """
        if next_claim_time is None:
            return "pronto"

        from datetime import datetime
        now = datetime.utcnow()
        if next_claim_time <= now:
            return "disponible"

        remaining = next_claim_time - now
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def vip_menu_greeting(
        self,
        user_name: str,
        vip_expires_at: Optional[datetime] = None,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None,
        streak_info: Optional[Dict[str, any]] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main VIP menu greeting with Diana's direct voice.

        Args:
            user_name: User's first name (will be HTML-escaped)
            vip_expires_at: Optional datetime when VIP subscription expires
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for VIP main menu

        Voice (Diana 🫦):
            Direct, empowering message establishing VIP status:
            "Ya no estás afuera. Aquí el juego cambia."

            Note: User menus intentionally use Diana's voice (🫦), not Lucien's (🎩),
            for direct personal connection with users.

        Examples:
            >>> provider = UserMenuMessages()
            >>> text, kb = provider.vip_menu_greeting("Juan", vip_expires_at=datetime.now())
            >>> '🫦' in text  # Diana's voice
            True
            >>> 'Ya no estás afuera' in text
            True
        """
        # Build greeting with streak info if provided
        streak_display = ""
        if streak_info:
            current_streak = streak_info.get("current_streak", 0)
            streak_display = self._format_streak_display(current_streak)

        # Fixed greeting for VIP users - with streak display
        if streak_display:
            text = f"🫦 <b>Diana:</b>\n\nYa no estás afuera.\nAquí el juego cambia.\n\n{streak_display}"
        else:
            text = "🫦 <b>Diana:</b>\n\nYa no estás afuera.\nAquí el juego cambia."

        keyboard = self._vip_main_menu_keyboard(streak_info)
        return text, keyboard

    def free_menu_greeting(
        self,
        user_name: str,
        free_queue_position: Optional[int] = None,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None,
        streak_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main Free menu greeting with Diana's direct voice.

        Args:
            user_name: User's first name (will be HTML-escaped)
            free_queue_position: Optional position in Free channel queue
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for Free main menu

        Voice (Diana 🫦):
            Direct, welcoming message acknowledging Kinky identity:
            "Sí… ya eres Kinky. Aquí empieza el juego."

            Note: User menus intentionally use Diana's voice (🫦), not Lucien's (🎩),
            for direct personal connection with users.

        Examples:
            >>> provider = UserMenuMessages()
            >>> text, kb = provider.free_menu_greeting("Ana", free_queue_position=5)
            >>> '🫦' in text  # Diana's voice
            True
            >>> 'ya eres Kinky' in text
            True
        """
        # Build greeting with streak info if provided
        streak_display = ""
        if streak_info:
            current_streak = streak_info.get("current_streak", 0)
            streak_display = self._format_streak_display(current_streak)

        # Fixed greeting for Free users - with streak display
        if streak_display:
            text = f"🫦 <b>Diana:</b>\n\nSí… ya eres Kinky.\nAquí empieza el juego.\n\n{streak_display}"
        else:
            text = "🫦 <b>Diana:</b>\n\nSí… ya eres Kinky.\nAquí empieza el juego."

        keyboard = self._free_main_menu_keyboard(streak_info)
        return text, keyboard

    def vip_premium_section(
        self,
        user_name: str,
        packages: List[ContentPackage],
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate VIP premium content section with minimalist package list.

        Args:
            user_name: User's first name (will be HTML-escaped)
            packages: List of ContentPackage objects for VIP premium content
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for VIP premium content listing

        Voice Rationale:
            VIP premium content is "tesoros del sanctum" (sanctum treasures).
            Minimalist list format: only package names (no prices or categories).
            Packages sorted by price: free first, then lowest to highest.
            Individual buttons navigate to detail view before registering interest.

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> packages = [ContentPackage(id=1, name="Tesoro 1")]
            >>> text, kb = provider.vip_premium_section("Juan", packages)
            >>> '🎩' in text and 'Juan' in text
            True
            >>> 'tesoros' in text.lower()
            True
        """
        safe_name = escape_html(user_name)

        # Weighted section introductions
        introductions = [
            "Los tesoros del sanctum...",
            "Diana ha dispuesto estos secretos para el círculo exclusivo...",
            "El sanctum revela sus tesoros más preciados..."
        ]

        introduction = self._choose_variant(
            introductions,
            user_id=user_id,
            method_name="vip_premium_section",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{introduction}</i>"

        # Sort packages by price (free first, then ascending)
        sorted_packages = self._sort_packages_by_price(packages)

        body = (
            f"<b>💎 Sección Premium VIP</b>\n\n"
            f"<b>{safe_name}</b>, explore los tesoros del sanctum...\n\n"
            f"<i>Seleccione un paquete para ver detalles completos antes de manifestar interés...</i>"
        )

        text = self._compose(header, body)

        # Create minimalist package buttons (one per row, name only)
        package_buttons = [
            [{"text": f"📦 {pkg.name}", "callback_data": f"vip:packages:{pkg.id}"}]
            for pkg in sorted_packages
        ]

        keyboard = create_content_with_navigation(
            package_buttons,
            back_text="⬅️ Volver al Menú VIP",
            back_callback="menu:back"
        )

        return text, keyboard

    def free_content_section(
        self,
        user_name: str,
        packages: List[ContentPackage],
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate Free content browsing section with minimalist package list.

        Args:
            user_name: User's first name (will be HTML-escaped)
            packages: List of ContentPackage objects for Free content
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for Free content listing

        Voice Rationale:
            Free content is "muestras del jardín" (garden samples).
            Minimalist list format: only package names (no prices or categories).
            Packages sorted by price: free first, then lowest to highest.
            Individual buttons navigate to detail view before registering interest.

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> packages = [ContentPackage(id=1, name="Muestra 1")]
            >>> text, kb = provider.free_content_section("Ana", packages)
            >>> '🎩' in text and 'Ana' in text
            True
            >>> 'muestras' in text.lower()
            True
        """
        # Solo la cabecera solicitada para "Mi contenido"
        text = "🫦 <b>Diana:</b>\n\nLo que no publico… lo dejo aquí."

        # Sort packages by price (free first, then ascending)
        sorted_packages = self._sort_packages_by_price(packages)

        # Create minimalist package buttons (one per row, name only)
        # NOTE: Using "free:packages:" prefix to avoid conflict with VIP router
        package_buttons = [
            [{"text": f"📦 {pkg.name}", "callback_data": f"free:packages:{pkg.id}"}]
            for pkg in sorted_packages
        ]

        keyboard = create_content_with_navigation(
            package_buttons,
            back_text="⬅️ Volver al Menú Free",
            back_callback="menu:free:main"
        )

        return text, keyboard

    def vip_free_content_section(
        self,
        user_name: str,
        packages: List[ContentPackage],
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate Free content section for VIP users browsing free content.

        Args:
            user_name: User's first name (will be HTML-escaped)
            packages: List of ContentPackage objects for Free content
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for Free content listing shown to VIP users

        Voice Rationale:
            VIP users viewing Free content are "miembros del círculo explorando el jardín público".
            Same minimalist list format as free_content_section.
            Uses "vip:free:" prefix for callbacks to route through VIP handlers.
            Back button returns to VIP main menu (not Free menu).

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> packages = [ContentPackage(id=1, name="Muestra 1")]
            >>> text, kb = provider.vip_free_content_section("Juan", packages)
            >>> '🎩' in text and 'Juan' in text
            True
            >>> 'jardín público' in text.lower()
            True
        """
        # Solo la cabecera solicitada para "Mi contenido"
        text = "🫦 <b>Diana:</b>\n\nLo que no publico… lo dejo aquí."

        # Sort packages by price (free first, then ascending)
        sorted_packages = self._sort_packages_by_price(packages)

        # Create minimalist package buttons with vip:free: prefix
        # This ensures callbacks go through VIP router with proper validation
        package_buttons = [
            [{"text": f"📦 {pkg.name}", "callback_data": f"vip:free:packages:{pkg.id}"}]
            for pkg in sorted_packages
        ]

        keyboard = create_content_with_navigation(
            package_buttons,
            back_text="⬅️ Volver al Menú VIP",
            back_callback="menu:back"
        )

        return text, keyboard

    def _sort_packages_by_price(self, packages: List[ContentPackage]) -> List[ContentPackage]:
        """
        Sort packages by price: free packages first (price is None), then paid packages by price ascending.

        Args:
            packages: List of ContentPackage objects to sort

        Returns:
            Sorted list with free packages first, then paid packages sorted by price (lowest first)

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> pkg1 = ContentPackage(id=1, name="Free", price=None)
            >>> pkg2 = ContentPackage(id=2, name="Cheap", price=5.00)
            >>> pkg3 = ContentPackage(id=3, name="Expensive", price=20.00)
            >>> sorted_pkgs = provider._sort_packages_by_price([pkg3, pkg1, pkg2])
            >>> sorted_pkgs[0].name, sorted_pkgs[1].name, sorted_pkgs[2].name
            ('Free', 'Cheap', 'Expensive')
        """
        if not packages:
            return []

        # Separate free (price is None) and paid packages
        free_packages = [p for p in packages if p.price is None]
        paid_packages = [p for p in packages if p.price is not None]

        # Sort free packages by name (alphabetically)
        free_packages_sorted = sorted(free_packages, key=lambda p: p.name)

        # Sort paid packages by price (ascending), then by name for ties
        paid_packages_sorted = sorted(paid_packages, key=lambda p: (p.price, p.name))

        # Return free packages first, then paid packages
        return free_packages_sorted + paid_packages_sorted

    def package_detail_view(
        self,
        package: ContentPackage,
        user_role: str = "VIP",
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None,
        source_section: Optional[str] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate detailed package view with all user-facing information.

        Args:
            package: ContentPackage object to display
            user_role: User role for context-aware messages ("VIP" or "Free")
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness
            source_section: Optional source section ("premium" or "free") for navigation

        Returns:
            Tuple of (text, keyboard) for package detail view

        Voice Rationale:
            Shows complete package information before user registers interest.
            Price formatted elegantly: "Acceso promocional" for None, "$X.XX" for paid.
            Category badges with emoji: VIP_PREMIUM="💎", VIP_CONTENT="🛋️", FREE_CONTENT="🌸".
            Lucien's closing adapts to user role ("círculo" for VIP, "jardín" for Free).

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> pkg = ContentPackage(id=1, name="Pack Premium", price=15.00)
            >>> text, kb = provider.package_detail_view(pkg, user_role="VIP")
            >>> '💎' in text and 'Pack Premium' in text
            True
        """
        # Weighted introductions based on user role
        if user_role == "VIP":
            introductions = [
                "Un tesoro del sanctum seleccionado...",
                "Diana ha preparado este contenido exclusivo...",
                "Los detalles del círculo exclusivo..."
            ]
            context_closing = "¿Desea manifestar su interés en este tesoro del círculo?"
        else:  # Free
            introductions = [
                "Una muestra del jardín seleccionada...",
                "Diana permite contemplar este contenido...",
                "Los detalles del jardín público..."
            ]
            context_closing = "¿Desea manifestar su interés en esta muestra del jardín?"

        introduction = self._choose_variant(
            introductions,
            user_id=user_id,
            method_name="package_detail_view",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{introduction}</i>"

        # Category badge mapping
        category_emoji = {
            "VIP_PREMIUM": "💎",
            "VIP_CONTENT": "👑",
            "FREE_CONTENT": "🌸"
        }

        category_label = {
            "VIP_PREMIUM": "Premium",
            "VIP_CONTENT": "El Diván",
            "FREE_CONTENT": "Promos"
        }

        # Get category value (handle both enum and string)
        category_value = package.category.value if hasattr(package.category, 'value') else str(package.category)
        emoji = category_emoji.get(category_value, "📦")
        label = category_label.get(category_value, "Paquete")

        # Format price
        if package.price is None:
            price_section = "💰 <b>Precio:</b> Acceso promocional"
        else:
            price_section = f"💰 <b>Precio:</b> ${package.price:.2f}"

        # Format description
        description_text = package.description if package.description else "Sin descripción"

        # Build body
        body = (
            f"<b>{emoji} {escape_html(package.name)}</b>\n\n"
            f"<i>{description_text}</i>\n\n"
            f"{price_section}\n"
            f"{emoji} <b>Categoría:</b> {label}\n\n"
            f"<i>{context_closing}</i>"
        )

        text = self._compose(header, body)

        # Create keyboard with action and navigation
        # Use role-specific callback prefixes to avoid router conflicts
        role_prefix = "vip" if user_role == "VIP" else "free"
        content_buttons = [
            [{"text": "⭐ Me interesa", "callback_data": f"{role_prefix}:package:interest:{package.id}"}]
        ]

        # Build back callback with source section for proper navigation
        # source_section helps determine where to return (premium vs free section)
        if source_section:
            back_callback = f"{role_prefix}:packages:back:{user_role}:{source_section}"
        else:
            back_callback = f"{role_prefix}:packages:back"

        keyboard = create_content_with_navigation(
            content_buttons,
            include_back=True,
            include_exit=False,  # Only back button, no exit
            back_text="⬅️ Volver",
            back_callback=back_callback
        )

        return text, keyboard

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _vip_main_menu_keyboard(self, streak_info: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
        """
        Generate keyboard for VIP main menu.

        Args:
            streak_info: Optional dict with streak data (current_streak, can_claim, next_claim_time)

        Returns:
            InlineKeyboardMarkup with VIP navigation options

        Voice Rationale:
            Button text uses Lucien voice terminology:
            - "Tesoros del Sanctum" not "Premium Content"
            - "Estado de la Membresía" not "Subscription Status"
            - Uses create_menu_navigation for consistent "Salir" button
        """
        content_buttons = [
            [{"text": "🛍️ Tienda", "callback_data": "shop_catalog"}],
            [{"text": "📖 Historias", "callback_data": "stories:menu"}],
            [{"text": "💎 Contenido Premium", "callback_data": "vip:premium"}],
            [{"text": "📦 Mi contenido", "callback_data": "vip:free_content"}],
            [{"text": "📊 Estado de la Membresía", "callback_data": "vip:status"}],
        ]

        # Add streak/daily gift button if streak info provided
        if streak_info:
            can_claim = streak_info.get("can_claim", False)
            next_claim_time = streak_info.get("next_claim_time")

            if can_claim:
                content_buttons.insert(0, [{"text": "🎁 Reclamar regalo diario", "callback_data": "streak:claim_daily"}])
            elif next_claim_time:
                time_str = self._format_time_until_next_claim(next_claim_time)
                content_buttons.insert(0, [{"text": f"⏳ Próximo regalo en {time_str}", "callback_data": "streak:status"}])

        return create_content_with_navigation(
            content_buttons,
            include_back=False  # Main menu has no navigation buttons (content only)
        )

    def _free_main_menu_keyboard(self, streak_info: Optional[Dict[str, Any]] = None) -> InlineKeyboardMarkup:
        """
        Generate keyboard for Free main menu.

        Args:
            streak_info: Optional dict with streak data (current_streak, can_claim, next_claim_time)

        Returns:
            InlineKeyboardMarkup with Free navigation options

        Voice Rationale:
            Button text uses Lucien voice terminology:
            - "Muestras del Jardín" not "Browse Content"
            - "Estado de la Cola" not "Queue Status"
            - "Círculo Exclusivo" not "VIP Info"
            - "Jardines Públicos" not "Social Media"
            - Uses create_menu_navigation for consistent "Salir" button
        """
        content_buttons = [
            [{"text": "🛍️ Tienda", "callback_data": "shop_catalog"}],
            [{"text": "📖 Historias", "callback_data": "stories:menu"}],
            [{"text": "📦 Mi contenido", "callback_data": "menu:free:content"}],
            [{"text": "🛋️ El Diván", "callback_data": "menu:free:vip"}],
            [{"text": "🔗 Mis redes", "callback_data": "menu:free:social"}],
        ]

        # Add streak/daily gift button if streak info provided
        if streak_info:
            can_claim = streak_info.get("can_claim", False)
            next_claim_time = streak_info.get("next_claim_time")

            if can_claim:
                content_buttons.insert(0, [{"text": "🎁 Reclamar regalo diario", "callback_data": "streak:claim_daily"}])
            elif next_claim_time:
                time_str = self._format_time_until_next_claim(next_claim_time)
                content_buttons.insert(0, [{"text": f"⏳ Próximo regalo en {time_str}", "callback_data": "streak:status"}])

        return create_content_with_navigation(
            content_buttons,
            include_back=False  # Main menu has no navigation buttons (content only)
        )