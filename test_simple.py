#!/usr/bin/env python3
"""
Test simple para verificar que los handlers se registran sin errores.
"""
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test que verifica que las importaciones funcionan sin errores."""
    print("🧪 Testeando importaciones...")

    try:
        # Importar el módulo main de admin que debería registrar los handlers
        from bot.handlers.admin.main import admin_router
        print("✅ Importación de admin_router exitosa")

        # Verificar que el router tiene handlers
        print(f"📋 Número de handlers en admin_router:")
        print(f"  - CallbackQuery: {len(admin_router.callback_query.handlers)}")
        print(f"  - Message: {len(admin_router.message.handlers)}")

        # Listar algunos handlers para verificar
        print(f"\n🔍 Algunos handlers registrados:")
        count = 0
        for handler in admin_router.callback_query.handlers:
            if count < 5:  # Mostrar solo los primeros 5
                print(f"  - Handler: {handler.callback.__name__ if hasattr(handler.callback, '__name__') else type(handler.callback).__name__}")
                count += 1
            else:
                print(f"  - ... y {len(admin_router.callback_query.handlers) - 5} más")
                break

        return True

    except Exception as e:
        print(f"❌ Error en importación: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_menu_callbacks():
    """Test que verifica específicamente los callbacks del menú."""
    print("\n🧪 Testeando callbacks del menú...")

    try:
        # Importar las funciones directamente
        from bot.handlers.admin.menu_callbacks import (
            callback_vip_management,
            callback_list_vips,
            callback_generate_vip_token,
            callback_content_management,
            callback_create_package,
            callback_list_packages,
            callback_free_queue,
            callback_process_free,
            register_menu_callbacks
        )

        print("✅ Importación de funciones de menu_callbacks exitosa")

        # Verificar que las funciones existen
        functions = [
            ("callback_vip_management", callback_vip_management),
            ("callback_list_vips", callback_list_vips),
            ("callback_generate_vip_token", callback_generate_vip_token),
            ("callback_content_management", callback_content_management),
            ("callback_create_package", callback_create_package),
            ("callback_list_packages", callback_list_packages),
            ("callback_free_queue", callback_free_queue),
            ("callback_process_free", callback_process_free),
            ("register_menu_callbacks", register_menu_callbacks)
        ]

        for name, func in functions:
            print(f"  ✅ {name}: {func}")

        return True

    except Exception as e:
        print(f"❌ Error en test de menu_callbacks: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("TEST DE REGISTRO DE HANDLERS DEL MENÚ ADMIN")
    print("=" * 50)

    success1 = test_imports()
    success2 = test_menu_callbacks()

    print("\n" + "=" * 50)
    if success1 and success2:
        print("✅ TODOS LOS TESTS PASARON")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
    print("=" * 50)