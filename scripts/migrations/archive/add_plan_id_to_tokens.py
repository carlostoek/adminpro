#!/usr/bin/env python3
"""
Migración: Agregar columna plan_id a tabla invitation_tokens

Esta migración agrega la columna plan_id para vincular tokens
con planes de suscripción (feature A3 - Deep Links).

Fecha: 2026-01-21
"""
import sqlite3
import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import Config


def check_column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Verifica si una columna existe en una tabla."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def add_plan_id_column():
    """Agrega la columna plan_id a la tabla invitation_tokens."""
    db_path = ROOT_DIR / Config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

    print(f"📂 Base de datos: {db_path}")

    if not db_path.exists():
        print(f"❌ Error: La base de datos no existe en {db_path}")
        return False

    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verificar si la columna ya existe
        if check_column_exists(cursor, "invitation_tokens", "plan_id"):
            print("✅ La columna 'plan_id' ya existe en 'invitation_tokens'")
            conn.close()
            return True

        print("🔧 Agregando columna 'plan_id' a 'invitation_tokens'...")

        # Agregar la columna (nullable, sin default)
        cursor.execute("""
            ALTER TABLE invitation_tokens
            ADD COLUMN plan_id INTEGER
            REFERENCES subscription_plans(id)
        """)

        conn.commit()

        # Verificar que se agregó correctamente
        if check_column_exists(cursor, "invitation_tokens", "plan_id"):
            print("✅ Columna 'plan_id' agregada exitosamente")

            # Mostrar estructura actualizada
            cursor.execute("PRAGMA table_info(invitation_tokens)")
            columns = cursor.fetchall()
            print("\n📋 Estructura actualizada de 'invitation_tokens':")
            for col in columns:
                print(f"   - {col[1]} ({col[2]}){' NOT NULL' if col[3] else ''}")

            conn.close()
            return True
        else:
            print("❌ Error: La columna no se agregó correctamente")
            conn.close()
            return False

    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def main():
    """Ejecuta la migración."""
    print("=" * 60)
    print("🚀 Migración: Agregar plan_id a invitation_tokens")
    print("=" * 60)
    print()

    success = add_plan_id_column()

    print()
    print("=" * 60)
    if success:
        print("✅ Migración completada exitosamente")
    else:
        print("❌ Migración falló")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
