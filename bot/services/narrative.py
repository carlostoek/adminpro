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

from bot.database.models import Story, StoryNode, StoryChoice, UserStoryProgress, User
from bot.database.enums import StoryStatus, NodeType, StoryProgressStatus

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

    def __init__(self, session: AsyncSession):
        """
        Inicializa el servicio.

        Args:
            session: Sesion de base de datos SQLAlchemy async
        """
        self.session = session
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

        # Base query: solo historias publicadas
        query = select(Story).where(Story.status == StoryStatus.PUBLISHED)

        # Filtrar por premium si el usuario no es premium
        if not is_premium_user:
            query = query.where(Story.is_premium == False)

        # Ordenar por fecha de creacion (mas recientes primero)
        query = query.order_by(Story.created_at.desc())

        # Contar total antes de aplicar limit/offset
        count_query = select(func.count(Story.id)).where(
            Story.status == StoryStatus.PUBLISHED
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
                    Story.status == StoryStatus.PUBLISHED
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
