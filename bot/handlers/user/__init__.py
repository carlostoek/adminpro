"""
User handlers module.
"""
# Importar routers
from bot.handlers.user.start import user_router
from bot.handlers.user.free_join_request import free_join_router
from bot.handlers.user.vip_entry import vip_entry_router
from bot.handlers.user.streak import streak_router
from bot.handlers.user.shop import shop_router

# Importar handlers adicionales para que sus decoradores se ejecuten
# IMPORTANTE: Estos imports ejecutan los decoradores @user_router.callback_query()
import bot.handlers.user.free_flow
# vip_flow.py removed - manual token redemption deprecated, only deep link activation exists

# Importar y registrar handlers de reacciones
from bot.handlers.user.reactions import register_reaction_handlers

# Registrar routers en el router principal de usuario
user_router.include_router(streak_router)
user_router.include_router(shop_router)

__all__ = ["user_router", "free_join_router", "vip_entry_router", "streak_router", "shop_router"]
