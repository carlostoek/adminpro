"""
Story Editor Service - Gestión de historias para administradores.

Responsabilidades:
- Crear historias (create_story)
- Crear nodos de historia (create_node)
- Crear opciones de elección (create_choice)
- Validar historias antes de publicar (validate_story)
- Publicar historias (publish_story)
- Obtener estadísticas de historias (get_story_stats)

Pattern: Sigue ContentService (async, session injection, sin commits, retorna tuplas)
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any, Set

from sqlalchemy import select, and_, func, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Story, StoryNode, StoryChoice, UserStoryProgress
from bot.database.enums import StoryStatus, NodeType, StoryProgressStatus

logger = logging.getLogger(__name__)


class StoryEditorService:
    """
    Servicio para gestión de historias (administrador).

    CRUD Operations:
    1. Create: create_story(), create_node(), create_choice()
    2. Read: get_story(), get_story_stats()
    3. Update: publish_story()
    4. Validate: validate_story() - Verifica integridad antes de publicar

    Transaction Handling:
    - Los métodos NO hacen commit
    - El handler gestiona la transacción con SessionContextManager
    - Sigue patrón de ContentService
    """

    def __init__(self, session: AsyncSession):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos SQLAlchemy
        """
        self.session = session
        logger.debug("✅ StoryEditorService inicializado")

    # ===== CREATE STORY =====

    async def create_story(
        self,
        title: str,
        description: Optional[str] = None,
        is_premium: bool = False
    ) -> Tuple[bool, str, Optional[Story]]:
        """
        Crea una nueva historia.

        Args:
            title: Título de la historia (max 200 chars)
            description: Descripción opcional
            is_premium: Si es contenido premium

        Returns:
            Tuple[bool, str, Optional[Story]]: (éxito, mensaje, historia creada)
        """
        # Validar título
        if not title or not title.strip():
            return (False, "Title is required (max 200 chars)", None)

        title = title.strip()
        if len(title) > 200:
            return (False, "Title is required (max 200 chars)", None)

        # Crear historia
        story = Story(
            title=title,
            description=description.strip() if description else None,
            is_premium=is_premium,
            status=StoryStatus.DRAFT
        )

        self.session.add(story)
        # NO commit - dejar que el handler gestione la transacción

        logger.info(f"Created story '{title}' (premium={is_premium})")

        return (True, "Story created", story)

    # ===== CREATE NODE =====

    async def create_node(
        self,
        story_id: int,
        node_type: NodeType,
        content_text: Optional[str] = None,
        media_file_ids: Optional[List[str]] = None,
        tier_required: int = 1,
        order_index: int = 0
    ) -> Tuple[bool, str, Optional[StoryNode]]:
        """
        Crea un nuevo nodo en una historia.

        Args:
            story_id: ID de la historia
            node_type: Tipo de nodo (START, STORY, CHOICE, ENDING)
            content_text: Contenido del nodo
            media_file_ids: Lista de IDs de archivos multimedia
            tier_required: Tier requerido (1-6)
            order_index: Índice de orden

        Returns:
            Tuple[bool, str, Optional[StoryNode]]: (éxito, mensaje, nodo creado)
        """
        # Verificar que la historia existe
        result = await self.session.execute(
            select(Story).where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()

        if not story:
            return (False, "Story not found", None)

        # Validar contenido para nodos que requieren texto
        if node_type in (NodeType.STORY, NodeType.START, NodeType.ENDING):
            if not content_text or not content_text.strip():
                return (False, "Content text is required for this node type", None)
            if len(content_text) > 4000:
                return (False, "Content text exceeds 4000 characters", None)

        # Crear nodo
        node = StoryNode(
            story_id=story_id,
            node_type=node_type,
            content_text=content_text.strip() if content_text else None,
            media_file_ids=media_file_ids or [],
            tier_required=max(1, min(6, tier_required)),  # Clamp a 1-6
            order_index=order_index,
            is_active=True
        )

        self.session.add(node)
        # NO commit - dejar que el handler gestione la transacción

        logger.info(f"Created {node_type.value} node for story {story_id}")

        return (True, "Node created", node)

    # ===== CREATE CHOICE =====

    async def create_choice(
        self,
        source_node_id: int,
        target_node_id: int,
        choice_text: str,
        cost_besitos: int = 0,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[StoryChoice]]:
        """
        Crea una elección conectando dos nodos.

        Args:
            source_node_id: ID del nodo origen
            target_node_id: ID del nodo destino
            choice_text: Texto de la elección
            cost_besitos: Costo en besitos
            conditions: Condiciones JSON para mostrar la elección

        Returns:
            Tuple[bool, str, Optional[StoryChoice]]: (éxito, mensaje, elección creada)
        """
        # Validar texto de elección
        if not choice_text or not choice_text.strip():
            return (False, "Choice text is required", None)

        choice_text = choice_text.strip()
        if len(choice_text) > 500:
            return (False, "Choice text exceeds 500 characters", None)

        # Verificar nodo origen
        result = await self.session.execute(
            select(StoryNode).where(StoryNode.id == source_node_id)
        )
        source_node = result.scalar_one_or_none()

        if not source_node:
            return (False, "Source node not found", None)

        # Verificar nodo destino
        result = await self.session.execute(
            select(StoryNode).where(StoryNode.id == target_node_id)
        )
        target_node = result.scalar_one_or_none()

        if not target_node:
            return (False, "Target node not found", None)

        # Verificar que los nodos están en la misma historia
        if source_node.story_id != target_node.story_id:
            return (False, "Nodes must be in the same story", None)

        # Validar costo
        if cost_besitos < 0:
            return (False, "Cost cannot be negative", None)

        # Crear elección
        choice = StoryChoice(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            choice_text=choice_text,
            cost_besitos=cost_besitos,
            conditions=conditions or {},
            is_active=True
        )

        self.session.add(choice)
        # NO commit - dejar que el handler gestione la transacción

        logger.info(f"Created choice from node {source_node_id} to {target_node_id}")

        return (True, "Choice created", choice)

    # ===== VALIDATE STORY =====

    async def validate_story(
        self,
        story_id: int
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Valida la integridad de una historia antes de publicar.

        Args:
            story_id: ID de la historia a validar

        Returns:
            Tuple[bool, List[str], Dict[str, Any]]: (es_válida, errores, info)
        """
        # Cargar historia con nodos y elecciones
        result = await self.session.execute(
            select(Story)
            .where(Story.id == story_id)
            .options(
                selectinload(Story.nodes).selectinload(StoryNode.choices)
            )
        )
        story = result.scalar_one_or_none()

        if not story:
            return (False, ["Story not found"], {})

        errors = []
        info = {
            "story_id": story_id,
            "node_count": 0,
            "choice_count": 0,
            "start_node_id": None,
            "ending_node_ids": [],
            "unreachable_nodes": []
        }

        nodes = story.nodes
        info["node_count"] = len(nodes)

        if not nodes:
            errors.append("Story has no nodes")
            return (False, errors, info)

        # Check 1: Exactamente un nodo START
        start_nodes = [n for n in nodes if n.node_type == NodeType.START]
        if len(start_nodes) != 1:
            errors.append(f"Story must have exactly one START node (found {len(start_nodes)})")
        else:
            info["start_node_id"] = start_nodes[0].id

        # Check 2: Al menos un nodo ENDING
        ending_nodes = [n for n in nodes if n.node_type == NodeType.ENDING]
        if len(ending_nodes) == 0:
            errors.append("Story must have at least one ENDING node")
        else:
            info["ending_node_ids"] = [n.id for n in ending_nodes]

        # Check 3: Todos los nodos (excepto ENDING) tienen al menos una elección activa
        for node in nodes:
            if node.node_type != NodeType.ENDING:
                active_choices = [c for c in node.choices if c.is_active]
                if not active_choices:
                    errors.append(f"Node {node.id} has no outgoing choices")

        # Check 4: Contar elecciones totales
        total_choices = sum(len(node.choices) for node in nodes)
        info["choice_count"] = total_choices

        # Check 5: Verificar que todas las elecciones apuntan a nodos existentes
        node_ids = {n.id for n in nodes}
        for node in nodes:
            for choice in node.choices:
                if choice.target_node_id not in node_ids:
                    errors.append(f"Choice {choice.id} points to non-existent node {choice.target_node_id}")

        # Check opcional: Nodos no alcanzables desde START
        if start_nodes:
            reachable = self._get_reachable_nodes(start_nodes[0], nodes)
            unreachable = [n.id for n in nodes if n.id not in reachable]
            if unreachable:
                info["unreachable_nodes"] = unreachable
                # Esto es una advertencia, no un error crítico

        is_valid = len(errors) == 0

        logger.info(
            f"Validated story {story_id}: {len(errors)} errors, "
            f"{info['node_count']} nodes, {info['choice_count']} choices"
        )

        return (is_valid, errors, info)

    def _get_reachable_nodes(self, start_node: StoryNode, all_nodes: List[StoryNode]) -> Set[int]:
        """
        Obtiene todos los nodos alcanzables desde el nodo inicial.

        Args:
            start_node: Nodo inicial
            all_nodes: Lista de todos los nodos

        Returns:
            Set[int]: IDs de nodos alcanzables
        """
        reachable = {start_node.id}
        to_visit = [start_node]
        node_map = {n.id: n for n in all_nodes}

        while to_visit:
            current = to_visit.pop()
            for choice in current.choices:
                if choice.is_active and choice.target_node_id not in reachable:
                    reachable.add(choice.target_node_id)
                    target_node = node_map.get(choice.target_node_id)
                    if target_node:
                        to_visit.append(target_node)

        return reachable

    # ===== PUBLISH STORY =====

    async def publish_story(
        self,
        story_id: int,
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Publica una historia después de validarla.

        Args:
            story_id: ID de la historia a publicar
            force: Forzar publicación aunque tenga errores de validación

        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        # Obtener historia
        result = await self.session.execute(
            select(Story).where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()

        if not story:
            return (False, "Story not found")

        # Verificar estado actual
        if story.status == StoryStatus.PUBLISHED:
            return (False, "Story is already published")

        if story.status == StoryStatus.ARCHIVED and not force:
            return (False, "Cannot publish archived story without force")

        # Validar historia
        is_valid, errors, _ = await self.validate_story(story_id)

        if not is_valid and not force:
            error_msg = f"Story validation failed: {'; '.join(errors)}"
            return (False, error_msg)

        # Actualizar estado
        story.status = StoryStatus.PUBLISHED
        story.updated_at = datetime.now(timezone.utc)

        # NO commit - dejar que el handler gestione la transacción

        if not is_valid and force:
            logger.warning(f"Force-published story {story_id} with validation errors")
        else:
            logger.info(f"Published story {story_id}")

        return (True, "Story published successfully")

    # ===== GET STORY STATS =====

    async def get_story_stats(
        self,
        story_id: int
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Obtiene estadísticas de una historia.

        Args:
            story_id: ID de la historia

        Returns:
            Tuple[bool, str, Optional[Dict]]: (éxito, mensaje, estadísticas)
        """
        # Verificar que la historia existe
        result = await self.session.execute(
            select(Story).where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()

        if not story:
            return (False, "Story not found", None)

        # Contar usuarios por estado
        result = await self.session.execute(
            select(func.count(UserStoryProgress.id))
            .where(UserStoryProgress.story_id == story_id)
        )
        total_starts = result.scalar_one()

        result = await self.session.execute(
            select(func.count(UserStoryProgress.id))
            .where(
                and_(
                    UserStoryProgress.story_id == story_id,
                    UserStoryProgress.status == StoryProgressStatus.ACTIVE
                )
            )
        )
        active = result.scalar_one()

        result = await self.session.execute(
            select(func.count(UserStoryProgress.id))
            .where(
                and_(
                    UserStoryProgress.story_id == story_id,
                    UserStoryProgress.status == StoryProgressStatus.COMPLETED
                )
            )
        )
        completed = result.scalar_one()

        result = await self.session.execute(
            select(func.count(UserStoryProgress.id))
            .where(
                and_(
                    UserStoryProgress.story_id == story_id,
                    UserStoryProgress.status == StoryProgressStatus.ABANDONED
                )
            )
        )
        abandoned = result.scalar_one()

        # Calcular promedio de decisiones
        result = await self.session.execute(
            select(func.avg(func.json_array_length(UserStoryProgress.decisions_made)))
            .where(UserStoryProgress.story_id == story_id)
        )
        avg_decisions = result.scalar_one() or 0.0

        # Encontrar el final más común
        result = await self.session.execute(
            select(
                UserStoryProgress.ending_reached,
                func.count(UserStoryProgress.id).label("count")
            )
            .where(
                and_(
                    UserStoryProgress.story_id == story_id,
                    UserStoryProgress.ending_reached.isnot(None)
                )
            )
            .group_by(UserStoryProgress.ending_reached)
            .order_by(func.count(UserStoryProgress.id).desc())
            .limit(1)
        )
        most_common_row = result.first()
        most_common_ending = most_common_row[0] if most_common_row else None

        # Calcular tasa de finalización
        completion_rate = completed / total_starts if total_starts > 0 else 0.0

        stats = {
            "story_id": story_id,
            "total_starts": total_starts,
            "active": active,
            "completed": completed,
            "abandoned": abandoned,
            "completion_rate": round(completion_rate, 2),
            "avg_decisions": round(float(avg_decisions), 2),
            "most_common_ending": most_common_ending
        }

        logger.debug(f"Retrieved stats for story {story_id}")

        return (True, "Stats retrieved", stats)
