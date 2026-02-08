"""
Tests for User Message Providers (UserStartMessages, UserFlowMessages).

Uses semantic assertions to test INTENT not exact wording,
making tests resilient to message variations.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from bot.services.message import LucienVoiceService


# ============================================================================
# TEST CLASS: UserStartMessages
# ============================================================================


class TestUserStartMessages:
    """Test suite for UserStartMessages provider."""

    @pytest.mark.parametrize("hour,expected_period", [
        (9, "morning"),    # 9 AM
        (15, "afternoon"), # 3 PM
        (22, "evening")    # 10 PM
    ])
    def test_greeting_time_aware(self, assert_time_aware, hour, expected_period):
        """Test greeting adapts to time of day."""
        # Mock datetime to specific hour
        mock_datetime = datetime(2026, 1, 24, hour, 0, 0, tzinfo=timezone.utc)

        with patch('bot.services.message.user_start.datetime') as mock_dt:
            mock_dt.now.return_value = mock_datetime

            service = LucienVoiceService()
            text, keyboard = service.user.start.greeting(
                user_name="Juan",
                is_admin=False,
                is_vip=False
            )

            # Validate time-appropriate greeting
            assert_time_aware(text, expected_period)

    def test_greeting_admin_redirect(self):
        """Test admin greeting redirects to /admin without keyboard."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.greeting(
            user_name="Admin",
            is_admin=True,
            is_vip=False
        )

        # Admin should be redirected to /admin
        assert "/admin" in text.lower()

        # No keyboard for admin (they use /admin command)
        assert keyboard is None

    def test_greeting_vip_shows_days(self):
        """Test VIP greeting shows days remaining."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.greeting(
            user_name="VIPUser",
            is_admin=False,
            is_vip=True,
            vip_days_remaining=15
        )

        # Must show days remaining
        assert "15" in text

        # Should mention VIP status or exclusive access
        text_lower = text.lower()
        vip_indicators = ["vip", "exclusivo", "privilegio", "círculo"]
        assert any(indicator in text_lower for indicator in vip_indicators)

        # No keyboard for VIP (already has access)
        assert keyboard is None

    def test_greeting_free_has_options_keyboard(self):
        """Test free user greeting has options keyboard."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.greeting(
            user_name="FreeUser",
            is_admin=False,
            is_vip=False
        )

        # Must have keyboard with 2 options
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2  # 2 rows

        # Check buttons exist (text can vary)
        button_texts = [
            row[0].text for row in keyboard.inline_keyboard
        ]
        assert len(button_texts) == 2

        # Callback data should be present
        callback_data = [
            row[0].callback_data for row in keyboard.inline_keyboard
        ]
        assert all(data for data in callback_data)

    def test_greeting_variations_distribution(self, assert_greeting_present):
        """Test greeting uses multiple variations (not always same text)."""
        service = LucienVoiceService()

        # Generate 30 greetings (catches all variants with >99% confidence)
        greetings = []
        for _ in range(30):
            text, _ = service.user.start.greeting(
                user_name="Test",
                is_admin=False,
                is_vip=False
            )
            greetings.append(text)

            # All must have greeting
            assert_greeting_present(text)

        # Should have at least 2 unique variations
        # (Use >=2 not ==3 to handle <1% randomness edge case)
        unique_greetings = set(greetings)
        assert len(unique_greetings) >= 2, \
            f"Expected variations, got {len(unique_greetings)} unique from 30 iterations"

    def test_deep_link_activation_success_celebratory(self):
        """Test deep link activation success has celebratory tone."""
        service = LucienVoiceService()
        text, keyboard = service.user.start.deep_link_activation_success(
            user_name="Pedro",
            plan_name="Plan Mensual",
            duration_days=30,
            price="$9.99",
            days_remaining=30,
            invite_link="https://t.me/+ABC123"
        )

        # Celebratory indicators
        text_lower = text.lower()
        celebratory = ["activado", "activada", "bienvenido", "felicidades", "éxito"]
        assert any(word in text_lower for word in celebratory), \
            "Success message should be celebratory"

        # Must show plan details
        assert "Plan Mensual" in text or "mensual" in text_lower

        # Must show duration
        assert "30" in text  # duration_days

        # Should have keyboard to join channel
        assert keyboard is not None

        # Keyboard should have URL button (link is in button, not text)
        assert len(keyboard.inline_keyboard) > 0
        button = keyboard.inline_keyboard[0][0]
        assert button.url == "https://t.me/+ABC123"

    @pytest.mark.parametrize("error_type,expected_keywords", [
        ("invalid", ["válida", "válido", "inválido"]),
        ("used", ["utilizada", "usado", "utilizado"]),
        ("expired", ["expirado", "caducado", "vencido"]),
        ("no_plan", ["plan", "disponible"])
    ])
    def test_deep_link_activation_error_types(self, error_type, expected_keywords):
        """Test deep link activation errors have appropriate messaging."""
        service = LucienVoiceService()
        text = service.user.start.deep_link_activation_error(error_type=error_type)

        # Check for expected keywords (any one of them)
        text_lower = text.lower()
        has_keyword = any(keyword in text_lower for keyword in expected_keywords)
        assert has_keyword, \
            f"Error type '{error_type}' should mention: {expected_keywords}"

    @pytest.mark.parametrize("method_name,kwargs", [
        ("greeting", {
            "user_name": "Test"
        }),
        ("deep_link_activation_success", {
            "user_name": "Test",
            "plan_name": "Plan Test",
            "duration_days": 30,
            "price": "$9.99",
            "days_remaining": 30,
            "invite_link": "https://t.me/+TEST"
        }),
        ("deep_link_activation_error", {
            "error_type": "invalid"
        })
    ])
    def test_all_messages_maintain_lucien_voice(self, assert_lucien_voice, method_name, kwargs):
        """Test all UserStartMessages maintain Lucien's voice."""
        service = LucienVoiceService()
        method = getattr(service.user.start, method_name)

        result = method(**kwargs)

        # Extract text (method returns tuple or str)
        text = result[0] if isinstance(result, tuple) else result

        # Validate voice characteristics
        assert_lucien_voice(text)


