#!/usr/bin/env python3
"""
Script para verificar y reparar migraciones en Railway.

Este script:
1. Verifica el estado actual de alembic_version en Railway
2. Verifica si existen las tablas de gamificación
3. Ejecuta las migraciones pendientes (alembic upgrade head)

Uso:
    export DATABASE_URL="postgresql+asyncpg://postgres:PASSWORD@HOST:5432/railway"
    python fix_railway_migrations.py
"""
import asyncio
import os
import sys
import subprocess

# ===== CONFIGURACIÓN =====
# El script usa la variable DATABASE_URL del entorno
# Si no está configurada, la pide al usuario

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("=" * 70)
    print("ERROR: DATABASE_URL no configurado")
    print("=" * 70)
    print("\nPara obtener el DATABASE_URL de Railway:")
    print("  1. Ve a railway.app")
    print("  2. Selecciona tu proyecto")
    print("  3. Haz click en PostgreSQL")
    print("  4. Copia el DATABASE_URL")
    print("\nLuego ejecuta:")
    print("  export DATABASE_URL='postgresql+asyncpg://postgres:...'")
    print("  python fix_railway_migrations.py")
    print("\nO usa railway CLI:")
    print("  railway variables get DATABASE_URL > .env")
    print("  source .env")
    print("  python fix_railway_migrations.py")
    sys.exit(1)

# Preparar DATABASE_URL para SQLAlchemy (con asyncpg) y para asyncpg directo (sin +asyncpg)
SQLALCHEMY_DATABASE_URL = DATABASE_URL
if "postgresql+" not in DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

# Para asyncpg directo, usar postgresql:// (sin +asyncpg)
ASYNCpg_DATABASE_URL = DATABASE_URL
if "postgresql+" in ASYNCpg_DATABASE_URL:
    ASYNCpg_DATABASE_URL = ASYNCpg_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

print("=" * 70)
print("VERIFICACIÓN Y REPARACIÓN DE MIGRACIONES - RAILWAY")
print("=" * 70)
print(f"\nDATABASE_URL: {DATABASE_URL[:60]}...")


async def check_alembic_version():
    """Verifica la tabla alembic_version y retorna la versión actual."""
    try:
        import asyncpg
    except ImportError:
        print("\n❌ ERROR: asyncpg no está instalado")
        print("   Ejecuta: pip install asyncpg")
        return None
    
    print("\n" + "-" * 70)
    print("1. CONECTANDO A POSTGRESQL")
    print("-" * 70)
    
    try:
        conn = await asyncpg.connect(ASYNCpg_DATABASE_URL)
        print("✅ Conexión exitosa")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None
    
    print("\n" + "-" * 70)
    print("2. VERIFICANDO TABLA alembic_version")
    print("-" * 70)
    
    try:
        # Check if table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            )
        """)
        
        if not table_exists:
            print("❌ Tabla alembic_version NO existe")
            print("   → Las migraciones nunca se ejecutaron")
            await conn.close()
            return None
        
        print("✅ Tabla alembic_version existe")
        
        # Get current version
        version = await conn.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
        
        if version is None:
            print("⚠️  Tabla vacía (sin migraciones aplicadas)")
            version_status = "VACÍA"
        elif version == 'f9c06e9cc285':
            print(f"⚠️  PROBLEMA DETECTADO: Versión = {version}")
            print("   → Esta migración fue mergeada, necesitas actualizar a head")
            version_status = "ANTICUADA"
        elif version == '20260211_000001':
            print(f"⚠️  Versión = {version}")
            print("   → Migración antigua (pre-gamification completa)")
            version_status = "PENDIENTE"
        elif version == '20260217_000001':
            print(f"✅ Versión = {version}")
            print("   → Solo falta seed de gamificación")
            version_status = "CASI LISTA"
        elif version == '20260221_000001':
            print(f"✅ Versión = {version} (HEAD)")
            print("   → Migraciones al día!")
            version_status = "OK"
        else:
            print(f"? Versión desconocida: {version}")
            version_status = "DESCONOCIDA"
        
        await conn.close()
        return version, version_status
        
    except Exception as e:
        print(f"❌ Error: {e}")
        await conn.close()
        return None, "ERROR"


async def check_tables():
    """Verifica qué tablas de gamificación existen."""
    try:
        import asyncpg
    except ImportError:
        return
    
    print("\n" + "-" * 70)
    print("3. VERIFICANDO TABLAS DE GAMIFICACIÓN")
    print("-" * 70)
    
    try:
        conn = await asyncpg.connect(ASYNCpg_DATABASE_URL)
        
        tables_to_check = [
            ('users', 'Usuarios'),
            ('user_gamification_profiles', 'Perfiles Gamificación'),
            ('transactions', 'Transacciones'),
            ('user_reactions', 'Reacciones'),
            ('user_streaks', 'Rachas'),
            ('rewards', 'Recompensas'),
            ('reward_conditions', 'Condiciones'),
            ('user_rewards', 'Recompensas Usuario'),
            ('content_sets', 'Contenidos'),
            ('shop_products', 'Productos Tienda'),
            ('user_content_access', 'Accesos Usuario')
        ]
        
        existing = []
        missing = []
        
        for table, description in tables_to_check:
            exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table}'
                )
            """)
            status = "✅" if exists else "❌"
            print(f"{status} {table:<35} ({description})")
            
            if exists:
                existing.append(table)
            else:
                missing.append(table)
        
        await conn.close()
        
        print(f"\nResumen: {len(existing)} existen, {len(missing)} faltan")
        return existing, missing
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return [], []


