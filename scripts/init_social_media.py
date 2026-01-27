"""
Initial Social Media Setup Script.

Run this to set initial social media links for Free channel entry flow.

Usage:
    python scripts/init_social_media.py

Requirements:
    - Phase 10 Plan 01 must be executed first (adds BotConfig fields)
    - Bot must have database initialized
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.engine import get_session
from bot.services.config import ConfigService


async def setup_social_media():
    """
    Set initial social media links for Free channel entry flow.

    Modify the values below to set your own social media handles/URLs.
    """
    async with get_session() as session:
        config_service = ConfigService(session)

        # ===== CONFIGURE THESE VALUES =====

        # Social media handles (use @ for handles or full URLs)
        instagram_handle = "@diana_handle"  # Example: "@diana_handle" or "https://instagram.com/diana_handle"
        tiktok_handle = "@diana_tiktok"     # Example: "@diana_tiktok" or "https://tiktok.com/@diana_tiktok"
        x_handle = "@diana_x"               # Example: "@diana_x" or "https://x.com/diana_x"

        # Free channel invite link (get from Telegram channel settings)
        # Instructions: https://telegram.org/blog/invite-links
        free_channel_link = "https://t.me/joinchat/..."  # Replace with actual invite link

        # ===== END CONFIGURATION =====

        try:
            # Set social media links
            await config_service.set_social_instagram(instagram_handle)
            await config_service.set_social_tiktok(tiktok_handle)
            await config_service.set_social_x(x_handle)
            await config_service.set_free_channel_invite_link(free_channel_link)

            # Commit changes
            await session.commit()

            # Verify and display
            print("✅ Social media links configured successfully")
            print(f"Instagram: {await config_service.get_social_instagram()}")
            print(f"TikTok: {await config_service.get_social_tiktok()}")
            print(f"X: {await config_service.get_social_x()}")
            print(f"Free channel link: {await config_service.get_free_channel_invite_link()}")

        except Exception as e:
            print(f"❌ Error configuring social media links: {e}")
            print("\nPossible issues:")
            print("1. Phase 10 Plan 01 not executed yet (BotConfig fields missing)")
            print("2. Database not initialized (run main.py first)")
            print("3. Invalid handle/link format")
            sys.exit(1)


async def show_current_config():
    """Display current social media configuration without modifying."""
    async with get_session() as session:
        config_service = ConfigService(session)

        print("Current social media configuration:")
        print(f"Instagram: {await config_service.get_social_instagram() or 'Not configured'}")
        print(f"TikTok: {await config_service.get_social_tiktok() or 'Not configured'}")
        print(f"X: {await config_service.get_social_x() or 'Not configured'}")
        print(f"Free channel link: {await config_service.get_free_channel_invite_link() or 'Not configured'}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup social media links for Free channel entry flow"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration without modifying"
    )
    args = parser.parse_args()

    if args.show:
        await show_current_config()
    else:
        await setup_social_media()


if __name__ == "__main__":
    asyncio.run(main())
