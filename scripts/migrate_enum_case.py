#!/usr/bin/env python3
"""
Script de migración para actualizar valores de enum de minúsculas a mayúsculas.

Este script actualiza los valores almacenados en la base de datos para que coincidan
con los nuevos valores de enum en mayúsculas.

Cambios:
- UserRole: "free" -> "FREE", "vip" -> "VIP", "admin" -> "ADMIN"
- ContentCategory: "free_content" -> "FREE_CONTENT", "vip_content" -> "VIP_CONTENT", "vip_premium" -> "VIP_PREMIUM"
- PackageType: "standard" -> "STANDARD", "bundle" -> "BUNDLE", "collection" -> "COLLECTION"
- RoleChangeReason: "admin_granted" -> "ADMIN_GRANTED", etc.

Uso:
    python scripts/migrate_enum_case.py

NOTA: Hacer backup de la base de datos antes de ejecutar.
"""
import asyncio
import sys
import os
from typing import Dict, List, Tuple

# Agregar el directorio raíz al path para importar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import update, select, func, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import Config
from bot.database.models import (
    User, UserRoleChangeLog, ContentPackage,
    UserInterest, VIPSubscriber, InvitationToken, FreeChannelRequest
)
from bot.database.enums import UserRole, ContentCategory, PackageType, RoleChangeReason


# Crear engine async para el script (usar aiosqlite)
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=False
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# Mapeos de valores antiguos a nuevos
USER_ROLE_MAP = {
    "free": UserRole.FREE.value,
    "vip": UserRole.VIP.value,
    "admin": UserRole.ADMIN.value
}

CONTENT_CATEGORY_MAP = {
    "free_content": ContentCategory.FREE_CONTENT.value,
    "vip_content": ContentCategory.VIP_CONTENT.value,
    "vip_premium": ContentCategory.VIP_PREMIUM.value
}

PACKAGE_TYPE_MAP = {
    "standard": PackageType.STANDARD.value,
    "bundle": PackageType.BUNDLE.value,
    "collection": PackageType.COLLECTION.value
}

ROLE_CHANGE_REASON_MAP = {
    "admin_granted": RoleChangeReason.ADMIN_GRANTED.value,
    "admin_revoked": RoleChangeReason.ADMIN_REVOKED.value,
    "vip_purchased": RoleChangeReason.VIP_PURCHASED.value,
    "vip_redeemed": RoleChangeReason.VIP_REDEEMED.value,
    "vip_expired": RoleChangeReason.VIP_EXPIRED.value,
    "vip_extended": RoleChangeReason.VIP_EXTENDED.value,
    "manual_change": RoleChangeReason.MANUAL_CHANGE.value,
    "system_automatic": RoleChangeReason.SYSTEM_AUTOMATIC.value
}


async def migrate_user_roles(session: AsyncSession) -> int:
    """Actualiza valores de User.role."""
    updated_count = 0
    for old_val, new_val in USER_ROLE_MAP.items():
        stmt = (
            update(User)
            .where(User.role == old_val)
            .values(role=new_val)
        )
        result = await session.execute(stmt)
        if result.rowcount:
            updated_count += result.rowcount
            print(f"  - User.role: {old_val} -> {new_val}: {result.rowcount} registros")

    return updated_count


async def migrate_role_change_log(session: AsyncSession) -> Tuple[int, int, int]:
    """Actualiza UserRoleChangeLog.previous_role, new_role y reason."""
    updated_prev = 0
    updated_new = 0
    updated_reason = 0

    # previous_role (puede ser NULL)
    for old_val, new_val in USER_ROLE_MAP.items():
        stmt = (
            update(UserRoleChangeLog)
            .where(UserRoleChangeLog.previous_role == old_val)
            .values(previous_role=new_val)
        )
        result = await session.execute(stmt)
        if result.rowcount:
            updated_prev += result.rowcount
            print(f"  - UserRoleChangeLog.previous_role: {old_val} -> {new_val}: {result.rowcount} registros")

    # new_role
    for old_val, new_val in USER_ROLE_MAP.items():
        stmt = (
            update(UserRoleChangeLog)
            .where(UserRoleChangeLog.new_role == old_val)
            .values(new_role=new_val)
        )
        result = await session.execute(stmt)
        if result.rowcount:
            updated_new += result.rowcount
            print(f"  - UserRoleChangeLog.new_role: {old_val} -> {new_val}: {result.rowcount} registros")

    # reason
    for old_val, new_val in ROLE_CHANGE_REASON_MAP.items():
        stmt = (
            update(UserRoleChangeLog)
            .where(UserRoleChangeLog.reason == old_val)
            .values(reason=new_val)
        )
        result = await session.execute(stmt)
        if result.rowcount:
            updated_reason += result.rowcount
            print(f"  - UserRoleChangeLog.reason: {old_val} -> {new_val}: {result.rowcount} registros")

    return updated_prev, updated_new, updated_reason


