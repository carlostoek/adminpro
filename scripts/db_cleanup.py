#!/usr/bin/env python3
"""
Script de utilidad para limpieza de base de datos.

Uso:
    python scripts/db_cleanup.py                    # Listar usuarios
    python scripts/db_cleanup.py --delete <user_id> # Eliminar usuario
    python scripts/db_cleanup.py --clean-all        # PELIGROSO: Eliminar todo
"""
import asyncio
import sys
import os

# Agregar el directorio raíz al path para importar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import Config
from bot.database.base import Base
from bot.database.models import (
    User, VIPSubscriber, InvitationToken, FreeChannelRequest,
    UserInterest, UserRoleChangeLog, ContentPackage,
    SubscriptionPlan, BotConfig
)


# Crear engine async para el script (usar aiosqlite)
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def list_users():
    """Lista todos los usuarios de la base de datos."""
    async with async_session() as session:
        # Contar registros
        users_count = await session.scalar(select(func.count()).select_from(User))
        vip_count = await session.scalar(select(func.count()).select_from(VIPSubscriber))
        tokens_count = await session.scalar(select(func.count()).select_from(InvitationToken))
        free_count = await session.scalar(select(func.count()).select_from(FreeChannelRequest))
        interests_count = await session.scalar(select(func.count()).select_from(UserInterest))

        print("\n📊 RESUMEN DE BASE DE DATOS")
        print("=" * 40)
        print(f"Usuarios:          {users_count}")
        print(f"VIP Subscribers:   {vip_count}")
        print(f"Tokens:            {tokens_count}")
        print(f"Free Requests:     {free_count}")
        print(f"User Interests:    {interests_count}")

        # Listar usuarios
        result = await session.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()

        if not users:
            print("\nNo hay usuarios en la base de datos.")
            return

        print("\n👥 USUARIOS REGISTRADOS")
        print("=" * 60)
        for u in users:
            print(f"ID: {u.user_id:15} | {u.username or 'sin username':20} | {u.role.value:8} | {u.first_name}")


async def delete_user(user_id: int):
    """Elimina un usuario y todos sus registros relacionados."""
    async with async_session() as session:
        # Verificar que el usuario existe
        user = await session.get(User, user_id)
        if not user:
            print(f"❌ Usuario con ID {user_id} no encontrado.")
            return

        print(f"\n🗑️  Eliminando usuario: {user.mention} (ID: {user_id})")
        print(f"   Rol: {user.role.value}")

        # Eliminar registros relacionados ( CASCADE lo maneja automáticamente)
        # pero lo hacemos explícitamente para mostrar qué se borra

        # User interests (cascade delete-orphan)
        interests_result = await session.execute(
            delete(UserInterest).where(UserInterest.user_id == user_id)
        )
        interests_deleted = interests_result.rowcount
        print(f"   - Intereses eliminados: {interests_deleted}")

        # VIP subscriber (delete manual)
        vip_result = await session.execute(
            delete(VIPSubscriber).where(VIPSubscriber.user_id == user_id)
        )
        vip_deleted = vip_result.rowcount
        print(f"   - Suscripción VIP eliminada: {vip_deleted}")

        # Free requests
        free_result = await session.execute(
            delete(FreeChannelRequest).where(FreeChannelRequest.user_id == user_id)
        )
        free_deleted = free_result.rowcount
        print(f"   - Solicitudes Free eliminadas: {free_deleted}")

        # Role change log (no tiene cascade, se borra manualmente)
        log_result = await session.execute(
            delete(UserRoleChangeLog).where(UserRoleChangeLog.user_id == user_id)
        )
        log_deleted = log_result.rowcount
        print(f"   - Logs de cambios de rol eliminados: {log_deleted}")

        # Finalmente, eliminar el usuario
        await session.execute(delete(User).where(User.user_id == user_id))
        await session.commit()

        print(f"✅ Usuario {user_id} eliminado correctamente.")


async def clean_all():
    """Elimina TODOS los datos de la base de datos (menos config)."""
    confirm = input("\n⚠️  ESTO ELIMINARÁ TODOS LOS DATOS (menos config)!")
    confirm2 = input("¿Estás seguro? Escribe 'BORRAR TODO' para confirmar: ")

    if confirm2 != "BORRAR TODO":
        print("❌ Operación cancelada.")
        return

    async with async_session() as session:
        print("\n🗑️  Eliminando todos los datos...")

        # Contar antes
        users_count = await session.scalar(select(func.count()).select_from(User))

        # Eliminar en orden correcto (respetando foreign keys)
        await session.execute(delete(UserInterest))
        print("   - UserInterests eliminados")

        await session.execute(delete(UserRoleChangeLog))
        print("   - RoleChangeLogs eliminados")

        await session.execute(delete(FreeChannelRequest))
        print("   - FreeRequests eliminados")

        await session.execute(delete(VIPSubscriber))
        print("   - VIPSubscribers eliminados")

        await session.execute(delete(InvitationToken))
        print("   - Tokens eliminados")

        await session.execute(delete(ContentPackage))
        print("   - ContentPackages eliminados")

        await session.execute(delete(SubscriptionPlan))
        print("   - SubscriptionPlans eliminados")

        await session.execute(delete(User))
        print(f"   - {users_count} usuarios eliminados")

        await session.commit()

        print("✅ Base de datos limpiada. Solo queda BotConfig.")


async def main():
    """Función principal."""
    if len(sys.argv) < 2:
        # Sin argumentos: listar usuarios
        await list_users()
    elif sys.argv[1] == "--delete":
        if len(sys.argv) < 3:
            print("❌ Error: --delete requiere un user_id")
            print("   Uso: python scripts/db_cleanup.py --delete <user_id>")
            sys.exit(1)
        try:
            user_id = int(sys.argv[2])
            await delete_user(user_id)
        except ValueError:
            print(f"❌ Error: '{sys.argv[2]}' no es un user_id válido")
            sys.exit(1)
    elif sys.argv[1] == "--clean-all":
        await clean_all()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
