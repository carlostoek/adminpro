"""
User Flow Messages - Messages for user interaction flows.

Provides messages for Free channel request flow with Lucien's voice.
Social media keyboard generation and approval messages included.
"""
from typing import Optional

from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard


class UserFlowMessages(BaseMessageProvider):
    """
    User flow messages for Free channel access requests with Lucien's voice.

    Voice Characteristics:
    - **Lucien's presence**: "🎩 <b>Lucien:</b>" header format
    - **Elegant Spanish**: "usted", refined language, dramatic pauses with "..."
    - **Welcoming**: "Los Kinkys" channel name, references to Diana
    - **Reassuring**: Automatic process emphasis, notification promises
    - **Social media integration**: Prominent CTA buttons for Instagram/TikTok/X

    Terminology:
    - "Los Kinkys" (not "Free channel" or "jardín")
    - "Diana se complace" (references to creator)
    - "Le notificaré" (I will notify you) - Lucien's service commitment
    - Social media buttons: 📸 Instagram, 🎵 TikTok, 𝕏 X (fixed order)

    Return Types:
    - free_request_success(): tuple[str, InlineKeyboardMarkup] (with social buttons)
    - free_request_duplicate(): str (text-only reminder)
    - free_request_approved(): tuple[str, InlineKeyboardMarkup] (channel button)
    - free_request_error(): str (text-only error)

    Examples:
        >>> flows = UserFlowMessages()
        >>> text, kb = flows.free_request_success(30, {'instagram': '@diana'})
        >>> '🎩 <b>Lucien:</b>' in text
        True
        >>> 'Los Kinkys' in text
        True
        >>> kb is not None
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

    def free_request_success(
        self,
        wait_time_minutes: int,
        social_links: Optional[dict[str, str]] = None
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Free request success message with Lucien's voice and social media buttons.

        Args:
            wait_time_minutes: Wait time configured (NOT shown to user per Phase 10 spec)
            social_links: Dict of social media links {'instagram': '@handle', ...}

        Returns:
            Tuple of (text, keyboard) with social media buttons

        Voice Rationale:
            - Ritualistic wait: Frame the delay as part of the experience, not friction
            - Mystery narrative: "no todos entienden lo que eso implica"
            - Social media as "fragments of presence" - meta-commentary
            - "yo mismo vendré a buscarle" - Lucien's personal commitment
            - No specific wait time - creates anticipation

        Examples:
            >>> flows = UserFlowMessages()
            >>> text, kb = flows.free_request_success(5, {'instagram': '@diana'})
            >>> '🎩 <b>Lucien:</b>' in text
            True
            >>> 'Los Kinkys' in text
            True
            >>> kb is not None
            True
        """
        header = "🎩 <b>Lucien:</b>"

        body = (
            "<i>Ah… alguien ha llamado a la puerta.</i>\n\n"
            "<i>Su solicitud para entrar a Los Kinkys ha sido registrada.</i>\n\n"
            "<i>Diana siempre nota cuando alguien decide cruzar hacia su mundo… "
            "aunque no todos entienden lo que eso implica.</i>\n\n"
            "<i>Mientras su acceso se prepara, hay algo que puede hacer.</i>\n\n"
            "<i>Las redes de Diana no son simples perfiles.</i>\n"
            "<i>Son fragmentos de su presencia… señales de lo que se insinúa antes de mostrarse.</i>\n\n"
            "<i>Obsérvela.</i>\n"
            "<i>Escuche el tono.</i>\n"
            "<i>Empiece a entender el juego.</i>"
        )

        footer = (
            "💡 <i>No necesita quedarse aquí esperando.</i>\n"
            "<i>Cuando todo esté listo, yo mismo vendré a buscarle.</i>\n\n"
            "<i>Mientras tanto… aquí puede seguir su rastro 👇</i>"
        )

        text = self._compose(header, body, footer)

        # Generate social media keyboard
        keyboard = self._social_media_keyboard(social_links or {})

        return text, keyboard

    def _social_media_keyboard(
        self,
        social_links: dict[str, str]
    ) -> InlineKeyboardMarkup:
        """
        Generate inline keyboard with social media buttons.

        Args:
            social_links: Dict with keys 'instagram', 'tiktok', 'x'
                          Values are handles (e.g., '@diana') or full URLs

        Returns:
            InlineKeyboardMarkup with social media buttons (clickable URLs)

        Voice Rationale:
            - Fixed order: Instagram → TikTok → X (priority)
            - Emoji + handle format: "📸 @diana_insta"
            - Links embedded in button URLs (clickable)
            - Omits None/unconfigured platforms gracefully

        Examples:
            >>> flows = UserFlowMessages()
            >>> kb = flows._social_media_keyboard({'instagram': '@diana'})
            >>> len(kb.inline_keyboard) == 1
            True
            >>> 'instagram.com' in kb.inline_keyboard[0][0].url
            True
        """
        if not social_links:
            return InlineKeyboardMarkup(inline_keyboard=[])

        # Platform order: Instagram → TikTok → X
        platform_order = ['instagram', 'tiktok', 'x']

        # Button configuration: emoji + URL template
        platform_config = {
            'instagram': {'emoji': '📸', 'url_template': 'https://instagram.com/{}'},
            'tiktok': {'emoji': '🎵', 'url_template': 'https://tiktok.com/@{}'},
            'x': {'emoji': '𝕏', 'url_template': 'https://x.com/{}'}
        }

        buttons = []

        for platform in platform_order:
            if platform not in social_links:
                continue  # Skip unconfigured platforms

            handle = social_links[platform].strip()
            if not handle:
                continue  # Skip empty handles

            # Get platform config
            config = platform_config.get(platform)
            if not config:
                continue

            # Extract handle (remove @ prefix and existing URLs)
            if handle.startswith('@'):
                handle = handle[1:]
            elif 'instagram.com/' in handle:
                handle = handle.split('instagram.com/')[-1].split('/')[0]
            elif 'tiktok.com/@' in handle:
                handle = handle.split('tiktok.com/@')[-1].split('/')[0]
            elif 'x.com/' in handle or 'twitter.com/' in handle:
                # Extract from x.com/username or twitter.com/username
                parts = handle.split('/')
                for i, part in enumerate(parts):
                    if part in ['x.com', 'twitter.com']:
                        if i + 1 < len(parts):
                            handle = parts[i + 1].split('?')[0]
                            break

            # Build URL
            url = config['url_template'].format(handle)

            # Button text: emoji + @handle
            button_text = f"{config['emoji']} @{handle}"

            buttons.append([{
                'text': button_text,
                'url': url
            }])

        # Use create_inline_keyboard utility
        return create_inline_keyboard(buttons)

    def free_request_duplicate(
        self,
        time_elapsed_minutes: int,
        time_remaining_minutes: int
    ) -> str:
        """
        Message when user requests Free access again (duplicate).

        Shows progress (elapsed/remaining) with Lucien's voice.

        Args:
            time_elapsed_minutes: Minutes since original request (NOT shown)
            time_remaining_minutes: Minutes until approval (NOT shown)

        Returns:
            HTML-formatted reminder message (text-only, no keyboard)

        Voice Rationale:
            - "el deseo de entrar no ha disminuido" - validates user's persistence
            - Narrative tension: turn impatience into story, not system error
            - "Los umbrales importantes no se cruzan corriendo" - philosophical framing
            - "La puerta se abrirá" - inevitability, reassurance
            - Time display REMOVED - mystery over precision

        Examples:
            >>> flows = UserFlowMessages()
            >>> msg = flows.free_request_duplicate(10, 20)
            >>> '🎩 <b>Lucien:</b>' in msg
            True
        """
        header = "🎩 <b>Lucien:</b>"

        body = (
            "<i>Veo que el deseo de entrar no ha disminuido…</i>\n\n"
            "<i>Su acceso a Los Kinkys ya está en movimiento.</i>\n\n"
            "<i>Los umbrales importantes no se cruzan corriendo.</i>\n\n"
            "<i>No es una espera vacía.</i>\n"
            "<i>Es el momento exacto en que muchos deciden si de verdad quieren entrar… "
            "o si solo estaban mirando desde fuera.</i>\n\n"
            "<i>Puede cerrar este chat con tranquilidad.</i>\n"
            "<i>Cuando llegue el momento, no tendrá que buscar la puerta.</i>\n"
            "<i>La puerta se abrirá.</i>"
        )

        return self._compose(header, body)

    def free_request_approved(
        self,
        channel_name: str,
        channel_link: str
    ) -> tuple[str, InlineKeyboardMarkup]:
        """
        Approval message when wait time elapses.

        Sent as NEW message (not edit) with channel access button.

        Args:
            channel_name: Name of Free channel ("Los Kinkys")
            channel_link: Invite link or public URL (t.me/loskinkys)

        Returns:
            Tuple of (text, keyboard) with channel access button

        Voice Rationale:
            - "Listo." - dramatic pause, anticipation resolved
            - "Diana ha permitido su entrada" - admission granted, not simply added
            - "no es el lugar donde ella se entrega" - teaser of VIP
            - "Empieza a insinuarse" - mystery, gradual revelation
            - "Entre con intención" - call to purposeful action
            - Single button: "🚀 Acceder al canal" (action-oriented)

        Examples:
            >>> flows = UserFlowMessages()
            >>> text, kb = flows.free_request_approved("Los Kinkys", "t.me/loskinkys")
            >>> '🚀' in text or 'Acceder' in text
            True
            >>> kb is not None and len(kb.inline_keyboard) > 0
            True
        """
        header = "🎩 <b>Lucien:</b>"

        body = (
            "<i>Listo.</i>\n\n"
            "<i>Diana ha permitido su entrada.</i>\n\n"
            f"<b>Bienvenido a {channel_name}.</b>\n\n"
            "<i>Este no es el lugar donde ella se entrega.</i>\n"
            "<i>Es el lugar donde comienza a insinuarse…</i>\n"
            "<i>y donde algunos descubren que ya no quieren quedarse solo aquí.</i>\n\n"
            "<i>El enlace está abajo.</i>\n"
            "<i>Tiene 24 horas para cruzar antes de que se cierre de nuevo.</i>\n\n"
            "<i>Entre con intención.</i>\n"
            "👇"
        )

        text = self._compose(header, body)

        # Channel access button
        keyboard = create_inline_keyboard([
            [{"text": "🚀 Acceder al canal", "url": channel_link}]
        ])

        return text, keyboard

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
