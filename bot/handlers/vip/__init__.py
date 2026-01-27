"""
VIP Handlers Package - Menú y funcionalidades para usuarios VIP.

Exporta:
- show_vip_menu: Handler principal del menú VIP
- vip_callbacks_router: Router para callbacks del menú VIP
"""

from .menu import show_vip_menu
from .callbacks import vip_callbacks_router

__all__ = ["show_vip_menu", "vip_callbacks_router"]
