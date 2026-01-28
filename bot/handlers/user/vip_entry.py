"""
VIP Entry Flow Handlers - 3-stage ritual admission.

Phase 13: Ritualized VIP entry flow replacing immediate link delivery.

Entry Points:
- /start with token activation (creates vip_entry_stage=1)
- /start without token (resumes from current vip_entry_stage)
- VIP menu open (checks vip_entry_stage for incomplete flow)

Stage Transitions:
- Stage 1 → Stage 2: "Continuar" button (vip_entry:stage_2)
- Stage 2 → Stage 3: "Estoy listo" button (vip_entry:stage_3)
- Stage 3 → Complete: User joins channel, vip_entry_stage=NULL

Expiry Handling:
- Check subscription expiry before allowing stage progression
- Show Lucien's expiry message if expired (blocks continuation)
- No retry option (must renew subscription)

Resumption:
- Seamless return to current stage (no timeout)
- Brief stage_resumption_message() then current stage message
"""
import logging
from datetime import datetime

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.user import VIPEntryStates
from bot.services.container import ServiceContainer
from bot.services.message.vip_entry import VIPEntryFlowMessages
from bot.database.enums import UserRole, RoleChangeReason
from bot.middlewares import DatabaseMiddleware

logger = logging.getLogger(__name__)

# Router for VIP entry handlers
vip_entry_router = Router(name="vip_entry")

# Middleware registration
vip_entry_router.message.middleware(DatabaseMiddleware())
vip_entry_router.callback_query.middleware(DatabaseMiddleware())


async def show_vip_entry_stage(
    message: Message,
    container: ServiceContainer,
    stage: int,
    state: FSMContext = None
):
    """
    Muestra el mensaje correspondiente a la etapa actual del flujo VIP.

    Args:
        message: Mensaje original (para respuesta)
        container: Service container
        stage: Etapa actual (1, 2, o 3)
        state: FSM context (opcional, para establecer estado)

    Flow:
        - Stage 1: Mostrar confirmación de activación
        - Stage 2: Mostrar alineación de expectativas
        - Stage 3: Mostrar mensaje con enlace (invoca VIPEntryService)
    """
    # Use chat.id for user ID in private chats (message.from_user is bot for bot-sent messages)
    user_id = message.chat.id
    provider: VIPEntryFlowMessages = container.message.user.vip_entry
    service = container.vip_entry

    # Verificar expiración de suscripción (antes de mostrar etapa)
    subscriber = await container.subscription.get_vip_subscriber(user_id)

    if not subscriber:
        logger.error(f"❌ VIPSubscriber not found for user {user_id} in entry flow")
        await message.answer(
            "❌ Error: Suscripción no encontrada. Contacte al administrador."
        )
        return

    # Expiry check (critical - blocks continuation)
    if subscriber.is_expired():
        logger.info(f"⚠️ User {user_id} VIP subscription expired during entry flow")
        expiry_msg = provider.expired_subscription_message()
        await message.answer(expiry_msg, parse_mode="HTML")

        # Clear FSM state if exists
        if state:
            await state.clear()
        return

    # Show appropriate stage message
    if stage == 1:
        text, keyboard = provider.stage_1_activation_confirmation()
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        if state:
            await state.set_state(VIPEntryStates.stage_1_confirmation)

        logger.info(f"✅ User {user_id} VIP entry stage 1 shown")

    elif stage == 2:
        text, keyboard = provider.stage_2_expectation_alignment()
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        if state:
            await state.set_state(VIPEntryStates.stage_2_alignment)

        logger.info(f"✅ User {user_id} VIP entry stage 2 shown")

    elif stage == 3:
        # Stage 3 requires invite link generation
        invite_link = await service.create_24h_invite_link(user_id)

        if not invite_link:
            await message.answer(
                "❌ Error: No se pudo generar el enlace de acceso. "
                "Contacte al administrador."
            )
            return

        text, keyboard = provider.stage_3_access_delivery(invite_link.invite_link)
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        if state:
            await state.set_state(VIPEntryStates.stage_3_delivery)

        logger.info(f"✅ User {user_id} VIP entry stage 3 shown (link sent)")

    else:
        logger.error(f"❌ Invalid VIP entry stage: {stage} for user {user_id}")
        await message.answer("❌ Error: Etapa de flujo inválida.")


