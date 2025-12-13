"""
Tests de validación para BroadcastStates y ReactionSetupStates.

T21: Estados FSM para Broadcasting Multimedia
"""
from aiogram.fsm.state import State, StatesGroup
from bot.states.admin import BroadcastStates, ReactionSetupStates


def test_broadcast_states():
    """Verifica que BroadcastStates tiene todos los estados."""
    print("\n🧪 Test 1: BroadcastStates")

    assert hasattr(BroadcastStates, 'waiting_for_content')
    assert hasattr(BroadcastStates, 'waiting_for_confirmation')
    assert hasattr(BroadcastStates, 'selecting_reactions')

    print("✅ BroadcastStates completo")


def test_reaction_setup_states():
    """Verifica que ReactionSetupStates existe y tiene estados."""
    print("\n🧪 Test 2: ReactionSetupStates")

    assert hasattr(ReactionSetupStates, 'waiting_for_vip_reactions')
    assert hasattr(ReactionSetupStates, 'waiting_for_free_reactions')

    print("✅ ReactionSetupStates completo")


def test_state_types():
    """Verifica que todos son State instances."""
    print("\n🧪 Test 3: Tipos correctos")

    assert isinstance(BroadcastStates.waiting_for_content, State)
    assert isinstance(BroadcastStates.waiting_for_confirmation, State)
    assert isinstance(BroadcastStates.selecting_reactions, State)

    assert isinstance(ReactionSetupStates.waiting_for_vip_reactions, State)
    assert isinstance(ReactionSetupStates.waiting_for_free_reactions, State)

    assert issubclass(BroadcastStates, StatesGroup)
    assert issubclass(ReactionSetupStates, StatesGroup)

    print("✅ Tipos correctos")


def test_state_strings():
    """Verifica que los estados tengan las strings correctas."""
    print("\n🧪 Test 4: State strings")

    # BroadcastStates
    assert BroadcastStates.waiting_for_content.state == "BroadcastStates:waiting_for_content"
    assert BroadcastStates.waiting_for_confirmation.state == "BroadcastStates:waiting_for_confirmation"
    assert BroadcastStates.selecting_reactions.state == "BroadcastStates:selecting_reactions"

    # ReactionSetupStates
    assert ReactionSetupStates.waiting_for_vip_reactions.state == "ReactionSetupStates:waiting_for_vip_reactions"
    assert ReactionSetupStates.waiting_for_free_reactions.state == "ReactionSetupStates:waiting_for_free_reactions"

    print("✅ State strings correctos")


def test_exports():
    """Verifica que los estados se exportan correctamente desde __init__.py."""
    print("\n🧪 Test 5: Exports desde __init__.py")

    from bot.states import BroadcastStates as BS, ReactionSetupStates as RSS

    assert BS is BroadcastStates
    assert RSS is ReactionSetupStates

    print("✅ Exports funcionan correctamente")


if __name__ == "__main__":
    test_broadcast_states()
    test_reaction_setup_states()
    test_state_types()
    test_state_strings()
    test_exports()
    print("\n✅✅✅ TODOS LOS TESTS PASARON")
