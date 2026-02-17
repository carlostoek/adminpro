"""
Reward Service - Sistema de logros y recompensas.

Responsabilidades:
- Evaluar condiciones de recompensas para usuarios
- Verificar elegibilidad en eventos (event-driven)
- Gestionar reclamo de recompensas
- Rastrear progreso de usuarios hacia recompensas
- Entregar notificaciones agrupadas

Patrones:
- Event-driven checking: condiciones verificadas cuando ocurren eventos relevantes
- Lógica AND/OR: AND por defecto, grupos usan OR
- Notificaciones agrupadas: un solo mensaje con múltiples logros
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    Reward, RewardCondition, UserReward,
    UserGamificationProfile, UserContentAccess, UserReaction, Transaction, User
)
from bot.database.enums import (
    RewardType, RewardConditionType, RewardStatus,
    TransactionType, StreakType, UserRole
)

logger = logging.getLogger(__name__)


class RewardService:
    """
    Service para gestionar recompensas y sistema de logros.

    Responsabilidades:
    - Evaluar condiciones de recompensas para usuarios
    - Verificar elegibilidad en eventos (event-driven)
    - Gestionar reclamo de recompensas
    - Rastrear progreso de usuarios hacia recompensas
    - Entregar notificaciones agrupadas

    Patrones:
    - Event-driven checking: condiciones verificadas cuando ocurren eventos relevantes
    - Lógica AND/OR: AND por defecto, grupos usan OR
    - Notificaciones agrupadas: un solo mensaje con múltiples logros
    """

    def __init__(
        self,
        session: AsyncSession,
        wallet_service=None,
        streak_service=None
    ):
        """
        Inicializa el RewardService.

        Args:
            session: Sesión de base de datos async
            wallet_service: WalletService opcional para recompensas BESITOS
            streak_service: StreakService opcional para verificar rachas
        """
        self.session = session
        self.wallet_service = wallet_service
        self.streak_service = streak_service
        self.logger = logging.getLogger(__name__)

    # ===== CONDITION EVALUATION =====

    async def _evaluate_numeric_condition(
        self,
        profile: UserGamificationProfile,
        condition_type: RewardConditionType,
        threshold: Optional[int]
    ) -> bool:
        """
        Evalúa una condición numérica contra el perfil del usuario.

        Args:
            profile: Perfil de gamificación del usuario
            condition_type: Tipo de condición numérica
            threshold: Valor umbral para comparación

        Returns:
            True si la condición se cumple
        """
        if threshold is None:
            return False

        if condition_type == RewardConditionType.STREAK_LENGTH:
            # Use streak_service if available, otherwise return False
            if self.streak_service is None:
                return False
            try:
                streak_info = await self.streak_service.get_streak_info(
                    profile.user_id, StreakType.DAILY_GIFT
                )
                return streak_info.get("current_streak", 0) >= threshold
            except Exception as e:
                self.logger.error(f"Error getting streak info: {e}")
                return False

        elif condition_type == RewardConditionType.TOTAL_POINTS:
            return profile.total_earned >= threshold

        elif condition_type == RewardConditionType.LEVEL_REACHED:
            return profile.level >= threshold

        elif condition_type == RewardConditionType.BESITOS_SPENT:
            return profile.total_spent >= threshold

        return False

    async def _evaluate_event_condition(
        self,
        user_id: int,
        condition_type: RewardConditionType
    ) -> bool:
        """
        Evalúa una condición basada en eventos.

        Args:
            user_id: ID del usuario
            condition_type: Tipo de condición de evento

        Returns:
            True si el evento ha ocurrido
        """
        if condition_type == RewardConditionType.FIRST_PURCHASE:
            # Check if UserContentAccess exists with shop_purchase type
            result = await self.session.execute(
                select(func.count(UserContentAccess.id)).where(
                    UserContentAccess.user_id == user_id,
                    UserContentAccess.access_type == "shop_purchase"
                )
            )
            count = result.scalar_one_or_none() or 0
            return count > 0

        elif condition_type == RewardConditionType.FIRST_DAILY_GIFT:
            # Check if any EARN_DAILY transaction exists
            result = await self.session.execute(
                select(func.count(Transaction.id)).where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.EARN_DAILY
                )
            )
            count = result.scalar_one_or_none() or 0
            return count > 0

        elif condition_type == RewardConditionType.FIRST_REACTION:
            # Check if UserReaction exists for user
            result = await self.session.execute(
                select(func.count(UserReaction.id)).where(
                    UserReaction.user_id == user_id
                )
            )
            count = result.scalar_one_or_none() or 0
            return count > 0

        return False

    async def _evaluate_exclusion_condition(
        self,
        user_id: int,
        condition_type: RewardConditionType,
        reward_id: int
    ) -> bool:
        """
        Evalúa una condición de exclusión.

        Args:
            user_id: ID del usuario
            condition_type: Tipo de condición de exclusión
            reward_id: ID de la recompensa

        Returns:
            True si la exclusión se cumple (usuario NO está excluido)
        """
        if condition_type == RewardConditionType.NOT_VIP:
            # Check user role != VIP
            result = await self.session.execute(
                select(User.role).where(User.user_id == user_id)
            )
            role = result.scalar_one_or_none()
            return role != UserRole.VIP if role else True

        elif condition_type == RewardConditionType.NOT_CLAIMED_BEFORE:
            # Check UserReward claim_count == 0
            result = await self.session.execute(
                select(UserReward.claim_count).where(
                    UserReward.user_id == user_id,
                    UserReward.reward_id == reward_id
                )
            )
            count = result.scalar_one_or_none()
            return count == 0 if count is not None else True

        return True

    async def evaluate_single_condition(
        self,
        user_id: int,
        condition: RewardCondition
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evalúa una sola condición para un usuario.

        Args:
            user_id: ID del usuario
            condition: Condición a evaluar

        Returns:
            Tuple de (passed: bool, details: dict)
        """
        details = {
            "condition_id": condition.id,
            "condition_type": condition.condition_type.value,
            "condition_value": condition.condition_value
        }

        # Get user profile for numeric conditions
        if condition.condition_type.requires_value:
            result = await self.session.execute(
                select(UserGamificationProfile).where(
                    UserGamificationProfile.user_id == user_id
                )
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                return False, {**details, "reason": "no_profile"}

            passed = await self._evaluate_numeric_condition(
                profile,
                condition.condition_type,
                condition.condition_value
            )
            return passed, details

        # Event-based conditions
        elif condition.condition_type.is_event_based:
            passed = await self._evaluate_event_condition(
                user_id,
                condition.condition_type
            )
            return passed, details

        # Exclusion conditions
        elif condition.condition_type.is_exclusion:
            passed = await self._evaluate_exclusion_condition(
                user_id,
                condition.condition_type,
                condition.reward_id
            )
            return passed, details

        return False, {**details, "reason": "unknown_condition_type"}

    async def evaluate_reward_conditions(
        self,
        user_id: int,
        reward: Reward
    ) -> Tuple[bool, List[Dict], List[Dict]]:
        """
        Evalúa todas las condiciones de una recompensa para un usuario.

        Args:
            user_id: ID del usuario
            reward: Recompensa a evaluar

        Returns:
            Tuple de (eligible: bool, passed_conditions: list, failed_conditions: list)
        """
        # Get all conditions for reward using async query
        from sqlalchemy import select
        result = await self.session.execute(
            select(RewardCondition).where(RewardCondition.reward_id == reward.id)
        )
        conditions = list(result.scalars().all())

        if not conditions:
            # No conditions means always eligible
            return True, [], []

        passed_conditions = []
        failed_conditions = []

        # Group conditions by condition_group
        groups: Dict[int, List[RewardCondition]] = {}
        for condition in conditions:
            group = condition.condition_group
            if group not in groups:
                groups[group] = []
            groups[group].append(condition)

        # Evaluate group 0 (AND logic - all must pass)
        if 0 in groups:
            for condition in groups[0]:
                passed, details = await self.evaluate_single_condition(
                    user_id, condition
                )
                if passed:
                    passed_conditions.append(details)
                else:
                    failed_conditions.append(details)

        # Evaluate groups 1+ (OR logic - at least one in each group must pass)
        for group_id in sorted(groups.keys()):
            if group_id == 0:
                continue

            group_conditions = groups[group_id]
            group_passed = False

            for condition in group_conditions:
                passed, details = await self.evaluate_single_condition(
                    user_id, condition
                )
                if passed:
                    passed_conditions.append(details)
                    group_passed = True
                else:
                    failed_conditions.append(details)

            # For OR groups, if at least one passed, remove failed ones from this group
            # from the failed_conditions list
            if group_passed:
                failed_conditions = [
                    f for f in failed_conditions
                    if f["condition_id"] not in {c.id for c in group_conditions}
                ]
            else:
                # None passed in this OR group - mark all as failed
                pass

        eligible = len(failed_conditions) == 0
        return eligible, passed_conditions, failed_conditions

    # ===== EVENT-DRIVEN CHECKING =====

    async def _get_rewards_for_event(
        self,
        event_type: str
    ) -> List[Reward]:
        """
        Obtiene recompensas que podrían verse afectadas por un evento.

        Args:
            event_type: Tipo de evento ocurrido

        Returns:
            Lista de recompensas activas con condiciones relevantes
        """
        # Map event types to condition types
        event_to_conditions = {
            "daily_gift_claimed": [
                RewardConditionType.STREAK_LENGTH,
                RewardConditionType.FIRST_DAILY_GIFT,
                RewardConditionType.TOTAL_POINTS
            ],
            "reaction_added": [
                RewardConditionType.FIRST_REACTION,
                RewardConditionType.TOTAL_POINTS
            ],
            "purchase_completed": [
                RewardConditionType.FIRST_PURCHASE,
                RewardConditionType.BESITOS_SPENT,
                RewardConditionType.TOTAL_POINTS
            ],
            "level_up": [
                RewardConditionType.LEVEL_REACHED,
                RewardConditionType.TOTAL_POINTS
            ],
            "streak_updated": [
                RewardConditionType.STREAK_LENGTH,
                RewardConditionType.TOTAL_POINTS
            ]
        }

        condition_types = event_to_conditions.get(event_type, [])
        if not condition_types:
            return []

        # Query rewards that have conditions matching the event type
        result = await self.session.execute(
            select(Reward).distinct()
            .join(RewardCondition)
            .where(
                Reward.is_active == True,
                RewardCondition.condition_type.in_(condition_types)
            )
        )
        return list(result.scalars().all())

    async def _get_or_create_user_reward(
        self,
        user_id: int,
        reward_id: int
    ) -> UserReward:
        """
        Obtiene o crea un registro UserReward.

        Args:
            user_id: ID del usuario
            reward_id: ID de la recompensa

        Returns:
            UserReward existente o nuevo
        """
        result = await self.session.execute(
            select(UserReward).where(
                UserReward.user_id == user_id,
                UserReward.reward_id == reward_id
            )
        )
        user_reward = result.scalar_one_or_none()

        if user_reward is None:
            user_reward = UserReward(
                user_id=user_id,
                reward_id=reward_id,
                status=RewardStatus.LOCKED
            )
            self.session.add(user_reward)
            await self.session.flush()
            self.logger.debug(
                f"Created UserReward record for user {user_id}, reward {reward_id}"
            )

        return user_reward

    async def _update_user_reward_status(
        self,
        user_id: int,
        reward: Reward,
        is_eligible: bool
    ) -> str:
        """
        Actualiza el estado de UserReward basado en elegibilidad.

        Args:
            user_id: ID del usuario
            reward: Recompensa evaluada
            is_eligible: Si el usuario cumple las condiciones

        Returns:
            Estado resultante: "newly_unlocked", "repeatable_available",
            "no_change", "already_claimed"
        """
        user_reward = await self._get_or_create_user_reward(user_id, reward.id)

        # If already claimed and not repeatable, check if can claim again
        if user_reward.status == RewardStatus.CLAIMED:
            if not reward.is_repeatable:
                return "already_claimed"

            # For repeatable rewards, check if eligible again
            if is_eligible:
                # Check if conditions were met after last claim
                if user_reward.last_claimed_at and user_reward.unlocked_at:
                    if user_reward.unlocked_at > user_reward.last_claimed_at:
                        user_reward.status = RewardStatus.UNLOCKED
                        user_reward.expires_at = datetime.utcnow() + timedelta(
                            hours=reward.claim_window_hours
                        )
                        await self.session.flush()
                        return "repeatable_available"
            return "no_change"

        # If expired, check if can unlock again
        if user_reward.status == RewardStatus.EXPIRED:
            if is_eligible:
                user_reward.status = RewardStatus.UNLOCKED
                user_reward.unlocked_at = datetime.utcnow()
                user_reward.expires_at = datetime.utcnow() + timedelta(
                    hours=reward.claim_window_hours
                )
                await self.session.flush()
                return "newly_unlocked"
            return "no_change"

        # If locked and now eligible -> unlock
        if user_reward.status == RewardStatus.LOCKED and is_eligible:
            user_reward.status = RewardStatus.UNLOCKED
            user_reward.unlocked_at = datetime.utcnow()
            user_reward.expires_at = datetime.utcnow() + timedelta(
                hours=reward.claim_window_hours
            )
            await self.session.flush()
            self.logger.info(
                f"User {user_id} unlocked reward {reward.id}: {reward.name}"
            )
            return "newly_unlocked"

        # If unlocked but no longer eligible -> lock (unless already claimed)
        if user_reward.status == RewardStatus.UNLOCKED and not is_eligible:
            # Don't re-lock if it was a repeatable that was claimed
            if user_reward.claim_count > 0:
                user_reward.status = RewardStatus.LOCKED
                user_reward.expires_at = None
                await self.session.flush()
                return "no_change"

        return "no_change"

    async def check_rewards_on_event(
        self,
        user_id: int,
        event_type: str,
        event_data: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Verifica recompensas cuando ocurre un evento.

        Args:
            user_id: ID del usuario
            event_type: Tipo de evento ocurrido
            event_data: Datos adicionales del evento (opcional)

        Returns:
            Lista de recompensas recién desbloqueadas
        """
        unlocked_rewards = []

        # Get rewards that could be affected by this event
        rewards = await self._get_rewards_for_event(event_type)

        for reward in rewards:
            # Evaluate conditions
            is_eligible, passed, failed = await self.evaluate_reward_conditions(
                user_id, reward
            )

            # Update status
            status_result = await self._update_user_reward_status(
                user_id, reward, is_eligible
            )

            if status_result in ("newly_unlocked", "repeatable_available"):
                unlocked_rewards.append({
                    "reward": reward,
                    "status_result": status_result,
                    "passed_conditions": passed,
                    "event_type": event_type
                })

        if unlocked_rewards:
            self.logger.info(
                f"User {user_id} unlocked {len(unlocked_rewards)} rewards on {event_type}"
            )

        return unlocked_rewards

    # ===== REWARD CLAIMING =====

    async def _apply_reward_cap(
        self,
        reward_type: RewardType,
        reward_value: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Aplica límite máximo a valores de recompensa (REWARD-06).

        Args:
            reward_type: Tipo de recompensa
            reward_value: Valor original de la recompensa

        Returns:
            Tuple de (valor_capado, fue_capeado)
        """
        # Default caps (will be used if config service not available)
        max_besitos = 100
        max_vip_days = 30

        # Get caps from config service if available
        if self.wallet_service:
            try:
                # Access config through wallet service's session
                from bot.services.config import ConfigService
                config_service = ConfigService(self.session)
                max_besitos = await config_service.get_max_reward_besitos()
                max_vip_days = await config_service.get_max_reward_vip_days()
            except Exception as e:
                self.logger.debug(f"Could not load reward caps from config: {e}")

        capped_value = reward_value.copy()
        was_capped = False

        if reward_type == RewardType.BESITOS:
            original_amount = reward_value.get("amount", 0)
            if original_amount > max_besitos:
                capped_value["amount"] = max_besitos
                was_capped = True
                self.logger.info(
                    f"Reward value capped from {original_amount} to {max_besitos} besitos"
                )

        elif reward_type == RewardType.VIP_EXTENSION:
            original_days = reward_value.get("days", 0)
            if original_days > max_vip_days:
                capped_value["days"] = max_vip_days
                was_capped = True
                self.logger.info(
                    f"Reward value capped from {original_days} to {max_vip_days} days"
                )

        # CONTENT and BADGE don't have caps
        return capped_value, was_capped

    async def claim_reward(
        self,
        user_id: int,
        reward_id: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Procesa el reclamo de una recompensa.

        Args:
            user_id: ID del usuario
            reward_id: ID de la recompensa

        Returns:
            Tuple de (success: bool, message: str, details: dict)
        """
        # Get reward
        reward = await self.session.get(Reward, reward_id)
        if reward is None:
            return False, "reward_not_found", {}

        if not reward.is_active:
            return False, "reward_inactive", {}

        # Get UserReward record
        user_reward = await self._get_or_create_user_reward(user_id, reward_id)

        # Check if expired
        if user_reward.expires_at and user_reward.expires_at < datetime.utcnow():
            user_reward.status = RewardStatus.EXPIRED
            await self.session.flush()
            return False, "reward_expired", {"expires_at": user_reward.expires_at}

        # Check status
        if user_reward.status == RewardStatus.LOCKED:
            return False, "reward_locked", {}

        if user_reward.status == RewardStatus.CLAIMED and not reward.is_repeatable:
            return False, "already_claimed", {}

        # Apply reward caps
        capped_value, was_capped = await self._apply_reward_cap(
            reward.reward_type,
            reward.reward_value
        )

        # Process reward based on type
        reward_result = {}

        if reward.reward_type == RewardType.BESITOS:
            if self.wallet_service is None:
                return False, "wallet_service_not_available", {}

            amount = capped_value.get("amount", 0)
            success, msg, transaction = await self.wallet_service.earn_besitos(
                user_id=user_id,
                amount=amount,
                transaction_type=TransactionType.EARN_REWARD,
                reason=f"Reward claim: {reward.name}",
                metadata={"reward_id": reward_id, "was_capped": was_capped}
            )

            if not success:
                return False, f"wallet_error: {msg}", {}

            reward_result = {"amount": amount, "transaction_id": transaction.id}

        elif reward.reward_type == RewardType.CONTENT:
            content_set_id = capped_value.get("content_set_id")
            if content_set_id:
                # Create UserContentAccess record
                access = UserContentAccess(
                    user_id=user_id,
                    content_set_id=content_set_id,
                    access_type="reward_claim",
                    besitos_paid=0,
                    access_metadata={"reward_id": reward_id, "reward_name": reward.name}
                )
                self.session.add(access)
                await self.session.flush()
                reward_result = {"content_set_id": content_set_id, "access_id": access.id}

        elif reward.reward_type == RewardType.BADGE:
            badge_name = capped_value.get("badge_name", "Unknown")
            badge_emoji = capped_value.get("emoji", "🏆")
            reward_result = {"badge_name": badge_name, "emoji": badge_emoji}

        elif reward.reward_type == RewardType.VIP_EXTENSION:
            days = capped_value.get("days", 0)
            # Integrate with subscription service to extend VIP
            try:
                from bot.services.subscription import SubscriptionService
                subscription_service = SubscriptionService(self.session, None)

                # Check if user is already VIP
                existing_subscriber = await subscription_service.get_vip_subscriber(user_id)

                if existing_subscriber:
                    # Extend existing subscription
                    extension = timedelta(days=days)

                    # If expired, start from now; otherwise extend from current expiry
                    if existing_subscriber.is_expired():
                        existing_subscriber.expiry_date = datetime.utcnow() + extension
                        existing_subscriber.status = "active"
                    else:
                        existing_subscriber.expiry_date += extension

                    await self.session.flush()
                    reward_result = {
                        "days": days,
                        "new_expiry": existing_subscriber.expiry_date.isoformat(),
                        "extended": True
                    }
                    logger.info(
                        f"✅ User {user_id} VIP extended by {days} days "
                        f"(new expiry: {existing_subscriber.expiry_date})"
                    )
                else:
                    # Create new VIP subscription
                    # First create a system token for this reward-based VIP
                    from bot.database.models import InvitationToken
                    system_token = InvitationToken(
                        token=f"REWARD_{user_id}_{datetime.utcnow().timestamp()}",
                        generated_by=0,  # SYSTEM
                        duration_hours=days * 24,
                        used=True,
                        used_by=user_id,
                        used_at=datetime.utcnow()
                    )
                    self.session.add(system_token)
                    await self.session.flush()

                    expiry_date = datetime.utcnow() + timedelta(days=days)

                    from bot.database.models import VIPSubscriber
                    subscriber = VIPSubscriber(
                        user_id=user_id,
                        join_date=datetime.utcnow(),
                        expiry_date=expiry_date,
                        status="active",
                        token_id=system_token.id
                    )
                    self.session.add(subscriber)
                    await self.session.flush()

                    reward_result = {
                        "days": days,
                        "expiry": expiry_date.isoformat(),
                        "new_subscription": True
                    }
                    logger.info(
                        f"✅ User {user_id} new VIP subscription created "
                        f"({days} days, expires: {expiry_date})"
                    )

            except Exception as e:
                logger.error(f"❌ Error extending VIP for user {user_id}: {e}")
                return False, f"vip_extension_error: {str(e)}", {}

        # Update UserReward
        user_reward.status = RewardStatus.CLAIMED
        user_reward.claimed_at = datetime.utcnow()
        user_reward.claim_count += 1
        user_reward.last_claimed_at = datetime.utcnow()

        # For repeatable rewards, reset to LOCKED if conditions still met
        if reward.is_repeatable:
            is_eligible, _, _ = await self.evaluate_reward_conditions(user_id, reward)
            if is_eligible:
                user_reward.status = RewardStatus.UNLOCKED
                user_reward.unlocked_at = datetime.utcnow()
                user_reward.expires_at = datetime.utcnow() + timedelta(
                    hours=reward.claim_window_hours
                )
            else:
                user_reward.status = RewardStatus.LOCKED
                user_reward.expires_at = None

        await self.session.flush()

        self.logger.info(
            f"User {user_id} claimed reward {reward_id}: {reward.name} "
            f"(type: {reward.reward_type.value})"
        )

        return True, "reward_claimed", {
            "reward": reward,
            "user_reward": user_reward,
            "reward_result": reward_result,
            "was_capped": was_capped
        }

    async def get_available_rewards(
        self,
        user_id: int,
        include_secret: bool = False
    ) -> List[Tuple[Reward, UserReward, Dict]]:
        """
        Obtiene recompensas disponibles para un usuario.

        Args:
            user_id: ID del usuario
            include_secret: Si incluir recompensas secretas bloqueadas

        Returns:
            Lista de tuplas (reward, user_reward, progress_info)
        """
        # Get all active rewards
        result = await self.session.execute(
            select(Reward).where(Reward.is_active == True)
        )
        rewards = result.scalars().all()

        available = []
        for reward in rewards:
            user_reward = await self._get_or_create_user_reward(user_id, reward.id)

            # Filter secret rewards
            if reward.is_secret and user_reward.status == RewardStatus.LOCKED:
                if not include_secret:
                    continue

            # Get progress info
            progress_info = await self.get_reward_progress(user_id, reward.id)

            available.append((reward, user_reward, progress_info))

        # Sort by status (unlocked first), then by sort_order
        status_order = {
            RewardStatus.UNLOCKED: 0,
            RewardStatus.LOCKED: 1,
            RewardStatus.CLAIMED: 2,
            RewardStatus.EXPIRED: 3
        }
        available.sort(key=lambda x: (
            status_order.get(x[1].status, 99),
            x[0].sort_order
        ))

        return available

    async def get_reward_progress(
        self,
        user_id: int,
        reward_id: int
    ) -> Dict[int, Dict[str, Any]]:
        """
        Obtiene progreso de un usuario hacia una recompensa.

        Args:
            user_id: ID del usuario
            reward_id: ID de la recompensa

        Returns:
            Dict con progreso por condición: {condition_id: {current, required, passed}}
        """
        reward = await self.session.get(Reward, reward_id)
        if reward is None:
            return {}

        # Get conditions using async query
        result = await self.session.execute(
            select(RewardCondition).where(RewardCondition.reward_id == reward_id)
        )
        conditions = result.scalars().all()

        progress = {}

        for condition in conditions:
            # Get current value based on condition type
            current = None

            if condition.condition_type.requires_value:
                result = await self.session.execute(
                    select(UserGamificationProfile).where(
                        UserGamificationProfile.user_id == user_id
                    )
                )
                profile = result.scalar_one_or_none()

                if profile:
                    if condition.condition_type == RewardConditionType.STREAK_LENGTH:
                        if self.streak_service:
                            streak_info = await self.streak_service.get_streak_info(
                                user_id, StreakType.DAILY_GIFT
                            )
                            current = streak_info.get("current_streak", 0)
                    elif condition.condition_type == RewardConditionType.TOTAL_POINTS:
                        current = profile.total_earned
                    elif condition.condition_type == RewardConditionType.LEVEL_REACHED:
                        current = profile.level
                    elif condition.condition_type == RewardConditionType.BESITOS_SPENT:
                        current = profile.total_spent

            # Evaluate condition
            passed, _ = await self.evaluate_single_condition(user_id, condition)

            progress[condition.id] = {
                "current": current,
                "required": condition.condition_value,
                "passed": passed,
                "condition_type": condition.condition_type.value
            }

        return progress

    # ===== GROUPED NOTIFICATION BUILDER =====

    def build_reward_notification(
        self,
        unlocked_rewards: List[Dict[str, Any]],
        event_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Construye una notificación agrupada de recompensas desbloqueadas.

        Args:
            unlocked_rewards: Lista de recompensas desbloqueadas
            event_context: Contexto del evento (daily_gift, purchase, etc.)

        Returns:
            Dict con texto formateado, lista de recompensas y acción primaria
        """
        if not unlocked_rewards:
            return {"text": "", "rewards": [], "primary_action": "none"}

        rewards = [r["reward"] for r in unlocked_rewards]
        count = len(rewards)

        # Build message with Lucien's voice (🎩)
        if count == 1:
            reward = rewards[0]
            text = f"🎩 <b>Excelente</b>\n\n"
            text += f"Ha desbloqueado una recompensa:\n\n"
            text += self.format_reward_summary(reward, RewardStatus.UNLOCKED)
        else:
            text = f"🎩 <b>¡Qué jornada!</b>\n\n"
            text += f"Ha desbloqueado <b>{count}</b> recompensas:\n\n"
            for reward in rewards:
                text += self.format_reward_summary(reward, RewardStatus.UNLOCKED)
                text += "\n"

        # Add context-specific message
        if event_context:
            context_messages = {
                "daily_gift": "\n<i>Su constancia tiene su recompensa.</i>",
                "purchase": "\n<i>Su adquisición abre nuevas puertas.</i>",
                "level_up": "\n<i>Su progreso es notable.</i>",
                "reaction_added": "\n<i>Su participación no pasa desapercibida.</i>",
                "streak_updated": "\n<i>Su racha continúa...</i>"
            }
            text += context_messages.get(event_context, "")

        # Add claim instruction
        text += "\n\n<i>Toque 'Reclamar' para recibir sus recompensas.</i>"

        return {
            "text": text,
            "rewards": [
                {
                    "id": r.id,
                    "name": r.name,
                    "type": r.reward_type.value,
                    "emoji": r.reward_type.emoji
                }
                for r in rewards
            ],
            "primary_action": "claim"
        }

    def format_reward_summary(
        self,
        reward: Reward,
        status: RewardStatus
    ) -> str:
        """
        Formatea una recompensa individual para mostrar.

        Args:
            reward: Recompensa a formatear
            status: Estado de la recompensa

        Returns:
            Texto formateado
        """
        emoji = reward.reward_type.emoji
        name = reward.name
        status_emoji = status.emoji

        summary = f"{emoji} <b>{name}</b> {status_emoji}\n"

        if reward.description:
            summary += f"   <i>{reward.description[:50]}...</i>\n" if len(reward.description) > 50 else f"   <i>{reward.description}</i>\n"

        # Add reward value info
        if reward.reward_type == RewardType.BESITOS:
            amount = reward.reward_value.get("amount", 0)
            summary += f"   💰 +{amount} besitos\n"
        elif reward.reward_type == RewardType.VIP_EXTENSION:
            days = reward.reward_value.get("days", 0)
            summary += f"   ⭐ +{days} días VIP\n"
        elif reward.reward_type == RewardType.CONTENT:
            summary += f"   🎁 Contenido exclusivo\n"
        elif reward.reward_type == RewardType.BADGE:
            badge_emoji = reward.reward_value.get("emoji", "🏆")
            summary += f"   {badge_emoji} Insignia\n"

        return summary

    async def get_user_reward_stats(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de recompensas de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Dict con estadísticas
        """
        result = await self.session.execute(
            select(
                UserReward.status,
                func.count(UserReward.id).label("count")
            ).where(
                UserReward.user_id == user_id
            ).group_by(UserReward.status)
        )
        status_counts = {row.status: row.count for row in result.all()}

        # Count by type (claimed rewards only)
        type_result = await self.session.execute(
            select(
                Reward.reward_type,
                func.count(UserReward.id).label("count")
            ).join(
                UserReward, UserReward.reward_id == Reward.id
            ).where(
                UserReward.user_id == user_id,
                UserReward.claim_count > 0
            ).group_by(Reward.reward_type)
        )
        type_counts = {row.reward_type.value: row.count for row in type_result.all()}

        total_unlocked = sum(
            count for status, count in status_counts.items()
            if status in (RewardStatus.UNLOCKED, RewardStatus.CLAIMED)
        )

        return {
            "total_unlocked": total_unlocked,
            "total_claimed": status_counts.get(RewardStatus.CLAIMED, 0),
            "total_expired": status_counts.get(RewardStatus.EXPIRED, 0),
            "currently_unlocked": status_counts.get(RewardStatus.UNLOCKED, 0),
            "by_type": type_counts
        }
