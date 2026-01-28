"""
User Menu Messages Provider - VIP and Free user menu messages.

Provides messages for VIP and Free user menus with Lucien's voice consistency.
All messages maintain Lucien's sophisticated mayordomo voice from docs/guia-estilo.md.

VIP users: "miembros del círculo exclusivo" (exclusive circle members)
Free users: "visitantes del jardín público" (public garden visitors)
VIP premium content: "tesoros del sanctum" (sanctum treasures)
Free content: "muestras del jardín" (garden samples)
"""
import random
from datetime import datetime
from typing import Tuple, List, Optional

from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard, create_menu_navigation, create_content_with_navigation
from bot.utils.formatters import escape_html
from bot.database.models import ContentPackage


class UserMenuMessages(BaseMessageProvider):
    """
    User menu messages provider for VIP and Free user menus.

    Voice Characteristics (from docs/guia-estilo.md):
    - VIP users = "miembros del círculo exclusivo" (exclusive circle members)
    - Free users = "visitantes del jardín público" (public garden visitors)
    - VIP premium content = "tesoros del sanctum" (sanctum treasures)
    - Free content = "muestras del jardín" (garden samples)
    - Uses "usted", never "tú"
    - Emoji 🎩 always present
    - References Diana for authority/mystique
    - Subscription status shown elegantly (expiration dates, queue positions)

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI
    - Uses create_content_with_navigation for consistent navigation buttons

    Examples:
        >>> provider = UserMenuMessages()
        >>> text, kb = provider.vip_menu_greeting("Juan", vip_expires_at=datetime.now())
        >>> '🎩' in text and 'círculo exclusivo' in text.lower()
        True
        >>> text, kb = provider.free_menu_greeting("Ana", free_queue_position=5)
        >>> 'jardín público' in text.lower() and '5' in text
        True
    """

    def __init__(self):
        """
        Initialize UserMenuMessages provider.

        Stateless: no session or bot stored.
        """
        super().__init__()

    def vip_menu_greeting(
        self,
        user_name: str,
        vip_expires_at: Optional[datetime] = None,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main VIP menu greeting with subscription info placeholders.

        Args:
            user_name: User's first name (will be HTML-escaped)
            vip_expires_at: Optional datetime when VIP subscription expires
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for VIP main menu

        Voice Rationale:
            Weighted variations prevent robotic repetition:
            - 60% common greeting (familiar, welcoming)
            - 30% alternate greeting (mystery)
            - 10% poetic greeting (rare, special)

            VIP users are "miembros del círculo exclusivo" (exclusive circle members).
            Subscription expiration shown elegantly: "Su membresía expira el [fecha]"
            or "Su membresía es permanente" for permanent access.

        Examples:
            >>> provider = UserMenuMessages()
            >>> text, kb = provider.vip_menu_greeting("Juan", vip_expires_at=datetime.now())
            >>> '🎩' in text and 'Juan' in text
            True
            >>> 'círculo exclusivo' in text.lower()
            True
        """
        safe_name = escape_html(user_name)

        # Weighted greeting variations (common, alternate, poetic)
        greetings = [
            ("Ah, un miembro del círculo exclusivo...", 0.6),
            ("Bienvenido de nuevo al sanctum...", 0.3),
            ("Los portales del reino se abren para usted...", 0.1),
        ]

        greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="vip_menu_greeting",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{greeting}</i>"

        # Subscription status section
        if vip_expires_at:
            # Check if subscription is still active (not expired)
            from datetime import datetime
            if vip_expires_at > datetime.utcnow():
                # Active subscription - show expiry date
                expiry_text = vip_expires_at.strftime("%d de %B de %Y")
                subscription_status = f"<b>⏳ Su membresía expira el {expiry_text}</b>"
            else:
                # Expired subscription - show warning
                subscription_status = f"<b>⚠️ Su membresía ha expirado</b>"
        else:
            subscription_status = "<b>✨ Su membresía es permanente</b>"

        body = (
            f"<b>👑 Menú del Círculo Exclusivo</b>\n\n"
            f"Bienvenido, <b>{safe_name}</b>.\n\n"
            f"{subscription_status}\n\n"
            f"<i>¿Qué tesoros del sanctum desea explorar hoy?</i>"
        )

        text = self._compose(header, body)
        keyboard = self._vip_main_menu_keyboard()
        return text, keyboard

    def free_menu_greeting(
        self,
        user_name: str,
        free_queue_position: Optional[int] = None,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main Free menu greeting with content browsing.

        Args:
            user_name: User's first name (will be HTML-escaped)
            free_queue_position: Optional position in Free channel queue
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for Free main menu

        Voice Rationale:
            Weighted variations:
            - 70% welcoming (familiar, reassuring)
            - 30% informative (educational, guiding)

            Free users are "visitantes del jardín público" (public garden visitors).
            Queue status shown if applicable: "Su posición en la cola: [número]"
            Content browsing emphasized as "muestras del jardín" (garden samples).

        Examples:
            >>> provider = UserMenuMessages()
            >>> text, kb = provider.free_menu_greeting("Ana", free_queue_position=5)
            >>> '🎩' in text and 'Ana' in text
            True
            >>> 'jardín público' in text.lower()
            True
            >>> '5' in text  # Queue position
            True
        """
        safe_name = escape_html(user_name)

        # Weighted greeting variations (welcoming, informative)
        greetings = [
            ("Bienvenido al jardín público...", 0.7),
            ("El vestíbulo de acceso aguarda su contemplación...", 0.3),
        ]

        greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="free_menu_greeting",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{greeting}</i>"

        # Queue status section (if applicable)
        queue_status = ""
        if free_queue_position is not None and free_queue_position > 0:
            queue_status = (
                f"<b>🕐 Su posición en la cola:</b> <code>{free_queue_position}</code>\n\n"
            )

        body = (
            f"<b>📺 Menú del Vestíbulo de Acceso</b>\n\n"
            f"Bienvenido, <b>{safe_name}</b>.\n\n"
            f"{queue_status}"
            f"<i>Explore las muestras del jardín que Diana ha dispuesto "
            f"para los visitantes del vestíbulo...</i>"
        )

        text = self._compose(header, body)
        keyboard = self._free_main_menu_keyboard()
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
            [{"text": f"📦 {pkg.name}", "callback_data": f"user:packages:{pkg.id}"}]
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
        safe_name = escape_html(user_name)

        # Weighted section introductions
        introductions = [
            "Las muestras del jardín...",
            "Diana permite que estos fragmentos sean contemplados...",
            "El jardín público revela sus muestras..."
        ]

        introduction = self._choose_variant(
            introductions,
            user_id=user_id,
            method_name="free_content_section",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{introduction}</i>"

        # Sort packages by price (free first, then ascending)
        sorted_packages = self._sort_packages_by_price(packages)

        body = (
            f"<b>🌸 Sección de Contenido Free</b>\n\n"
            f"<b>{safe_name}</b>, explore las muestras del jardín...\n\n"
            f"<i>Seleccione un paquete para ver detalles completos antes de manifestar interés...</i>"
        )

        text = self._compose(header, body)

        # Create minimalist package buttons (one per row, name only)
        package_buttons = [
            [{"text": f"📦 {pkg.name}", "callback_data": f"user:packages:{pkg.id}"}]
            for pkg in sorted_packages
        ]

        keyboard = create_content_with_navigation(
            package_buttons,
            back_text="⬅️ Volver al Menú Free",
            back_callback="menu:free:main"
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
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate detailed package view with all user-facing information.

        Args:
            package: ContentPackage object to display
            user_role: User role for context-aware messages ("VIP" or "Free")
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for package detail view

        Voice Rationale:
            Shows complete package information before user registers interest.
            Price formatted elegantly: "Acceso gratuito" for None, "$X.XX" for paid.
            Category badges with emoji: VIP_PREMIUM="💎", VIP_CONTENT="👑", FREE_CONTENT="🌸".
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
            "VIP_PREMIUM": "Premium Exclusivo",
            "VIP_CONTENT": "Contenido VIP",
            "FREE_CONTENT": "Contenido Gratuito"
        }

        # Get category value (handle both enum and string)
        category_value = package.category.value if hasattr(package.category, 'value') else str(package.category)
        emoji = category_emoji.get(category_value, "📦")
        label = category_label.get(category_value, "Paquete")

        # Format price
        if package.price is None:
            price_section = "💰 <b>Precio:</b> Acceso gratuito"
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
        content_buttons = [
            [{"text": "⭐ Me interesa", "callback_data": f"user:package:interest:{package.id}"}]
        ]

        keyboard = create_content_with_navigation(
            content_buttons,
            include_back=True,
            include_exit=False,  # Only back button, no exit
            back_text="⬅️ Volver",
            back_callback="user:packages:back"
        )

        return text, keyboard

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _vip_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for VIP main menu.

        Returns:
            InlineKeyboardMarkup with VIP navigation options

        Voice Rationale:
            Button text uses Lucien voice terminology:
            - "Tesoros del Sanctum" not "Premium Content"
            - "Estado de la Membresía" not "Subscription Status"
            - Uses create_menu_navigation for consistent "Salir" button
        """
        content_buttons = [
            [{"text": "💎 Tesoros del Sanctum", "callback_data": "vip:premium"}],
            [{"text": "📊 Estado de la Membresía", "callback_data": "vip:status"}],
        ]
        return create_content_with_navigation(
            content_buttons,
            include_back=False  # Main menu has no navigation buttons (content only)
        )

    def _free_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for Free main menu.

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
            [{"text": "🌸 Muestras del Jardín", "callback_data": "menu:free:content"}],
            [{"text": "⭐ Círculo Exclusivo", "callback_data": "menu:free:vip"}],
            [{"text": "🌺 Jardines Públicos", "callback_data": "menu:free:social"}],
        ]
        return create_content_with_navigation(
            content_buttons,
            include_back=False  # Main menu has no navigation buttons (content only)
        )