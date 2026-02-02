"""
VIP Handlers - Gestión del canal VIP.

Handlers para:
- Submenú VIP
- Configuración del canal VIP
- Generación de tokens de invitación con deep links

All messages now use centralized AdminVIPMessages provider for voice consistency.
"""
import logging
from datetime import timedelta

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.main import admin_router
from bot.services.container import ServiceContainer
from bot.states.admin import ChannelSetupStates
from bot.utils.keyboards import create_inline_keyboard
from config import Config

logger = logging.getLogger(__name__)


@admin_router.callback_query(F.data == "admin:vip")
async def callback_vip_menu(callback: CallbackQuery, session: AsyncSession):
    """
    Muestra el submenú de gestión VIP.

    Migrated to use AdminVIPMessages provider for all text/keyboard generation.

    Args:
        callback: Callback query
        session: Sesión de BD (inyectada por middleware)
    """
    logger.debug(f"📺 Usuario {callback.from_user.id} abrió menú VIP")

    container = ServiceContainer(session, callback.bot)

    # Verificar si canal VIP está configurado
    is_configured = await container.channel.is_vip_channel_configured()

    # Get channel info for configured state
    channel_name = "Canal VIP"
    subscriber_count = 0

    if is_configured:
        vip_channel_id = await container.channel.get_vip_channel_id()
        channel_info = await container.channel.get_channel_info(vip_channel_id)
        channel_name = channel_info.title if channel_info else "Canal VIP"

        # Get subscriber count (optional - can be 0 if stats not available)
        try:
            all_vips = await container.subscription.get_all_vip_subscribers(status="active")
            subscriber_count = len(all_vips)
        except Exception as e:
            logger.warning(f"Could not get VIP count: {e}")
            subscriber_count = 0

    # Generate message and keyboard from provider
    session_history = container.session_history
    text, keyboard = container.message.admin.vip.vip_menu(
        is_configured=is_configured,
        channel_name=channel_name,
        subscriber_count=subscriber_count,
        user_id=callback.from_user.id,
        session_history=session_history
    )

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje VIP: {e}")

    await callback.answer()


