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
