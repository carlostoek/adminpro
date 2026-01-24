"""
Admin Free Messages Provider - Free channel management messages.

Provides messages for Free channel setup, wait time configuration, and queue management.
"""
from typing import Tuple
import random
from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard
from bot.utils.formatters import format_duration_minutes


class AdminFreeMessages(BaseMessageProvider):
    """
    Admin Free channel management messages provider.

    Voice Characteristics (from docs/guia-estilo.md):
    - Free channel = "vestíbulo" (vestibule/entry)
    - Wait time = "tiempo de contemplación" (contemplation time)
    - Queue = "lista de espera" (waiting list)
    - Uses "usted", never "tú"
    - Emoji 🎩 always present
    - References Diana for authority validation

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI
    """

    def free_menu(
        self,
        is_configured: bool,
        channel_name: str = "Canal Free",
        wait_time_minutes: int = 0,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate Free menu message with conditional content.

        Args:
            is_configured: Whether Free channel is configured
            channel_name: Name of the Free channel
            wait_time_minutes: Current wait time in minutes
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            Weighted variations prevent robotic repetition while maintaining
            Lucien's mysterious but helpful mayordomo voice. "Vestíbulo"
            implies entry to Diana's exclusive realm.
        """
        # Weighted greeting variations (common, moderate, rare)
        greetings = [
            ("El vestíbulo de Diana permanece accesible, custodio...", 0.5),
            ("La antesala del círculo exclusivo aguarda su calibración...", 0.3),
            ("Bienvenido a la zona de preparación...", 0.2),
        ]

        greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="free_menu",
            session_history=session_history
        )

        if is_configured:
            wait_time_str = format_duration_minutes(wait_time_minutes)
            body = (
                f"✅ Canal configurado: <b>{channel_name}</b>\n"
                f"⏱️ Tiempo de contemplación: <b>{wait_time_str}</b>\n\n"
                f"Desde aquí administra el acceso al vestíbulo, custodio."
            )
            keyboard = self._free_configured_keyboard()
        else:
            body = (
                "⚠️ El vestíbulo aún no ha sido calibrado.\n\n"
                "Configure el canal para que los visitantes puedan solicitar su entrada."
            )
            keyboard = self._free_unconfigured_keyboard()

        text = self._compose("🎩 <b>Gestión del Vestíbulo</b>", greeting + "\n\n" + body)

        return (text, keyboard)

    def setup_channel_prompt(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Prompt for Free channel setup via forwarded message.

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            "Calibración" implies precision and care, matching Lucien's
            attention to detail. Instructions are clear but elegant.
        """
        text = self._compose(
            "🎩 <b>Calibrar el Vestíbulo</b>",
            (
                "Para configurar el canal del vestíbulo:\n\n"
                "1️⃣ Vaya al canal Free\n"
                "2️⃣ Reenvíe cualquier mensaje del canal a este chat\n"
                "3️⃣ Extraeré el identificador automáticamente\n\n"
                "⚠️ <b>Importante:</b>\n"
                "- El bot debe ser administrador del canal\n"
                "- El bot debe tener permiso para invitar usuarios\n\n"
                "👉 Reenvíe un mensaje del canal ahora..."
            )
        )

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "admin:free"}]
        ])

        return (text, keyboard)

    def channel_configured_success(
        self,
        channel_name: str,
        channel_id: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Success message after Free channel configuration.

        Args:
            channel_name: Name of the configured channel
            channel_id: ID of the configured channel

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            Success with Diana reference maintains authority.
            "Vestíbulo está listo" indicates preparedness for visitors.
        """
        text = self._compose(
            "🎩 <b>Vestíbulo Calibrado</b>",
            (
                f"✅ El vestíbulo está listo para recibir visitantes.\n\n"
                f"Canal: <b>{channel_name}</b>\n"
                f"ID: <code>{channel_id}</code>\n\n"
                f"Diana observa que los solicitantes ya pueden pedir su entrada..."
            )
        )

        keyboard = create_inline_keyboard([
            [{"text": "📋 Ver Lista de Espera", "callback_data": "free:view_queue"}],
            [{"text": "🔙 Volver", "callback_data": "admin:free"}]
        ])

        return (text, keyboard)

    def wait_time_setup_prompt(self, current_wait_time: int) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Prompt for wait time configuration.

        Args:
            current_wait_time: Current wait time in minutes

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            "Tiempo de contemplación" adds mystique to wait time.
            Clear instructions with example maintain usability.
        """
        wait_time_str = format_duration_minutes(current_wait_time)

        text = self._compose(
            "🎩 <b>Configurar Tiempo de Contemplación</b>",
            (
                f"Tiempo actual: <b>{wait_time_str}</b>\n\n"
                f"Envíe el nuevo tiempo de espera en minutos.\n"
                f"Ejemplo: <code>5</code>\n\n"
                f"El tiempo debe ser mayor o igual a 1 minuto.\n\n"
                f"Este es el período que los visitantes esperarán "
                f"antes de recibir su invitación al vestíbulo."
            )
        )

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "admin:free"}]
        ])

        return (text, keyboard)

    def wait_time_updated(self, new_wait_time: int) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Success message after wait time update.

        Args:
            new_wait_time: New wait time in minutes

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            Confirmation with poetic "tiempo de contemplación" language.
        """
        wait_time_str = format_duration_minutes(new_wait_time)

        text = self._compose(
            "🎩 <b>Tiempo Actualizado</b>",
            (
                f"✅ El período de contemplación ha sido ajustado.\n\n"
                f"Nuevo tiempo: <b>{wait_time_str}</b>\n\n"
                f"Las nuevas solicitudes esperarán {wait_time_str} "
                f"antes de que Diana les conceda el acceso."
            )
        )

        keyboard = self._free_configured_keyboard()

        return (text, keyboard)

    def invalid_wait_time_input(self, reason: str = "invalid") -> Tuple[str, InlineKeyboardMarkup]:
        """
        Error message for invalid wait time input.

        Args:
            reason: Reason for invalidity ("not_number", "too_low", or "invalid")

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            Errors are presented as gentle corrections, maintaining Lucien's
            helpful but sophisticated demeanor.
        """
        if reason == "not_number":
            body = (
                "Hmm... parece que ese no es un número válido.\n\n"
                "Envíe un número en minutos, custodio.\n"
                "Ejemplo: <code>5</code>"
            )
        elif reason == "too_low":
            body = (
                "El tiempo debe ser al menos 1 minuto.\n\n"
                "Diana prefiere que los visitantes tengan "
                "un período mínimo de contemplación..."
            )
        else:
            body = (
                "Algo inesperado ocurrió con ese valor.\n\n"
                "Intente nuevamente con un número de minutos válido."
            )

        text = self._compose("🎩 <b>Entrada No Válida</b>", body)

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "admin:free"}]
        ])

        return (text, keyboard)

    def config_menu(self, wait_time_minutes: int) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Free configuration submenu.

        Args:
            wait_time_minutes: Current wait time in minutes

        Returns:
            Tuple of (message_text, inline_keyboard)

        Voice Rationale:
            Configuration presented as "ajustes del vestíbulo" maintains
            narrative consistency.
        """
        wait_time_str = format_duration_minutes(wait_time_minutes)

        text = self._compose(
            "🎩 <b>Ajustes del Vestíbulo</b>",
            (
                f"⏱️ Tiempo de contemplación actual: <b>{wait_time_str}</b>\n\n"
                f"Seleccione el aspecto que desea ajustar, custodio."
            )
        )

        keyboard = self._free_config_submenu_keyboard()

        return (text, keyboard)

    # ===== PRIVATE KEYBOARD FACTORIES =====

    def _free_configured_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard for configured Free menu."""
        return create_inline_keyboard([
            [{"text": "📤 Enviar Publicación", "callback_data": "free:broadcast"}],
            [{"text": "📋 Cola de Solicitudes", "callback_data": "free:view_queue"}],
            [{"text": "⚙️ Configuración", "callback_data": "free:config"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

    def _free_unconfigured_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard for unconfigured Free menu."""
        return create_inline_keyboard([
            [{"text": "⚙️ Configurar Canal Free", "callback_data": "free:setup"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

    def _free_config_submenu_keyboard(self) -> InlineKeyboardMarkup:
        """Keyboard for Free config submenu."""
        return create_inline_keyboard([
            [{"text": "⏱️ Cambiar Tiempo de Espera", "callback_data": "free:set_wait_time"}],
            [{"text": "🔧 Reconfigurar Canal", "callback_data": "free:setup"}],
            [{"text": "🔙 Volver", "callback_data": "admin:free"}]
        ])
