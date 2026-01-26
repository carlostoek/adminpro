#!/usr/bin/env python3
"""
Test to understand Aiogram handler registration with methods vs functions.
"""
import asyncio
import inspect
from unittest.mock import Mock
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message


class MenuRouter:
    def __init__(self):
        self.router = Router()
        self._setup_routes()

    def _setup_routes(self):
        # Register method as handler
        self.router.message.register(self._route_to_menu, Command("menu"))

    async def _route_to_menu(self, message: Message, data: dict):
        print(f"In _route_to_menu: message={message}, data={data}")
        return "OK"


async def test_handler_registration():
    """Test how Aiogram registers and calls method handlers."""
    print("Testing Aiogram handler registration with methods...")

    # Create router instance
    router = MenuRouter()

    # Get the registered handler
    # In Aiogram, handlers are stored in router.message.handlers
    handlers = router.router.message.handlers
    print(f"Number of handlers registered: {len(handlers)}")

    if handlers:
        handler = handlers[0].callback
        print(f"Handler type: {type(handler)}")
        print(f"Handler: {handler}")

        # Check signature
        try:
            sig = inspect.signature(handler)
            print(f"Handler signature: {sig}")
        except Exception as e:
            print(f"Error getting signature: {e}")

        # Check if it's a bound method
        print(f"Is method? {inspect.ismethod(handler)}")
        print(f"Is function? {inspect.isfunction(handler)}")

        # Try to call it
        mock_message = Mock(spec=Message)
        mock_data = {"test": "data"}

        print("\nTrying to call handler directly...")
        try:
            result = await handler(mock_message, mock_data)
            print(f"Direct call result: {result}")
        except Exception as e:
            print(f"Direct call error: {type(e).__name__}: {e}")

        # Try to call via instance
        print("\nTrying to call via instance method...")
        try:
            result = await router._route_to_menu(mock_message, mock_data)
            print(f"Instance call result: {result}")
        except Exception as e:
            print(f"Instance call error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_handler_registration())