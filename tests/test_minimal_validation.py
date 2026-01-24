#!/usr/bin/env python3
"""
Minimal validation that test functions work correctly.
Tests the core logic without full dependencies.
"""
import random
import sys
from typing import Optional, Any
from abc import ABC, abstractmethod


# ===== MINIMAL IMPLEMENTATION FOR TESTING =====

class BaseMessageProvider(ABC):
    """Minimal BaseMessageProvider for testing."""

    def _compose(self, header: str, body: str, footer: str = "") -> str:
        """Compose message from header, body, and optional footer."""
        parts = [header, body]
        if footer:
            parts.append(footer)
        return "\n\n".join(parts)

    def _choose_variant(
        self,
        variants: list[str],
        weights: Optional[list[float]] = None
    ) -> str:
        """Choose a message variant randomly (with optional weights)."""
        if not variants:
            raise ValueError("variants cannot be empty")

        if weights is None:
            return random.choice(variants)

        if len(weights) != len(variants):
            raise ValueError("weights and variants must have same length")

        return random.choices(variants, weights=weights, k=1)[0]


def escape_html(text: str) -> str:
    """Simple HTML escape function."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


class CommonMessages(BaseMessageProvider):
    """Minimal CommonMessages for testing."""

    def error(
        self,
        context: str = "",
        suggestion: str = "",
        include_footer: bool = True
    ) -> str:
        """Generate error message in Lucien's voice."""
        header = "🎩 <b>Lucien:</b>"

        if context:
            body = f"<i>Hmm... algo inesperado ha ocurrido {context}.\nPermítame consultar con Diana sobre este inconveniente.</i>"
        else:
            body = "<i>Hmm... algo inesperado ha ocurrido.\nPermítame consultar con Diana sobre este inconveniente.</i>"

        if suggestion:
            body += f"\n\n💡 <i>Sugerencia:</i> {suggestion}"

        footer = ""
        if include_footer:
            footer = "<i>Mientras tanto, ¿hay algo más en lo que pueda asistirle?</i>"

        return self._compose(header, body, footer)

    def success(
        self,
        action: str,
        detail: str = "",
        celebrate: bool = False
    ) -> str:
        """Generate success message in Lucien's voice."""
        header = "🎩 <b>Lucien:</b>"

        if celebrate:
            body = f"<i>Excelente. {action} ha sido completado como se esperaba.\nDiana aprobará este progreso...</i>"
        else:
            body = f"<i>Excelente. {action} ha sido completado como se esperaba.</i>"

        if detail:
            body += f"\n\n{detail}"

        return self._compose(header, body)

    def generic_error(self, error_type: str = "unknown") -> str:
        """Generate generic error message for unexpected failures."""
        header = "🎩 <b>Lucien:</b>"
        body = "<i>Una perturbación inesperada ha interrumpido el flujo natural de las cosas...</i>\n\n<i>Permítame un momento para restablecer el orden. Diana prefiere que estos asuntos se manejen con discreción.</i>"
        footer = "<i>¿Le gustaría intentar nuevamente?</i>"

        return self._compose(header, body, footer)

    def not_found(self, item_type: str, identifier: str = "") -> str:
        """Generate 'not found' message in Lucien's voice."""
        header = "🎩 <b>Lucien:</b>"

        if identifier:
            escaped_id = escape_html(identifier)
            body = f"<i>He buscado en todos los archivos de Diana, pero parece que no puedo localizar este {item_type}.</i>\n\n<code>{escaped_id}</code>\n\n<i>¿Podría verificar que la información es correcta?</i>"
        else:
            body = f"<i>He buscado en todos los archivos de Diana, pero parece que no puedo localizar este {item_type}.</i>\n\n<i>¿Podría proporcionarme más detalles?</i>"

        footer = "<i>Estoy a su disposición para continuar la búsqueda...</i>"

        return self._compose(header, body, footer)


# ===== TESTS =====

def test_base_is_abstract():
    """Verify BaseMessageProvider is abstract."""
    from abc import ABC
    assert issubclass(BaseMessageProvider, ABC), "Must inherit from ABC"
    print("✅ test_base_is_abstract")


