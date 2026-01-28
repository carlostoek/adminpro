"""
FSM States para handlers de usuarios.

Estados para flujos de usuarios (solicitud Free).

Note: TokenRedemptionStates removed - manual token redemption deprecated.
Only deep link activation exists (no FSM state needed).
"""
from aiogram.fsm.state import State, StatesGroup


class FreeAccessStates(StatesGroup):
    """
    Estados para solicitud de acceso Free.

    Flujo:
    1. Usuario solicita acceso Free
    2. Bot crea solicitud
    3. Bot puede usar estado para tracking (opcional)

    Nota: Este flujo es mayormente automático (background task),
    pero el estado se puede usar para prevenir spam de solicitudes.

    Estados:
    - waiting_for_approval: Usuario tiene solicitud pendiente de aprobación
    """

    # Usuario tiene solicitud pendiente
    waiting_for_approval = State()


class VIPEntryStates(StatesGroup):
    """
    Estados para flujo ritual de entrada VIP.

    Flujo:
    1. Stage 1: Confirmación de activación → user pulsa "Continuar"
    2. Stage 2: Alineación de expectativas → user pulsa "Estoy listo"
    3. Stage 3: Entrega de enlace → user accede al canal

    Estados:
    - stage_1_confirmation: Usuario en etapa 1 (espera "Continuar")
    - stage_2_alignment: Usuario en etapa 2 (espera "Estoy listo")
    - stage_3_delivery: Enlace enviado (espera que user se una al canal)

    Abandono: Usuario puede abandonar y retomar desde etapa actual
    (no hay timeout, estado persiste en vip_entry_stage field)

    Expiración: Si VIPSubscriber expira durante etapas 1-2,
    se muestra mensaje de Lucien y se bloquea continuación.
    """
    stage_1_confirmation = State()
    stage_2_alignment = State()
    stage_3_delivery = State()
