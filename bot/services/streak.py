"""
Streak Service - Gestión de rachas diarias y recompensas.

Responsabilidades:
- Tracking de rachas de regalo diario
- Cálculo de bonus por racha
- Validación de disponibilidad de reclamo (24h UTC)
- Integración con WalletService para crédito de besitos

Patrones:
- UTC-based day boundaries para consistencia global
- Bonus calculation con cap máximo configurable
- Streak reset en missed days (no grace period v2.0)
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Tuple, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserStreak
from bot.database.enums import StreakType, TransactionType

logger = logging.getLogger(__name__)


class StreakService:
    """
    Service para gestionar rachas de usuarios en el sistema de gamificación.

    Soporta dos tipos de rachas:
    - DAILY_GIFT: Días consecutivos reclamando el regalo diario
    - REACTION: Días consecutivos con al menos una reacción

    Flujo de regalo diario:
    1. Usuario solicita reclamar → can_claim_daily_gift()
    2. Si disponible, calcula racha y bonus → claim_daily_gift()
    3. Crédito de besitos vía WalletService
    4. Actualización de registro UserStreak

    Boundaries:
    - Las rachas usan UTC para consistencia global
    - Un reclamo por día UTC (00:00-23:59 UTC)
    - Streak incrementa solo en días consecutivos UTC
    - Missed day = reset a 1 (o 0 si no reclama ese día)
    """

    # Configuration constants
    BASE_BESITOS = 20  # Base amount for daily gift
    STREAK_BONUS_PER_DAY = 2  # Bonus per streak day
    STREAK_BONUS_MAX = 50  # Maximum streak bonus cap

    def __init__(self, session: AsyncSession, wallet_service=None):
        """
        Inicializa el StreakService.

        Args:
            session: Sesión de base de datos async
            wallet_service: WalletService opcional para crédito de besitos
        """
        self.session = session
        self.wallet_service = wallet_service
        self.logger = logging.getLogger(__name__)

    async def _get_or_create_streak(
        self,
        user_id: int,
        streak_type: StreakType
    ) -> UserStreak:
        """
        Obtiene o crea un registro de racha para el usuario.

        Args:
            user_id: ID del usuario
            streak_type: Tipo de racha (DAILY_GIFT o REACTION)

        Returns:
            UserStreak: Registro existente o nuevo
        """
        # Try to get existing streak using composite key pattern
        result = await self.session.execute(
            select(UserStreak).where(
                UserStreak.user_id == user_id,
                UserStreak.streak_type == streak_type
            )
        )
        streak = result.scalar_one_or_none()

        if streak is None:
            # Create new streak record
            streak = UserStreak(
                user_id=user_id,
                streak_type=streak_type,
                current_streak=0,
                longest_streak=0,
                last_claim_date=None,
                last_reaction_date=None
            )
            self.session.add(streak)
            await self.session.flush()
            self.logger.info(
                f"✅ Created new {streak_type.value} streak for user {user_id}"
            )

        return streak

    @staticmethod
    def _get_utc_date(dt: Optional[datetime] = None) -> date:
        """
        Obtiene la fecha UTC de un datetime.

        Args:
            dt: Datetime opcional (default: ahora)

        Returns:
            date: Fecha en UTC
        """
        if dt is None:
            dt = datetime.utcnow()
        return dt.date()

    def _get_next_claim_time(self, last_claim_date: Optional[datetime]) -> datetime:
        """
        Calcula el próximo momento disponible para reclamar.

        Args:
            last_claim_date: Fecha del último reclamo

        Returns:
            datetime: Próximo momento disponible (00:00 UTC del día siguiente)
        """
        if last_claim_date is None:
            return datetime.utcnow()

        last_date = self._get_utc_date(last_claim_date)
        next_date = last_date + timedelta(days=1)
        return datetime.combine(next_date, datetime.min.time())

    async def can_claim_daily_gift(self, user_id: int) -> Tuple[bool, str]:
        """
        Verifica si el usuario puede reclamar el regalo diario.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, str]:
                - bool: True si puede reclamar
                - str: Código de estado o tiempo hasta próximo reclamo
                    - "available": Puede reclamar ahora
                    - "already_claimed": Ya reclamó hoy
                    - "next_claim_in_Xh_Ym": Tiempo hasta próximo reclamo
        """
        streak = await self._get_or_create_streak(user_id, StreakType.DAILY_GIFT)

        # If never claimed, can claim now
        if streak.last_claim_date is None:
            return True, "available"

        # Get UTC dates for comparison
        today = self._get_utc_date()
        last_claim = self._get_utc_date(streak.last_claim_date)

        # Already claimed today
        if last_claim == today:
            # Calculate time until next claim
            next_claim = self._get_next_claim_time(streak.last_claim_date)
            now = datetime.utcnow()

            if now >= next_claim:
                return True, "available"

            # Calculate remaining time
            remaining = next_claim - now
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60

            return False, f"next_claim_in_{hours}h_{minutes}m"

        # Can claim (either new or continuing streak)
        return True, "available"

    def calculate_streak_bonus(self, current_streak: int) -> Tuple[int, int, int]:
        """
        Calcula el bonus de besitos basado en la racha actual.

        Args:
            current_streak: Días consecutivos de racha

        Returns:
            Tuple[int, int, int]: (base, bonus, total)
                - base: Cantidad base (20 besitos)
                - bonus: Bonus por racha (min(streak * 2, 50))
                - total: Total a otorgar (base + bonus)
        """
        base = self.BASE_BESITOS
        bonus = min(current_streak * self.STREAK_BONUS_PER_DAY, self.STREAK_BONUS_MAX)
        total = base + bonus

        return base, bonus, total

    async def claim_daily_gift(self, user_id: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Procesa el reclamo del regalo diario.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, Dict]: (éxito, resultado)
                - success: True si se otorgó el regalo
                - result: Dict con detalles:
                    - success: bool
                    - base_amount: int
                    - streak_bonus: int
                    - total: int
                    - new_streak: int
                    - longest_streak: int
                    - error: str (opcional, si falló)
        """
        # Check if can claim
        can_claim, status = await self.can_claim_daily_gift(user_id)

        if not can_claim:
            return False, {
                "success": False,
                "error": status,
                "base_amount": 0,
                "streak_bonus": 0,
                "total": 0,
                "new_streak": 0,
                "longest_streak": 0
            }

        # Get or create streak record
        streak = await self._get_or_create_streak(user_id, StreakType.DAILY_GIFT)

        # Calculate streak
        today = self._get_utc_date()

        if streak.last_claim_date is None:
            # First claim ever
            new_streak = 1
        else:
            last_claim = self._get_utc_date(streak.last_claim_date)
            yesterday = today - timedelta(days=1)

            if last_claim == yesterday:
                # Consecutive day - increment streak
                new_streak = streak.current_streak + 1
            elif last_claim == today:
                # Same day (shouldn't happen due to can_claim check)
                return False, {
                    "success": False,
                    "error": "already_claimed",
                    "base_amount": 0,
                    "streak_bonus": 0,
                    "total": 0,
                    "new_streak": streak.current_streak,
                    "longest_streak": streak.longest_streak
                }
            else:
                # Missed a day - reset to 1
                new_streak = 1

        # Calculate besitos
        base, bonus, total = self.calculate_streak_bonus(new_streak)

        # Credit besitos via wallet service
        if self.wallet_service is not None:
            success, msg, transaction = await self.wallet_service.earn_besitos(
                user_id=user_id,
                amount=total,
                transaction_type=TransactionType.EARN_DAILY,
                reason=f"Daily gift claim - streak day {new_streak}",
                metadata={
                    "streak_day": new_streak,
                    "base_amount": base,
                    "streak_bonus": bonus
                }
            )

            if not success:
                self.logger.error(
                    f"❌ Failed to credit besitos for daily gift to user {user_id}: {msg}"
                )
                return False, {
                    "success": False,
                    "error": f"credit_failed: {msg}",
                    "base_amount": base,
                    "streak_bonus": bonus,
                    "total": total,
                    "new_streak": new_streak,
                    "longest_streak": streak.longest_streak
                }

        # Update streak record
        streak.current_streak = new_streak
        streak.last_claim_date = datetime.utcnow()

        # Update longest streak if applicable
        if new_streak > streak.longest_streak:
            streak.longest_streak = new_streak

        await self.session.flush()

        self.logger.info(
            f"✅ User {user_id} claimed daily gift: {total} besitos "
            f"(base={base}, bonus={bonus}, streak={new_streak})"
        )

        return True, {
            "success": True,
            "base_amount": base,
            "streak_bonus": bonus,
            "total": total,
            "new_streak": new_streak,
            "longest_streak": streak.longest_streak
        }

    async def get_streak_info(
        self,
        user_id: int,
        streak_type: StreakType
    ) -> Dict[str, Any]:
        """
        Obtiene información actual de la racha del usuario.

        Args:
            user_id: ID del usuario
            streak_type: Tipo de racha

        Returns:
            Dict con información de la racha:
                - current_streak: int
                - longest_streak: int
                - last_claim_date: datetime o None
                - can_claim: bool
                - next_claim_time: datetime o None
        """
        streak = await self._get_or_create_streak(user_id, streak_type)

        # Check if can claim (only for DAILY_GIFT type)
        can_claim = False
        next_claim_time = None

        if streak_type == StreakType.DAILY_GIFT:
            can_claim, status = await self.can_claim_daily_gift(user_id)
            if not can_claim and streak.last_claim_date is not None:
                next_claim_time = self._get_next_claim_time(streak.last_claim_date)
            elif can_claim:
                next_claim_time = datetime.utcnow()

        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "last_claim_date": streak.last_claim_date,
            "can_claim": can_claim,
            "next_claim_time": next_claim_time
        }

    async def reset_streak(self, user_id: int, streak_type: StreakType) -> bool:
        """
        Resetea la racha actual a 0 (llamado por background job en expiración).

        No afecta longest_streak que es histórico.

        Args:
            user_id: ID del usuario
            streak_type: Tipo de racha a resetear

        Returns:
            bool: True si se reseteó, False si no existía
        """
        result = await self.session.execute(
            select(UserStreak).where(
                UserStreak.user_id == user_id,
                UserStreak.streak_type == streak_type
            )
        )
        streak = result.scalar_one_or_none()

        if streak is None:
            return False

        old_streak = streak.current_streak
        streak.current_streak = 0
        await self.session.flush()

        self.logger.info(
            f"🔄 Reset {streak_type.value} streak for user {user_id} "
            f"(was {old_streak})"
        )

        return True

    async def update_reaction_streak(self, user_id: int) -> Tuple[bool, int]:
        """
        Actualiza la racha de reacciones para el usuario.

        Llama cada vez que el usuario reacciona a contenido.
        Incrementa la racha si es un día diferente al último.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, int]: (streak_incremented, current_streak)
        """
        streak = await self._get_or_create_streak(user_id, StreakType.REACTION)

        today = self._get_utc_date()

        if streak.last_reaction_date is None:
            # First reaction ever
            streak.current_streak = 1
            streak.last_reaction_date = datetime.utcnow()
            await self.session.flush()
            return True, 1

        last_reaction = self._get_utc_date(streak.last_reaction_date)

        if last_reaction == today:
            # Already reacted today, no streak change
            return False, streak.current_streak

        # New day - increment streak
        yesterday = today - timedelta(days=1)

        if last_reaction == yesterday:
            # Consecutive day
            streak.current_streak += 1
        else:
            # Missed a day - reset to 1
            streak.current_streak = 1

        # Update longest streak if applicable
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak

        streak.last_reaction_date = datetime.utcnow()
        await self.session.flush()

        self.logger.info(
            f"✅ Updated reaction streak for user {user_id}: "
            f"{streak.current_streak} days"
        )

        return True, streak.current_streak
