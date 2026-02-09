"""
Wallet Service - Gestión de economía y gamificación.

Responsabilidades:
- Gestión de balances de besitos (earn/spend)
- Registro de transacciones (audit trail)
- Cálculo de niveles basado en total_earned
- Historial de transacciones con paginación

Patrones:
- Operaciones atómicas usando UPDATE SET (no read-modify-write)
- Transacciones siempre registradas (audit trail completo)
- Niveles calculados desde total_earned (progresión clara)
"""
import logging
import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserGamificationProfile, Transaction
from bot.database.enums import TransactionType

logger = logging.getLogger(__name__)


class WalletService:
    """
    Service para gestionar la economía de besitos y gamificación.

    Flujo de ganancia:
    1. Usuario gana besitos → earn_besitos()
    2. Balance y total_earned actualizados atómicamente
    3. Transacción registrada con amount positivo

    Flujo de gasto:
    1. Usuario gasta besitos → spend_besitos()
    2. Verificación atómica de balance suficiente
    3. Balance decrementado, total_spent incrementado
    4. Transacción registrada con amount negativo

    Niveles:
    - Calculados desde total_earned usando fórmula configurable
    - Default: floor(sqrt(total_earned / 100)) + 1
    - Mínimo nivel 1
    """

    def __init__(self, session: AsyncSession):
        """
        Inicializa el WalletService.

        Args:
            session: Sesión de base de datos async
        """
        self.session = session
        self.logger = logging.getLogger(__name__)

    async def _get_or_create_profile(self, user_id: int) -> UserGamificationProfile:
        """
        Obtiene o crea el perfil de gamificación de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            UserGamificationProfile: Perfil existente o nuevo
        """
        result = await self.session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == user_id
            )
        )
        profile = result.scalar_one_or_none()

        if profile is None:
            profile = UserGamificationProfile(
                user_id=user_id,
                balance=0,
                total_earned=0,
                total_spent=0,
                level=1
            )
            self.session.add(profile)
            await self.session.flush()
            self.logger.info(f"✅ Perfil de gamificación creado para user {user_id}")

        return profile

    async def get_balance(self, user_id: int) -> int:
        """
        Obtiene el balance actual de besitos de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            int: Balance actual (0 si no tiene perfil)
        """
        result = await self.session.execute(
            select(UserGamificationProfile.balance).where(
                UserGamificationProfile.user_id == user_id
            )
        )
        balance = result.scalar_one_or_none()
        return balance or 0

    async def get_profile(self, user_id: int) -> Optional[UserGamificationProfile]:
        """
        Obtiene el perfil completo de gamificación de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            UserGamificationProfile si existe, None si no
        """
        result = await self.session.execute(
            select(UserGamificationProfile).where(
                UserGamificationProfile.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
