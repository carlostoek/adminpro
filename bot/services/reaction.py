"""
Reaction Service - Gestión de reacciones a contenido de canales.

Responsabilidades:
- Registrar reacciones de usuarios a contenido
- Prevenir reacciones duplicadas (mismo emoji al mismo contenido)
- Rate limiting (30 segundos entre reacciones)
- Límite diario de reacciones por usuario
- Validar acceso al contenido (VIP solo para VIP)
- Otorgar besitos por reacciones válidas

Patrones:
- Atomic operations para evitar race conditions
- Deduplication via unique constraint en DB
- Rate limiting basado en timestamp de última reacción
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserReaction, BotConfig
from bot.database.enums import TransactionType, ContentCategory, UserRole

logger = logging.getLogger(__name__)


class ReactionService:
    """
    Service para gestionar reacciones a contenido de canales.

    Flujo típico:
    1. Usuario toca botón de reacción → add_reaction()
    2. Validar acceso al contenido (VIP check)
    3. Validar rate limiting (30s cooldown)
    4. Validar límite diario
    5. Verificar duplicado
    6. Guardar reacción + otorgar besitos
    """

    # Configuración de rate limiting y límites
    REACTION_COOLDOWN_SECONDS = 30

    def __init__(self, session: AsyncSession, wallet_service=None, streak_service=None):
        """
        Inicializa el ReactionService.

        Args:
            session: Sesión de base de datos async
            wallet_service: WalletService opcional para otorgar besitos
            streak_service: StreakService opcional para tracking de rachas
        """
        self.session = session
        self.wallet = wallet_service
        self.streak = streak_service
        self.logger = logging.getLogger(__name__)

    async def _get_config_value(self, key: str, default: int) -> int:
        """
        Obtiene un valor de configuración de BotConfig.

        Args:
            key: Nombre del campo de configuración
            default: Valor por defecto si no está configurado

        Returns:
            Valor configurado o default
        """
        result = await self.session.execute(
            select(getattr(BotConfig, key)).where(BotConfig.id == 1)
        )
        value = result.scalar_one_or_none()
        return value if value is not None else default

    async def _check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Verifica si el usuario está en cooldown entre reacciones.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, int]: (puede_reaccionar, segundos_restantes)
            - True, 0: Puede reaccionar
            - False, N: Debe esperar N segundos
        """
        # Buscar última reacción del usuario
        result = await self.session.execute(
            select(UserReaction.created_at)
            .where(UserReaction.user_id == user_id)
            .order_by(UserReaction.created_at.desc())
            .limit(1)
        )
        last_reaction = result.scalar_one_or_none()

        if last_reaction is None:
            # Nunca ha reaccionado, puede hacerlo
            return True, 0

        # Calcular tiempo transcurrido
        elapsed = (datetime.utcnow() - last_reaction).total_seconds()

        if elapsed < self.REACTION_COOLDOWN_SECONDS:
            remaining = int(self.REACTION_COOLDOWN_SECONDS - elapsed)
            return False, remaining

        return True, 0

    async def _check_daily_limit(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Verifica si el usuario ha alcanzado el límite diario de reacciones.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[bool, int, int]: (puede_reaccionar, usadas_hoy, límite)
        """
        # Obtener límite configurado
        limit = await self._get_config_value('max_reactions_per_day', 20)

        # Contar reacciones de hoy
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = await self.session.execute(
            select(func.count(UserReaction.id))
            .where(
                UserReaction.user_id == user_id,
                UserReaction.created_at >= today_start
            )
        )
        count_today = result.scalar_one_or_none() or 0

        if count_today >= limit:
            return False, count_today, limit

        return True, count_today, limit

    async def _is_duplicate_reaction(
        self,
        user_id: int,
        content_id: int
    ) -> bool:
        """
        Verifica si el usuario ya reaccionó a este contenido.

        Args:
            user_id: ID del usuario
            content_id: ID del contenido

        Returns:
            True si ya existe reacción del usuario a este contenido
        """
        result = await self.session.execute(
            select(UserReaction.id)
            .where(
                UserReaction.user_id == user_id,
                UserReaction.content_id == content_id
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def validate_content_access(
        self,
        user_id: int,
        channel_id: str,
        content_category: Optional[ContentCategory] = None
    ) -> Tuple[bool, str]:
        """
        Valida si el usuario tiene acceso al contenido para reaccionar.

        Args:
            user_id: ID del usuario
            channel_id: ID del canal
            content_category: Categoría del contenido (VIP_CONTENT, FREE_CONTENT, etc)

        Returns:
            Tuple[bool, str]: (tiene_acceso, mensaje_error)
        """
        # Si es contenido VIP, verificar suscripción
        if content_category == ContentCategory.VIP_CONTENT:
            from bot.database.models import VIPSubscriber

            result = await self.session.execute(
                select(VIPSubscriber)
                .where(
                    VIPSubscriber.user_id == user_id,
                    VIPSubscriber.status == "active"
                )
            )
            subscriber = result.scalar_one_or_none()

            if subscriber is None or subscriber.is_expired():
                return False, "Este contenido es exclusivo para suscriptores VIP."

        # Contenido Free o sin categoría específica: permitir
        return True, ""

    async def add_reaction(
        self,
        user_id: int,
        content_id: int,
        channel_id: str,
        emoji: str,
        content_category: Optional[ContentCategory] = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Agrega una reacción al contenido si pasa todas las validaciones.

        Args:
            user_id: ID del usuario que reacciona
            content_id: ID del mensaje de canal
            channel_id: ID del canal
            emoji: Emoji de la reacción
            content_category: Categoría del contenido para validar acceso

        Returns:
            Tuple[bool, str, Optional[Dict]]:
                - bool: True si éxito
                - str: Mensaje descriptivo (código o texto)
                - Dict: Datos adicionales (besitos ganados, etc)

        Códigos de retorno:
            - "success": Reacción registrada, besitos otorgados
            - "duplicate": Ya reaccionó a este contenido
            - "rate_limited": Debe esperar N segundos
            - "daily_limit_reached": Límite diario alcanzado
            - "no_access": No tiene acceso al contenido (VIP)
        """
        # 1. Validar acceso al contenido
        has_access, error_msg = await self.validate_content_access(
            user_id, channel_id, content_category
        )
        if not has_access:
            return False, "no_access", {"error": error_msg}

        # 2. Validar rate limiting
        can_react, remaining = await self._check_rate_limit(user_id)
        if not can_react:
            return False, "rate_limited", {"seconds_remaining": remaining}

        # 3. Validar límite diario
        can_react_daily, used_today, limit = await self._check_daily_limit(user_id)
        if not can_react_daily:
            return False, "daily_limit_reached", {"used": used_today, "limit": limit}

        # 4. Verificar duplicado
        if await self._is_duplicate_reaction(user_id, content_id):
            return False, "duplicate", None

        try:
            # 5. Crear reacción
            reaction = UserReaction(
                user_id=user_id,
                content_id=content_id,
                channel_id=channel_id,
                emoji=emoji
            )
            self.session.add(reaction)
            await self.session.flush()

            # 6. Otorgar besitos si wallet service está disponible
            besitos_earned = 0
            if self.wallet:
                besitos_per_reaction = await self._get_config_value(
                    'besitos_per_reaction', 5
                )

                success, msg, tx = await self.wallet.earn_besitos(
                    user_id=user_id,
                    amount=besitos_per_reaction,
                    transaction_type=TransactionType.EARN_REACTION,
                    reason=f"Reacción {emoji} al contenido {content_id}",
                    metadata={
                        "content_id": content_id,
                        "channel_id": channel_id,
                        "emoji": emoji
                    }
                )

                if success:
                    besitos_earned = besitos_per_reaction
                    self.logger.info(
                        f"✅ User {user_id} earned {besitos_earned} besitos for reaction {emoji}"
                    )

                    # Track reaction streak (only for reactions that earn besitos)
                    if self.streak:
                        streak_incremented, current_streak = await self.streak.record_reaction(user_id)
                        self.logger.debug(
                            f"User {user_id} reaction streak: {current_streak} "
                            f"(incremented: {streak_incremented})"
                        )

            return True, "success", {
                "besitos_earned": besitos_earned,
                "reactions_today": used_today + 1,
                "daily_limit": limit
            }

        except Exception as e:
            self.logger.error(f"❌ Error adding reaction for user {user_id}: {e}")
            return False, "error", {"error": str(e)}

    async def get_content_reactions(
        self,
        content_id: int,
        channel_id: str
    ) -> Dict[str, int]:
        """
        Obtiene el conteo de reacciones por emoji para un contenido.

        Args:
            content_id: ID del contenido
            channel_id: ID del canal

        Returns:
            Dict[emoji, count]: Conteo de cada emoji
        """
        result = await self.session.execute(
            select(UserReaction.emoji, func.count(UserReaction.id))
            .where(
                UserReaction.content_id == content_id,
                UserReaction.channel_id == channel_id
            )
            .group_by(UserReaction.emoji)
        )

        counts = {}
        for row in result.all():
            counts[row[0]] = row[1]

        return counts

    async def get_user_reactions_today(self, user_id: int) -> Tuple[int, int]:
        """
        Obtiene estadísticas de reacciones del usuario hoy.

        Args:
            user_id: ID del usuario

        Returns:
            Tuple[int, int]: (reacciones_hoy, límite_diario)
        """
        limit = await self._get_config_value('max_reactions_per_day', 20)

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = await self.session.execute(
            select(func.count(UserReaction.id))
            .where(
                UserReaction.user_id == user_id,
                UserReaction.created_at >= today_start
            )
        )
        count_today = result.scalar_one_or_none() or 0

        return count_today, limit

    async def get_user_reactions_for_content(
        self,
        user_id: int,
        content_id: int,
        channel_id: str
    ) -> List[str]:
        """
        Obtiene lista de emojis que el usuario usó en un contenido.

        Args:
            user_id: ID del usuario
            content_id: ID del contenido
            channel_id: ID del canal

        Returns:
            Lista de emojis (ej: ["❤️", "🔥"])
        """
        result = await self.session.execute(
            select(UserReaction.emoji)
            .where(
                UserReaction.user_id == user_id,
                UserReaction.content_id == content_id,
                UserReaction.channel_id == channel_id
            )
        )

        return [row[0] for row in result.all()]
