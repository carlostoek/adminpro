"""
User Flow Messages - Messages for user interaction flows.

Provides messages for Free channel request flow with reassuring, patient tone.
Emphasizes automatic processing and clear expectations.
"""
from bot.services.message.base import BaseMessageProvider


class UserFlowMessages(BaseMessageProvider):
    """
    User flow messages for Free channel access requests.

    Voice Characteristics:
    - **Reassuring**: Users need to know the process is automatic
    - **Clear**: Simple explanations without technical jargon
    - **Patient**: Emphasize no action needed, process is async
    - **Progress-oriented**: Show elapsed/remaining time to reduce anxiety
    - **Lucien's voice**: Maintains "usted", elegant tone, emoji usage

    Terminology:
    - "Solicitud de acceso" (access request) not "cola" (queue)
    - "Proceso automático" (automatic process) to set expectations
    - "Tiempo de espera/contemplación" (wait time) from admin terminology
    - "Le notificaré" (I will notify you) reinforces Lucien's service

    All methods return str (text-only) - Free flow has no keyboards needed.
    Users either wait or close chat, no interactive choices required.

    Examples:
        >>> flows = UserFlowMessages()
        >>> msg = flows.free_request_success(wait_time_minutes=30)
        >>> '⏱️' in msg and '30 minutos' in msg
        True
        >>> msg = flows.free_request_duplicate(10, 20)
        >>> 'transcurrido' in msg and 'restante' in msg
        True
    """

    def __init__(self):
        """
        Initialize UserFlowMessages provider.

        Stateless: no session or bot stored as instance variables.
        """
        super().__init__()

    def free_request_success(self, wait_time_minutes: int) -> str:
        """
        Confirmation message after successful Free request creation.

        Shows wait time prominently and emphasizes automatic process.
        Reassures user they can close chat and will be notified.

        Args:
            wait_time_minutes: Wait time configured for Free channel access

        Returns:
            HTML-formatted confirmation message (text-only, no keyboard)

        Voice Rationale:
            Users need reassurance that:
            1. Request was received (confirmation)
            2. How long they wait (clear expectation)
            3. No action needed (reduce anxiety)
            4. They'll be notified (automatic delivery)

        Examples:
            >>> flows = UserFlowMessages()
            >>> msg = flows.free_request_success(30)
            >>> '30 minutos' in msg
            True
            >>> 'automático' in msg
            True
            >>> '🔔' in msg
            True
        """
        header = "🎩 <b>Excelente</b>"

        body = self._compose(
            "Su solicitud ha sido registrada con éxito.",
            f"⏱️ <b>Tiempo de espera:</b> {wait_time_minutes} minutos",
            (
                "📨 Recibirá un mensaje con el enlace de invitación "
                "cuando el tiempo se cumpla."
            )
        )

        footer = self._compose(
            "💡 <i>No necesita hacer nada más. El proceso es automático.</i>",
            "Puede cerrar este chat. Le notificaré cuando esté listo... 🔔"
        )

        return self._compose(header, body, footer)

    def free_request_duplicate(
        self,
        time_elapsed_minutes: int,
        time_remaining_minutes: int
    ) -> str:
        """
        Message when user tries to request Free access again (duplicate).

        Shows progress (elapsed and remaining time) to reduce user anxiety.
        Polite reminder tone, not scolding.

        Args:
            time_elapsed_minutes: Minutes since original request
            time_remaining_minutes: Minutes until link will be sent

        Returns:
            HTML-formatted reminder message (text-only, no keyboard)

        Voice Rationale:
            Progress indicators prevent user from feeling stuck or forgotten.
            Showing both elapsed and remaining creates sense of movement.
            Polite "ya tiene" instead of "no puede solicitar de nuevo".

        Examples:
            >>> flows = UserFlowMessages()
            >>> msg = flows.free_request_duplicate(10, 20)
            >>> '10 minutos' in msg and '20 minutos' in msg
            True
            >>> 'ya tiene' in msg.lower()
            True
            >>> '⏱️' in msg and '⌛' in msg
            True
        """
        header = "🎩 <b>Solicitud en Proceso</b>"

        body = self._compose(
            "Ya tiene una solicitud de acceso en proceso.",
            (
                f"⏱️ <b>Tiempo transcurrido:</b> {time_elapsed_minutes} minutos\n"
                f"⌛ <b>Tiempo restante:</b> {time_remaining_minutes} minutos"
            )
        )

        footer = self._compose(
            (
                "Recibirá el enlace de acceso automáticamente "
                "cuando el tiempo se cumpla."
            ),
            "💡 <i>Puede cerrar este chat. Le notificaré cuando esté listo.</i>"
        )

        return self._compose(header, body, footer)

    def free_request_error(self, error_type: str, details: str = "") -> str:
        """
        Error message for Free request failures.

        Handles common error scenarios with clear, polite messaging.

        Args:
            error_type: Type of error (channel_not_configured, already_in_channel, rate_limited)
            details: Optional additional details to append

        Returns:
            HTML-formatted error message (text-only, no keyboard)

        Voice Rationale:
            Errors are frustrating - maintain Lucien's polite, helpful tone.
            Clear instructions on what to do (contact admin, wait, etc).
            Avoid technical jargon ("configurado" is clearer than "BD no tiene registro").

        Examples:
            >>> flows = UserFlowMessages()
            >>> msg = flows.free_request_error('channel_not_configured')
            >>> 'administrador' in msg.lower()
            True
            >>> msg = flows.free_request_error('already_in_channel')
            >>> 'ya tiene acceso' in msg.lower()
            True
            >>> msg = flows.free_request_error('rate_limited', 'Espere 1 hora')
            >>> 'frecuentemente' in msg and 'Espere 1 hora' in msg
            True
        """
        error_messages = {
            "channel_not_configured": (
                "⚠️ El canal Free aún no está configurado.\n\n"
                "Por favor, contacte al administrador."
            ),
            "already_in_channel": (
                "ℹ️ Ya tiene acceso al canal Free.\n\n"
                "No necesita solicitarlo nuevamente."
            ),
            "rate_limited": (
                "⏳ Ha solicitado acceso muy frecuentemente.\n\n"
                "Por favor, espere antes de solicitar nuevamente."
            ),
        }

        # Get error message or fallback
        base_message = error_messages.get(
            error_type,
            f"⚠️ Ocurrió un error al procesar su solicitud.\n\nTipo: {error_type}"
        )

        # Append details if provided
        if details:
            return self._compose("🎩 <b>Atención</b>", base_message, details)

        return self._compose("🎩 <b>Atención</b>", base_message)
