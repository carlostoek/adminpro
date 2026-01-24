"""
Tests for Message Preview CLI Tool

Tests the CLI preview_messages.py tool for generating message variations
without full bot startup. Uses subprocess.run() to execute CLI as real user would.
"""

import subprocess
import sys
from pathlib import Path


def run_cli_command(*args):
    """
    Helper to run CLI command and return stdout.

    Args:
        *args: CLI arguments (e.g., "greeting", "--user-name", "TestUser")

    Returns:
        str: Command stdout
    """
    cli_path = Path(__file__).parent.parent / "tools" / "preview_messages.py"
    result = subprocess.run(
        [sys.executable, str(cli_path), *args],
        capture_output=True,
        text=True,
        timeout=10
    )
    return result.stdout


def test_greeting_command_generates_message():
    """Test greeting command generates message with preview header."""
    output = run_cli_command("greeting", "--user-name", "TestUser")

    # Assert expected output elements
    assert "📋 MESSAGE PREVIEW: user.start.greeting()" in output
    assert "TestUser" in output
    assert "📝 TEXT:" in output
    assert "⌨️ KEYBOARD:" in output
    # Lucien's voice indicators
    assert "🎩" in output or "Buenos" in output or "días" in output


def test_greeting_includes_keyboard():
    """Test greeting command includes keyboard with buttons."""
    output = run_cli_command("greeting")

    assert "⌨️ KEYBOARD:" in output
    assert "Row 0:" in output
    # Keyboard buttons have format: [Button Text] → callback_data
    assert "[" in output and "] → " in output


def test_variations_command_shows_distribution():
    """Test variations command generates multiple samples and shows unique count."""
    output = run_cli_command("variations", "greeting", "--count", "30")

    assert "🎲 VARIATION PREVIEW: greeting" in output
    assert "Generating 30 samples..." in output
    assert "Unique variations found:" in output
    # Should have at least 2 unique variations (weighted distribution)
    unique_count_line = [line for line in output.split('\n') if 'Unique variations found:' in line]
    if unique_count_line:
        count_part = unique_count_line[0].split('Unique variations found:')[1].strip()
        unique_count = int(count_part)
        assert unique_count >= 2, f"Expected at least 2 unique variations, got {unique_count}"


def test_list_command_displays_methods():
    """Test list command shows all available message methods organized by provider."""
    output = run_cli_command("list")

    # Provider sections
    assert "common:" in output
    assert "user.start:" in output
    assert "user.flows:" in output
    assert "admin.main:" in output
    assert "admin.vip:" in output
    assert "admin.free:" in output

    # Specific methods from each provider
    assert "error" in output  # common
    assert "greeting" in output  # user.start
    assert "free_request_success" in output  # user.flows
    assert "admin_menu_greeting" in output  # admin.main
    assert "vip_menu" in output  # admin.vip
    assert "free_menu" in output  # admin.free


def test_deep_link_command_with_args():
    """Test deep-link-success command with custom arguments."""
    output = run_cli_command(
        "deep-link-success",
        "--plan", "Premium",
        "--days", "60",
        "--price", "$19.99"
    )

    assert "📋 MESSAGE PREVIEW: user.start.deep_link_activation_success()" in output
    assert "Premium" in output
    assert "60" in output  # days
    assert "$19.99" in output
    assert "📝 TEXT:" in output


def test_greeting_with_vip_context():
    """Test greeting with VIP user context shows VIP-specific messaging."""
    output = run_cli_command("greeting", "--user-name", "María", "--vip", "--days", "15")

    assert "María" in output
    assert "Role: VIP" in output
    assert "VIP Days: 15" in output


def test_greeting_with_admin_context():
    """Test greeting with admin context shows admin-specific messaging."""
    output = run_cli_command("greeting", "--admin")

    assert "Role: ADMIN" in output


def test_variations_with_custom_count():
    """Test variations command respects custom sample count."""
    output = run_cli_command("variations", "greeting", "--count", "50")

    assert "Generating 50 samples..." in output


def test_help_displays_all_commands():
    """Test --help shows all available commands."""
    output = run_cli_command("--help")

    assert "greeting" in output
    assert "deep-link-success" in output
    assert "variations" in output
    assert "list" in output
