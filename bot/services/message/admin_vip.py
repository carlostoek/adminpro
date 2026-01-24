"""
Admin VIP Messages Provider - VIP management messages.

Provides messages for VIP channel setup, token generation, and VIP management.
All messages maintain Lucien's sophisticated mayordomo voice from docs/guia-estilo.md.
"""
import random
from datetime import datetime
from typing import Tuple, List, Dict, Optional

from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard
from bot.utils.formatters import format_datetime, format_currency


class AdminVIPMessages(BaseMessageProvider):
    """
    Admin VIP management messages provider.

    Voice Characteristics (from docs/guia-estilo.md):
    - VIP channel = "círculo exclusivo" (exclusive circle)
    - Token = "invitación" (invitation, never "token" in user-facing text)
    - Setup = "calibración" (calibration, implies precision)
    - Uses "usted", never "tú"
    - Emoji 🎩 always present
    - References Diana for authority validation

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI

    Examples:
        >>> provider = AdminVIPMessages()
        >>> text, keyboard = provider.vip_menu(is_configured=True)
        >>> '🎩' in text and 'círculo exclusivo' in text
        True
    """

    def vip_menu(
        self,
        is_configured: bool,
        channel_name: str = "Canal VIP",
        subscriber_count: int = 0,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate VIP menu message with weighted greeting variations.

        Args:
            is_configured: Whether VIP channel is configured
            channel_name: Name of VIP channel (if configured)
            subscriber_count: Number of active VIP subscribers
            user_id: Optional Telegram user ID for session-aware selection
            session_history: Optional SessionMessageHistory for context awareness

        Returns:
            Tuple of (text, keyboard) for VIP management menu

        Voice Rationale:
            Greetings use weighted random to feel organic:
            - 50% common greeting (familiar)
            - 30% alternate greeting (variety)
            - 20% rare greeting (surprise)

            Conditional body adapts based on configuration state.
            References "círculo exclusivo" for VIP terminology.

        Examples:
            >>> provider = AdminVIPMessages()
            >>> text, kb = provider.vip_menu(is_configured=False)
            >>> 'calibración' in text or 'configurar' in text.lower()
            True

            >>> text, kb = provider.vip_menu(is_configured=True, channel_name="VIP Club")
            >>> 'VIP Club' in text
            True
        """
        # Weighted greeting variations
        greetings = [
            ("Ah, el círculo exclusivo. Todo está preparado para sus decisiones, custodio...", 0.5),
            ("El santuario VIP aguarda su dirección, guardián de Diana...", 0.3),
            ("Bienvenido a la cámara de decisiones exclusivas...", 0.2),
        ]
        header_greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="vip_menu",
            session_history=session_history
        )

        # Header with Lucien emoji
        header = f"🎩 <b>Lucien:</b>\n\n<i>{header_greeting}</i>"

        # Conditional body based on configuration
        if is_configured:
            body = (
                f"<b>👑 Gestión del Círculo Exclusivo</b>\n\n"
                f"✅ <b>Estado:</b> Calibrado y operando\n"
                f"<b>Santuario:</b> {channel_name}\n"
                f"<b>Privilegiados:</b> {subscriber_count} almas selectas\n\n"
                f"<i>Diana observa con interés cada invitación emitida...</i>"
            )
            keyboard = self._vip_configured_keyboard()
        else:
            body = (
                f"<b>👑 Gestión del Círculo Exclusivo</b>\n\n"
                f"⚠️ <b>Estado:</b> Requiere calibración inicial\n\n"
                f"<i>Antes de emitir invitaciones, debo conocer cuál será el santuario "
                f"donde Diana revelará sus secretos más íntimos...</i>\n\n"
                f"<i>Permítame asistirle en la calibración.</i>"
            )
            keyboard = self._vip_unconfigured_keyboard()

        text = self._compose(header, body)
        return text, keyboard

    def token_generated(
        self,
        plan_name: str,
        duration_days: int,
        price: float,
        currency: str,
        token: str,
        deep_link: str,
        expiry_date: datetime
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate token creation success message with deep link.

        Args:
            plan_name: Name of the subscription plan
            duration_days: Duration in days
            price: Price amount
            currency: Currency symbol
            token: Generated token string
            deep_link: Deep link URL for activation
            expiry_date: When token expires

        Returns:
            Tuple of (text, keyboard) with token details and copy button

        Voice Rationale:
            "Invitación" instead of "token" maintains mystery.
            "Pase de entrada" (entry pass) feels exclusive.
            References Diana's approval of the issuance.

        Examples:
            >>> provider = AdminVIPMessages()
            >>> from datetime import datetime, timedelta
            >>> expiry = datetime.now() + timedelta(hours=24)
            >>> text, kb = provider.token_generated(
            ...     "Plan Mensual", 30, 9.99, "$", "ABC123",
            ...     "https://t.me/bot?start=ABC123", expiry
            ... )
            >>> 'invitación' in text.lower() or 'pase' in text.lower()
            True
        """
        price_str = format_currency(price, symbol=currency)
        expiry_str = format_datetime(expiry_date, include_time=False)

        header = "🎩 <b>Lucien:</b>\n\n<i>Excelente. La invitación ha sido preparada con meticulosa atención...</i>"

        body = (
            f"<b>🎟️ Pase de Entrada al Círculo Exclusivo</b>\n\n"
            f"<b>Plan Seleccionado:</b> {plan_name}\n"
            f"<b>Duración:</b> {duration_days} {'día' if duration_days == 1 else 'días'}\n"
            f"<b>Inversión:</b> {price_str}\n\n"
            f"<b>Invitación:</b> <code>{token}</code>\n\n"
            f"<b>🔗 Enlace de Activación Automática:</b>\n"
            f"<code>{deep_link}</code>\n\n"
            f"<b>Válido hasta:</b> {expiry_str}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<i>Entregue este enlace al destinatario. Al hacer clic, su acceso "
            f"al santuario de Diana será activado automáticamente...</i>\n\n"
            f"<i>Diana aprueba esta emisión.</i> 🌸"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🔗 Copiar Enlace", "url": deep_link}],
            [{"text": "🎟️ Emitir Otra Invitación", "callback_data": "vip:generate_token"}],
            [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
        ])

        text = self._compose(header, body)
        return text, keyboard

    def setup_channel_prompt(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate VIP channel setup instructions.

        Returns:
            Tuple of (text, keyboard) with forward instructions

        Voice Rationale:
            "Calibración" instead of "configuration" maintains sophistication.
            Instructions are framed as collaborative ("permítame asistirle").
            Technical requirements presented as Diana's preferences.

        Examples:
            >>> provider = AdminVIPMessages()
            >>> text, kb = provider.setup_channel_prompt()
            >>> 'reenvíe' in text.lower() or 'forward' in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Ah, la calibración del santuario exclusivo...</i>"

        body = (
            f"<b>⚙️ Calibración del Círculo Exclusivo</b>\n\n"
            f"<i>Para que Diana pueda conferir acceso a los privilegiados, necesito conocer "
            f"cuál será el santuario:</i>\n\n"
            f"<b>Instrucciones:</b>\n"
            f"1️⃣ Navegue al canal exclusivo de Diana\n"
            f"2️⃣ <b>Reenvíe</b> cualquier mensaje del canal a esta conversación\n"
            f"3️⃣ Extraeré el identificador automáticamente\n\n"
            f"<b>⚠️ Requisitos que Diana prefiere:</b>\n"
            f"• Debo ser administrador del canal\n"
            f"• Debo tener permiso para invitar visitantes\n\n"
            f"<i>Aguardo su mensaje reenviado...</i>"
        )

        keyboard = create_inline_keyboard([
            [{"text": "❌ Cancelar Calibración", "callback_data": "admin:vip"}]
        ])

        text = self._compose(header, body)
        return text, keyboard

    def channel_configured_success(
        self,
        channel_name: str,
        channel_id: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate channel configuration success message.

        Args:
            channel_name: Name of configured channel
            channel_id: Telegram channel ID

        Returns:
            Tuple of (text, keyboard) with success confirmation

        Voice Rationale:
            Diana's approval validates the configuration.
            "Santuario calibrado" maintains mystery while being clear.
            Encourages next action (emit invitations).

        Examples:
            >>> provider = AdminVIPMessages()
            >>> text, kb = provider.channel_configured_success("VIP Club", "-100123456")
            >>> 'Diana' in text and 'VIP Club' in text
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Excelente. Diana aprueba esta elección...</i>"

        body = (
            f"<b>✅ Santuario Calibrado</b>\n\n"
            f"<b>Círculo Exclusivo:</b> {channel_name}\n"
            f"<b>Identificador:</b> <code>{channel_id}</code>\n\n"
            f"<i>El santuario está preparado. Ya puede emitir invitaciones "
            f"para que los privilegiados accedan a los secretos de Diana...</i>\n\n"
            f"<i>Todo está en orden.</i> 🌸"
        )

        keyboard = create_inline_keyboard([
            [{"text": "🎟️ Emitir Primera Invitación", "callback_data": "vip:generate_token"}],
            [{"text": "🔙 Volver al Círculo", "callback_data": "admin:vip"}]
        ])

        text = self._compose(header, body)
        return text, keyboard

    def select_plan_for_token(
        self,
        plans: List[Dict]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate plan selection menu for token generation.

        Args:
            plans: List of plan dicts with keys: id, name, duration_days, price, currency

        Returns:
            Tuple of (text, keyboard) with plan selection options

        Voice Rationale:
            "Tarifas" becomes "inversiones" (investments) - more elegant.
            Each plan presented as choice Diana has curated.
            Maintains sophistication while being functional.

        Examples:
            >>> provider = AdminVIPMessages()
            >>> plans = [
            ...     {"id": 1, "name": "Mensual", "duration_days": 30,
            ...      "price": 9.99, "currency": "$"}
            ... ]
            >>> text, kb = provider.select_plan_for_token(plans)
            >>> 'invitación' in text.lower() or 'plan' in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Ah, emitir una invitación al círculo exclusivo...</i>"

        # Build plan list
        plan_list = []
        for plan in plans:
            price_str = format_currency(plan["price"], symbol=plan["currency"])
            plan_list.append(
                f"• <b>{plan['name']}</b>: {plan['duration_days']} días • {price_str}"
            )
        plans_text = "\n".join(plan_list)

        body = (
            f"<b>🎟️ Selección de Plan para la Invitación</b>\n\n"
            f"<i>Diana ha diseñado estas inversiones con meticulosa atención...</i>\n\n"
            f"<b>Planes Disponibles:</b>\n"
            f"{plans_text}\n\n"
            f"<i>Seleccione el plan apropiado para el destinatario:</i>"
        )

        # Build dynamic keyboard with plan buttons
        buttons = []
        for plan in plans:
            price_str = format_currency(plan["price"], symbol=plan["currency"])
            buttons.append([{
                "text": f"{plan['name']} - {price_str}",
                "callback_data": f"vip:generate:plan:{plan['id']}"
            }])
        buttons.append([{"text": "🔙 Volver", "callback_data": "admin:vip"}])

        keyboard = create_inline_keyboard(buttons)
        text = self._compose(header, body)
        return text, keyboard

    def no_plans_configured(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate error message when no pricing plans exist.

        Returns:
            Tuple of (text, keyboard) guiding to pricing setup

        Voice Rationale:
            Error presented as "imprevisto" not failure.
            Lucien offers helpful guidance to resolve.
            Maintains composure and elegance even in error state.

        Examples:
            >>> provider = AdminVIPMessages()
            >>> text, kb = provider.no_plans_configured()
            >>> 'tarifa' in text.lower() or 'plan' in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Hmm... un imprevisto en la preparación...</i>"

        body = (
            f"<b>⚠️ No Hay Planes Configurados</b>\n\n"
            f"<i>Para emitir invitaciones al círculo exclusivo, Diana requiere "
            f"que primero establezca las inversiones disponibles...</i>\n\n"
            f"<i>Permítame guiarle hacia la calibración de tarifas.</i>\n\n"
            f"<b>Navegue a:</b>\n"
            f"Configuración → Tarifas → Crear Nueva Tarifa"
        )

        keyboard = create_inline_keyboard([
            [{"text": "💰 Configurar Tarifas", "callback_data": "admin:pricing"}],
            [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
        ])

        text = self._compose(header, body)
        return text, keyboard

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _vip_configured_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for configured VIP channel state.

        Returns:
            InlineKeyboardMarkup with full VIP management options

        Voice Rationale:
            Button text uses elegant terminology:
            - "Emitir Invitación" not "Generate Token"
            - "Privilegiados" not "Subscribers"
            - "Calibración" not "Configuration"
        """
        return create_inline_keyboard([
            [{"text": "🎟️ Emitir Invitación", "callback_data": "vip:generate_token"}],
            [
                {"text": "👥 Ver Privilegiados", "callback_data": "vip:list_subscribers"},
                {"text": "📊 Observaciones", "callback_data": "admin:stats:vip"}
            ],
            [{"text": "📤 Enviar Publicación", "callback_data": "vip:broadcast"}],
            [{"text": "⚙️ Calibración", "callback_data": "vip:config"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])

    def _vip_unconfigured_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for unconfigured VIP channel state.

        Returns:
            InlineKeyboardMarkup with only setup option

        Voice Rationale:
            Single clear action to resolve unconfigured state.
            "Calibrar" maintains elegant terminology.
        """
        return create_inline_keyboard([
            [{"text": "⚙️ Calibrar Santuario", "callback_data": "vip:setup"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}]
        ])