@vip_entry_router.callback_query(
    lambda c: c.data and c.data.startswith("vip_entry:stage_")
)
async def handle_vip_entry_stage_transition(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Maneja las transiciones entre etapas del flujo VIP.

    Callbacks:
    - vip_entry:stage_2: Avanza de etapa 1 a 2
    - vip_entry:stage_3: Avanza de etapa 2 a 3 (genera enlace, cambia rol)

    Flow:
        1. Validar suscripción (no expirada)
        2. Avanzar vip_entry_stage
        3. Mostrar siguiente etapa
        4. (Stage 3) Cambiar UserRole a VIP, log auditoría
    """
    user_id = callback.from_user.id
    container = ServiceContainer(session, callback.bot)
    service = container.vip_entry

    # Parse callback data
    # Format: vip_entry:stage_{N} → ['vip_entry', 'stage_2']
    parts = callback.data.split(":")
    target_stage = int(parts[1].split("_")[1])  # Extract '2' from 'stage_2'

    logger.info(f"🎭 VIP entry transition: User {user_id} → Stage {target_stage}")

    # Get current subscriber
    subscriber = await container.subscription.get_vip_subscriber(user_id)

    if not subscriber:
        await callback.answer("❌ Suscripción no encontrada", show_alert=True)
        return

    # Expiry check (critical - blocks transition)
    if subscriber.is_expired():
        logger.info(f"⚠️ User {user_id} VIP subscription expired during transition")
        provider = container.message.user.vip_entry
        expiry_msg = provider.expired_subscription_message()

        await callback.message.answer(expiry_msg, parse_mode="HTML")
        await callback.answer()
        await state.clear()
        return

    # Validate stage progression
    current_stage = subscriber.vip_entry_stage if subscriber.vip_entry_stage else 0

    if target_stage != current_stage + 1:
        logger.warning(
            f"⚠️ Invalid stage progression: {current_stage} → {target_stage}"
        )
        await callback.answer("❌ Transición inválida", show_alert=True)
        return

    # Advance stage
    success = await service.advance_stage(user_id, current_stage)

    if not success:
        await callback.answer("❌ Error al avanzar etapa", show_alert=True)
        return

    # Stage 3 special handling: UserRole change + audit log
    if target_stage == 3:
        user = await container.user.get_user(user_id)

        if user:
            # Change role from FREE to VIP
            old_role = user.role
            user.role = UserRole.VIP

            # Log role change
            await container.role_change.log_role_change(
                user_id=user_id,
                previous_role=old_role,
                new_role=UserRole.VIP,
                reason=RoleChangeReason.VIP_ENTRY_COMPLETED,
                changed_by=0  # SYSTEM
            )

            logger.info(
                f"✅ User {user_id} role changed: {old_role.value} → VIP "
                f"(VIP entry flow completed)"
            )

    # Edit message to show next stage (consistent with bot UX - edit, not delete+new)
    provider = container.message.user.vip_entry
    if target_stage == 2:
        text, keyboard = provider.stage_2_expectation_alignment()
    elif target_stage == 3:
        # Generate invite link for Stage 3
        invite_link = await service.create_24h_invite_link(user_id)
        if not invite_link:
            await callback.answer("❌ Error generando enlace", show_alert=True)
            return
        text, keyboard = provider.stage_3_access_delivery(invite_link.invite_link)
    else:
        await callback.answer("❌ Etapa inválida", show_alert=True)
        return

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"⚠️ Could not edit stage message: {e}")

    await callback.answer()


@vip_entry_router.callback_query(
    lambda c: c.data and c.data == "vip_entry:main_menu"
)
async def handle_vip_entry_main_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext
):
    """
    Maneja el callback "Descubrir lo que cambió" después de completar el ritual VIP.

    Muestra el menú principal al usuario después de haber completado el flujo de entrada VIP.
    """
    user_id = callback.from_user.id  # CallbackQuery uses from_user, not chat

    # Create container first (needed for both operations)
    container = ServiceContainer(session, callback.bot)

    # Mark ritual as completed by setting vip_entry_stage = NULL
    subscriber = await container.subscription.get_vip_subscriber(user_id)
    if subscriber and subscriber.vip_entry_stage is not None:
        subscriber.vip_entry_stage = None  # Ritual completed
        logger.info(f"✅ User {user_id} VIP entry ritual marked as completed")

    # Clear FSM state
    await state.clear()

    # Import and call the start handler to show main menu
    from bot.handlers.user.start import _send_welcome_message

    logger.info(f"✅ User {user_id} returning to main menu after VIP entry completion")

    # Show main menu via start handler
    await _send_welcome_message(callback.message, None, container, user_id)

    # Delete the Stage 3 message
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"⚠️ Could not delete Stage 3 message: {e}")

    await callback.answer()
