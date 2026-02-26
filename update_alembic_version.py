#!/usr/bin/env python3
"""
Script para actualizar alembic_version y marcar migraciones como aplicadas.

Uso:
    export DATABASE_URL="postgresql://..."
    python3 update_alembic_version.py
"""
import asyncio
import asyncpg
import os
import sys

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no configurado")
    print("   export DATABASE_URL='postgresql://...'")
    sys.exit(1)

# Convertir para asyncpg directo
if "postgresql+" in DATABASE_URL:
    DIRECT_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
else:
    DIRECT_URL = DATABASE_URL


async def update_alembic_version():
    """Actualizar tabla alembic_version con la migración head."""
    print("=" * 70)
    print("ACTUALIZANDO ALEMBIC_VERSION")
    print("=" * 70)
    print(f"\nDatabase: {DATABASE_URL[:60]}...\n")
    
    try:
        conn = await asyncpg.connect(DIRECT_URL)
        
        # Verificar si existe alembic_version
        exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            )
        """)
        
        if not exists:
            print("❌ Tabla alembic_version no existe")
            await conn.close()
            return False
        
        # Obtener versión actual
        current = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
        print(f"Versión actual: {current}")
        
        # Actualizar a head
        print(f"Actualizando a: 20260223_000001 (head)")
        
        await conn.execute("""
            UPDATE alembic_version 
            SET version_num = '20260223_000001'
        """)
        
        # Verificar actualización
        new_version = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
        print(f"Nueva versión: {new_version}")
        
        if new_version == '20260223_000001':
            print("\n✅ alembic_version actualizado exitosamente")
        else:
            print("\n❌ Error actualizando alembic_version")
            return False
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 70)
    print("ACTUALIZACIÓN DE ALEMBIC_VERSION")
    print("=" * 70)
    print("\nEste script actualizará la tabla alembic_version para marcar")
    print("las migraciones de gamificación como aplicadas.\n")
    
    success = await update_alembic_version()
    
    if success:
        print("\n✅ ¡LISTO!")
        print("\nAhora puedes verificar el estado:")
        print("  alembic current")
        print("  Debe mostrar: 20260223_000001 (head)")
    else:
        print("\n❌ Error actualizando alembic_version")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
