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
