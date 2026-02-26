"""
Middlewares module - Procesamiento pre/post handlers.
"""
from bot.middlewares.admin_auth import AdminAuthMiddleware
from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.role_detection import RoleDetectionMiddleware
from bot.middlewares.user_registration import UserRegistrationMiddleware
from bot.middlewares.webhook_auth import TelegramIPValidationMiddleware

__all__ = [
    "AdminAuthMiddleware",
    "DatabaseMiddleware",
    "RoleDetectionMiddleware",
    "UserRegistrationMiddleware",
    "TelegramIPValidationMiddleware",
]
