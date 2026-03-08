"""
Narrative Service - Operaciones de usuario para historias interactivas.

Responsabilidades:
- Listar historias disponibles por tier de usuario (get_available_stories)
- Iniciar o reanudar historias (start_story)
- Obtener nodo actual con opciones (get_current_node)
- Procesar elecciones y avanzar historias (make_choice)
- Consultar progreso de usuario (get_story_progress)
- Abandonar historias (abandon_story)

Patron: Dual-track persistence - FSM para estado UI, base de datos para progreso.
El progreso se persiste inmediatamente despues de cada eleccion.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Story, StoryNode, StoryChoice, UserStoryProgress, User, Transaction
from bot.database.enums import StoryStatus, NodeType, StoryProgressStatus, TransactionType

logger = logging.getLogger(__name__)


class NarrativeService:
    """
    Servicio para operaciones de usuario en historias interactivas.

    Proporciona la API core para que usuarios descubran, inicien y progresen
    a traves de historias ramificadas. Implementa el patron de persistencia
    dual donde el progreso se guarda en base de datos inmediatamente despues
    de cada eleccion.

    Metodos principales:
    1. get_available_stories: Lista historias disponibles segun tier
    2. start_story: Inicia o reanuda una historia
    3. get_current_node: Obtiene nodo actual con opciones activas
    4. make_choice: Procesa eleccion y avanza (persistencia inmediata)
    5. get_story_progress: Consulta progreso de usuario en historia
    6. abandon_story: Marca historia como abandonada

    Transaction Handling:
    - Los metodos NO hacen commit
    - El handler gestiona la transaccion con SessionContextManager
    - Sigue patron de ContentService y SubscriptionService
    """

    def __init__(
        self,
        session: AsyncSession,
        wallet_service=None,
        reward_service=None,
        shop_service=None,
        streak_service=None
    ):
        """
        Inicializa el servicio.

        Args:
            session: Sesion de base de datos SQLAlchemy async
            wallet_service: WalletService opcional para operaciones de economia
            reward_service: RewardService opcional para reclamar recompensas
            shop_service: ShopService opcional para verificar productos
            streak_service: StreakService opcional para verificar rachas
        """
        self.session = session
        self.wallet_service = wallet_service
        self.reward_service = reward_service
        self.shop_service = shop_service
        self.streak_service = streak_service
        logger.debug("NarrativeService inicializado")

    async def get_available_stories(
        self,
        user_tier: int = 1,
        is_premium_user: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Story], int]:
        """
        Retorna historias disponibles para un usuario segun su tier.

        Filtra historias publicadas y aplica restriccion de premium.
        Las historias premium solo son visibles para usuarios premium.

        Args:
            user_tier: Nivel del usuario (1-6, afecta ordenamiento futuro)
            is_premium_user: True si el usuario tiene acceso premium
            limit: Maximo de resultados (default: 50)
            offset: Desplazamiento para paginacion (default: 0)

        Returns:
            Tuple[List[Story], int] - (lista de historias, total count)
        """
        logger.debug(
            f"Fetching available stories for tier={user_tier}, premium={is_premium_user}"
        )

        # Base query: solo historias publicadas y activas
        query = select(Story).where(
            and_(
                Story.status == StoryStatus.PUBLISHED,
                Story.is_active == True
            )
        )

        # Filtrar por premium si el usuario no es premium
        if not is_premium_user:
            query = query.where(Story.is_premium == False)

        # Ordenar por fecha de creacion (mas recientes primero)
        query = query.order_by(Story.created_at.desc())

        # Contar total antes de aplicar limit/offset
        count_query = select(func.count(Story.id)).where(
            and_(
                Story.status == StoryStatus.PUBLISHED,
                Story.is_active == True
            )
        )
        if not is_premium_user:
            count_query = count_query.where(Story.is_premium == False)

        # Ejecutar conteo
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Aplicar paginacion
        query = query.limit(limit).offset(offset)

        # Ejecutar query principal
        result = await self.session.execute(query)
        stories = list(result.scalars().all())

        logger.info(f"Found {len(stories)} available stories (total: {total})")

        return (stories, total)

    async def start_story(
        self,
        user_id: int,
        story_id: int
    ) -> Tuple[bool, str, Optional[UserStoryProgress]]:
        """
        Inicia una nueva historia para un usuario o reanuda progreso existente.

        Si el usuario ya tiene progreso:
        - ACTIVE o PAUSED: Retorna el progreso existente (reanudar)
        - COMPLETED: Retorna error (historia ya completada)

        Si no tiene progreso:
        - Verifica que la historia exista y este publicada
        - Busca el nodo START de la historia
        - Crea nuevo UserStoryProgress en estado ACTIVE

        Args:
            user_id: ID del usuario
            story_id: ID de la historia

        Returns:
            Tuple[bool, str, Optional[UserStoryProgress]]:
            - (True, "Story started", progress) - Nueva historia iniciada
            - (True, "Resuming story", progress) - Reanudando historia
            - (False, "Story already completed", progress) - Ya completada
            - (False, "Story not found or not published", None) - No disponible
            - (False, "Story has no start node", None) - Sin nodo inicial
        """
        logger.info(f"Starting story {story_id} for user {user_id}")

        # 1. Verificar si ya existe progreso para este usuario/historia
        existing_progress = await self.get_story_progress(user_id, story_id)

        if existing_progress:
            if existing_progress.status == StoryProgressStatus.COMPLETED:
                logger.info(f"User {user_id} already completed story {story_id}")
                return (False, "Story already completed", existing_progress)
            elif existing_progress.status in (StoryProgressStatus.ACTIVE, StoryProgressStatus.PAUSED):
                logger.info(f"Resuming story {story_id} for user {user_id}")
                # Actualizar a ACTIVE si estaba PAUSED
                if existing_progress.status == StoryProgressStatus.PAUSED:
                    existing_progress.status = StoryProgressStatus.ACTIVE
                    existing_progress.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                return (True, "Resuming story", existing_progress)
            elif existing_progress.status == StoryProgressStatus.ABANDONED:
                # Reactivar historia abandonada
                logger.info(f"Reactivating abandoned story {story_id} for user {user_id}")
                existing_progress.status = StoryProgressStatus.ACTIVE
                existing_progress.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                return (True, "Resuming story", existing_progress)

        # 2. No existe progreso - verificar que la historia exista y este publicada
        story_result = await self.session.execute(
            select(Story).where(
                and_(
                    Story.id == story_id,
                    Story.status == StoryStatus.PUBLISHED,
                    Story.is_active == True
                )
            )
        )
        story = story_result.scalar_one_or_none()

        if not story:
            logger.error(f"Story {story_id} not found or not published")
            return (False, "Story not found or not published", None)

        # 3. Buscar el nodo START de la historia
        start_node_result = await self.session.execute(
            select(StoryNode).where(
                and_(
                    StoryNode.story_id == story_id,
                    StoryNode.node_type == NodeType.START,
                    StoryNode.is_active == True
                )
            )
        )
        start_node = start_node_result.scalar_one_or_none()

        if not start_node:
            logger.error(f"Story {story_id} has no start node")
            return (False, "Story has no start node", None)

        # 4. Crear nuevo progreso
        progress = UserStoryProgress(
            user_id=user_id,
            story_id=story_id,
            current_node_id=start_node.id,
            status=StoryProgressStatus.ACTIVE,
            decisions_made=[],
            started_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )

        self.session.add(progress)

        logger.info(f"Story {story_id} started for user {user_id}")

        return (True, "Story started", progress)

    async def get_current_node(
        self,
        progress: UserStoryProgress
    ) -> Tuple[bool, str, Optional[StoryNode], List[StoryChoice]]:
        """
        Obtiene el nodo actual con sus opciones disponibles para un usuario.

        Usa eager loading para cargar las opciones del nodo y evitar N+1 queries.
        Filtra solo las opciones activas.

        Args:
            progress: Registro de progreso del usuario

        Returns:
            Tuple[bool, str, Optional[StoryNode], List[StoryChoice]]:
            - (True, "Node retrieved", node, active_choices) - Exito
            - (False, "No current node", None, []) - Sin nodo actual
            - (False, "Node not found", None, []) - Nodo no existe
        """
        user_id = progress.user_id
        node_id = progress.current_node_id

        # 1. Verificar que hay un nodo actual
        if node_id is None:
            logger.debug(f"No current node for user {user_id}")
            return (False, "No current node", None, [])

        logger.debug(f"Getting current node {node_id} for user {user_id}")

        # 2. Query con eager loading de opciones
        result = await self.session.execute(
            select(StoryNode)
            .where(StoryNode.id == node_id)
            .options(selectinload(StoryNode.choices))
        )
        node = result.scalar_one_or_none()

        # 3. Verificar que el nodo existe
        if not node:
            logger.warning(f"Node {node_id} not found for user {user_id}")
            return (False, "Node not found", None, [])

        # 4. Filtrar opciones activas
        active_choices = [c for c in node.choices if c.is_active]

        logger.debug(f"Node has {len(active_choices)} active choices")

        return (True, "Node retrieved", node, active_choices)

    async def make_choice(
        self,
        user_id: int,
        progress: UserStoryProgress,
        choice_id: int
    ) -> Tuple[bool, str, Optional[StoryNode], Optional[UserStoryProgress]]:
        """
        Procesa la eleccion de un usuario y avanza la historia.

        Persiste el progreso inmediatamente (aunque el commit real lo hace el handler).
        Actualiza: historial de decisiones, nodo actual, estado si llega a un final.

        Args:
            user_id: ID del usuario (para verificacion de propiedad)
            progress: Registro de progreso del usuario
            choice_id: ID de la opcion elegida

        Returns:
            Tuple[bool, str, Optional[StoryNode], Optional[UserStoryProgress]]:
            - (True, "Choice made", target_node, progress) - Exito
            - (True, "Story completed", target_node, progress) - Llego a un final
            - (False, "Invalid choice", None, None) - Opcion invalida
            - (False, "Progress belongs to different user", None, None) - Error de seguridad
        """
        # 1. Verificar que el progreso pertenece al usuario
        if progress.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to access progress belonging to {progress.user_id}"
            )
            return (False, "Progress belongs to different user", None, None)

        # 2. Fetch la opcion con eager loading del nodo destino
        result = await self.session.execute(
            select(StoryChoice)
            .where(StoryChoice.id == choice_id)
            .options(selectinload(StoryChoice.target_node))
        )
        choice = result.scalar_one_or_none()

        # 3. Validar la opcion
        if not choice:
            logger.warning(f"Choice {choice_id} not found for user {user_id}")
            return (False, "Invalid choice", None, None)

        if not choice.is_active:
            logger.warning(f"Choice {choice_id} is not active for user {user_id}")
            return (False, "Invalid choice", None, None)

        if choice.source_node_id != progress.current_node_id:
            logger.warning(
                f"Choice {choice_id} does not belong to current node "
                f"{progress.current_node_id} for user {user_id}"
            )
            return (False, "Invalid choice", None, None)

        # 4. Registrar la decision
        decision_record = {
            "choice_id": choice_id,
            "node_id": progress.current_node_id,
            "made_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        }

        if progress.decisions_made is None:
            progress.decisions_made = []
        progress.decisions_made.append(decision_record)

        # 5. Avanzar al nodo destino
        target_node = choice.target_node
        progress.current_node_id = choice.target_node_id

        # 6. Verificar si llego a un final
        if target_node and target_node.node_type == NodeType.ENDING:
            progress.status = StoryProgressStatus.COMPLETED
            progress.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            progress.ending_reached = f"ending_{target_node.id}"
            logger.info(
                f"User {user_id} completed story {progress.story_id}, "
                f"ending: ending_{target_node.id}"
            )

        # 7. Actualizar timestamp
        progress.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # 8. Marcar como modificado (el handler hara el commit)
        # SQLAlchemy detecta automaticamente los cambios en objetos attached

        logger.info(
            f"User {user_id} made choice {choice_id} in story {progress.story_id}"
        )

        return (True, "Choice made", target_node, progress)

    async def get_story_progress(
        self,
        user_id: int,
        story_id: int
    ) -> Optional[UserStoryProgress]:
        """
        Obtiene el progreso de un usuario en una historia especifica.

        Args:
            user_id: ID del usuario
            story_id: ID de la historia

        Returns:
            UserStoryProgress si existe, None si no tiene progreso
        """
        result = await self.session.execute(
            select(UserStoryProgress).where(
                and_(
                    UserStoryProgress.user_id == user_id,
                    UserStoryProgress.story_id == story_id
                )
            )
        )
        progress = result.scalar_one_or_none()

        if progress:
            logger.debug(
                f"Progress found for user {user_id} in story {story_id}: "
                f"{progress.status.value}"
            )
        else:
            logger.debug(f"No progress for user {user_id} in story {story_id}")

        return progress

    async def abandon_story(
        self,
        user_id: int,
        progress: UserStoryProgress
    ) -> Tuple[bool, str]:
        """
        Marca una historia como abandonada por el usuario.

        No se puede abandonar una historia completada.

        Args:
            user_id: ID del usuario (para verificacion)
            progress: Registro de progreso a abandonar

        Returns:
            Tuple[bool, str]:
            - (True, "Story abandoned") - Exito
            - (False, "Cannot abandon completed story") - Ya completada
            - (False, "Progress belongs to different user") - Error de seguridad
        """
        # 1. Verificar que el progreso pertenece al usuario
        if progress.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to abandon progress belonging to "
                f"{progress.user_id}"
            )
            return (False, "Progress belongs to different user")

        # 2. Verificar que no este completada
        if progress.status == StoryProgressStatus.COMPLETED:
            logger.info(
                f"User {user_id} attempted to abandon completed story "
                f"{progress.story_id}"
            )
            return (False, "Cannot abandon completed story")

        # 3. Marcar como abandonada
        progress.status = StoryProgressStatus.ABANDONED
        progress.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        logger.info(f"User {user_id} abandoned story {progress.story_id}")

        return (True, "Story abandoned")

    # ===== CHOICE CONDITION EVALUATION =====

    async def evaluate_choice_conditions(
        self,
        user_id: int,
        choice: StoryChoice
    ) -> Tuple[bool, List[str]]:
        """
        Evalua si un usuario puede acceder a una eleccion basada en sus condiciones.

        Parsea choice.conditions JSON (lista de objetos de condicion) y evalua
        usando logica AND/OR en cascada.

        Args:
            user_id: ID del usuario
            choice: StoryChoice con condiciones a evaluar

        Returns:
            Tuple[bool, List[str]]: (puede_acceder, requisitos_faltantes)

        Condition types supported:
            - level: Nivel requerido (usa wallet_service para verificar nivel)
            - streak: Racha de dias requerida (usa streak_service)
            - product_owned: Producto de tienda requerido (usa shop_service)
            - total_earned: Besitos totales ganados requeridos (usa wallet_service)
        """
        # Si no hay condiciones, la eleccion es accesible
        if not choice.conditions:
            return True, []

        missing_requirements = []

        try:
            conditions = choice.conditions if isinstance(choice.conditions, list) else []
        except (TypeError, ValueError):
            logger.warning(f"Invalid conditions format for choice {choice.id}")
            return True, []

        # Group conditions by condition_group (0 = AND, 1+ = OR)
        groups: Dict[int, List[Dict]] = {}
        for condition in conditions:
            group = condition.get("condition_group", 0)
            if group not in groups:
                groups[group] = []
            groups[group].append(condition)

        # Evaluate group 0 (AND logic - all must pass)
        group_0_passed = True
        if 0 in groups:
            for condition in groups[0]:
                passed, requirement = await self._evaluate_single_condition(
                    user_id, condition
                )
                if not passed:
                    group_0_passed = False
                    if requirement:
                        missing_requirements.append(requirement)

        # Evaluate groups 1+ (OR logic - at least one in each group must pass)
        all_or_groups_passed = True
        for group_id in sorted(groups.keys()):
            if group_id == 0:
                continue

            group_conditions = groups[group_id]
            if not group_conditions:
                continue

            group_has_passing = False
            group_requirements = []

            for condition in group_conditions:
                passed, requirement = await self._evaluate_single_condition(
                    user_id, condition
                )
                if passed:
                    group_has_passing = True
                    break
                elif requirement:
                    group_requirements.append(requirement)

            if not group_has_passing:
                all_or_groups_passed = False
                missing_requirements.extend(group_requirements)

        can_access = group_0_passed and all_or_groups_passed

        return can_access, missing_requirements

    async def _evaluate_single_condition(
        self,
        user_id: int,
        condition: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Evalua una sola condicion para un usuario.

        Args:
            user_id: ID del usuario
            condition: Dict con condition_type y condition_value

        Returns:
            Tuple[bool, Optional[str]]: (paso, mensaje_requisito)
        """
        condition_type = condition.get("condition_type")
        condition_value = condition.get("condition_value")

        if not condition_type:
            return True, None

        try:
            if condition_type == "level":
                return await self._check_level_condition(user_id, condition_value)
            elif condition_type == "streak":
                return await self._check_streak_condition(user_id, condition_value)
            elif condition_type == "product_owned":
                return await self._check_product_condition(user_id, condition_value)
            elif condition_type == "total_earned":
                return await self._check_total_earned_condition(user_id, condition_value)
            else:
                logger.debug(f"Unknown condition type: {condition_type}")
                return True, None
        except Exception as e:
            logger.error(f"Error evaluating condition {condition_type}: {e}")
            return True, None  # Fail open to not block users

    async def _check_level_condition(
        self,
        user_id: int,
        required_level: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Verifica condicion de nivel."""
        if required_level is None or required_level <= 1:
            return True, None

        if self.wallet_service is None:
            return True, None

        try:
            current_level = await self.wallet_service.get_user_level(user_id)
            if current_level >= required_level:
                return True, None
            return False, f"nivel {required_level}"
        except Exception as e:
            logger.error(f"Error checking level for user {user_id}: {e}")
            return True, None

    async def _check_streak_condition(
        self,
        user_id: int,
        required_streak: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Verifica condicion de racha."""
        if required_streak is None or required_streak <= 0:
            return True, None

        if self.streak_service is None:
            return True, None

        try:
            from bot.database.enums import StreakType
            streak_info = await self.streak_service.get_streak_info(
                user_id, StreakType.DAILY_GIFT
            )
            current_streak = streak_info.get("current_streak", 0)
            if current_streak >= required_streak:
                return True, None
            return False, f"racha {required_streak} dias"
        except Exception as e:
            logger.error(f"Error checking streak for user {user_id}: {e}")
            return True, None

    async def _check_product_condition(
        self,
        user_id: int,
        product_id: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Verifica condicion de producto poseido."""
        if product_id is None:
            return True, None

        if self.shop_service is None:
            return True, None

        try:
            # Check if user has purchased this product
            has_product = await self.shop_service.has_user_purchased(user_id, product_id)
            if has_product:
                return True, None
            return False, "producto especifico"
        except Exception as e:
            logger.error(f"Error checking product for user {user_id}: {e}")
            return True, None

    async def _check_total_earned_condition(
        self,
        user_id: int,
        required_total: Optional[int]
    ) -> Tuple[bool, Optional[str]]:
        """Verifica condicion de besitos totales ganados."""
        if required_total is None or required_total <= 0:
            return True, None

        if self.wallet_service is None:
            return True, None

        try:
            profile = await self.wallet_service.get_profile(user_id)
            if profile is None:
                return False, f"{required_total} besitos ganados"
            if profile.total_earned >= required_total:
                return True, None
            return False, f"{required_total} besitos ganados"
        except Exception as e:
            logger.error(f"Error checking total earned for user {user_id}: {e}")
            return True, None

    async def calculate_choice_cost(
        self,
        choice: StoryChoice,
        user_role: str
    ) -> int:
        """
        Calcula el costo para un usuario de hacer esta eleccion.

        Args:
            choice: StoryChoice a evaluar
            user_role: Rol del usuario ("VIP", "FREE", etc.)

        Returns:
            int: Costo en besitos

        Logic:
            - Si user_role == "VIP" y choice.vip_cost_besitos no es None,
              retorna vip_cost_besitos
            - De lo contrario, retorna choice.cost_besitos
        """
        if user_role == "VIP" and choice.vip_cost_besitos is not None:
            return choice.vip_cost_besitos
        return choice.cost_besitos

    def _format_requirement_message(self, missing: List[str]) -> str:
        """
        Formatea requisitos faltantes en mensaje amigable para el usuario.

        Usa la voz de Lucien (formal, elegante).

        Args:
            missing: Lista de requisitos faltantes

        Returns:
            str: Mensaje formateado
        """
        if not missing:
            return ""

        if len(missing) == 1:
            return f"Necesita: {missing[0]}"

        # Join with " Y " for multiple requirements
        requirements_text = " Y ".join(missing)
        return f"Necesita: {requirements_text}"

    # ===== CHOICE COST PROCESSING =====

    async def _deliver_node_rewards(
        self,
        user_id: int,
        node: StoryNode
    ) -> Tuple[bool, List[Dict]]:
        """
        Entrega las recompensas asociadas a un nodo cuando el usuario lo alcanza.

        Consulta node.attached_rewards, verifica que cada recompensa este activa
        y no haya sido reclamada previamente (para recompensas no repetibles),
        y llama a reward_service.claim_reward() para entregarlas.

        Args:
            user_id: ID del usuario
            node: StoryNode alcanzado

        Returns:
            Tuple[bool, List[Dict]]:
            - all_delivered: True si todas las recompensas se entregaron
            - results: Lista de dicts con reward_id, reward_name, success, message, details
        """
        # 1. Si no hay recompensas o reward_service no disponible, retornar vacio
        if not node.attached_rewards or self.reward_service is None:
            return True, []

        results = []
        all_delivered = True

        # 2. Iterar sobre las recompensas adjuntas al nodo
        for node_reward in node.attached_rewards:
            # Saltar si no esta activa
            if not node_reward.is_active:
                continue

            reward = node_reward.reward
            if not reward or not reward.is_active:
                continue

            # 3. Verificar si ya fue reclamada (previene replay farming)
            # Para recompensas no repetibles, verificar claim_count
            if not reward.is_repeatable:
                from bot.database.models import UserReward
                from bot.database.enums import RewardStatus

                user_reward_result = await self.session.execute(
                    select(UserReward).where(
                        UserReward.user_id == user_id,
                        UserReward.reward_id == reward.id
                    )
                )
                user_reward = user_reward_result.scalar_one_or_none()

                if user_reward and user_reward.claim_count > 0:
                    # Ya fue reclamada, saltar
                    results.append({
                        "reward_id": reward.id,
                        "reward_name": reward.name,
                        "success": False,
                        "message": "already_claimed",
                        "details": {"claim_count": user_reward.claim_count}
                    })
                    continue

            # 4. Intentar reclamar la recompensa
            try:
                success, msg, details = await self.reward_service.claim_reward(
                    user_id=user_id,
                    reward_id=reward.id
                )

                results.append({
                    "reward_id": reward.id,
                    "reward_name": reward.name,
                    "success": success,
                    "message": msg,
                    "details": details
                })

                if not success:
                    all_delivered = False
                    logger.warning(
                        f"Failed to deliver reward {reward.id} to user {user_id}: {msg}"
                    )
                else:
                    logger.info(
                        f"Delivered reward {reward.id} ({reward.name}) to user {user_id}"
                    )

            except Exception as e:
                logger.error(f"Error delivering reward {reward.id} to user {user_id}: {e}")
                results.append({
                    "reward_id": reward.id,
                    "reward_name": reward.name,
                    "success": False,
                    "message": f"error: {str(e)}",
                    "details": {}
                })
                all_delivered = False

        return all_delivered, results

    async def _deduct_choice_cost(
        self,
        user_id: int,
        choice: StoryChoice,
        user_role: str
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """
        Deduce el costo de una eleccion de forma atomica.

        Calcula el costo usando calculate_choice_cost(), verifica si el usuario
        tiene suficientes besitos, y realiza la deduccion atomica con registro
        de transaccion.

        Args:
            user_id: ID del usuario
            choice: StoryChoice a procesar
            user_role: Rol del usuario ("VIP", "FREE", etc.)

        Returns:
            Tuple[bool, str, Optional[Transaction]]:
            - (True, "no_cost", None) - Sin costo
            - (True, "spent", Transaction) - Deduccion exitosa
            - (False, "insufficient_funds", None) - Fondos insuficientes
            - (False, "wallet_service_unavailable", None) - Servicio no disponible
        """
        # 1. Calcular costo
        cost = await self.calculate_choice_cost(choice, user_role)

        # 2. Si no hay costo, retornar exito inmediatamente
        if cost == 0:
            return True, "no_cost", None

        # 3. Verificar que wallet_service este disponible
        if self.wallet_service is None:
            logger.warning(f"WalletService not available for choice cost deduction")
            return False, "wallet_service_unavailable", None

        # 4. Llamar a spend_besitos para deduccion atomica
        success, msg, transaction = await self.wallet_service.spend_besitos(
            user_id=user_id,
            amount=cost,
            transaction_type=TransactionType.SPEND_STORY_CHOICE,
            reason=f"Story choice #{choice.id}: {choice.choice_text[:50]}",
            metadata={
                "choice_id": choice.id,
                "source_node_id": choice.source_node_id,
                "target_node_id": choice.target_node_id,
                "user_role": user_role,
                "original_cost": choice.cost_besitos,
                "vip_cost": choice.vip_cost_besitos
            }
        )

        if success:
            logger.info(
                f"User {user_id} spent {cost} besitos for choice {choice.id} "
                f"({TransactionType.SPEND_STORY_CHOICE.value})"
            )
            return True, "spent", transaction
        else:
            logger.warning(
                f"User {user_id} failed to spend {cost} besitos for choice {choice.id}: {msg}"
            )
            return False, msg, None
