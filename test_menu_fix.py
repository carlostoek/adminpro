#!/usr/bin/env python3
"""
Test para verificar que los handlers del menú admin están registrados correctamente.
"""
import asyncio
import logging
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_menu_handlers():
    """Test que verifica que los handlers del menú están registrados."""
    print("🧪 Testeando registro de handlers del menú admin...")

    # Crear router de admin directamente para evitar importaciones circulares
    from aiogram import Router, F
    admin_router = Router(name="admin")

    # Registrar handlers de callbacks del menú
    from bot.handlers.admin.menu_callbacks import register_menu_callbacks
    register_menu_callbacks(admin_router)

    # También registrar algunos handlers existentes para la prueba
    from bot.handlers.admin.vip import callback_vip_menu
    from bot.handlers.admin.management import callback_list_vip_subscribers
    from bot.handlers.admin.content import callback_content_menu, callback_content_list
    from bot.handlers.admin.management import callback_view_free_queue

    admin_router.callback_query.register(callback_vip_menu, F.data == "admin:vip")
    admin_router.callback_query.register(callback_list_vip_subscribers, F.data == "vip:list_subscribers")
    admin_router.callback_query.register(callback_content_menu, F.data == "admin:content")
    admin_router.callback_query.register(callback_content_list, F.data == "admin:content:list")
    admin_router.callback_query.register(callback_view_free_queue, F.data == "free:view_queue")

    print(f"\n📋 Handlers en admin_router:")
    print(f"  CallbackQuery handlers: {len(admin_router.callback_query.handlers)}")
    print(f"  Message handlers: {len(admin_router.message.handlers)}")

    # Listar callbacks registrados
    print(f"\n🔍 Callbacks registrados en admin_router:")
    for handler in admin_router.callback_query.handlers:
        # Intentar obtener información del filtro
        if hasattr(handler, 'filters') and handler.filters:
            for f in handler.filters:
                if hasattr(f, 'callback_data'):
                    print(f"  - {f.callback_data}")
                elif hasattr(f, '__dict__'):
                    # Buscar callback_data en el filtro
                    for key, value in f.__dict__.items():
                        if 'callback_data' in str(key) or 'callback_data' in str(value):
                            print(f"  - {value}")

    # Verificar handlers específicos
    target_callbacks = [
        "admin:vip_management",
        "admin:list_vips",
        "admin:generate_vip_token",
        "admin:content_management",
        "admin:create_package",
        "admin:list_packages",
        "admin:free_queue",
        "admin:process_free"
    ]

    print(f"\n🎯 Verificando callbacks del menú:")

    # Obtener todos los callbacks registrados
    registered_callbacks = []
    for handler in admin_router.callback_query.handlers:
        if hasattr(handler, 'filters') and handler.filters:
            for f in handler.filters:
                if hasattr(f, 'callback_data'):
                    registered_callbacks.append(f.callback_data)
                # También buscar en otros atributos
                elif hasattr(f, '__dict__'):
                    for key, value in f.__dict__.items():
                        if isinstance(value, str) and value.startswith("admin:"):
                            registered_callbacks.append(value)

    # Verificar cada callback
    for callback in target_callbacks:
        if callback in registered_callbacks:
            print(f"  ✅ {callback}")
        else:
            print(f"  ❌ {callback} (FALTANTE)")

    print(f"\n📊 Resumen: {sum(1 for c in target_callbacks if c in registered_callbacks)}/{len(target_callbacks)} callbacks registrados")

    # También verificar handlers existentes que podrían usarse
    print(f"\n🔗 Handlers existentes que podrían redirigirse:")
    existing_handlers = [
        ("admin:vip", "Menú VIP"),
        ("vip:list_subscribers", "Listar VIPs"),
        ("vip:generate_token", "Generar token VIP"),
        ("admin:content", "Menú contenido"),
        ("admin:content:create:start", "Crear paquete"),
        ("admin:content:list", "Listar paquetes"),
        ("free:view_queue", "Ver cola Free"),
    ]

    for callback, desc in existing_handlers:
        if callback in registered_callbacks:
            print(f"  ✅ {callback} - {desc}")
        else:
            print(f"  ⚠️  {callback} - {desc} (no en admin_router)")


if __name__ == "__main__":
    asyncio.run(test_menu_handlers())