"""
User handlers module.
"""
# Importar routers
from bot.handlers.user.start import user_router
from bot.handlers.user.free_join_request import free_join_router
from bot.handlers.user.vip_entry import vip_entry_router

# Importar handlers adicionales para que sus decoradores se ejecuten
# IMPORTANTE: Estos imports ejecutan los decoradores @user_router.callback_query()
import bot.handlers.user.free_flow
# vip_flow.py removed - manual token redemption deprecated, only deep link activation exists

__all__ = ["user_router", "free_join_router", "vip_entry_router"]
