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

from sqlalchemy import select, update
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

            # Calculate remaining time using total_seconds() for >24h support
            remaining = next_claim - now
            remaining_seconds = remaining.total_seconds()
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)

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

        Usa UPDATE atómico con condición WHERE para prevenir race conditions
        en reclamos concurrentes. Si el UPDATE no afecta filas, el usuario
        ya reclamó hoy.

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
        from bot.database.models import UserStreak

        # First check if can claim to get proper error message (e.g., "next_claim_in_Xh_Ym")
        can_claim, status = await self.can_claim_daily_gift(user_id)

        if not can_claim:
            # Return error with proper message from can_claim_daily_gift
            # Get streak info for current streak values in error response
            streak_info = await self._get_streak_for_claim(user_id)
            longest_streak = streak_info[3] if streak_info else 0

            return False, {
                "success": False,
                "error": status,  # Contains "next_claim_in_Xh_Ym" or other status
                "base_amount": 0,
                "streak_bonus": 0,
                "total": 0,
                "new_streak": 0,  # Default for failed claim
                "longest_streak": longest_streak
            }

        # Get streak info first (for calculations)
        streak_info = await self._get_streak_for_claim(user_id)

        if streak_info is None:
            # No streak record exists yet - need to create one
            streak = await self._get_or_create_streak(user_id, StreakType.DAILY_GIFT)
            new_streak = 1
        else:
            streak_id, current_streak, last_claim_date, longest_streak = streak_info

            # Calculate new streak value
            today = self._get_utc_date()

            if last_claim_date is None:
                new_streak = 1
            else:
                last_claim = self._get_utc_date(last_claim_date)
                yesterday = today - timedelta(days=1)

                if last_claim == yesterday:
                    new_streak = current_streak + 1
                elif last_claim == today:
                    # Should not happen due to can_claim check above, but handle anyway
                    return False, {
                        "success": False,
                        "error": status,  # Use status from can_claim_daily_gift
                        "base_amount": 0,
                        "streak_bonus": 0,
                        "total": 0,
                        "new_streak": current_streak,
                        "longest_streak": longest_streak
                    }
                else:
                    new_streak = 1

        # Calculate besitos before atomic update
        base, bonus, total = self.calculate_streak_bonus(new_streak)
        now = datetime.utcnow()
        today_start = datetime.combine(self._get_utc_date(), datetime.min.time())

        # ATOMIC UPDATE: Only succeeds if user hasn't claimed today
        # This prevents race conditions from concurrent requests
        if streak_info is not None:
            # Update existing streak atomically
            result = await self.session.execute(
                update(UserStreak)
                .where(
                    UserStreak.user_id == user_id,
                    UserStreak.streak_type == StreakType.DAILY_GIFT,
                    # Atomic condition: last_claim_date must be before today
                    (
                        (UserStreak.last_claim_date < today_start) |
                        (UserStreak.last_claim_date.is_(None))
                    )
                )
                .values(
                    current_streak=new_streak,
                    last_claim_date=now,
                    longest_streak=UserStreak.longest_streak if new_streak <= streak_info[3] else new_streak,
                    updated_at=now
                )
            )

            if result.rowcount == 0:
                # Another concurrent request claimed first
                return False, {
                    "success": False,
                    "error": "already_claimed",
                    "base_amount": 0,
                    "streak_bonus": 0,
                    "total": 0,
                    "new_streak": new_streak,
                    "longest_streak": streak_info[3]
                }
        else:
            # New streak - was created by _get_or_create_streak above
            # Need to update it atomically
            result = await self.session.execute(
                update(UserStreak)
                .where(
                    UserStreak.user_id == user_id,
                    UserStreak.streak_type == StreakType.DAILY_GIFT,
                    UserStreak.last_claim_date.is_(None)
                )
                .values(
                    current_streak=1,
                    last_claim_date=now,
                    longest_streak=1,
                    updated_at=now
                )
            )

            if result.rowcount == 0:
                # Another concurrent request claimed first
                return False, {
                    "success": False,
                    "error": "already_claimed",
                    "base_amount": 0,
                    "streak_bonus": 0,
                    "total": 0,
                    "new_streak": 0,
                    "longest_streak": 0
                }

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
                    "longest_streak": max(streak_info[3] if streak_info else 0, new_streak)
                }

        # Refresh streak data for return
        longest = max(
            (streak_info[3] if streak_info else 0),
            new_streak
        )

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
            "longest_streak": longest
        }

    async def _get_streak_for_claim(
        self,
        user_id: int
    ) -> Optional[Tuple[int, int, Optional[datetime], int]]:
        """
        Obtiene datos de racha para procesar reclamo.

        Args:
            user_id: ID del usuario

        Returns:
            Optional tuple: (id, current_streak, last_claim_date, longest_streak)
            o None si no existe racha
        """
        from bot.database.models import UserStreak

        result = await self.session.execute(
            select(
                UserStreak.id,
                UserStreak.current_streak,
                UserStreak.last_claim_date,
                UserStreak.longest_streak
            ).where(
                UserStreak.user_id == user_id,
                UserStreak.streak_type == StreakType.DAILY_GIFT
            )
        )
        row = result.one_or_none()

        if row is None:
            return None

        return (row.id, row.current_streak, row.last_claim_date, row.longest_streak)

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

    async def record_reaction(
        self,
        user_id: int,
        reaction_date: Optional[datetime] = None
    ) -> Tuple[bool, int]:
        """
        Registra una reacción y actualiza la racha de reacciones.

        Called when user adds a reaction to content.
        Gets or creates REACTION type streak for user.
        Checks if reaction is on a new day (UTC).
        If new day: increment streak, update last_reaction_date.
        If same day: no streak change (already counted for today).

        Args:
            user_id: ID del usuario
            reaction_date: Fecha opcional de la reacción (default: ahora UTC)

        Returns:
            Tuple[bool, int]: (streak_incremented, new_streak)
            - streak_incremented: True si se incrementó la racha (nuevo día)
            - new_streak: Valor actual de la racha
        """
        if reaction_date is None:
            reaction_date = datetime.utcnow()

        # Get or create reaction streak
        streak = await self._get_or_create_streak(user_id, StreakType.REACTION)

        # Get today's date (UTC)
        today = self._get_utc_date(reaction_date)

        # Check if already reacted today
        if streak.last_reaction_date is not None:
            last_date = self._get_utc_date(streak.last_reaction_date)

            if last_date == today:
                # Same day: no streak change
                self.logger.debug(
                    f"User {user_id} already reacted today, "
                    f"streak unchanged at {streak.current_streak}"
                )
                return False, streak.current_streak

            # Check if consecutive day or missed
            yesterday = today - timedelta(days=1)
            if last_date == yesterday:
                # Consecutive day: increment streak
                streak.current_streak += 1
                if streak.current_streak > streak.longest_streak:
                    streak.longest_streak = streak.current_streak

                self.logger.info(
                    f"User {user_id} reaction streak incremented to "
                    f"{streak.current_streak}"
                )
            else:
                # Missed day(s): reset to 1
                streak.current_streak = 1
                self.logger.info(
                    f"User {user_id} reaction streak reset to 1 "
                    f"(missed days)"
                )
        else:
            # First reaction ever: start at 1
            streak.current_streak = 1
            self.logger.info(
                f"User {user_id} started reaction streak at 1"
            )

        # Update last reaction date
        streak.last_reaction_date = reaction_date
        await self.session.flush()

        return True, streak.current_streak

    async def process_streak_expirations(self) -> int:
        """
        Procesa expiraciones de rachas DAILY_GIFT que no reclamaron hoy.

        Busca todas las rachas DAILY_GIFT donde last_claim_date < hoy (UTC)
        y resetea current_streak a 0. Preserva longest_streak como histórico.

        Returns:
            int: Cantidad de rachas reseteadas
        """
        today = self._get_utc_date()

        # Find all DAILY_GIFT streaks where last_claim_date < today
        result = await self.session.execute(
            select(UserStreak).where(
                UserStreak.streak_type == StreakType.DAILY_GIFT,
                UserStreak.current_streak > 0,
                UserStreak.last_claim_date < datetime.combine(today, datetime.min.time())
            )
        )
        expired_streaks = result.scalars().all()

        reset_count = 0
        for streak in expired_streaks:
            old_streak = streak.current_streak
            streak.current_streak = 0

            self.logger.info(
                f"🔄 Reset DAILY_GIFT streak for user {streak.user_id} "
                f"(was {old_streak}, missed day)"
            )
            reset_count += 1

        if reset_count > 0:
            await self.session.flush()
            self.logger.info(
                f"✅ Processed {reset_count} expired DAILY_GIFT streaks"
            )

        return reset_count

    async def process_reaction_streak_expirations(self) -> int:
        """
        Procesa expiraciones de rachas REACTION que no reaccionaron hoy.

        Busca todas las rachas REACTION donde last_reaction_date < hoy (UTC)
        y resetea current_streak a 0. Preserva longest_streak como histórico.

        Returns:
            int: Cantidad de rachas reseteadas
        """
        today = self._get_utc_date()

        # Find all REACTION streaks where last_reaction_date < today
        result = await self.session.execute(
            select(UserStreak).where(
                UserStreak.streak_type == StreakType.REACTION,
                UserStreak.current_streak > 0,
                UserStreak.last_reaction_date < datetime.combine(today, datetime.min.time())
            )
        )
        expired_streaks = result.scalars().all()

        reset_count = 0
        for streak in expired_streaks:
            old_streak = streak.current_streak
            streak.current_streak = 0

            self.logger.info(
                f"🔄 Reset REACTION streak for user {streak.user_id} "
                f"(was {old_streak}, missed day)"
            )
            reset_count += 1

        if reset_count > 0:
            await self.session.flush()
            self.logger.info(
                f"✅ Processed {reset_count} expired REACTION streaks"
            )

        return reset_count

    async def get_reaction_streak(self, user_id: int) -> int:
        """
        Obtiene la racha actual de reacciones del usuario.

        Args:
            user_id: ID del usuario

        Returns:
            int: Racha actual (0 si no existe)
        """
        result = await self.session.execute(
            select(UserStreak).where(
                UserStreak.user_id == user_id,
                UserStreak.streak_type == StreakType.REACTION
            )
        )
        streak = result.scalar_one_or_none()

        if streak is None:
            return 0

        return streak.current_streak

    async def update_reaction_streak(self, user_id: int) -> Tuple[bool, int]:
        """
        Actualiza la racha de reacciones para el usuario.

        Llama cada vez que el usuario reacciona a contenido.
        Incrementa la racha si es un día diferente al último.

        DEPRECATED: Use record_reaction() instead.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, int]: (streak_incremented, current_streak)
        """
        return await self.record_reaction(user_id)
