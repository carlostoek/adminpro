#!/usr/bin/env python3
"""
Message Preview CLI Tool

Command-line interface for previewing message variations from LucienVoiceService
without full bot startup. Enables rapid iteration on voice changes during development.

Usage:
    python tools/preview_messages.py <command> [options]

Commands:
    greeting              Preview /start greeting message
    deep-link-success     Preview deep link activation success
    variations            Preview all variations of a message
    list                  List all available message methods

Examples:
    python tools/preview_messages.py greeting --user-name "Juan" --vip --days 15
    python tools/preview_messages.py variations greeting --count 30
    python tools/preview_messages.py list
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to sys.path for imports
parent = Path(__file__).parent.parent
sys.path.insert(0, str(parent))

from bot.services.message import LucienVoiceService


def preview_greeting(args):
    """Preview /start greeting message with various user contexts."""
    service = LucienVoiceService()

    # Build user context
    user_name = args.user_name or "Usuario"
    role_info = f"User: {user_name}"

    if args.admin:
        role_info += "\nRole: ADMIN"
    elif args.vip:
        role_info += "\nRole: VIP"
        if args.days:
            role_info += f"\nVIP Days: {args.days}"
    else:
        role_info += "\nRole: FREE"

    # Generate message
    text, keyboard = service.user.start.greeting(
        user_name=user_name,
        is_admin=args.admin,
        is_vip=args.vip,
        vip_days_remaining=args.days
    )

    # Display output
    print("=" * 60)
    print("📋 MESSAGE PREVIEW: user.start.greeting()")
    print("=" * 60)
    print(role_info)
    print()
    print("📝 TEXT:")
    print("-" * 60)
    print(text)
    print("-" * 60)
    print()
    if keyboard:
        print("⌨️ KEYBOARD:")
        for row_idx, row in enumerate(keyboard.inline_keyboard):
            print(f"  Row {row_idx}:")
            for button in row:
                target = button.callback_data or button.url
                print(f"    - [{button.text}] → {target}")
    else:
        print("⌨️ KEYBOARD: None")


def preview_deep_link_success(args):
    """Preview deep link activation success message."""
    service = LucienVoiceService()

    # Build user context
    user_name = args.user_name or "Usuario"
    role_info = f"User: {user_name}\nPlan: {args.plan}\nDuration: {args.days} days\nPrice: {args.price}"

    # Generate message
    text, keyboard = service.user.start.deep_link_activation_success(
        user_name=user_name,
        plan_name=args.plan,
        duration_days=args.days,
        price=args.price,
        days_remaining=args.days,
        invite_link=args.invite_link
    )

    # Display output
    print("=" * 60)
    print("📋 MESSAGE PREVIEW: user.start.deep_link_activation_success()")
    print("=" * 60)
    print(role_info)
    print()
    print("📝 TEXT:")
    print("-" * 60)
    print(text)
    print("-" * 60)
    print()
    if keyboard:
        print("⌨️ KEYBOARD:")
        for row_idx, row in enumerate(keyboard.inline_keyboard):
            print(f"  Row {row_idx}:")
            for button in row:
                target = button.callback_data or button.url
                print(f"    - [{button.text}] → {target}")
    else:
        print("⌨️ KEYBOARD: None")


def preview_variations(args):
    """Preview all variations of a message by generating multiple samples."""
    service = LucienVoiceService()

    print("=" * 60)
    print(f"🎲 VARIATION PREVIEW: {args.method}")
    print("=" * 60)
    print(f"Generating {args.count} samples...")
    print()

    messages = set()

    # Generate samples based on method
    for i in range(args.count):
        if args.method == "greeting":
            text, _ = service.user.start.greeting(
                user_name=args.user_name or "Usuario"
            )
            messages.add(text)
        else:
            print(f"❌ Unknown method: {args.method}")
            print("   Available methods: greeting")
            return

    unique_count = len(messages)
    print(f"Unique variations found: {unique_count}")
    print()

    # Display each variation
    for idx, variation in enumerate(sorted(messages), 1):
        print(f"VARIATION {idx}:")
        print("-" * 60)
        print(variation)
        print("-" * 60)
        print()


def list_message_methods(args):
    """List all available message methods organized by provider."""
    service = LucienVoiceService()

    print("=" * 60)
    print("📜 AVAILABLE MESSAGE METHODS")
    print("=" * 60)
    print()

    # Common messages
    print("common:")
    for method_name in dir(service.common):
        if not method_name.startswith('_') and callable(getattr(service.common, method_name)):
            method = getattr(service.common, method_name)
            doc = method.__doc__.split('\n')[0] if method.__doc__ else "No description"
            print(f"  - {method_name:<20} # {doc}")
    print()

    # User start messages
    print("user.start:")
    for method_name in dir(service.user.start):
        if not method_name.startswith('_') and callable(getattr(service.user.start, method_name)):
            method = getattr(service.user.start, method_name)
            doc = method.__doc__.split('\n')[0] if method.__doc__ else "No description"
            print(f"  - {method_name:<35} # {doc}")
    print()

    # User flows messages
    print("user.flows:")
    for method_name in dir(service.user.flows):
        if not method_name.startswith('_') and callable(getattr(service.user.flows, method_name)):
            method = getattr(service.user.flows, method_name)
            doc = method.__doc__.split('\n')[0] if method.__doc__ else "No description"
            print(f"  - {method_name:<35} # {doc}")
    print()

    # Admin main messages
    print("admin.main:")
    for method_name in dir(service.admin.main):
        if not method_name.startswith('_') and callable(getattr(service.admin.main, method_name)):
            method = getattr(service.admin.main, method_name)
            doc = method.__doc__.split('\n')[0] if method.__doc__ else "No description"
            print(f"  - {method_name:<35} # {doc}")
    print()

    # Admin VIP messages
    print("admin.vip:")
    for method_name in dir(service.admin.vip):
        if not method_name.startswith('_') and callable(getattr(service.admin.vip, method_name)):
            method = getattr(service.admin.vip, method_name)
            doc = method.__doc__.split('\n')[0] if method.__doc__ else "No description"
            print(f"  - {method_name:<35} # {doc}")
    print()

    # Admin free messages
    print("admin.free:")
    for method_name in dir(service.admin.free):
        if not method_name.startswith('_') and callable(getattr(service.admin.free, method_name)):
            method = getattr(service.admin.free, method_name)
            doc = method.__doc__.split('\n')[0] if method.__doc__ else "No description"
            print(f"  - {method_name:<35} # {doc}")


def main():
    """Main entry point for CLI tool."""
    parser = argparse.ArgumentParser(
        description="Preview message variations from LucienVoiceService",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Greeting command
    greeting_parser = subparsers.add_parser("greeting", help="Preview /start greeting")
    greeting_parser.add_argument("--user-name", default="Usuario", help="User name")
    greeting_parser.add_argument("--admin", action="store_true", help="User is admin")
    greeting_parser.add_argument("--vip", action="store_true", help="User is VIP")
    greeting_parser.add_argument("--days", type=int, help="VIP days remaining")

    # Deep link success command
    dl_parser = subparsers.add_parser("deep-link-success", help="Preview deep link success")
    dl_parser.add_argument("--user-name", default="Usuario", help="User name")
    dl_parser.add_argument("--plan", default="Plan Mensual", help="Plan name")
    dl_parser.add_argument("--days", type=int, default=30, help="Plan duration")
    dl_parser.add_argument("--price", default="$9.99", help="Plan price")
    dl_parser.add_argument("--invite-link", default="https://t.me/+EXAMPLE", help="Invite link")

    # Variations command
    var_parser = subparsers.add_parser("variations", help="Preview all variations")
    var_parser.add_argument("method", help="Message method name (e.g., greeting)")
    var_parser.add_argument("--user-name", default="Usuario", help="User name")
    var_parser.add_argument("--count", type=int, default=30, help="Number of samples")

    # List command
    subparsers.add_parser("list", help="List all available message methods")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == "greeting":
        preview_greeting(args)
    elif args.command == "deep-link-success":
        preview_deep_link_success(args)
    elif args.command == "variations":
        preview_variations(args)
    elif args.command == "list":
        list_message_methods(args)


if __name__ == "__main__":
    main()