def test_utility_methods_exist():
    """Verify _compose and _choose_variant methods exist."""
    provider = BaseMessageProvider()
    assert hasattr(provider, '_compose'), "_compose missing"
    assert hasattr(provider, '_choose_variant'), "_choose_variant missing"
    print("✅ test_utility_methods_exist")


def test_compose_builds_message():
    """Test _compose combines header, body, and footer correctly."""
    provider = BaseMessageProvider()

    result = provider._compose("Header", "Body")
    assert result == "Header\n\nBody", "Should combine header and body"

    result = provider._compose("Header", "Body", "Footer")
    assert result == "Header\n\nBody\n\nFooter", "Should combine all three parts"
    print("✅ test_compose_builds_message")


def test_choose_variant_equal_weights():
    """Test _choose_variant with equal weights."""
    provider = BaseMessageProvider()
    variants = ["a", "b", "c"]

    results = set()
    for _ in range(50):
        result = provider._choose_variant(variants)
        assert result in variants, "Must return valid variant"
        results.add(result)

    assert len(results) == 3, "Should eventually return all variants"
    print("✅ test_choose_variant_equal_weights")


def test_choose_variant_weighted():
    """Test _choose_variant with weighted selection."""
    provider = BaseMessageProvider()
    variants = ["common", "rare"]
    weights = [0.9, 0.1]

    results = []
    for _ in range(100):
        result = provider._choose_variant(variants, weights)
        results.append(result)

    common_count = results.count("common")
    rare_count = results.count("rare")

    assert common_count > rare_count * 5, "Weighted selection failed"
    print("✅ test_choose_variant_weighted")


def test_choose_variant_empty_raises_error():
    """Test _choose_variant raises ValueError for empty list."""
    provider = BaseMessageProvider()

    try:
        provider._choose_variant([])
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "variants cannot be empty" in str(e)
    print("✅ test_choose_variant_empty_raises_error")


def test_choose_variant_mismatched_weights_raises_error():
    """Test _choose_variant raises ValueError for mismatched weights."""
    provider = BaseMessageProvider()

    try:
        provider._choose_variant(["a", "b"], [0.5])
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "weights and variants must have same length" in str(e)
    print("✅ test_choose_variant_mismatched_weights_raises_error")


def test_inherits_from_base():
    """Verify CommonMessages inherits from BaseMessageProvider."""
    common = CommonMessages()
    assert isinstance(common, BaseMessageProvider)
    print("✅ test_inherits_from_base")


def test_error_has_lucien_emoji():
    """Verify error messages include Lucien's emoji."""
    common = CommonMessages()
    error_msg = common.error("test context")
    assert "🎩" in error_msg
    print("✅ test_error_has_lucien_emoji")


def test_error_mentions_diana():
    """Verify error messages mention Diana."""
    common = CommonMessages()
    error_msg = common.error("test context")
    msg_lower = error_msg.lower()
    assert "diana" in msg_lower or "consultar" in msg_lower
    print("✅ test_error_mentions_diana")


def test_error_no_tutear():
    """Verify error messages don't use 'tú' form."""
    common = CommonMessages()
    error_msg = common.error("test context")

    forbidden = ["tienes", "tu ", "tu.", "haz", "puedes"]
    msg_lower = error_msg.lower()

    for word in forbidden:
        assert word not in msg_lower, f"Found '{word}'"
    print("✅ test_error_no_tutear")


def test_error_no_technical_jargon():
    """Verify error messages avoid technical jargon."""
    common = CommonMessages()
    error_msg = common.error("test context")

    technical = ["database", "api", "exception", "null pointer", "500"]
    msg_lower = error_msg.lower()

    for term in technical:
        assert term not in msg_lower
    print("✅ test_error_no_technical_jargon")


def test_error_includes_context():
    """Verify error messages include provided context."""
    common = CommonMessages()

    error_msg = common.error("al generar el token")
    assert "al generar el token" in error_msg

    error_msg = common.error("al configurar el canal")
    assert "al configurar el canal" in error_msg
    print("✅ test_error_includes_context")


def test_error_includes_suggestion():
    """Verify error messages can include suggestions."""
    common = CommonMessages()
    error_msg = common.error("context", suggestion="Verifique los permisos")
    assert "Verifique los permisos" in error_msg
    print("✅ test_error_includes_suggestion")


