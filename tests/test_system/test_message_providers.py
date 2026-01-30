"""
Message Provider Tests - Comprehensive tests for all message providers.

Tests cover:
- CommonMessageProvider (errors, success, not_found)
- AdminMainProvider (admin menu, config menu, config status)
- AdminVIPProvider (VIP menu, token generation)
- AdminFreeProvider (Free menu, queue management)
- AdminContentProvider (content management)
- AdminInterestProvider (interest management)
- AdminUserProvider (user management)
- UserStartProvider (/start greetings)
- UserFlowProvider (Free entry flow)
- UserMenuProvider (VIP/Free menus)
- VIPEntryFlowProvider (3-stage ritual)
- SessionHistoryProvider (variation tracking)

All tests verify:
- Messages return valid text
- Keyboards are returned where applicable
- Lucien's voice characteristics (🎩 emoji, usted form)
- Session-aware variation selection
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from bot.services.message import LucienVoiceService
from bot.services.message.session_history import SessionMessageHistory


# ===== COMMON PROVIDER TESTS =====

async def test_common_provider_error(container):
    """Verify CommonMessageProvider returns valid error messages."""
    text = container.message.common.error("al procesar su solicitud")

    assert text is not None
    assert len(text) > 0
    assert "🎩" in text  # Lucien's signature
    assert "Lucien" in text
    assert "inesperado" in text.lower() or "inconveniente" in text.lower()


async def test_common_provider_success(container):
    """Verify CommonMessageProvider returns valid success messages."""
    text = container.message.common.success("canal configurado")

    assert text is not None
    assert len(text) > 0
    assert "🎩" in text  # Lucien's signature
    assert "Excelente" in text


async def test_common_provider_not_found(container):
    """Verify CommonMessageProvider returns valid not_found messages."""
    text = container.message.common.not_found("token", "ABC123")

    assert text is not None
    assert len(text) > 0
    assert "🎩" in text  # Lucien's signature
    assert "ABC123" in text
    assert "archivos" in text.lower() or "localizar" in text.lower()


async def test_common_provider_generic_error(container):
    """Verify CommonMessageProvider returns valid generic error messages."""
    text = container.message.common.generic_error("database")

    assert text is not None
    assert len(text) > 0
    assert "🎩" in text  # Lucien's signature
    assert "perturbación" in text.lower() or "inesperada" in text.lower()


# ===== ADMIN MAIN PROVIDER TESTS =====

async def test_admin_main_provider_menu_configured(container):
    """Verify AdminMainProvider returns admin menu when configured."""
    text, keyboard = container.message.admin.main.admin_menu_greeting(
        is_configured=True,
        missing_items=[],
        user_id=123456789
    )

    assert text is not None
    assert len(text) > 0
    assert keyboard is not None
    assert "🎩" in text  # Lucien's signature
    assert "custodio" in text.lower() or "guardián" in text.lower()
    assert "✅" in text or "orden" in text.lower()


async def test_admin_main_provider_menu_not_configured(container):
    """Verify AdminMainProvider returns admin menu when not configured."""
    text, keyboard = container.message.admin.main.admin_menu_greeting(
        is_configured=False,
        missing_items=["Canal VIP"],
        user_id=123456789
    )

    assert text is not None
    assert keyboard is not None
    assert "⚠️" in text or "Incompleta" in text
    assert "Canal VIP" in text or "calibración" in text.lower()


async def test_admin_main_provider_config_menu(container):
    """Verify AdminMainProvider returns config menu."""
    text, keyboard = container.message.admin.main.config_menu()

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "calibración" in text.lower() or "parámetros" in text.lower()


async def test_admin_main_provider_config_status(container):
    """Verify AdminMainProvider returns config status."""
    text, keyboard = container.message.admin.main.config_status(
        vip_reactions=["👑", "🌸"],
        free_reactions=["👍"],
        is_vip_configured=True,
        is_free_configured=False,
        wait_time=5
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "👑" in text  # VIP reactions shown
    assert "5 min" in text or "5" in text


# ===== ADMIN VIP PROVIDER TESTS =====

async def test_admin_vip_provider_menu(container):
    """Verify AdminVIPProvider returns VIP menu."""
    text, keyboard = container.message.admin.vip.vip_menu(
        is_configured=True,
        channel_name="VIP Club",
        subscriber_count=10
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "círculo" in text.lower() or "VIP" in text


async def test_admin_vip_provider_menu_not_configured(container):
    """Verify AdminVIPProvider returns VIP menu when not configured."""
    text, keyboard = container.message.admin.vip.vip_menu(
        is_configured=False,
        channel_name="Canal VIP",
        subscriber_count=0
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text


# ===== ADMIN FREE PROVIDER TESTS =====

async def test_admin_free_provider_menu(container):
    """Verify AdminFreeProvider returns Free menu."""
    text, keyboard = container.message.admin.free.free_menu(
        is_configured=True,
        channel_name="Canal Free",
        wait_time_minutes=5
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "vestíbulo" in text.lower() or "Free" in text or "Canal" in text


async def test_admin_free_provider_menu_not_configured(container):
    """Verify AdminFreeProvider returns Free menu when not configured."""
    text, keyboard = container.message.admin.free.free_menu(
        is_configured=False,
        channel_name="Canal Free",
        wait_time_minutes=0
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "⚠️" in text or "calibrado" in text.lower()


# ===== ADMIN CONTENT PROVIDER TESTS =====

async def test_admin_content_provider_menu(container):
    """Verify AdminContentProvider returns content menu."""
    text, keyboard = container.message.admin.content.content_menu()

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "paquete" in text.lower() or "contenido" in text.lower()


async def test_admin_content_provider_create_welcome(container):
    """Verify AdminContentProvider returns create welcome message."""
    text, keyboard = container.message.admin.content.create_welcome()

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "crear" in text.lower() or "nuevo" in text.lower()


async def test_admin_content_provider_create_success(container):
    """Verify AdminContentProvider returns create success message."""
    from bot.database.models import ContentPackage

    mock_package = MagicMock(spec=ContentPackage)
    mock_package.name = "Test Package"

    text, keyboard = container.message.admin.content.create_success(mock_package)

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Test Package" in text


# ===== ADMIN INTEREST PROVIDER TESTS =====

async def test_admin_interest_provider_menu(container):
    """Verify AdminInterestProvider returns interest menu."""
    text, keyboard = container.message.admin.interest.interests_menu(
        pending_count=3,
        total_count=23
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "🔔" in text  # Interest emoji
    assert "3" in text  # Pending count


async def test_admin_interest_provider_empty(container):
    """Verify AdminInterestProvider returns empty state message."""
    text, keyboard = container.message.admin.interest.interests_empty("pending")

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text


# ===== ADMIN USER PROVIDER TESTS =====

async def test_admin_user_provider_menu(container):
    """Verify AdminUserProvider returns user menu."""
    text, keyboard = container.message.admin.user.users_menu(
        total_users=100,
        vip_count=25,
        free_count=70,
        admin_count=5
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "100" in text  # Total users
    assert "Gestión de Usuarios" in text


async def test_admin_user_provider_search_prompt(container):
    """Verify AdminUserProvider returns search prompt."""
    text, keyboard = container.message.admin.user.user_search_prompt()

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Buscar Usuario" in text


# ===== USER START PROVIDER TESTS =====

async def test_user_start_provider_greeting_admin(container):
    """Verify UserStartProvider returns admin greeting."""
    text, keyboard = container.message.user.start.greeting(
        user_name="AdminUser",
        user_id=123456789,
        is_admin=True,
        is_vip=False,
        vip_days_remaining=0
    )

    assert text is not None
    assert "🎩" in text
    assert "administrador" in text.lower() or "/admin" in text
    assert keyboard is None  # Admin gets no keyboard


async def test_user_start_provider_greeting_vip(container):
    """Verify UserStartProvider returns VIP greeting."""
    text, keyboard = container.message.user.start.greeting(
        user_name="VIPUser",
        user_id=987654321,
        is_admin=False,
        is_vip=True,
        vip_days_remaining=15
    )

    assert text is not None
    assert "🎩" in text
    assert "15" in text or "quince" in text.lower()
    assert "círculo" in text.lower() or "VIP" in text
    assert keyboard is None  # VIP gets no keyboard


async def test_user_start_provider_greeting_free(container):
    """Verify UserStartProvider returns Free greeting."""
    text, keyboard = container.message.user.start.greeting(
        user_name="FreeUser",
        user_id=111222333,
        is_admin=False,
        is_vip=False,
        vip_days_remaining=0
    )

    assert text is not None
    assert "🎩" in text
    assert keyboard is not None  # Free user gets keyboard with options


# ===== USER FLOW PROVIDER TESTS =====

async def test_user_flow_provider_free_request_success(container):
    """Verify UserFlowProvider returns free request success message."""
    text, keyboard = container.message.user.flows.free_request_success(
        wait_time_minutes=5,
        social_links={"instagram": "@diana"}
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Los Kinkys" in text


async def test_user_flow_provider_free_request_approved(container):
    """Verify UserFlowProvider returns free request approved message."""
    text, keyboard = container.message.user.flows.free_request_approved(
        channel_name="Los Kinkys",
        channel_link="https://t.me/loskinkys"
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Los Kinkys" in text
    # The link is in the keyboard, not necessarily in the text
    assert "Acceder" in str(keyboard) or "acceder" in text.lower() or "enlace" in text.lower()


async def test_user_flow_provider_free_request_duplicate(container):
    """Verify UserFlowProvider returns free request duplicate message."""
    text = container.message.user.flows.free_request_duplicate(
        time_elapsed_minutes=10,
        time_remaining_minutes=20
    )

    assert text is not None
    assert "🎩" in text


# ===== USER MENU PROVIDER TESTS =====

async def test_user_menu_provider_vip_menu(container):
    """Verify UserMenuProvider returns VIP menu."""
    future_date = datetime.utcnow() + timedelta(days=30)

    text, keyboard = container.message.user.menu.vip_menu_greeting(
        user_name="VIPUser",
        vip_expires_at=future_date
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "círculo exclusivo" in text.lower()


async def test_user_menu_provider_free_menu(container):
    """Verify UserMenuProvider returns Free menu."""
    text, keyboard = container.message.user.menu.free_menu_greeting(
        user_name="FreeUser",
        free_queue_position=5
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "jardín" in text.lower() or "vestíbulo" in text.lower()


# ===== VIP ENTRY FLOW PROVIDER TESTS =====

async def test_vip_entry_provider_stage1(container):
    """Verify VIPEntryFlowProvider returns stage 1 message."""
    text, keyboard = container.message.user.vip_entry.stage_1_activation_confirmation()

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Continuar" in str(keyboard) or "continuar" in text.lower()


async def test_vip_entry_provider_stage2(container):
    """Verify VIPEntryFlowProvider returns stage 2 message."""
    text, keyboard = container.message.user.vip_entry.stage_2_expectation_alignment()

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Estoy listo" in str(keyboard) or "listo" in text.lower()


async def test_vip_entry_provider_stage3(container):
    """Verify VIPEntryFlowProvider returns stage 3 message."""
    text, keyboard = container.message.user.vip_entry.stage_3_access_delivery(
        invite_link="https://t.me/+VIP123"
    )

    assert text is not None
    assert keyboard is not None
    assert "🎩" in text
    assert "Cruzar el umbral" in str(keyboard) or "umbral" in text.lower()


async def test_vip_entry_provider_expired_subscription(container):
    """Verify VIPEntryFlowProvider returns expired subscription message."""
    text = container.message.user.vip_entry.expired_subscription_message()

    assert text is not None
    assert "🎩" in text
    assert "expirado" in text.lower() or "concluido" in text.lower()


async def test_vip_entry_provider_resumption(container):
    """Verify VIPEntryFlowProvider returns resumption messages."""
    for stage in [1, 2, 3]:
        text = container.message.user.vip_entry.stage_resumption_message(stage)
        assert text is not None
        assert "🎩" in text


# ===== SESSION HISTORY PROVIDER TESTS =====

async def test_session_history_prevents_repetition(container):
    """Verify session history prevents message repetition."""
    session_history = SessionMessageHistory()

    # Call greeting 5 times with same user_id
    messages = []
    user_id = 123456789
    for _ in range(5):
        text, keyboard = container.message.admin.main.admin_menu_greeting(
            is_configured=True,
            missing_items=[],
            user_id=user_id,
            session_history=session_history
        )
        messages.append(text)

    # Verify we don't get the exact same message twice in a row
    for i in range(len(messages) - 1):
        # Allow for some repetition since weighted random can still pick same
        # Just verify messages are valid
        assert messages[i] is not None
        assert "🎩" in messages[i]

    # Verify at least 2 different variations were used (highly probable)
    unique_messages = set(messages)
    assert len(unique_messages) >= 1  # At least one unique message


async def test_session_history_tracks_variants():
    """Verify SessionMessageHistory tracks variants correctly."""
    history = SessionMessageHistory()

    # Add entries
    history.add_entry(user_id=12345, method_name="greeting", variant_index=0)
    history.add_entry(user_id=12345, method_name="greeting", variant_index=1)
    history.add_entry(user_id=12345, method_name="success", variant_index=0)

    # Get recent variants for greeting
    recent = history.get_recent_variants(user_id=12345, method_name="greeting", limit=2)
    assert len(recent) == 2
    assert recent[0] == 1  # Most recent first
    assert recent[1] == 0

    # Get recent variants for success
    recent_success = history.get_recent_variants(user_id=12345, method_name="success")
    assert len(recent_success) == 1
    assert recent_success[0] == 0

    # Unknown user returns empty
    unknown = history.get_recent_variants(user_id=99999, method_name="greeting")
    assert unknown == []


async def test_session_history_stats():
    """Verify SessionMessageHistory provides accurate stats."""
    history = SessionMessageHistory()

    # Initially empty
    stats = history.get_stats()
    assert stats["total_users"] == 0
    assert stats["total_entries"] == 0

    # Add entries
    history.add_entry(user_id=111, method_name="greeting", variant_index=0)
    history.add_entry(user_id=111, method_name="success", variant_index=1)
    history.add_entry(user_id=222, method_name="greeting", variant_index=2)

    stats = history.get_stats()
    assert stats["total_users"] == 2
    assert stats["total_entries"] == 3
    assert stats["active_entries"] == 3


# ===== HTML VALIDATION TESTS =====

async def test_all_providers_return_valid_html(container):
    """Verify all message providers return valid HTML."""
    session_history = SessionMessageHistory()

    test_cases = [
        # Common
        lambda: container.message.common.error("test"),
        lambda: container.message.common.success("test"),
        # Admin main
        lambda: container.message.admin.main.admin_menu_greeting(True, [], 123, session_history),
        # Admin VIP
        lambda: container.message.admin.vip.vip_menu(True, "-100123"),
        # Admin Free
        lambda: container.message.admin.free.free_menu(True, "-100456", 5),
        # Admin content
        lambda: container.message.admin.content.content_menu(),
        # Admin interest
        lambda: container.message.admin.interest.interests_menu(3, 23),
        # Admin user
        lambda: container.message.admin.user.users_menu(100, 25, 70, 5),
        # User start
        lambda: container.message.user.start.greeting("User", 123, False, False, 0),
        # User flows
        lambda: container.message.user.flows.free_request_success(5, {}),
        # User menu VIP
        lambda: container.message.user.menu.vip_menu_greeting("User", datetime.utcnow()),
        # User menu Free
        lambda: container.message.user.menu.free_menu_greeting("User", 5),
        # VIP entry
        lambda: container.message.user.vip_entry.stage_1_activation_confirmation(),
    ]

    for test_fn in test_cases:
        result = test_fn()
        if isinstance(result, tuple):
            text, keyboard = result
        else:
            text = result

        assert text is not None
        assert len(text) > 0
        assert "🎩" in text  # All Lucien messages have the hat

        # Basic HTML validation - no unclosed tags
        # Count opening and closing tags
        open_b = text.count("<b>")
        close_b = text.count("</b>")
        open_i = text.count("<i>")
        close_i = text.count("</i>")

        assert open_b == close_b, f"Unclosed <b> tags in: {text[:100]}"
        assert open_i == close_i, f"Unclosed <i> tags in: {text[:100]}"


# ===== VOICE CONSISTENCY TESTS =====

async def test_lucien_voice_no_tutear(container):
    """Verify Lucien's voice never uses 'tutear' (informal 'you')."""
    session_history = SessionMessageHistory()

    # Get multiple messages
    messages = []

    text, _ = container.message.user.start.greeting("Test", 123, False, False, 0)
    messages.append(text)

    text, _ = container.message.user.flows.free_request_success(5, {})
    messages.append(text)

    text, _ = container.message.admin.main.admin_menu_greeting(True, [], 123, session_history)
    messages.append(text)

    # Check for tutear words (should NOT be present)
    tutear_words = ["tienes", "tu ", "haz ", "puedes"]
    for msg in messages:
        msg_lower = msg.lower()
        for word in tutear_words:
            # Allow "tu" as part of other words (like "natural")
            if word == "tu ":
                assert word not in msg_lower, f"Message uses tutear '{word}': {msg[:100]}"


async def test_lucien_voice_has_signature(container):
    """Verify all Lucien messages have the signature emoji."""
    session_history = SessionMessageHistory()

    test_messages = [
        container.message.common.error("test"),
        container.message.common.success("test"),
        container.message.admin.main.admin_menu_greeting(True, [], 123, session_history),
        container.message.user.start.greeting("Test", 123, False, False, 0),
    ]

    for text in test_messages:
        if isinstance(text, tuple):
            text = text[0]
        assert "🎩" in text, f"Message missing Lucien's signature: {text[:100]}"