# ============================================================================
# TEST CLASS: UserFlowMessages
# ============================================================================


class TestUserFlowMessages:
    """Test suite for UserFlowMessages provider."""

    def test_free_request_success_has_lucien_voice(self):
        """Test free request success uses Lucien's voice and format."""
        service = LucienVoiceService()
        text, keyboard = service.user.flows.free_request_success(wait_time_minutes=30)

        # Must have Lucien's signature
        assert "🎩" in text
        assert "Lucien" in text

        # Should mention the channel
        assert "Los Kinkys" in text

        # Should have social media keyboard
        assert keyboard is not None

    def test_free_request_success_reassures_patience(self):
        """Test free request success reassures patience and Diana's evaluation."""
        service = LucienVoiceService()
        text, keyboard = service.user.flows.free_request_success(wait_time_minutes=30)

        # Should mention Diana's decision/evaluation
        text_lower = text.lower()
        reassurance_keywords = ["diana", "revisión", "evalúa", "decisión", "vendré a buscarle"]
        assert any(keyword in text_lower for keyword in reassurance_keywords), \
            "Message should reassure user that request is being evaluated"

    def test_free_request_success_can_close_chat(self):
        """Test free request success tells user they don't need to wait."""
        service = LucienVoiceService()
        text, keyboard = service.user.flows.free_request_success(wait_time_minutes=30)

        # Should mention user doesn't need to wait in chat
        text_lower = text.lower()
        wait_keywords = ["no necesita quedarse", "no necesita esperar", "esperando en este chat"]
        assert any(keyword in text_lower for keyword in wait_keywords), \
            "Message should tell user they don't need to wait in the chat"

    def test_free_request_duplicate_reassures_waiting(self):
        """Test duplicate request reassures user their request is in progress."""
        service = LucienVoiceService()
        text = service.user.flows.free_request_duplicate(
            time_elapsed_minutes=15,
            time_remaining_minutes=10
        )

        # Should reassure that access is in motion
        text_lower = text.lower()
        progress_keywords = ["ya está en movimiento", "acceso", "puerta se abrirá"]
        assert any(keyword in text_lower for keyword in progress_keywords), \
            "Message should reassure user that their request is in progress"

    def test_free_request_duplicate_philosophical_tone(self):
        """Test duplicate request uses philosophical tone (not scolding)."""
        service = LucienVoiceService()
        text = service.user.flows.free_request_duplicate(
            time_elapsed_minutes=15,
            time_remaining_minutes=10
        )

        # Should NOT scold or be harsh
        text_lower = text.lower()
        harsh_words = ["error", "incorrecto", "prohibido", "no puede", "ya le dije", "espere"]
        assert not any(word in text_lower for word in harsh_words), \
            "Message should be philosophical, not scolding"

        # Should use philosophical/reflective language
        philosophical_keywords = ["deseo", "umbral", "espera", "puerta", "entrar"]
        assert any(keyword in text_lower for keyword in philosophical_keywords), \
            "Message should use philosophical tone about waiting and entry"

    @pytest.mark.parametrize("error_type,expected_keywords", [
        ("channel_not_configured", ["canal", "configurado", "disponible"]),
        ("already_in_channel", ["ya", "miembro", "canal"]),
        ("rate_limited", ["intentos", "espere", "momento"])
    ])
    def test_free_request_error_types(self, error_type, expected_keywords):
        """Test free request errors have appropriate messaging."""
        service = LucienVoiceService()
        text = service.user.flows.free_request_error(error_type=error_type)

        # Check for expected keywords (any one of them)
        text_lower = text.lower()
        has_keyword = any(keyword in text_lower for keyword in expected_keywords)
        assert has_keyword, \
            f"Error type '{error_type}' should mention: {expected_keywords}"

    @pytest.mark.parametrize("method_name,kwargs", [
        ("free_request_success", {
            "wait_time_minutes": 30
        }),
        ("free_request_duplicate", {
            "time_elapsed_minutes": 15,
            "time_remaining_minutes": 10
        }),
        ("free_request_error", {
            "error_type": "channel_not_configured"
        })
    ])
    def test_all_free_messages_maintain_voice(self, assert_lucien_voice, method_name, kwargs):
        """Test all UserFlowMessages maintain Lucien's voice."""
        service = LucienVoiceService()
        method = getattr(service.user.flows, method_name)

        result = method(**kwargs)

        # Extract text (methods may return tuple or str)
        text = result[0] if isinstance(result, tuple) else result

        # Validate voice characteristics
        assert_lucien_voice(text)
