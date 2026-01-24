"""
Test suite for LucienVoiceService foundation (Phase 1).

Tests validate:
- Stateless interface enforcement
- Voice consistency (Lucien's personality)
- HTML formatting
- ServiceContainer integration
- Lazy loading
- Utility methods (_compose, _choose_variant)
"""
import pytest
from bot.services.message.base import BaseMessageProvider
from bot.services.message.common import CommonMessages
from bot.services.message import LucienVoiceService
from bot.services.container import ServiceContainer


# ===== BASE MESSAGE PROVIDER TESTS =====

class TestBaseMessageProvider:
    """Test BaseMessageProvider abstract class and utility methods."""

    def test_base_is_abstract(self):
        """Verify BaseMessageProvider is abstract and cannot be instantiated directly."""
        from abc import ABC

        assert issubclass(BaseMessageProvider, ABC), \
            "BaseMessageProvider must inherit from ABC"

    def test_utility_methods_exist(self):
        """Verify _compose and _choose_variant methods exist."""
        # Create a concrete implementation for testing
        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()

        assert hasattr(provider, '_compose'), \
            "BaseMessageProvider must have _compose method"
        assert hasattr(provider, '_choose_variant'), \
            "BaseMessageProvider must have _choose_variant method"

    def test_compose_builds_message(self):
        """Test _compose combines header, body, and footer correctly."""
        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()

        # Test with header and body only
        result = provider._compose("Header", "Body")
        assert result == "Header\n\nBody", \
            "Should combine header and body with double newline"

        # Test with header, body, and footer
        result = provider._compose("Header", "Body", "Footer")
        assert result == "Header\n\nBody\n\nFooter", \
            "Should combine all three parts with double newlines"

    def test_choose_variant_equal_weights(self):
        """Test _choose_variant with equal weights (random.choice behavior)."""
        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()
        variants = ["a", "b", "c"]

        # Multiple calls should eventually return all variants
        results = set()
        for _ in range(50):
            result = provider._choose_variant(variants)
            assert result in variants, "Must return valid variant"
            results.add(result)

        # With 50 iterations, should have seen all variants at least once
        assert len(results) == 3, "Should eventually return all variants"

    def test_choose_variant_weighted(self):
        """Test _choose_variant with weighted selection."""
        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()
        variants = ["common", "rare"]
        weights = [0.9, 0.1]  # 90% common, 10% rare

        # With 100 iterations, "common" should appear much more often
        results = []
        for _ in range(100):
            result = provider._choose_variant(variants, weights)
            results.append(result)

        common_count = results.count("common")
        rare_count = results.count("rare")

        # "common" should appear significantly more often
        assert common_count > rare_count * 5, \
            f"Weighted selection failed: common={common_count}, rare={rare_count}"

    def test_choose_variant_empty_raises_error(self):
        """Test _choose_variant raises ValueError for empty list."""
        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()

        with pytest.raises(ValueError, match="variants cannot be empty"):
            provider._choose_variant([])

    def test_choose_variant_mismatched_weights_raises_error(self):
        """Test _choose_variant raises ValueError for mismatched weights."""
        class TestProvider(BaseMessageProvider):
            pass

        provider = TestProvider()

        with pytest.raises(ValueError, match="weights and variants must have same length"):
            provider._choose_variant(["a", "b"], [0.5])  # 2 variants, 1 weight


# ===== COMMON MESSAGES TESTS =====

