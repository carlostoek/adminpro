#!/usr/bin/env python3
"""
Script para crear tablas de gamificación directamente en la BD.

Uso:
    export DATABASE_URL="postgresql://..."
    python create_gamification_tables.py
"""
import asyncio
import os
import sys

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL no configurado")
    print("   export DATABASE_URL='postgresql://...'")
    sys.exit(1)

# Convertir a asyncpg si es necesario
if "postgresql+" not in DATABASE_URL:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL


async def create_tables():
    """Crear todas las tablas de gamificación usando SQLAlchemy."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from bot.database.models import Base
    
    print("=" * 70)
    print("CREANDO TABLAS DE GAMIFICACIÓN")
    print("=" * 70)
    print(f"\nDatabase: {DATABASE_URL[:60]}...\n")
    
    engine = create_async_engine(ASYNC_DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            # Crear todas las tablas
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Tablas creadas exitosamente\n")
        
        # Verificar tablas creadas
        print("Verificando tablas creadas...")
        async with engine.acquire_connection() as conn:
            tables = await conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            print("\nTablas en la base de datos:")
            gamification_tables = [
                'user_gamification_profiles',
                'transactions',
                'user_reactions',
                'user_streaks',
                'rewards',
                'reward_conditions',
                'user_rewards',
                'content_sets',
                'shop_products',
                'user_content_access'
            ]
            
            existing = []
            missing = []
            
            for row in tables:
                table_name = row[0]
                if table_name in gamification_tables:
                    existing.append(table_name)
                    print(f"  ✅ {table_name}")
                elif table_name in ['users', 'bot_config', 'alembic_version']:
                    print(f"  ✅ {table_name} (existente)")
            
            for table in gamification_tables:
                if table not in existing:
                    missing.append(table)
                    print(f"  ❌ {table} (FALTA)")
            
            print(f"\nResumen: {len(existing)} tablas de gamificación creadas")
            if missing:
                print(f"           {len(missing)} tablas faltantes: {', '.join(missing)}")
        
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    return True


async def seed_data():
    """Insertar datos iniciales de gamificación."""
    import asyncpg
    
    print("\n" + "=" * 70)
    print("INSERTANDO DATOS INICIALES")
    print("=" * 70)
    
    # Convertir URL para asyncpg
    if "postgresql+" in DATABASE_URL:
        DIRECT_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    else:
        DIRECT_URL = DATABASE_URL
    
    try:
        conn = await asyncpg.connect(DIRECT_URL)
        
        # 1. Actualizar BotConfig con configuración de economía
        print("\n1. Actualizando BotConfig con configuración de economía...")
        await conn.execute("""
            UPDATE bot_config
            SET
                level_formula = 'floor(sqrt(total_earned / 100)) + 1',
                besitos_per_reaction = 5,
                besitos_daily_gift = 50,
                besitos_daily_streak_bonus = 10,
                max_reactions_per_day = 20,
                besitos_daily_base = 20,
                besitos_streak_bonus_per_day = 2,
                besitos_streak_bonus_max = 50,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """)
        print("   ✅ BotConfig actualizado")
        
        # 2. Backfill UserGamificationProfile para usuarios existentes
        print("\n2. Creando perfiles de gamificación para usuarios existentes...")
        result = await conn.execute("""
            INSERT INTO user_gamification_profiles
            (user_id, balance, total_earned, total_spent, level, created_at, updated_at)
            SELECT
                user_id,
                0,
                0,
                0,
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM users
            WHERE user_id NOT IN (
                SELECT user_id FROM user_gamification_profiles
            )
            ON CONFLICT (user_id) DO NOTHING
        """)
        print(f"   ✅ Perfiles creados")
        
        # 3. Insertar rewards por defecto
        print("\n3. Insertando recompensas por defecto...")
        await conn.execute("""
            INSERT INTO rewards
            (name, description, reward_type, reward_value, is_repeatable, is_secret, claim_window_hours, is_active, sort_order, created_at, updated_at)
            VALUES
            ('Primeros Pasos', 'Da tu primera reacción al contenido', 'BESITOS', '{"amount": 10}', false, false, 168, true, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('Ahorrador Principiante', 'Acumula 100 besitos en tu cuenta', 'BADGE', '{"badge_name": "ahorrador", "emoji": "💰"}', false, false, 168, true, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
            ('Racha de 7 Días', 'Mantén una racha de 7 días reclamando el regalo diario', 'BESITOS', '{"amount": 50}', false, false, 168, true, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
        """)
        print("   ✅ Recompensas insertadas")
        
        await conn.close()
        print("\n✅ Datos iniciales insertados exitosamente")
        
    except Exception as e:
        print(f"❌ Error insertando datos: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    """Función principal."""
    print("\n" + "=" * 70)
    print("SCRIPT DE CREACIÓN DE TABLAS DE GAMIFICACIÓN")
    print("=" * 70)
    print("\nEste script creará las tablas de gamificación directamente")
    print("sin usar Alembic, e insertará datos iniciales.\n")
    
    # Crear tablas
    tables_ok = await create_tables()
    
    if not tables_ok:
        print("\n❌ Error creando tablas. Abortando.")
        return
    
    # Insertar datos iniciales
    response = input("\n¿Insertar datos iniciales? [s/N]: ")
    
    if response.lower() in ['s', 'si', 'yes', 'y']:
        await seed_data()
    
    print("\n" + "=" * 70)
    print("SIGUIENTES PASOS")
    print("=" * 70)
    print("\n1. Actualizar alembic_version para marcar migraciones como aplicadas:")
    print("   python3 update_alembic_version.py")
    print("\n2. Verificar en Railway:")
    print("   railway logs --follow")
    print("\n3. Probar health check:")
    print("   curl https://tu-app.railway.app/health")
    print("\n4. Probar comandos en Telegram:")
    print("   /daily_gift")
    print("   /rewards")
    print("   /shop")
    print("\n✅ ¡LISTO!")


if __name__ == "__main__":
    asyncio.run(main())
