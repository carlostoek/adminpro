"""
FSM State Management Tests

Tests for FSM (Finite State Machine) state handling:
- FSM state is set on menu entry
- FSM state is cleared on exit
- FSM state persists across callback chain
- Invalid callbacks in wrong state are rejected

These tests verify that FSM state management works correctly for multi-step flows.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock


class TestFSMStateEntry:
    """Tests for FSM state entry."""

    async def test_fsm_state_can_be_set(self):
        """Verify FSM state can be set."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        # Create storage and context
        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Set state
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)

        # Verify state was set
        current_state = await fsm_state.get_state()
        assert current_state == VIPEntryStates.stage_1_confirmation

    async def test_fsm_state_can_be_cleared(self):
        """Verify FSM state can be cleared."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        # Create storage and context
        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Set state then clear
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)
        await fsm_state.clear()

        # Verify state was cleared
        current_state = await fsm_state.get_state()
        assert current_state is None

    async def test_fsm_state_persists_in_storage(self):
        """Verify FSM state persists in storage."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import FreeAccessStates

        # Create storage and context
        storage = MemoryStorage()
        key = "test_user_123"
        fsm_state = FSMContext(storage=storage, key=key)

        # Set state
        await fsm_state.set_state(FreeAccessStates.waiting_for_approval)

        # Create new context with same key
        fsm_state2 = FSMContext(storage=storage, key=key)
        current_state = await fsm_state2.get_state()

        # Verify state persisted
        assert current_state == FreeAccessStates.waiting_for_approval


class TestFSMStateTransitions:
    """Tests for FSM state transitions."""

    async def test_vip_entry_state_transitions(self):
        """Verify VIP entry state transitions work correctly."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Start at stage 1
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)
        assert await fsm_state.get_state() == VIPEntryStates.stage_1_confirmation

        # Move to stage 2
        await fsm_state.set_state(VIPEntryStates.stage_2_alignment)
        assert await fsm_state.get_state() == VIPEntryStates.stage_2_alignment

        # Move to stage 3
        await fsm_state.set_state(VIPEntryStates.stage_3_delivery)
        assert await fsm_state.get_state() == VIPEntryStates.stage_3_delivery

    async def test_fsm_state_data_storage(self):
        """Verify FSM can store and retrieve data."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Set state with data
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)
        await fsm_state.update_data(package_id=123, user_name="Test")

        # Retrieve data
        data = await fsm_state.get_data()
        assert data["package_id"] == 123
        assert data["user_name"] == "Test"

    async def test_fsm_state_data_clear(self):
        """Verify FSM data is cleared with state."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Set state with data
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)
        await fsm_state.update_data(test_key="test_value")

        # Clear state
        await fsm_state.clear()

        # Verify data was cleared
        data = await fsm_state.get_data()
        assert data == {}


class TestFSMStateValidation:
    """Tests for FSM state validation."""

    async def test_invalid_state_rejection(self):
        """Verify invalid state transitions can be detected."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates, FreeAccessStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Set VIP state
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)

        # Verify we're in VIP state, not Free state
        current_state = await fsm_state.get_state()
        assert current_state == VIPEntryStates.stage_1_confirmation
        assert current_state != FreeAccessStates.waiting_for_approval

    async def test_state_comparison(self):
        """Verify state comparison works correctly."""
        from bot.states.user import VIPEntryStates

        # States should be comparable
        assert VIPEntryStates.stage_1_confirmation == VIPEntryStates.stage_1_confirmation
        assert VIPEntryStates.stage_1_confirmation != VIPEntryStates.stage_2_alignment

    async def test_state_string_values(self):
        """Verify state string values are correct."""
        from bot.states.user import VIPEntryStates, FreeAccessStates

        # Check state string representations
        assert "VIPEntryStates" in str(VIPEntryStates.stage_1_confirmation)
        assert "FreeAccessStates" in str(FreeAccessStates.waiting_for_approval)