class TestCommonMessages:
    """Test CommonMessages provider for voice consistency and formatting."""

    def test_inherits_from_base(self):
        """Verify CommonMessages inherits from BaseMessageProvider."""
        common = CommonMessages()
        assert isinstance(common, BaseMessageProvider), \
            "CommonMessages must inherit from BaseMessageProvider"

    def test_error_maintains_lucien_voice(self, assert_lucien_voice):
        """Verify error messages maintain Lucien's voice (semantic test)."""
        common = CommonMessages()
        error_msg = common.error("test context")

        # Use semantic assertion - tests emoji, no tutear, no jargon, HTML
        assert_lucien_voice(error_msg)

    def test_success_maintains_lucien_voice(self, assert_lucien_voice):
        """Verify success messages maintain Lucien's voice (semantic test)."""
        common = CommonMessages()
        success_msg = common.success("action completed")

        # Use semantic assertion
        assert_lucien_voice(success_msg)

    def test_error_has_lucien_emoji(self):
        """Verify error messages include Lucien's characteristic emoji."""
        common = CommonMessages()
        error_msg = common.error("test context")

        assert "🎩" in error_msg, \
            "Error messages must include 🎩 emoji (Lucien's signature)"

    def test_error_mentions_diana(self):
        """Verify error messages mention Diana (authority figure)."""
        common = CommonMessages()
        error_msg = common.error("test context")

        # Check for "Diana" or "consultar" (Lucien defers to Diana)
        msg_lower = error_msg.lower()
        assert "diana" in msg_lower or "consultar" in msg_lower, \
            "Error messages should mention Diana or consulting with her"

    def test_error_no_tutear(self):
        """Verify error messages don't use 'tú' form (tutear)."""
        common = CommonMessages()
        error_msg = common.error("test context")

        forbidden = ["tienes", "tu ", "tu.", "haz", "puedes"]
        msg_lower = error_msg.lower()

        for word in forbidden:
            assert word not in msg_lower, \
                f"Error messages must not tutear (found '{word}')"

    def test_error_no_technical_jargon(self):
        """Verify error messages avoid technical jargon."""
        common = CommonMessages()
        error_msg = common.error("test context")

        technical = ["database", "api", "exception", "null pointer", "500"]
        msg_lower = error_msg.lower()

        for term in technical:
            assert term not in msg_lower, \
                f"Error messages must avoid technical jargon (found '{term}')"

    def test_error_includes_context(self):
        """Verify error messages include provided context."""
        common = CommonMessages()

        error_msg = common.error("al generar el token")
        assert "al generar el token" in error_msg, \
            "Error messages must include provided context"

        error_msg = common.error("al configurar el canal")
        assert "al configurar el canal" in error_msg, \
            "Error messages must include provided context"

    def test_error_includes_suggestion(self):
        """Verify error messages can include optional suggestions."""
        common = CommonMessages()
        error_msg = common.error("context", suggestion="Verifique los permisos")

        assert "Verifique los permisos" in error_msg, \
            "Error messages must include suggestion when provided"

    def test_error_has_html_formatting(self):
        """Verify error messages use HTML formatting."""
        common = CommonMessages()
        error_msg = common.error("test context")

        # Should have bold tags for "Lucien:"
        assert "<b>" in error_msg and "</b>" in error_msg, \
            "Error messages must use HTML <b> tags"

        # Should have italic tags for message body
        assert "<i>" in error_msg and "</i>" in error_msg, \
            "Error messages must use HTML <i> tags"

    def test_success_has_lucien_emoji(self):
        """Verify success messages include Lucien's emoji."""
        common = CommonMessages()
        success_msg = common.success("action completed")

        assert "🎩" in success_msg, \
            "Success messages must include 🎩 emoji"

    def test_success_positive_tone(self):
        """Verify success messages have positive tone."""
        common = CommonMessages()
        success_msg = common.success("action completed")

        positive_words = ["excelente", "como se esperaba", "completado"]
        msg_lower = success_msg.lower()

        has_positive = any(word in msg_lower for word in positive_words)
        assert has_positive, \
            "Success messages must have positive tone"

    def test_success_includes_action(self):
        """Verify success messages include the action that was completed."""
        common = CommonMessages()

        success_msg = common.success("token generado")
        assert "token generado" in success_msg, \
            "Success messages must include the completed action"

        success_msg = common.success("canal configurado")
        assert "canal configurado" in success_msg, \
            "Success messages must include the completed action"

    def test_success_celebratory_tone(self):
        """Verify success messages can have celebratory tone."""
        common = CommonMessages()

        # Normal success
        normal_msg = common.success("action")
        assert "Diana" not in normal_msg or "aprob" not in normal_msg.lower(), \
            "Normal success should not mention Diana's approval"

        # Celebratory success
        celebrate_msg = common.success("action", celebrate=True)
        # Celebratory messages should mention Diana approving
        assert "Diana" in celebrate_msg or "aprob" in celebrate_msg.lower() or "progreso" in celebrate_msg.lower(), \
            "Celebratory success should mention Diana or progress"

    def test_not_found_escapes_html(self):
        """Verify not_found messages escape HTML in identifiers."""
        common = CommonMessages()
        not_found_msg = common.not_found("token", "<script>alert('xss')</script>")

        # Should escape < and >
        assert ("&lt;" in not_found_msg and "&gt;" in not_found_msg), \
            "not_found must escape HTML in identifiers"

        # Should NOT contain raw script tags
        assert "<script>" not in not_found_msg, \
            "not_found must not include raw HTML tags"
        assert "</script>" not in not_found_msg, \
            "not_found must not include raw HTML tags"

    def test_not_found_has_lucien_voice(self):
        """Verify not_found messages maintain Lucien's voice."""
        common = CommonMessages()
        not_found_msg = common.not_found("token", "ABC123")

        # Should have emoji
        assert "🎩" in not_found_msg, \
            "not_found messages must include 🎩 emoji"

        # Should be polite and offer help
        assert "archiv" in not_found_msg.lower() or "diana" in not_found_msg.lower() or "ayud" in not_found_msg.lower(), \
            "not_found messages should reference files or offer help"

        # Should include identifier
        assert "ABC123" in not_found_msg, \
            "not_found messages must include the identifier"

    def test_generic_error_maintains_composure(self):
        """Verify generic_error maintains Lucien's sophisticated composure."""
        common = CommonMessages()
        generic_msg = common.generic_error()

        # Should have emoji
        assert "🎩" in generic_msg, \
            "generic_error must include 🎩 emoji"

        # Should be mysterious but calm (not panicking)
        panic_words = ["critical", "fatal", "panic", "crash"]
        msg_lower = generic_msg.lower()

        for word in panic_words:
            assert word not in msg_lower, \
                f"generic_error must not show panic (found '{word}')"

        # Should offer to help
        help_words = ["intente", "ayuda", "asist", "disposición"]
        has_help = any(word in msg_lower for word in help_words)
        assert has_help, \
            "generic_error should offer assistance"


