"""
VIP Entry Flow Messages - Lucien's voice for 3-stage ritual admission.

Phase 13: Ritualized VIP entry flow with sequential stages:
- Stage 1: Activation confirmation (mysterious acknowledgment)
- Stage 2: Expectation alignment (intimate warning)
- Stage 3: Access delivery (dramatic link delivery)

Voice Rationale:
- No variations - every VIP gets same ritual (consistency over novelty)
- Continuous flow - messages reference each other as extended conversation
- 🎩 emoji only - no stage-specific emojis (maintains visual identity)
- Abstract time - show "24 hours" not timestamp (mystery over precision)
"""
import logging
from typing import Tuple, List, Dict, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.message.base import BaseMessageProvider

logger = logging.getLogger(__name__)


class VIPEntryFlowMessages(BaseMessageProvider):
    """
    Message provider for VIP ritual entry flow.

    Provides 5 message methods for 3-stage admission ritual:
    - Stage 1: Activation confirmation with "Continuar" button
    - Stage 2: Expectation alignment with "Estoy listo" button
    - Stage 3: Access delivery with embedded "Entrar al Diván" link button
    - Expiry: Lucien-voiced blocking message for expired subscriptions
    - Resumption: Seamless return to current stage after abandonment

    All messages use Lucien's voice with 🎩 emoji (no variations).
    """

    def __init__(self):
        """Initialize provider (stateless, no dependencies)."""
        super().__init__()
        logger.debug("✅ VIPEntryFlowMessages inicializado")

    # ===== STAGE 1: ACTIVATION CONFIRMATION =====

    def stage_1_activation_confirmation(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Stage 1: Mysterious acknowledgment emphasizing exclusivity.

        Message: "Veo que ha dado el paso que muchos contemplan... y pocos toman."
        Button: "Continuar" (advances to Stage 2)

        Returns:
            Tuple of (message_text, keyboard_markup)

        Voice Rationale:
            Creates mystery and exclusivity perception.
            References "few take this step" to validate user's commitment.
            Hints at something important to know before access (builds anticipation).
        """
        # Message body (exact wording from spec)
        body = """Veo que ha dado el paso que muchos contemplan… y pocos toman.

Su acceso al Diván de Diana está siendo preparado.

Este no es un espacio público.
No es un canal más.
Y definitivamente no es para quien solo siente curiosidad.

Antes de entregarle la entrada, hay algo que debe saber…"""

        # Format with Lucien's header
        message = f"🎩 Lucien:\n\n{body}"

        # Create keyboard with "Continuar" button
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="Continuar",
            callback_data="vip_entry:stage_2"
        )

        return message, keyboard.as_markup()

    # ===== STAGE 2: EXPECTATION ALIGNMENT =====

    def stage_2_expectation_alignment(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Stage 2: Intimate warning about the nature of the space.

        Message: "El Diván no es un lugar donde se mira y se olvida..."
        Button: "Estoy listo" (commits to Stage 3)

        Returns:
            Tuple of (message_text, keyboard_markup)

        Voice Rationale:
            Sets expectations about intimate, unfiltered content.
            Warns about "no masks" and "real presence" required.
            Gives opportunity to opt out before final commitment.
        """
        # Message body (exact wording from spec)
        body = """El Diván no es un lugar donde se mira y se olvida.
Es un espacio íntimo, sin filtros, sin máscaras.

Aquí Diana se muestra sin la distancia de las redes,
y eso exige discreción, respeto y presencia real.

Si ha llegado hasta aquí solo para observar de paso…
este es el momento de detenerse.

Si entiende lo que significa entrar… entonces sí."""

        # Format with Lucien's header
        message = f"🎩 Lucien:\n\n{body}"

        # Create keyboard with "Estoy listo" button
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="Estoy listo",
            callback_data="vip_entry:stage_3"
        )

        return message, keyboard.as_markup()

    # ===== STAGE 3: ACCESS DELIVERY =====

    def stage_3_access_delivery(
        self,
        invite_link: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Stage 3: Dramatic delivery with VIP channel invite link.

        Message: "Entonces no le haré esperar más. Diana le abre la puerta..."
        Button: "Entrar al Diván" -> opens invite link

        Args:
            invite_link: VIP channel invite link URL

        Returns:
            Tuple of (message_text, keyboard_markup)

        Voice Rationale:
            Dramatic culmination of ritual ("no le haré esperar más").
            Emphasizes link is personal, non-shareable, expires with subscription.
            Abstract time ("24 hours") not timestamp (mystery over precision).
            Direct delivery - no acknowledgment of "Estoy listo" click.
        """
        # Message body (exact wording from spec)
        body = """Entonces no le haré esperar más.

Diana le abre la puerta al Diván.

Este acceso es personal.
No se comparte.
No se replica.
Y se cierra cuando el vínculo termina.

Tiene 24 horas para usar el enlace.

Entre con intención.

—

Y yo le invito a volver conmigo, notará que algunas cosas aquí ya no se ven igual.
El espacio se adapta a quienes cruzan.

👇"""

        # Format with Lucien's header
        message = f"🎩 Lucien:\n\n{body}"

        # Create keyboard with both buttons
        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="Entrar al Diván ✨",
            url=invite_link  # URL button, not callback
        )
        keyboard.button(
            text="Descubrir lo que cambió",
            callback_data="vip_entry:main_menu"
        )

        return message, keyboard.as_markup()

    # ===== EXPIRY & CANCELLATION =====

    def expired_subscription_message(self) -> str:
        """
        Lucien-voiced expiry message blocking further progress.

        Shown when VIPSubscriber expires during Stages 1-2.

        Returns:
            Message text (no keyboard - flow blocked)

        Voice Rationale:
            Consistent with ritual tone (not neutral system message).
            Maintains mystery even in rejection.
            No retry option - subscription must be renewed.
        """
        # Claude's discretion: Use Lucien's voice for expiry
        message = """🎩 Lucien:

El tiempo en el Diván es limitado… y su tiempo ha concluido.

El vínculo que le permitía el acceso se ha disuelto.

Si desea volver al círculo, deberá renovar su conexión.

El umbral permanece cerrado hasta entonces."""

        return message

    def stage_resumption_message(self, stage: int) -> str:
        """
        Seamless return to current stage after abandonment.

        Shown when user returns to flow after leaving (no time limit).

        Args:
            stage: Current vip_entry_stage (1, 2, or 3)

        Returns:
            Message text (no keyboard - uses stage-specific keyboard)

        Voice Rationale:
            No acknowledgment of time gap (seamless resumption).
            Brief reminder of current stage context.
            Does NOT show "you've been away" message (breaks immersion).
        """
        if stage == 1:
            return "🎩 Lucien:\n\nContinuemos donde nos quedamos."
        elif stage == 2:
            return "🎩 Lucien:\n\nEstaba a punto de contarle lo que debe saber."
        elif stage == 3:
            return "🎩 Lucien:\n\nLa puerta está abierta. El enlace espera."
        else:
            return "🎩 Lucien:\n\nContinuemos."
