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
from bot.utils.keyboards import create_inline_keyboard
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
            # Format date elegantly
            expiry_text = vip_expires_at.strftime("%d de %B de %Y")
            subscription_status = f"<b>⏳ Su membresía expira el {expiry_text}</b>"
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
        Generate VIP premium content section.

        Args:
            user_name: User's first name (will be HTML-escaped)
            packages: List of ContentPackage objects for VIP premium content
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for VIP premium content listing

        Voice Rationale:
            VIP premium content is "tesoros del sanctum" (sanctum treasures).
            Package count shown: "[count] tesoros disponibles"
            Dynamic "Me interesa" buttons generated from ContentPackage list.

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> packages = [ContentPackage(id=1, title="Tesoro 1"), ContentPackage(id=2, title="Tesoro 2")]
            >>> text, kb = provider.vip_premium_section("Juan", packages)
            >>> '🎩' in text and 'Juan' in text
            True
            >>> 'tesoros' in text.lower() and '2' in text
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

        package_count = len(packages)
        body = (
            f"<b>💎 Sección Premium VIP</b>\n\n"
            f"<b>{safe_name}</b>, estos son los tesoros disponibles:\n\n"
            f"<b>📦 {package_count} tesoros disponibles</b>\n\n"
            f"<i>Seleccione aquellos que despierten su interés...</i>"
        )

        text = self._compose(header, body)

        # Create keyboard with package buttons and navigation
        package_buttons = self._create_package_buttons(packages)
        keyboard_rows = package_buttons + [
            [{"text": "🔙 Volver al Menú VIP", "callback_data": "menu:vip:main"}],
            [{"text": "🚪 Salir", "callback_data": "menu:exit"}]
        ]
        keyboard = create_inline_keyboard(keyboard_rows)

        return text, keyboard

    def free_content_section(
        self,
        user_name: str,
        packages: List[ContentPackage],
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate Free content browsing section.

        Args:
            user_name: User's first name (will be HTML-escaped)
            packages: List of ContentPackage objects for Free content
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for Free content listing

        Voice Rationale:
            Free content is "muestras del jardín" (garden samples).
            Package count shown: "[count] muestras disponibles"
            Dynamic "Me interesa" buttons generated from ContentPackage list.

        Examples:
            >>> provider = UserMenuMessages()
            >>> from bot.database.models import ContentPackage
            >>> packages = [ContentPackage(id=1, title="Muestra 1"), ContentPackage(id=2, title="Muestra 2")]
            >>> text, kb = provider.free_content_section("Ana", packages)
            >>> '🎩' in text and 'Ana' in text
            True
            >>> 'muestras' in text.lower() and '2' in text
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

        package_count = len(packages)
        body = (
            f"<b>🌸 Sección de Contenido Free</b>\n\n"
            f"<b>{safe_name}</b>, estas son las muestras disponibles:\n\n"
            f"<b>📦 {package_count} muestras disponibles</b>\n\n"
            f"<i>Seleccione aquellas que despierten su curiosidad...</i>"
        )

        text = self._compose(header, body)

        # Create keyboard with package buttons and navigation
        package_buttons = self._create_package_buttons(packages)
        keyboard_rows = package_buttons + [
            [{"text": "🔙 Volver al Menú Free", "callback_data": "menu:free:main"}],
            [{"text": "🚪 Salir", "callback_data": "menu:exit"}]
        ]
        keyboard = create_inline_keyboard(keyboard_rows)

        return text, keyboard

    def _create_package_buttons(self, packages: List[ContentPackage]) -> List[List[dict]]:
        """
        Convierte lista de ContentPackage a filas de botones "Me interesa".

        Args:
            packages: Lista de ContentPackage objects

        Returns:
            Lista de filas de botones para create_inline_keyboard
        """
        if not packages:
            return []

        buttons = []
        for package in packages:
            # Truncate title if too long for button text
            title = package.title
            if len(title) > 30:
                title = title[:27] + "..."

            button_row = [{
                "text": f"⭐ {title} - Me interesa",
                "callback_data": f"interest:package:{package.id}"
            }]
            buttons.append(button_row)

        return buttons

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
            - "Salir" maintains elegance
        """
        return create_inline_keyboard([
            [{"text": "💎 Tesoros del Sanctum", "callback_data": "menu:vip:premium"}],
            [{"text": "📊 Estado de la Membresía", "callback_data": "menu:vip:status"}],
            [{"text": "🚪 Salir", "callback_data": "menu:exit"}]
        ])

    def _free_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for Free main menu.

        Returns:
            InlineKeyboardMarkup with Free navigation options

        Voice Rationale:
            Button text uses Lucien voice terminology:
            - "Muestras del Jardín" not "Browse Content"
            - "Estado de la Cola" not "Queue Status"
            - "Salir" maintains elegance
        """
        return create_inline_keyboard([
            [{"text": "🌸 Muestras del Jardín", "callback_data": "menu:free:content"}],
            [{"text": "🕐 Estado de la Cola", "callback_data": "menu:free:queue"}],
            [{"text": "🚪 Salir", "callback_data": "menu:exit"}]
        ])