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

    async def earn_besitos(
        self,
        user_id: int,
        amount: int,
        transaction_type: TransactionType,
        reason: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """
        Gana besitos de forma atómica.

        Actualiza el balance y total_earned atómicamente usando UPDATE SET,
        luego registra la transacción en el audit trail.

        Args:
            user_id: ID del usuario que gana besitos
            amount: Cantidad a ganar (debe ser > 0)
            transaction_type: Tipo de transacción (EARN_*)
            reason: Descripción legible de la ganancia
            metadata: Datos adicionales opcionales

        Returns:
            Tuple[bool, str, Optional[Transaction]]:
                - bool: True si éxito, False si error
                - str: Mensaje descriptivo ("earned" o "invalid_amount")
                - Optional[Transaction]: Transacción creada o None

        Example:
            success, msg, tx = await wallet.earn_besitos(
                user_id=123,
                amount=100,
                transaction_type=TransactionType.EARN_REACTION,
                reason="Reaction to content #456"
            )
        """
        # Validation
        if amount <= 0:
            return False, "invalid_amount", None

        try:
            # Atomic UPDATE: try to update existing profile
            result = await self.session.execute(
                update(UserGamificationProfile)
                .where(UserGamificationProfile.user_id == user_id)
                .values(
                    balance=UserGamificationProfile.balance + amount,
                    total_earned=UserGamificationProfile.total_earned + amount,
                    updated_at=datetime.utcnow()
                )
            )

            # If no rows affected, profile doesn't exist - create it
            if result.rowcount == 0:
                profile = UserGamificationProfile(
                    user_id=user_id,
                    balance=amount,
                    total_earned=amount,
                    total_spent=0,
                    level=1
                )
                self.session.add(profile)
                await self.session.flush()
                self.logger.info(f"✅ Perfil creado al ganar besitos: user {user_id}")

            # Create transaction record
            transaction = Transaction(
                user_id=user_id,
                amount=amount,  # Positive for earn
                type=transaction_type,
                reason=reason,
                transaction_metadata=metadata
            )
            self.session.add(transaction)
            await self.session.flush()

            self.logger.info(
                f"✅ User {user_id} earned {amount} besitos ({transaction_type.value}): {reason}"
            )

            return True, "earned", transaction

        except Exception as e:
            self.logger.error(f"❌ Error en earn_besitos para user {user_id}: {e}")
            return False, str(e), None

    async def spend_besitos(
        self,
        user_id: int,
        amount: int,
        transaction_type: TransactionType,
        reason: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """
        Gasta besitos de forma atómica con prevención de balance negativo.

        Solo permite el gasto si el usuario tiene suficiente balance.
        Usa UPDATE con condición balance >= amount para atomicidad.

        Args:
            user_id: ID del usuario que gasta besitos
            amount: Cantidad a gastar (debe ser > 0)
            transaction_type: Tipo de transacción (SPEND_*)
            reason: Descripción legible del gasto
            metadata: Datos adicionales opcionales

        Returns:
            Tuple[bool, str, Optional[Transaction]]:
                - bool: True si éxito, False si error
                - str: Mensaje descriptivo ("spent", "insufficient_funds", "no_profile", "invalid_amount")
                - Optional[Transaction]: Transacción creada o None

        Example:
            success, msg, tx = await wallet.spend_besitos(
                user_id=123,
                amount=50,
                transaction_type=TransactionType.SPEND_SHOP,
                reason="Purchase item #789"
            )
        """
        # Validation
        if amount <= 0:
            return False, "invalid_amount", None

        try:
            # Atomic UPDATE with balance check
            # Only succeeds if balance >= amount
            result = await self.session.execute(
                update(UserGamificationProfile)
                .where(
                    UserGamificationProfile.user_id == user_id,
                    UserGamificationProfile.balance >= amount
                )
                .values(
                    balance=UserGamificationProfile.balance - amount,
                    total_spent=UserGamificationProfile.total_spent + amount,
                    updated_at=datetime.utcnow()
                )
            )

            # Check if update succeeded
            if result.rowcount == 0:
                # Either no profile or insufficient balance
                # Query to determine which case
                profile = await self.get_profile(user_id)
                if profile is None:
                    return False, "no_profile", None
                else:
                    return False, "insufficient_funds", None

            # Create transaction record (negative amount for spend)
            transaction = Transaction(
                user_id=user_id,
                amount=-amount,  # Negative for spend
                type=transaction_type,
                reason=reason,
                transaction_metadata=metadata
            )
            self.session.add(transaction)
            await self.session.flush()

            self.logger.info(
                f"✅ User {user_id} spent {amount} besitos ({transaction_type.value}): {reason}"
            )

            return True, "spent", transaction

        except Exception as e:
            self.logger.error(f"❌ Error en spend_besitos para user {user_id}: {e}")
            return False, str(e), None

    async def get_transaction_history(
        self,
        user_id: int,
        page: int = 1,
        per_page: int = 10,
        transaction_type: Optional[TransactionType] = None
    ) -> Tuple[List[Transaction], int]:
        """
        Get paginated transaction history for user.

        Args:
            user_id: User ID to query
            page: Page number (1-indexed)
            per_page: Items per page
            transaction_type: Optional filter by type

        Returns:
            Tuple of (transactions list, total count)

        Example:
            txs, total = await wallet.get_transaction_history(
                user_id=123,
                page=1,
                per_page=10
            )
        """
        # Build base query
        base_query = select(Transaction).where(Transaction.user_id == user_id)

        # Add type filter if provided
        if transaction_type is not None:
            base_query = base_query.where(Transaction.type == transaction_type)

        # Get total count
        count_query = select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
        if transaction_type is not None:
            count_query = count_query.where(Transaction.type == transaction_type)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one_or_none() or 0

        # Apply pagination and ordering
        offset = (page - 1) * per_page
        query = (
            base_query
            .order_by(Transaction.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )

        result = await self.session.execute(query)
        transactions = list(result.scalars().all())

        return transactions, total

    def _evaluate_level_formula(self, total_earned: int, formula: str) -> int:
        """
        Evalúa la fórmula de nivel de forma segura.

        Args:
            total_earned: Total de besitos ganados
            formula: Fórmula a evaluar (default: "floor(sqrt(total_earned / 100)) + 1")

        Returns:
            int: Nivel calculado (mínimo 1)

        Supported operations:
            - sqrt(x): Raíz cuadrada
            - floor(x): Redondeo hacia abajo
            - +, -, *, /: Operaciones aritméticas
            - (, ): Agrupación

        Variable:
            - total_earned: Total de besitos ganados
        """
        if not formula:
            formula = "floor(sqrt(total_earned / 100)) + 1"

        try:
            # Create safe evaluation environment
            # Only allow specific math functions and operators
            safe_dict = {
                'sqrt': math.sqrt,
                'floor': math.floor,
                'total_earned': total_earned
            }

            # Validate formula contains only allowed characters
            # Allowed: letters, numbers, spaces, operators, parentheses, dots
            if not re.match(r'^[\w\s+\-*/().]+$', formula):
                self.logger.warning(f"⚠️ Fórmula contiene caracteres inválidos: {formula}")
                # Fallback to default
                formula = "floor(sqrt(total_earned / 100)) + 1"

            # Evaluate formula safely
            level = eval(formula, {"__builtins__": {}}, safe_dict)

            # Ensure minimum level of 1
            return max(1, int(level))

        except Exception as e:
            self.logger.error(f"❌ Error evaluando fórmula '{formula}': {e}")
            # Fallback: linear formula
            return max(1, 1 + (total_earned // 100))

    async def get_user_level(self, user_id: int, formula: Optional[str] = None) -> int:
        """
        Calculate user level based on total_earned.

        Args:
            user_id: User to calculate for
            formula: Optional formula override (uses default if None)

        Returns:
            Current level (1 if no profile)

        Example:
            level = await wallet.get_user_level(user_id=123)
            # Returns: 1, 2, 3, etc.
        """
        profile = await self.get_profile(user_id)

        if profile is None:
            return 1

        return self._evaluate_level_formula(profile.total_earned, formula)

    async def update_user_level(self, user_id: int, formula: Optional[str] = None) -> int:
        """
        Calculate and update cached level in profile.

        Args:
            user_id: User to update
            formula: Optional formula override

        Returns:
            New level value

        Example:
            new_level = await wallet.update_user_level(user_id=123)
        """
        # Calculate new level
        new_level = await self.get_user_level(user_id, formula)

        # Update profile
        profile = await self._get_or_create_profile(user_id)

        if profile.level != new_level:
            profile.level = new_level
            await self.session.flush()
            self.logger.info(f"✅ User {user_id} level updated to {new_level}")

        return new_level
