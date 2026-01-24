"""
Tests for Voice Linter - AST-based voice consistency checker.

Tests cover all violation types:
- Tutear detection (tienes, tu, haz, puedes, hagas)
- Technical jargon detection (database, api, exception, error code, null)
- Missing emoji in multi-line messages
- Missing HTML in long messages
- Edge cases (short strings, HTML-only strings, syntax errors)
"""

import pytest
from pathlib import Path
from bot.utils.voice_linter import check_file, VoiceViolationChecker, FORBIDDEN_TUTEAR, TECHNICAL_JARGON, LUCIEN_EMOJI


class TestTutearDetection:
    """Tests for tutear (informal Spanish) detection."""

    def test_tutear_detection_tienes(self, tmp_path):
        """Test detection of 'tienes' in strings."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    return "Si tienes alguna pregunta, no dudes en contactarme."
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "tutear"
        assert "tienes" in violations[0]["word"]

    def test_tutear_detection_tu_with_space(self, tmp_path):
        """Test detection of 'tu ' with space boundary."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    # String >50 chars to avoid being skipped
    return "tu solicitud ha sido procesada correctamente y le agradecemos su paciencia."
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "tutear"
        assert violations[0]["word"] == "tu "

    def test_tutear_detection_haz(self, tmp_path):
        """Test detection of 'haz' command form."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    return "Por favor, haz clic en el botón de abajo para continuar."
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "tutear"
        assert violations[0]["word"] == "haz"

    def test_tutear_false_positive_future(self, tmp_path):
        """Test that 'future' doesn't trigger 'tu' detection."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    return "En el futuro, podremos mejorar este servicio."
''')
        violations = check_file(test_file)
        # Should not detect 'tu' in 'future'
        tutear_violations = [v for v in violations if v["type"] == "tutear"]
        assert len(tutear_violations) == 0


class TestJargonDetection:
    """Tests for technical jargon detection."""

    def test_jargon_detection_database(self, tmp_path):
        """Test detection of 'database' term."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    return "Error connecting to database, please try again later."
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "jargon"
        assert violations[0]["term"] == "database"

    def test_jargon_detection_api(self, tmp_path):
        """Test detection of 'api' term."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    return "The API is currently unavailable, please try again soon."
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "jargon"
        assert violations[0]["term"] == "api"

    def test_jargon_detection_exception(self, tmp_path):
        """Test detection of 'exception' term."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_message():
    return "An exception occurred while processing your request."
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "jargon"
        assert violations[0]["term"] == "exception"


class TestMissingEmoji:
    """Tests for missing emoji detection in multi-line messages."""

    def test_missing_emoji_multiline(self, tmp_path):
        """Test detection of missing emoji in multi-line strings."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_welcome_message():
    return """
    Bienvenido al servicio exclusivo.

    Estamos encantados de recibirle en nuestro círculo.
    """
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "missing_emoji"
        assert "emoji" in violations[0]["message"].lower()

    def test_emoji_present_no_violation(self, tmp_path):
        """Test that emoji presence prevents violation."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_welcome_message():
    return """
    🎩 Bienvenido al servicio exclusivo.

    Estamos encantados de recibirle.
    """
''')
        violations = check_file(test_file)
        emoji_violations = [v for v in violations if v["type"] == "missing_emoji"]
        assert len(emoji_violations) == 0


class TestMissingHTML:
    """Tests for missing HTML formatting detection in long messages."""

    def test_missing_html_long_message(self, tmp_path):
        """Test detection of missing HTML in long messages (>400 chars)."""
        # Create a message >400 chars without HTML
        long_text = "Este es un mensaje muy largo " * 30  # ~600 chars
        test_file = tmp_path / "test.py"
        test_file.write_text(f'''
def get_long_message():
    return "{long_text}"
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "missing_html"
        assert "html" in violations[0]["message"].lower()

    def test_html_present_no_violation(self, tmp_path):
        """Test that HTML presence prevents violation."""
        long_text = "Este es un mensaje muy largo " * 30
        test_file = tmp_path / "test.py"
        test_file.write_text(f'''
def get_long_message():
    return "<b>{long_text}</b>"
''')
        violations = check_file(test_file)
        html_violations = [v for v in violations if v["type"] == "missing_html"]
        assert len(html_violations) == 0

    def test_short_message_no_html_required(self, tmp_path):
        """Test that short messages don't require HTML."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_short_message():
    return "Este es un mensaje corto sin HTML."
''')
        violations = check_file(test_file)
        html_violations = [v for v in violations if v["type"] == "missing_html"]
        assert len(html_violations) == 0