def run_alembic_upgrade():
    """Ejecuta alembic upgrade head."""
    print("\n" + "=" * 70)
    print("4. EJECUTANDO MIGRACIONES")
    print("=" * 70)
    
    # Verificar que alembic esté disponible
    try:
        result = subprocess.run(
            ["alembic", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print("❌ Alembic no está instalado o no está en PATH")
            print("   Ejecuta: pip install alembic")
            return False
    except FileNotFoundError:
        print("❌ Alembic no encontrado")
        print("   Ejecuta: pip install alembic")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Timeout verificando alembic")
        return False
    
    print("\nEjecutando: alembic upgrade head")
    print("-" * 70)
    
    # Ejecutar migraciones
    env = os.environ.copy()
    env["DATABASE_URL"] = DATABASE_URL
    
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutos máximo
            env=env
        )
        
        if result.stdout:
            print("\nSalida:")
            print(result.stdout)
        
        if result.stderr:
            print("\nErrores/Warnings:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n" + "=" * 70)
            print("✅ MIGRACIONES EJECUTADAS EXITOSAMENTE")
            print("=" * 70)
            return True
        else:
            print(f"\n" + "=" * 70)
            print(f"❌ MIGRACIONES FALLARON (código {result.returncode})")
            print("=" * 70)
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ Timeout: Las migraciones tardaron más de 5 minutos")
        return False
    except Exception as e:
        print(f"\n❌ Error ejecutando migraciones: {e}")
        return False


def verify_after_upgrade():
    """Verifica el estado después de las migraciones."""
    print("\n" + "=" * 70)
    print("5. VERIFICANDO RESULTADO")
    print("=" * 70)
    
    env = os.environ.copy()
    env["DATABASE_URL"] = DATABASE_URL
    
    try:
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        if result.returncode == 0:
            print("\nVersión actual:")
            print(result.stdout)
            
            if "20260221_000001" in result.stdout:
                print("✅ ¡Migraciones actualizadas a HEAD!")
                return True
            else:
                print("⚠️  Versión actual no es HEAD")
                return False
        else:
            print("❌ Error verificando versión")
            if result.stderr:
                print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Función principal."""
    print("\n" + "=" * 70)
    print("SCRIPT DE REPARACIÓN DE MIGRACIONES")
    print("=" * 70)
    print("\nEste script verificará el estado de las migraciones en Railway")
    print("y aplicará las migraciones pendientes de gamificación.\n")
    
    # Check current state
    version_info = asyncio.run(check_alembic_version())
    
    if version_info is None:
        print("\n⚠️  No se pudo verificar el estado actual")
        print("   Continuando con verificación de tablas...\n")
        version_status = "DESCONOCIDA"
    else:
        version, version_status = version_info
    
    existing, missing = asyncio.run(check_tables())
    
    # Decision logic
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO")
    print("=" * 70)
    
    if version_status == "OK":
        print("✅ Las migraciones están actualizadas")
        print("   No es necesario hacer nada más.\n")
        
        if missing:
            print("⚠️  PERO faltan tablas de gamificación:")
            for table in missing:
                print(f"   - {table}")
            print("\n   Esto es inconsistente. Recomendado ejecutar migraciones.\n")
            proceed = True
        else:
            proceed = False
    elif version_status == "ERROR":
        print("❌ Error verificando migraciones")
        print("   Probablemente las tablas no existen aún.\n")
        proceed = True
    else:
        print(f"⚠️  Estado: {version_status}")
        print("   Se necesitan aplicar migraciones.\n")
        proceed = True
    
    # Ask user if they want to proceed
    if proceed:
        print("=" * 70)
        response = input("\n¿Ejecutar migraciones ahora? [s/N]: ")
        
        if response.lower() not in ['s', 'si', 'yes', 'y']:
            print("\n❌ Operación cancelada")
            print("\nPara ejecutar migraciones manualmente:")
            print("  export DATABASE_URL='postgresql+asyncpg://...'")
            print("  alembic upgrade head")
            return
        
        # Run migrations
        success = run_alembic_upgrade()
        
        if success:
            # Verify
            verify_after_upgrade()
            
            print("\n" + "=" * 70)
            print("SIGUIENTES PASOS")
            print("=" * 70)
            print("\n1. Verifica los logs de Railway:")
            print("   railway logs --follow")
            print("\n2. Verifica el health check:")
            print("   curl https://tu-app.railway.app/health")
            print("\n3. Prueba los comandos de gamificación en Telegram:")
            print("   /daily_gift")
            print("   /rewards")
            print("   /shop")
            print("\n✅ ¡LISTO!")
        else:
            print("\n" + "=" * 70)
            print("ERROR EN MIGRACIONES")
            print("=" * 70)
            print("\nPosibles causas:")
            print("  1. asyncpg no está instalado: pip install asyncpg")
            print("  2. DATABASE_URL incorrecto")
            print("  3. Problema de conexión a Railway")
            print("\nPara ayuda, revisa:")
            print("  FIX_RAILWAY_MIGRATIONS.md")
    else:
        print("\n✅ Todo está correcto. No se necesitan acciones.")
        print("\nPara hacer redeploy en Railway:")
        print("  1. Commit y push a GitHub")
        print("  2. Railway redeploy automático")
        print("  3. railway logs --follow")


if __name__ == "__main__":
    main()