@admin_router.callback_query(F.data == "vip:setup")
async def callback_vip_setup(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Inicia el proceso de configuración del canal VIP.

    Entra en estado FSM esperando que el admin reenvíe un mensaje del canal.
    Migrated to use AdminVIPMessages provider.

    Args:
        callback: Callback query
        session: Sesión de BD
        state: FSM context
    """
    logger.info(f"⚙️ Usuario {callback.from_user.id} iniciando setup VIP")

    # Entrar en estado FSM
    await state.set_state(ChannelSetupStates.waiting_for_vip_channel)

    container = ServiceContainer(session, callback.bot)

    # Generate message and keyboard from provider
    text, keyboard = container.message.admin.vip.setup_channel_prompt()

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje setup VIP: {e}")

    await callback.answer()


@admin_router.message(ChannelSetupStates.waiting_for_vip_channel)
async def process_vip_channel_forward(
    message: Message,
    session: AsyncSession,
    state: FSMContext
):
    """
    Procesa el mensaje reenviado para configurar el canal VIP.

    Extrae el ID del canal del forward y lo configura.

    Args:
        message: Mensaje reenviado del canal
        session: Sesión de BD
        state: FSM context
    """
    # Verificar que es un forward de un canal
    if not message.forward_from_chat:
        await message.answer(
            "❌ Debes <b>reenviar</b> un mensaje del canal VIP.\n\n"
            "No me envíes el ID manualmente, reenvía un mensaje.",
            parse_mode="HTML"
        )
        return

    forward_chat = message.forward_from_chat

    # Verificar que es un canal (no grupo ni usuario)
    if forward_chat.type not in ["channel", "supergroup"]:
        await message.answer(
            "❌ El mensaje debe ser de un <b>canal</b> o <b>supergrupo</b>.\n\n"
            "Reenvía un mensaje del canal VIP.",
            parse_mode="HTML"
        )
        return

    channel_id = str(forward_chat.id)
    channel_title = forward_chat.title

    logger.info(f"📺 Configurando canal VIP: {channel_id} ({channel_title})")

    container = ServiceContainer(session, message.bot)

    # Intentar configurar el canal
    success, msg = await container.channel.setup_vip_channel(channel_id)

    if success:
        # Configuración exitosa - use message provider
        text, keyboard = container.message.admin.vip.channel_configured_success(
            channel_name=channel_title,
            channel_id=channel_id
        )

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        # Limpiar estado FSM
        await state.clear()
    else:
        # Error en configuración
        await message.answer(
            f"{msg}\n\n"
            f"Verifica que:\n"
            f"• El bot es administrador del canal\n"
            f"• El bot tiene permiso para invitar usuarios\n\n"
            f"Intenta nuevamente reenviando un mensaje del canal.",
            parse_mode="HTML"
        )
        # Mantener estado FSM para reintentar


@admin_router.callback_query(F.data == "vip:generate_token")
async def callback_generate_token_select_plan(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Muestra menú de selección de tarifa para generar token.

    MODIFICADO: Ahora muestra tarifas configuradas en lugar de pedir duración.
    El admin selecciona un plan y el token se genera vinculado a ese plan.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.info(f"🎟️ Usuario {callback.from_user.id} generando token VIP")

    container = ServiceContainer(session, callback.bot)

    # Verificar que canal VIP está configurado
    if not await container.channel.is_vip_channel_configured():
        await callback.answer(
            "❌ Debes configurar el canal VIP primero",
            show_alert=True
        )
        return

    try:
        # Obtener planes activos
        plans = await container.pricing.get_all_plans(active_only=True)

        if not plans:
            # Use message provider for no plans case
            text, keyboard = container.message.admin.vip.no_plans_configured()

            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await callback.answer()
            return

        # Convert SQLAlchemy objects to dicts for message provider
        plans_data = [
            {
                "id": plan.id,
                "name": plan.name,
                "duration_days": plan.duration_days,
                "price": plan.price,
                "currency": plan.currency
            }
            for plan in plans
        ]

        # Use message provider for plan selection
        text, keyboard = container.message.admin.vip.select_plan_for_token(plans_data)

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"❌ Error mostrando planes: {e}", exc_info=True)
        await callback.answer(
            "❌ Error al cargar tarifas. Intenta nuevamente.",
            show_alert=True
        )


@admin_router.callback_query(F.data.startswith("vip:generate:plan:"))
async def callback_generate_token_with_plan(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Genera token VIP vinculado a una tarifa específica con deep link.

    NUEVO: Genera token con deep link profesional (t.me/bot?start=TOKEN).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    # Extraer plan_id del callback
    try:
        plan_id = int(callback.data.split(":")[3])
    except (IndexError, ValueError) as e:
        logger.error(f"❌ Error parseando plan_id: {callback.data} - {e}")
        await callback.answer("❌ Error al generar token", show_alert=True)
        return

    container = ServiceContainer(session, callback.bot)

    # Obtener plan
    plan = await container.pricing.get_plan_by_id(plan_id)

    if not plan or not plan.active:
        await callback.answer("❌ Tarifa no disponible", show_alert=True)
        return

    logger.info(
        f"🎟️ Admin {callback.from_user.id} generando token con plan: "
        f"{plan.name} (ID: {plan_id})"
    )

    await callback.answer("🎟️ Generando token...", show_alert=False)

    try:
        # Generar token vinculado al plan
        # La duración se toma del plan automáticamente
        token = await container.subscription.generate_vip_token(
            generated_by=callback.from_user.id,
            duration_hours=plan.duration_days * 24,  # Convertir días a horas
            plan_id=plan.id  # NUEVO: Vincular con plan
        )

        # Commit la transacción
        await session.commit()
        await session.refresh(token)

        # GENERAR DEEP LINK
        bot_username = (await callback.bot.me()).username
        deep_link = f"https://t.me/{bot_username}?start={token.token}"

        # Calculate expiry date
        expiry_date = token.created_at + timedelta(hours=24)

        # Use message provider for token generated message
        text, keyboard = container.message.admin.vip.token_generated(
            plan_name=plan.name,
            duration_days=plan.duration_days,
            price=plan.price,
            currency=plan.currency,
            token=token.token,
            deep_link=deep_link,
            expiry_date=expiry_date
        )

        await callback.message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        logger.info(
            f"✅ Token generado: {token.token} | Plan: {plan.name} | "
            f"Deep link: {deep_link}"
        )

    except Exception as e:
        logger.error(f"❌ Error generando token: {e}", exc_info=True)

        # Use common error message from message service
        from bot.utils.keyboards import create_inline_keyboard
        error_msg = container.message.common.error(
            context="al generar la invitación",
            suggestion="Verifique que el plan seleccionado sigue activo"
        )

        await callback.message.edit_text(
            error_msg,
            reply_markup=create_inline_keyboard([
                [{"text": "🔄 Reintentar", "callback_data": "vip:generate_token"}],
                [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
            ]),
            parse_mode="HTML"
        )


# ===== SUBMENÚ DE CONFIGURACIÓN VIP =====

@admin_router.callback_query(F.data == "vip:config")
async def callback_vip_config(callback: CallbackQuery, session: AsyncSession):
    """
    Muestra el submenú de configuración VIP.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"⚙️ Usuario {callback.from_user.id} abrió configuración VIP")

    text = (
        "⚙️ <b>Configuración Canal VIP</b>\n\n"
        "Selecciona una opción:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "💰 Gestión de Tarifas", "callback_data": "admin:pricing"}],
        [{"text": "🔧 Reconfigurar Canal", "callback_data": "vip:setup"}],
        [{"text": "🔙 Volver", "callback_data": "admin:vip"}]
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje config VIP: {e}")

    await callback.answer()