async def migrate_content_packages(session: AsyncSession) -> Tuple[int, int]:
    """Actualiza ContentPackage.category y .type."""
    updated_category = 0
    updated_type = 0

    # category
    for old_val, new_val in CONTENT_CATEGORY_MAP.items():
        stmt = (
            update(ContentPackage)
            .where(ContentPackage.category == old_val)
            .values(category=new_val)
        )
        result = await session.execute(stmt)
        if result.rowcount:
            updated_category += result.rowcount
            print(f"  - ContentPackage.category: {old_val} -> {new_val}: {result.rowcount} registros")

    # type
    for old_val, new_val in PACKAGE_TYPE_MAP.items():
        stmt = (
            update(ContentPackage)
            .where(ContentPackage.type == old_val)
            .values(type=new_val)
        )
        result = await session.execute(stmt)
        if result.rowcount:
            updated_type += result.rowcount
            print(f"  - ContentPackage.type: {old_val} -> {new_val}: {result.rowcount} registros")

    return updated_category, updated_type


async def check_remaining_lowercase(session: AsyncSession):
    """Verifica si quedan valores en minúsculas después de la migración."""
    print("\n--- Verificación de valores restantes en minúsculas ---")

    # User.role
    for old_val in USER_ROLE_MAP.keys():
        stmt = select(func.count()).select_from(User).where(User.role == old_val)
        count = await session.scalar(stmt)
        if count:
            print(f"  ⚠️  User.role = '{old_val}': {count} registros")

    # UserRoleChangeLog
    for old_val in USER_ROLE_MAP.keys():
        stmt = select(func.count()).select_from(UserRoleChangeLog).where(
            UserRoleChangeLog.previous_role == old_val
        )
        count = await session.scalar(stmt)
        if count:
            print(f"  ⚠️  UserRoleChangeLog.previous_role = '{old_val}': {count} registros")

        stmt = select(func.count()).select_from(UserRoleChangeLog).where(
            UserRoleChangeLog.new_role == old_val
        )
        count = await session.scalar(stmt)
        if count:
            print(f"  ⚠️  UserRoleChangeLog.new_role = '{old_val}': {count} registros")

    for old_val in ROLE_CHANGE_REASON_MAP.keys():
        stmt = select(func.count()).select_from(UserRoleChangeLog).where(
            UserRoleChangeLog.reason == old_val
        )
        count = await session.scalar(stmt)
        if count:
            print(f"  ⚠️  UserRoleChangeLog.reason = '{old_val}': {count} registros")

    # ContentPackage
    for old_val in CONTENT_CATEGORY_MAP.keys():
        stmt = select(func.count()).select_from(ContentPackage).where(
            ContentPackage.category == old_val
        )
        count = await session.scalar(stmt)
        if count:
            print(f"  ⚠️  ContentPackage.category = '{old_val}': {count} registros")

    for old_val in PACKAGE_TYPE_MAP.keys():
        stmt = select(func.count()).select_from(ContentPackage).where(
            ContentPackage.type == old_val
        )
        count = await session.scalar(stmt)
        if count:
            print(f"  ⚠️  ContentPackage.type = '{old_val}': {count} registros")

    print("--- Fin de verificación ---")


async def main():
    """Función principal de migración."""
    print("=== Migración de valores de enum (minúsculas → mayúsculas) ===")
    print("NOTA: Se recomienda hacer backup de la base de datos antes de continuar.")
    print()

    async with async_session() as session:
        try:
            # Iniciar transacción
            await session.begin()

            print("1. Actualizando User.role...")
            user_updated = await migrate_user_roles(session)
            print(f"   Total: {user_updated} registros actualizados")

            print("\n2. Actualizando UserRoleChangeLog...")
            prev_role, new_role, reason = await migrate_role_change_log(session)
            print(f"   previous_role: {prev_role}, new_role: {new_role}, reason: {reason}")

            print("\n3. Actualizando ContentPackage...")
            category, package_type = await migrate_content_packages(session)
            print(f"   category: {category}, type: {package_type}")

            # Verificar valores restantes
            await check_remaining_lowercase(session)

            # Confirmar transacción
            await session.commit()
            print("\n✅ Migración completada exitosamente.")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error durante la migración: {e}")
            raise

    print("\n=== Migración finalizada ===")


if __name__ == "__main__":
    asyncio.run(main())