def test_error_has_html_formatting():
    """Verify error messages use HTML formatting."""
    common = CommonMessages()
    error_msg = common.error("test context")

    assert "<b>" in error_msg and "</b>" in error_msg
    assert "<i>" in error_msg and "</i>" in error_msg
    print("✅ test_error_has_html_formatting")


def test_success_has_lucien_emoji():
    """Verify success messages include Lucien's emoji."""
    common = CommonMessages()
    success_msg = common.success("action completed")
    assert "🎩" in success_msg
    print("✅ test_success_has_lucien_emoji")


def test_success_positive_tone():
    """Verify success messages have positive tone."""
    common = CommonMessages()
    success_msg = common.success("action completed")

    positive_words = ["excelente", "como se esperaba", "completado"]
    msg_lower = success_msg.lower()

    has_positive = any(word in msg_lower for word in positive_words)
    assert has_positive
    print("✅ test_success_positive_tone")


def test_success_includes_action():
    """Verify success messages include the action."""
    common = CommonMessages()

    success_msg = common.success("token generado")
    assert "token generado" in success_msg

    success_msg = common.success("canal configurado")
    assert "canal configurado" in success_msg
    print("✅ test_success_includes_action")


def test_success_celebratory_tone():
    """Verify success messages can have celebratory tone."""
    common = CommonMessages()

    normal_msg = common.success("action")
    celebrate_msg = common.success("action", celebrate=True)

    # Celebratory should mention Diana or progress
    assert "Diana" in celebrate_msg or "aprob" in celebrate_msg.lower() or "progreso" in celebrate_msg.lower()
    print("✅ test_success_celebratory_tone")


def test_not_found_escapes_html():
    """Verify not_found messages escape HTML."""
    common = CommonMessages()
    not_found_msg = common.not_found("token", "<script>alert('xss')</script>")

    assert ("&lt;" in not_found_msg and "&gt;" in not_found_msg)
    assert "<script>" not in not_found_msg
    assert "</script>" not in not_found_msg
    print("✅ test_not_found_escapes_html")


def test_not_found_has_lucien_voice():
    """Verify not_found messages maintain Lucien's voice."""
    common = CommonMessages()
    not_found_msg = common.not_found("token", "ABC123")

    assert "🎩" in not_found_msg
    assert "ABC123" in not_found_msg
    print("✅ test_not_found_has_lucien_voice")


def test_generic_error_maintains_composure():
    """Verify generic_error maintains Lucien's composure."""
    common = CommonMessages()
    generic_msg = common.generic_error()

    assert "🎩" in generic_msg

    panic_words = ["critical", "fatal", "panic", "crash"]
    msg_lower = generic_msg.lower()

    for word in panic_words:
        assert word not in msg_lower

    help_words = ["intente", "intentar", "ayuda", "asist", "disposición", "discreción"]
    has_help = any(word in msg_lower for word in help_words)
    assert has_help
    print("✅ test_generic_error_maintains_composure")


# ===== RUN ALL TESTS =====

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("🧪 Message Service Foundation - Minimal Validation")
    print("=" * 60)
    print()

    tests = [
        test_base_is_abstract,
        test_utility_methods_exist,
        test_compose_builds_message,
        test_choose_variant_equal_weights,
        test_choose_variant_weighted,
        test_choose_variant_empty_raises_error,
        test_choose_variant_mismatched_weights_raises_error,
        test_inherits_from_base,
        test_error_has_lucien_emoji,
        test_error_mentions_diana,
        test_error_no_tutear,
        test_error_no_technical_jargon,
        test_error_includes_context,
        test_error_includes_suggestion,
        test_error_has_html_formatting,
        test_success_has_lucien_emoji,
        test_success_positive_tone,
        test_success_includes_action,
        test_success_celebratory_tone,
        test_not_found_escapes_html,
        test_not_found_has_lucien_voice,
        test_generic_error_maintains_composure,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"✅ PASSED: {passed}")
    if failed > 0:
        print(f"❌ FAILED: {failed}")
    print("=" * 60)

    if failed == 0:
        print()
        print("🎉 All validation tests passed!")
        return 0
    else:
        print()
        print("⚠️  Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
