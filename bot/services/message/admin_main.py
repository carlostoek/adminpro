"""
Admin Main Messages Provider - Main admin menu messages.

Provides messages for main admin menu navigation and configuration status.
All messages maintain Lucien's sophisticated mayordomo voice from docs/guia-estilo.md.
"""
import random
from typing import Tuple, List, Optional

from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard


class AdminMainMessages(BaseMessageProvider):
    """
    Admin main menu messages provider.

    Voice Characteristics (from docs/guia-estilo.md):
    - Admin = "custodio" (custodian) or "guardián" (guardian)
    - Main menu = "sanctum" or "dominios de Diana"
    - Configuration = "calibración del reino"
    - Uses "usted", never "tú"
    - Emoji 🎩 always present
    - References Diana for authority validation

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI

    Examples:
        >>> provider = AdminMainMessages()
        >>> text, kb = provider.admin_menu_greeting(is_configured=True)
        >>> '🎩' in text and 'custodio' in text.lower()
        True
    """

    def admin_menu_greeting(
        self,
        is_configured: bool,
        missing_items: List[str] = None,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main admin menu greeting with weighted variations.

        Args:
            is_configured: Whether bot is fully configured
            missing_items: List of missing configuration items (if not configured)
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for main admin menu

        Voice Rationale:
            Weighted variations prevent robotic repetition:
            - 50% common greeting (familiar, welcoming)
            - 30% alternate greeting (mystery)
            - 20% rare greeting (poetic)

            Conditional body adapts based on configuration state.
            References "sanctum" and "dominios de Diana" for admin area.

        Examples:
            >>> provider = AdminMainMessages()
            >>> text, kb = provider.admin_menu_greeting(is_configured=False, missing_items=["Canal VIP"])
            >>> 'Canal VIP' in text or 'calibración' in text.lower()
            True

            >>> text, kb = provider.admin_menu_greeting(is_configured=True)
            >>> '✅' in text or 'orden' in text.lower()
            True
        """
        # Weighted greeting variations (common, moderate, rare)
        greetings = [
            ("Ah, el custodio de los dominios de Diana...", 0.5),
            ("Bienvenido de nuevo al sanctum, guardián...", 0.3),
            ("Los portales del reino aguardan su dirección...", 0.2),
        ]

        greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="admin_menu_greeting",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b>\n\n<i>{greeting}</i>"

        # Conditional body based on configuration
        if is_configured:
            body = (
                f"<b>⚙️ Panel de Administración</b>\n\n"
                f"✅ <b>Estado:</b> Todo está en orden.\n\n"
                f"<i>¿Qué aspecto del reino requiere su atención hoy?</i>"
            )
        else:
            if missing_items is None:
                missing_items = []
            missing_text = ", ".join(missing_items)
            body = (
                f"<b>⚙️ Panel de Administración</b>\n\n"
                f"⚠️ <b>Configuración Incompleta</b>\n"
                f"<b>Faltante:</b> {missing_text}\n\n"
                f"<i>Antes de que Diana pueda revelar sus secretos completos, "
                f"el reino requiere cierta... calibración.</i>\n\n"
                f"<i>Permítame asistirle en la configuración.</i>"
            )

        text = self._compose(header, body)
        keyboard = self._admin_main_menu_keyboard()
        return text, keyboard

    def config_menu(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate configuration submenu message.

        Returns:
            Tuple of (text, keyboard) with configuration options

        Voice Rationale:
            "Calibración del reino" maintains elegant terminology.
            "Parámetros" sounds more sophisticated than "settings".
            References Diana's realm to maintain narrative consistency.

        Examples:
            >>> provider = AdminMainMessages()
            >>> text, kb = provider.config_menu()
            >>> 'parámetros' in text.lower() or 'ajustar' in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>La calibración del reino...</i>"

        body = (
            f"<b>⚙️ Menú de Configuración</b>\n\n"
            f"<i>Desde aquí puede ajustar los parámetros del reino según "
            f"las preferencias de Diana...</i>\n\n"
            f"<i>Seleccione el aspecto que desea calibrar, custodio.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._config_menu_keyboard()
        return text, keyboard

    def config_status(
        self,
        vip_reactions: List[str],
        free_reactions: List[str],
        is_vip_configured: bool,
        is_free_configured: bool,
        wait_time: int
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate complete configuration status message.

        Args:
            vip_reactions: List of VIP channel reactions
            free_reactions: List of Free channel reactions
            is_vip_configured: Whether VIP channel is configured
            is_free_configured: Whether Free channel is configured
            wait_time: Wait time for Free channel in minutes

        Returns:
            Tuple of (text, keyboard) with configuration summary

        Voice Rationale:
            "Estado del reino" maintains narrative while being clear.
            Emoji indicators (✅/⚠️) for quick visual scanning.
            "Círculo exclusivo" and "vestíbulo" maintain consistent terminology.

        Examples:
            >>> provider = AdminMainMessages()
            >>> text, kb = provider.config_status(
            ...     vip_reactions=["👑", "🌸"],
            ...     free_reactions=["👍"],
            ...     is_vip_configured=True,
            ...     is_free_configured=False,
            ...     wait_time=5
            ... )
            >>> '👑' in text and '🌸' in text
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Permítame mostrarle el estado del reino...</i>"

        # Build configuration summary
        vip_status_emoji = "✅" if is_vip_configured else "⚠️"
        free_status_emoji = "✅" if is_free_configured else "⚠️"

        vip_reactions_text = " ".join(vip_reactions) if vip_reactions else "<i>No configuradas</i>"
        free_reactions_text = " ".join(free_reactions) if free_reactions else "<i>No configuradas</i>"

        body = (
            f"<b>📊 Estado del Reino</b>\n\n"
            f"<b>👑 Círculo Exclusivo VIP:</b>\n"
            f"{vip_status_emoji} Estado: {'Calibrado' if is_vip_configured else 'Pendiente'}\n"
            f"Reacciones: {vip_reactions_text}\n\n"
            f"<b>📺 Vestíbulo de Acceso (Free):</b>\n"
            f"{free_status_emoji} Estado: {'Calibrado' if is_free_configured else 'Pendiente'}\n"
            f"Reacciones: {free_reactions_text}\n"
            f"Tiempo de contemplación: <b>{wait_time} min</b>\n\n"
            f"<i>Diana observa que todo {'marcha según lo previsto' if is_vip_configured and is_free_configured else 'requiere ciertos ajustes'}...</i>"
        )

        text = self._compose(header, body)
        keyboard = self._config_menu_keyboard()
        return text, keyboard

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _admin_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for main admin menu.

        Returns:
            InlineKeyboardMarkup with admin navigation options

        Voice Rationale:
            Button text uses Lucien voice terminology:
            - "Círculo Exclusivo VIP" not "VIP Channel"
            - "Vestíbulo de Acceso" not "Free Channel"
            - "Paquetes de Contenido" not "Content Packages"
            - "Intereses" not "User Interests"
            - "Gestión de Usuarios" not "User Management"
            - "Calibración del Reino" not "Configuration"
            - "Planes de Suscripción" not "Pricing"
            - "Observaciones del Reino" not "Stats"
        """
        return create_inline_keyboard([
            [{"text": "📊 Dashboard Completo", "callback_data": "admin:dashboard"}],
            [{"text": "👑 Círculo Exclusivo VIP", "callback_data": "admin:vip"}],
            [{"text": "📺 Vestíbulo de Acceso", "callback_data": "admin:free"}],
            [{"text": "📦 Paquetes de Contenido", "callback_data": "admin:content"}],
            [{"text": "📖 Historias", "callback_data": "admin:stories"}],
            [{"text": "📁 ContentSets", "callback_data": "admin:content_sets"}],
            [{"text": "🛍️ Tienda", "callback_data": "admin:shop"}],
            [{"text": "🏆 Recompensas", "callback_data": "admin:rewards"}],
            [{"text": "🔔 Intereses", "callback_data": "admin:interests"}],
            [{"text": "👥 Gestión de Usuarios", "callback_data": "admin:users"}],
            [{"text": "👤 Buscar Usuario", "callback_data": "admin:user:lookup"}],
            [{"text": "⚙️ Calibración del Reino", "callback_data": "admin:config"}],
            [{"text": "💰 Planes de Suscripción", "callback_data": "admin:pricing"}],
            [{"text": "📈 Observaciones del Reino", "callback_data": "admin:stats"}],
            [{"text": "📊 Métricas Economía", "callback_data": "admin:economy_stats"}],
        ])

    def _config_menu_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for configuration submenu.

        Returns:
            InlineKeyboardMarkup with configuration options

        Voice Rationale:
            "Estado del Reino" instead of "View Status"
            "Reacciones del Círculo/Vestíbulo" maintains terminology
        """
        return create_inline_keyboard([
            [{"text": "📊 Estado del Reino", "callback_data": "config:status"}],
            [{"text": "💰 Economía", "callback_data": "admin:economy_config"}],
            [{"text": "👑 Reacciones del Círculo", "callback_data": "config:reactions:vip"}],
            [{"text": "📺 Reacciones del Vestíbulo", "callback_data": "config:reactions:free"}],
            [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}],
        ])