# ===== SERVICE CONTAINER INTEGRATION TESTS =====

class TestServiceContainerIntegration:
    """Test LucienVoiceService integration with ServiceContainer."""

    def test_message_property_exists(self):
        """Verify ServiceContainer has message property."""
        # Create minimal mock objects
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        assert hasattr(container, 'message'), \
            "ServiceContainer must have 'message' property"

    def test_message_property_lazy_loading(self):
        """Verify message service is lazy-loaded (not loaded until accessed)."""
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        # Should not be loaded initially
        loaded = container.get_loaded_services()
        assert "message" not in loaded, \
            "Message service should not be loaded before first access"

        # Access the property
        _ = container.message

        # Now it should be loaded
        loaded = container.get_loaded_services()
        assert "message" in loaded, \
            "Message service should be loaded after first access"

    def test_message_returns_lucien_voice_service(self):
        """Verify message property returns LucienVoiceService instance."""
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        msg_service = container.message
        assert isinstance(msg_service, LucienVoiceService), \
            "message property must return LucienVoiceService instance"

    def test_message_service_caching(self):
        """Verify message service is cached and reused."""
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        # Access twice
        service1 = container.message
        service2 = container.message

        # Should be the same instance
        assert service1 is service2, \
            "Message service must be cached and reused"

    def test_common_provider_accessible(self):
        """Verify CommonMessages provider is accessible through service."""
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        # Access common provider
        common = container.message.common
        assert isinstance(common, CommonMessages), \
            "Common provider must be accessible via container.message.common"

    def test_end_to_end_message_generation(self):
        """Test complete flow: container -> service -> provider -> message."""
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        # Generate error message through complete chain
        error_msg = container.message.common.error("test context")

        # Verify it works
        assert "🎩" in error_msg, "Must include Lucien emoji"
        assert "test context" in error_msg, "Must include context"
        assert ("<b>" in error_msg and "</b>" in error_msg), "Must have HTML formatting"

        # Generate success message
        success_msg = container.message.common.success("test action")

        # Verify it works
        assert "🎩" in success_msg, "Must include Lucien emoji"
        assert "test action" in success_msg, "Must include action"

    def test_service_is_stateless(self):
        """Verify message service does not store session or bot."""
        class MockSession:
            pass

        class MockBot:
            pass

        container = ServiceContainer(MockSession(), MockBot())

        msg_service = container.message

        # Should not have session or bot as instance variables
        assert not hasattr(msg_service, 'session'), \
            "LucienVoiceService must not store session"
        assert not hasattr(msg_service, 'bot'), \
            "LucienVoiceService must not store bot"

        # Common provider should also be stateless
        common = msg_service.common
        assert not hasattr(common, 'session'), \
            "CommonMessages must not store session"
        assert not hasattr(common, 'bot'), \
            "CommonMessages must not store bot"
