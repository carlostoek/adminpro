"""
Common Messages Provider - Shared messages for all flows.

This module provides commonly used messages (errors, success, not_found)
that maintain Lucien's voice consistently across all bot interactions.
"""
from typing import Optional

from bot.utils.formatters import escape_html
from .base import BaseMessageProvider


class CommonMessages(BaseMessageProvider):
    """
    Common messages provider for shared messages across all flows.

    Provides error messages, success messages, and generic responses
    that maintain Lucien's sophisticated voice consistently.

    Voice Characteristics (from docs/guia-estilo.md):
    - Mayordomo sofisticado y elegante
    - Nunca es directo, siempre sugiere e insinúa
    - Usa "usted", nunca tutea
    - Emplea pausas dramáticas con "..."
    - Emoji 🎩 siempre presente

    Anti-Patterns Validated:
    - NO: "Error, algo falló" (too direct, technical)
    - NO: "Oye, tienes un problema" (tutea, breaks voice)
    - NO: "❌ Error" (wrong emoji for Lucien)

    Correct Pattern:
    - YES: "🎩 Hmm... algo inesperado ha ocurrido." (elegant, mysterious)
    """

    def error(
        self,
        context: str = "",
        suggestion: str = "",
        include_footer: bool = True
    ) -> str:
        """
        Generate error message in Lucien's voice.

        Args:
            context: What operation failed (e.g., "al generar el token")
            suggestion: Optional suggestion for resolution
            include_footer: Whether to include helpful footer

        Returns:
            HTML-formatted error message

        Voice Rationale:
            Errors are "inconvenientes" or "imprevistos" not system failures.
            Lucien maintains calm sophistication even when things go wrong.
            Consults "Diana" for serious issues (mysterious authority).

        Examples:
            >>> common = CommonMessages()
            >>> msg = common.error("al procesar su solicitud")
            >>> '🎩' in msg and 'Lucien' in msg
            True

            >>> msg = common.error("al configurar el canal", "Verifique que soy administrador")
            >>> 'Sugerencia' in msg and 'administrador' in msg
            True
        """
        # Header
        header = "🎩 <b>Lucien:</b>"

        # Body with context
        if context:
            body = f"<i>Hmm... algo inesperado ha ocurrido {context}.\nPermítame consultar con Diana sobre este inconveniente.</i>"
        else:
            body = "<i>Hmm... algo inesperado ha ocurrido.\nPermítame consultar con Diana sobre este inconveniente.</i>"

        # Optional suggestion
        if suggestion:
            body += f"\n\n💡 <i>Sugerencia:</i> {suggestion}"

        # Optional footer
        footer = ""
        if include_footer:
            footer = "<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"

        return self._compose(header, body, footer)

    def success(
        self,
        action: str,
        detail: str = "",
        celebrate: bool = False
    ) -> str:
        """
        Generate success message in Lucien's voice.

        Args:
            action: What was accomplished (e.g., "canal configurado")
            detail: Optional additional detail
            celebrate: Whether to add celebratory tone

        Returns:
            HTML-formatted success message

        Voice Rationale:
            Success is "excelente elección" or "como se esperaba" (understated).
            Diana approves of successful actions (authority validation).
            Never overly enthusiastic - maintains sophistication.

        Examples:
            >>> common = CommonMessages()
            >>> msg = common.success("token generado")
            >>> 'Excelente' in msg and 'token generado' in msg
            True

            >>> msg = common.success("canal VIP configurado", "Todo está listo", celebrate=True)
            >>> 'Diana aprobará' in msg
            True
        """
        # Header
        header = "🎩 <b>Lucien:</b>"

        # Body
        if celebrate:
            body = f"<i>Excelente. {action} ha sido completado como se esperaba.\nDiana aprobará este progreso...</i>"
        else:
            body = f"<i>Excelente. {action} ha sido completado como se esperaba.</i>"

        # Optional detail
        if detail:
            body += f"\n\n{detail}"

        return self._compose(header, body)

    def generic_error(self, error_type: str = "unknown") -> str:
        """
        Generate generic error message for unexpected failures.

        Args:
            error_type: Type of error (for logging, not shown to user)

        Returns:
            HTML-formatted generic error message

        Voice Rationale:
            When something truly unexpected happens, Lucien maintains composure.
            "Perturbación" conveys something disturbed the natural order.
            Still offers assistance without breaking character.

        Examples:
            >>> common = CommonMessages()
            >>> msg = common.generic_error()
            >>> 'Perturbación' in msg or 'perturbación' in msg
            True

            >>> msg = common.generic_error("database")
            >>> 'discreción' in msg.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>"
        body = "<i>Una perturbación inesperada ha interrumpido el flujo natural de las cosas...</i>\n\n<i>Permítame un momento para restablecer el orden. Diana prefiere que estos asuntos se manejen con discreción.</i>"
        footer = "<i>¿Le gustaría intentar nuevamente?</i>"

        return self._compose(header, body, footer)

    def not_found(self, item_type: str, identifier: str = "") -> str:
        """
        Generate 'not found' message in Lucien's voice.

        Args:
            item_type: What wasn't found (e.g., "token", "suscriptor")
            identifier: Optional identifier (e.g., token value, user ID)

        Returns:
            HTML-formatted not found message

        Voice Rationale:
            Not found is "parece que no puedo localizar" not "ERROR NOT FOUND".
            Lucien takes responsibility ("he buscado en todos los archivos").
            Maintains helpfulness without breaking character.

        Examples:
            >>> common = CommonMessages()
            >>> msg = common.not_found("token", "ABC123")
            >>> 'ABC123' in msg and '<code>' in msg
            True

            >>> msg = common.not_found("suscriptor")
            >>> 'archivos' in msg and 'Diana' in msg
            True
        """
        header = "🎩 <b>Lucien:</b>"

        if identifier:
            escaped_id = escape_html(identifier)
            body = f"<i>He buscado en todos los archivos de Diana, pero parece que no puedo localizar este {item_type}.</i>\n\n<code>{escaped_id}</code>\n\n<i>¿Podría verificar que la información es correcta?</i>"
        else:
            body = f"<i>He buscado en todos los archivos de Diana, pero parece que no puedo localizar este {item_type}.</i>\n\n<i>¿Podría proporcionarme más detalles?</i>"

        footer = "<i>Estoy a su disposición para continuar la búsqueda...</i>"

        return self._compose(header, body, footer)
