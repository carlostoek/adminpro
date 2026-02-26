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