class TestEdgeCases:
    """Tests for edge cases and special conditions."""

    def test_skips_short_strings(self, tmp_path):
        """Test that strings <50 chars are skipped."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_short():
    return "Hola mundo"
    return "tienes un mensaje"  # Has tutear but too short
''')
        violations = check_file(test_file)
        # Both strings are <50 chars, so no violations
        assert len(violations) == 0

    def test_skips_html_only_strings(self, tmp_path):
        """Test that strings starting with '<' are skipped."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_html():
    return "<b>Texto en negrita</b>"
    return "<i>Texto en cursiva</i>"
''')
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_syntax_error_handling(self, tmp_path):
        """Test that syntax errors are caught as violations."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def broken():
    return "unclosed string
''')
        violations = check_file(test_file)
        assert len(violations) == 1
        assert violations[0]["type"] == "syntax"
        assert "syntax" in violations[0]["message"].lower()

    def test_no_violations_clean_code(self, tmp_path):
        """Test clean Lucien voice code has no violations."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def get_welcome():
    return """
    🎩 Bienvenido al círculo exclusivo.

    <b>Estamos encantados de recibirle</b> en nuestro
    servicio de mayordomo personal.
    """

def get_success():
    return "<i>Su solicitud ha sido procesada con éxito.</i>"
''')
        violations = check_file(test_file)
        assert len(violations) == 0

    def test_function_context_tracking(self, tmp_path):
        """Test that current_method context is tracked."""
        test_file = tmp_path / "test.py"
        test_file.write_text('''
def method_one():
    return "tienes un problema importante que necesita su atención inmediata por favor"

def method_two():
    return "All good here with proper formal voice and no violations present"
''')
        checker = VoiceViolationChecker(str(test_file))
        import ast
        with open(test_file, "r") as f:
            tree = ast.parse(f.read(), filename=str(test_file))
        checker.visit(tree)

        # Verify checker tracked function context
        assert checker.current_method is None  # Reset after visiting
        assert len(checker.violations) == 1
        assert checker.violations[0]["type"] == "tutear"


class TestIntegration:
    """Integration tests for pre-commit hook workflow."""

    def test_pre_commit_hook_blocks_violations(self, tmp_path):
        """Test that check_file detects violations correctly."""
        # Create a message provider file with violation
        test_file = tmp_path / "test_provider.py"
        test_file.write_text('''
def get_message():
    """This message has tutear violation."""
    return "Si tienes alguna pregunta, por favor contáctese y le responderemos a la brevedad posible."
''')

        # Run check_file
        violations = check_file(test_file)

        # Should detect tutear violation
        assert len(violations) >= 1
        tutear_violations = [v for v in violations if v["type"] == "tutear"]
        assert len(tutear_violations) >= 1
        assert "tienes" in tutear_violations[0]["word"]

    def test_pre_commit_hook_allows_clean_code(self, tmp_path):
        """Test that check_file allows clean Lucien voice code."""
        # Create a message provider file with clean voice
        test_file = tmp_path / "clean_provider.py"
        test_file.write_text('''
def get_welcome():
    """Welcome message with proper Lucien voice."""
    return "🎩 Bienvenido al servicio exclusivo."

def get_success():
    """Success message with HTML formatting."""
    return "<i>Su solicitud fue procesada con éxito.</i>"

def get_multi_line():
    """Multi-line message with emoji and HTML."""
    return """
    🎩 Bienvenido al círculo exclusivo.

    <b>Estamos encantados de recibirle</b> en nuestro
    servicio de mayordomo personal.
    """
''')

        # Run check_file
        violations = check_file(test_file)

        # Should have no violations
        assert len(violations) == 0