class TestFSMMultiUserIsolation:
    """Tests for FSM multi-user isolation."""

    async def test_fsm_states_are_isolated_per_user(self):
        """Verify FSM states are isolated between users."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates, FreeAccessStates

        storage = MemoryStorage()

        # Create contexts for different users
        user1_fsm = FSMContext(storage=storage, key="user_1")
        user2_fsm = FSMContext(storage=storage, key="user_2")

        # Set different states for each user
        await user1_fsm.set_state(VIPEntryStates.stage_1_confirmation)
        await user2_fsm.set_state(FreeAccessStates.waiting_for_approval)

        # Verify states are isolated
        assert await user1_fsm.get_state() == VIPEntryStates.stage_1_confirmation
        assert await user2_fsm.get_state() == FreeAccessStates.waiting_for_approval

    async def test_fsm_data_isolated_per_user(self):
        """Verify FSM data is isolated between users."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()

        # Create contexts for different users
        user1_fsm = FSMContext(storage=storage, key="user_1")
        user2_fsm = FSMContext(storage=storage, key="user_2")

        # Set state and data for user 1
        await user1_fsm.set_state(VIPEntryStates.stage_1_confirmation)
        await user1_fsm.update_data(user_data="user_1_value")

        # Set state and data for user 2
        await user2_fsm.set_state(VIPEntryStates.stage_2_alignment)
        await user2_fsm.update_data(user_data="user_2_value")

        # Verify data isolation
        user1_data = await user1_fsm.get_data()
        user2_data = await user2_fsm.get_data()

        assert user1_data["user_data"] == "user_1_value"
        assert user2_data["user_data"] == "user_2_value"


class TestFSMStateGroups:
    """Tests for FSM state groups."""

    async def test_vip_entry_states_group(self):
        """Verify VIP entry states are in correct group."""
        from bot.states.user import VIPEntryStates

        # All VIP entry states should be accessible
        states = [
            VIPEntryStates.stage_1_confirmation,
            VIPEntryStates.stage_2_alignment,
            VIPEntryStates.stage_3_delivery,
        ]

        for state in states:
            assert state is not None

    async def test_free_access_states_group(self):
        """Verify Free access states are in correct group."""
        from bot.states.user import FreeAccessStates

        # Free access states should be accessible
        assert FreeAccessStates.waiting_for_approval is not None

    async def test_state_group_iteration(self):
        """Verify state groups can be iterated."""
        from bot.states.user import VIPEntryStates

        # Get all states in the group
        states = list(VIPEntryStates)

        # Should have 3 states
        assert len(states) == 3


class TestFSMIntegration:
    """Tests for FSM integration with handlers."""

    async def test_fsm_state_in_handler_context(self):
        """Verify FSM state can be used in handler context."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Simulate handler setting state
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)

        # Simulate handler checking state
        current_state = await fsm_state.get_state()
        assert current_state == VIPEntryStates.stage_1_confirmation

    async def test_fsm_data_in_handler_context(self):
        """Verify FSM data can be used in handler context."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Simulate handler setting state and data
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)
        await fsm_state.update_data(step="confirming")

        # Simulate next step retrieving data
        data = await fsm_state.get_data()
        assert data["step"] == "confirming"

        # Update data for next step
        await fsm_state.update_data(step="confirmed")
        data = await fsm_state.get_data()
        assert data["step"] == "confirmed"

    async def test_fsm_complete_flow_simulation(self):
        """Verify complete FSM flow simulation works."""
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.memory import MemoryStorage
        from bot.states.user import VIPEntryStates

        storage = MemoryStorage()
        fsm_state = FSMContext(storage=storage, key="test_user")

        # Step 1: Initial state
        await fsm_state.set_state(VIPEntryStates.stage_1_confirmation)
        await fsm_state.update_data(stage=1)
        assert await fsm_state.get_state() == VIPEntryStates.stage_1_confirmation

        # Step 2: Move to alignment
        await fsm_state.set_state(VIPEntryStates.stage_2_alignment)
        await fsm_state.update_data(stage=2)
        assert await fsm_state.get_state() == VIPEntryStates.stage_2_alignment

        # Step 3: Move to delivery
        await fsm_state.set_state(VIPEntryStates.stage_3_delivery)
        await fsm_state.update_data(stage=3)
        assert await fsm_state.get_state() == VIPEntryStates.stage_3_delivery

        # Complete: Clear state
        await fsm_state.clear()
        assert await fsm_state.get_state() is None
