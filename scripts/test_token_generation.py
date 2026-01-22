#!/usr/bin/env python3
"""
Script de prueba: Generar token con plan_id

Verifica que la generación de tokens con plan_id funciona correctamente
después de la migración.
"""
import asyncio
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from bot.database.engine import get_session, init_db
from bot.services.container import ServiceContainer


async def test_token_generation():
    """Prueba la generación de un token con plan_id."""
    print("=" * 60)
    print("🧪 Prueba: Generación de Token con plan_id")
    print("=" * 60)
    print()

    async with get_session() as session:
        # Crear el container de servicios
        container = ServiceContainer(session, bot=None)

        # Obtener plan disponible
        plans = await container.pricing.get_all_plans(active_only=True)
        if not plans:
            print("❌ No hay planes disponibles. Crea uno primero.")
            return False

        plan = plans[0]
        print(f"📋 Plan seleccionado: {plan.name} (ID: {plan.id})")
        print(f"   Duración: {plan.duration_days} días")
        print(f"   Precio: {plan.currency}{plan.price}")
        print()

        # Generar token
        admin_id = 1280444712  # ID del admin
        duration_hours = plan.duration_days * 24

        print(f"🔧 Generando token con plan_id={plan.id}...")

        try:
            token = await container.subscription.generate_vip_token(
                generated_by=admin_id,
                duration_hours=duration_hours,
                plan_id=plan.id
            )

            print(f"✅ Token generado exitosamente!")
            print(f"   Token: {token.token}")
            print(f"   Generado por: {token.generated_by}")
            print(f"   Duración: {token.duration_hours} horas")
            print(f"   Plan ID: {token.plan_id}")
            print(f"   Creado: {token.created_at}")
            print(f"   Válido: {'Sí' if token.is_valid() else 'No'}")
            print()

            # Verificar que el plan se cargó correctamente (eager loading)
            if token.plan:
                print(f"✅ Relación con plan cargada correctamente:")
                print(f"   Nombre: {token.plan.name}")
                print(f"   Duración: {token.plan.duration_days} días")
            else:
                print("⚠️ Relación con plan no cargada (puede ser normal con lazy loading)")

            return True

        except Exception as e:
            print(f"❌ Error generando token: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Ejecuta la prueba."""
    # Inicializar BD
    await init_db()

    success = await test_token_generation()

    print()
    print("=" * 60)
    if success:
        print("✅ Prueba completada exitosamente")
    else:
        print("❌ Prueba falló")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
