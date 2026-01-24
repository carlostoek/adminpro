"""
Voice Linter - AST-based voice consistency checker for Lucien's messages.

This module provides AST parsing to detect voice violations before code is committed.
It checks for:
- Tutear forms (tienes, tu, haz, puedes, hagas)
- Technical jargon (database, api, exception, error code, null)
- Missing emoji in multi-line messages
- Missing HTML formatting in long messages

Uses stdlib ast module only - no external dependencies.
"""

import ast
from pathlib import Path
from typing import List, Dict, Any


# Violation pattern constants
FORBIDDEN_TUTEAR = ["tienes", "tu ", "tu.", "haz", "puedes", "hagas"]
TECHNICAL_JARGON = ["database", "api", "exception", "error code", "null"]
LUCIEN_EMOJI = "🎩"


class VoiceViolationChecker(ast.NodeVisitor):
    """AST visitor that detects voice violations in message providers."""

    def __init__(self, filename: str):
        """Initialize the voice violation checker.

        Args:
            filename: Path to the file being checked (for error reporting)
        """
        self.filename = filename
        self.violations: List[Dict[str, Any]] = []
        self.current_method: str = None

    def check_string(self, string: str, lineno: int) -> None:
        """Check a string literal for voice violations.

        Args:
            string: The string content to check
            lineno: Line number where the string appears
        """
        # Skip short strings (likely not user-facing messages)
        if len(string) < 50:
            return

        # Skip strings that are pure HTML tags
        if string.strip().startswith("<"):
            return

        string_lower = string.lower()

        # Check 1: Tutear (forbidden informal Spanish forms)
        for word in FORBIDDEN_TUTEAR:
            if word in string_lower:
                self.violations.append({
                    "line": lineno,
                    "type": "tutear",
                    "word": word,
                    "message": f'Uses tutear form "{word}"'
                })

        # Check 2: Technical jargon
        for term in TECHNICAL_JARGON:
            if term in string_lower:
                self.violations.append({
                    "line": lineno,
                    "type": "jargon",
                    "term": term,
                    "message": f'Contains technical jargon "{term}"'
                })

        # Check 3: Missing emoji in multi-line strings
        # Check for actual newline characters OR escaped \n in source
        if ("\n" in string or "\\n" in string) and LUCIEN_EMOJI not in string:
            self.violations.append({
                "line": lineno,
                "type": "missing_emoji",
                "message": f"Multi-line message missing {LUCIEN_EMOJI} emoji"
            })

        # Check 4: Missing HTML in long messages
        if len(string) > 400 and "<b>" not in string and "<i>" not in string:
            self.violations.append({
                "line": lineno,
                "type": "missing_html",
                "message": "Long message (>400 chars) missing HTML formatting"
            })

    def visit_Str(self, node: ast.Str) -> None:
        """Visit string literal node (Python 3.7 compatibility).

        Note: ast.Str is deprecated in Python 3.14 in favor of ast.Constant.
        We keep this for compatibility with Python 3.7-3.9.

        Args:
            node: AST string node
        """
        self.check_string(node.s, node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Visit constant node (Python 3.8+ string constants).

        Args:
            node: AST constant node
        """
        if isinstance(node.value, str):
            self.check_string(node.value, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition to track current method context.

        Args:
            node: AST function definition node
        """
        # Store current method name for context in violations
        old_method = self.current_method
        self.current_method = node.name
        self.generic_visit(node)
        self.current_method = old_method


def check_file(filepath: Path) -> List[Dict[str, Any]]:
    """Check a single file for voice violations.

    Args:
        filepath: Path to the Python file to check

    Returns:
        List of violation dictionaries. Each violation contains:
        - line: Line number where violation occurs
        - type: Type of violation (tutear, jargon, missing_emoji, missing_html, syntax)
        - message: Human-readable description
        - Additional fields depending on violation type (word, term, etc.)
    """
    violations = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        # Parse the source code
        tree = ast.parse(source, filename=str(filepath))

        # Create checker and visit AST
        checker = VoiceViolationChecker(str(filepath))
        checker.visit(tree)

        violations = checker.violations

    except SyntaxError as e:
        # Return syntax error as a violation
        violations.append({
            "line": e.lineno or 0,
            "type": "syntax",
            "message": f"Syntax error: {e.msg}"
        })
    except Exception as e:
        # Catch other errors (encoding, etc.)
        violations.append({
            "line": 0,
            "type": "error",
            "message": f"Error reading file: {str(e)}"
        })

    return violations
