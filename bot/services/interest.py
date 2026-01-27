"""
Interest Service - Gestión de intereses de usuarios en paquetes.

Servicio para registrar, consultar y gestionar intereses expresados por usuarios
en paquetes de contenido. Implementa deduplicación con ventana de tiempo para
evitar spam en notificaciones a administradores.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserInterest, ContentPackage, User
from bot.database.enums import ContentCategory

logger = logging.getLogger(__name__)


class InterestService:
    """
    Servicio para gestión de intereses de usuarios.

    Responsabilidades:
    - Registrar intereses con deduplicación (ventana de 5 minutos)
    - Listar intereses con filtros (pendientes, atendidos, por tipo)
    - Marcar intereses como atendidos
    - Obtener estadísticas de intereses
    - Verificar ventana de debounce para re-expresión de interés

    Patrón de deduplicación:
    - Un usuario puede expresar interés en el mismo paquete múltiples veces
    - Solo se crea notificación si ha pasado > 5 minutos desde el último interés
    - Se actualiza created_at para mantener el registro "fresco"

    Example:
        >>> # Registrar interés (con debounce)
        >>> success, status, interest = await service.register_interest(user_id=123, package_id=456)
        >>> if success:
        ...     # Notificar al admin
        ...     if status == "created":
        ...         print("Nuevo interés registrado")
        ...     elif status == "updated":
        ...         print("Interés re-expresado después de ventana")
        ... else:
        ...     if status == "debounce":
        ...         print("Usuario re-clickeó dentro de ventana (no notificar)")

        >>> # Listar intereses pendientes
        >>> interests, total = await service.get_interests(is_attended=False)

        >>> # Marcar como atendido
        >>> success, msg = await service.mark_as_attended(interest_id=789)

        >>> # Obtener estadísticas
        >>> stats = await service.get_interest_stats()
        >>> print(f"Pendientes: {stats['total_pending']}")
        >>> print(f"Atendidos: {stats['total_attended']}")
    """

    DEBOUNCE_WINDOW_MINUTES = 5

    def __init__(self, session: AsyncSession, bot):
        """
        Inicializar InterestService.

        Args:
            session: Sesión de base de datos SQLAlchemy async
            bot: Instancia del bot de Telegram
        """
        self.session = session
        self.bot = bot
        logger.debug("✅ InterestService inicializado")

    # ===== REGISTRO DE INTERESES =====

    async def register_interest(
        self,
        user_id: int,
        package_id: int
    ) -> Tuple[bool, str, Optional[UserInterest]]:
        """
        Registra interés de usuario en paquete con deduplicación.

        Lógica:
        1. Busca interés existente para (user_id, package_id)
        2. Si existe:
           - Verifica si está dentro de ventana de debounce (5 min)
           - Si está dentro: retorna (False, "debounce", existing_interest)
           - Si pasó ventana: actualiza created_at, retorna (True, "updated", interest)
        3. Si no existe:
           - Crea nuevo registro con is_attended=False
           - Retorna (True, "created", new_interest)

        Args:
            user_id: ID del usuario de Telegram
            package_id: ID del paquete de contenido

        Returns:
            Tupla (success, status, interest):
            - success: True si se debe notificar admin, False si es debounce
            - status: "created", "updated", "debounce", "error"
            - interest: Objeto UserInterest o None si error

        Raises:
            ValueError: Si package_id no existe
        """
        try:
            # Verify package exists
            package_stmt = select(ContentPackage).where(ContentPackage.id == package_id)
            package_result = await self.session.execute(package_stmt)
            package = package_result.scalar_one_or_none()

            if not package:
                logger.error(f"Package {package_id} not found for interest registration")
                return (False, "error", None)

            # Check existing interest
            existing_stmt = select(UserInterest).where(
                and_(
                    UserInterest.user_id == user_id,
                    UserInterest.package_id == package_id
                )
            )
            existing_result = await self.session.execute(existing_stmt)
            existing_interest = existing_result.scalar_one_or_none()

            if existing_interest:
                # Check debounce window
                if self._is_within_debounce_window(existing_interest.created_at):
                    logger.debug(
                        f"Interest for user {user_id}, package {package_id} "
                        f"within debounce window (ignoring)"
                    )
                    return (False, "debounce", existing_interest)
                else:
                    # Update timestamp (re-interest after window)
                    existing_interest.created_at = datetime.utcnow()
                    logger.info(
                        f"Updated interest timestamp for user {user_id}, "
                        f"package {package_id} (debounce window expired)"
                    )
                    return (True, "updated", existing_interest)
            else:
                # Create new interest
                new_interest = UserInterest(
                    user_id=user_id,
                    package_id=package_id,
                    is_attended=False,
                    attended_at=None,
                    created_at=datetime.utcnow()
                )
                self.session.add(new_interest)
                logger.info(
                    f"Registered new interest for user {user_id}, package {package_id}"
                )
                return (True, "created", new_interest)

        except Exception as e:
            logger.error(
                f"Error registering interest for user {user_id}, "
                f"package {package_id}: {e}",
                exc_info=True
            )
            return (False, "error", None)

    # ===== CONSULTA DE INTERESES =====

    async def get_interests(
        self,
        is_attended: Optional[bool] = None,
        package_type: Optional[ContentCategory] = None,
        user_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        sort_newest_first: bool = True
    ) -> Tuple[List[UserInterest], int]:
        """
        Obtiene lista de intereses con filtros y paginación.

        Args:
            is_attended: Filtrar por estado de atención (None = todos)
            package_type: Filtrar por tipo de paquete (None = todos)
            user_id: Filtrar por usuario específico (None = todos)
            limit: Máximo de registros a retornar
            offset: Registro inicial (para paginación)
            sort_newest_first: True para más recientes primero, False para más antiguos

        Returns:
            Tupla (interests, total_count):
            - interests: Lista de objetos UserInterest
            - total_count: Total de registros (sin paginar)

        Examples:
            >>> # Get all pending interests, newest first
            >>> interests, total = await service.get_interests(is_attended=False)

            >>> # Get attended VIP interests, paginated
            >>> interests, total = await service.get_interests(
            ...     is_attended=True,
            ...     package_type=ContentCategory.VIP_CONTENT,
            ...     limit=10,
            ...     offset=0
            ... )
        """
        try:
            # Build base query with joins
            stmt = select(UserInterest).join(ContentPackage)

            # Apply filters
            conditions = []
            if is_attended is not None:
                conditions.append(UserInterest.is_attended == is_attended)
            if package_type is not None:
                conditions.append(ContentPackage.category == package_type)
            if user_id is not None:
                conditions.append(UserInterest.user_id == user_id)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Count total
            count_stmt = select(UserInterest.__table__.c.id).join(ContentPackage)
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            count_result = await self.session.execute(count_stmt)
            total_count = len(count_result.all())

            # Apply sorting
            if sort_newest_first:
                stmt = stmt.order_by(desc(UserInterest.created_at))
            else:
                stmt = stmt.order_by(UserInterest.created_at)

            # Apply pagination
            stmt = stmt.limit(limit).offset(offset)

            # Execute
            result = await self.session.execute(stmt)
            interests = result.scalars().all()

            logger.debug(
                f"Retrieved {len(interests)} interests (total: {total_count}, "
                f"filters: attended={is_attended}, type={package_type}, user={user_id})"
            )

            return (interests, total_count)

        except Exception as e:
            logger.error(f"Error getting interests: {e}", exc_info=True)
            return ([], 0)

    async def get_interest_by_id(self, interest_id: int) -> Optional[UserInterest]:
        """
        Obtiene un interés por su ID.

        Args:
            interest_id: ID del registro UserInterest

        Returns:
            Objeto UserInterest o None si no existe
        """
        try:
            stmt = select(UserInterest).where(UserInterest.id == interest_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting interest {interest_id}: {e}", exc_info=True)
            return None

    async def get_user_interests(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[UserInterest]:
        """
        Obtiene intereses de un usuario específico.

        Args:
            user_id: ID del usuario
            limit: Máximo de registros a retornar

        Returns:
            Lista de UserInterest ordenados por fecha (más reciente primero)
        """
        try:
            stmt = select(UserInterest).where(
                UserInterest.user_id == user_id
            ).order_by(
                desc(UserInterest.created_at)
            ).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error getting interests for user {user_id}: {e}", exc_info=True)
            return []

    # ===== GESTIÓN DE INTERESES =====

    async def mark_as_attended(self, interest_id: int) -> Tuple[bool, str]:
        """
        Marca un interés como atendido.

        Args:
            interest_id: ID del registro UserInterest

        Returns:
            Tupla (success, message):
            - success: True si se marcó correctamente
            - message: Mensaje de éxito o error

        Examples:
            >>> success, msg = await service.mark_as_attended(123)
            >>> if success:
            ...     print("Interés marcado como atendido")
        """
        try:
            stmt = select(UserInterest).where(UserInterest.id == interest_id)
            result = await self.session.execute(stmt)
            interest = result.scalar_one_or_none()

            if not interest:
                return (False, "Interés no encontrado")

            if interest.is_attended:
                return (True, "El interés ya estaba marcado como atendido")

            interest.is_attended = True
            interest.attended_at = datetime.utcnow()

            logger.info(f"Marked interest {interest_id} as attended")
            return (True, "Interés marcado como atendido")

        except Exception as e:
            logger.error(f"Error marking interest {interest_id} as attended: {e}", exc_info=True)
            return (False, f"Error al marcar interés: {str(e)}")

    # ===== ESTADÍSTICAS =====

    async def get_interest_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de intereses.

        Returns:
            Diccionario con:
            - total_pending: Total de intereses pendientes
            - total_attended: Total de intereses atendidos
            - by_package_type: Dict con conteo por tipo de paquete
            - recent_interests: Lista de últimos 5 intereses (todos)

        Examples:
            >>> stats = await service.get_interest_stats()
            >>> print(f"Pendientes: {stats['total_pending']}")
        """
        try:
            # Total pending
            pending_stmt = select(UserInterest).where(UserInterest.is_attended == False)
            pending_result = await self.session.execute(pending_stmt)
            total_pending = len(pending_result.scalars().all())

            # Total attended
            attended_stmt = select(UserInterest).where(UserInterest.is_attended == True)
            attended_result = await self.session.execute(attended_stmt)
            total_attended = len(attended_result.scalars().all())

            # By package type
            stmt = select(UserInterest).join(ContentPackage)
            result = await self.session.execute(stmt)
            all_interests = result.scalars().all()

            by_package_type = {}
            for interest in all_interests:
                pkg_type = interest.package.category.value if interest.package else "unknown"
                by_package_type[pkg_type] = by_package_type.get(pkg_type, 0) + 1

            # Recent interests (last 5)
            recent_stmt = select(UserInterest).order_by(
                desc(UserInterest.created_at)
            ).limit(5)
            recent_result = await self.session.execute(recent_stmt)
            recent_interests = recent_result.scalars().all()

            return {
                "total_pending": total_pending,
                "total_attended": total_attended,
                "by_package_type": by_package_type,
                "recent_interests": recent_interests
            }

        except Exception as e:
            logger.error(f"Error getting interest stats: {e}", exc_info=True)
            return {
                "total_pending": 0,
                "total_attended": 0,
                "by_package_type": {},
                "recent_interests": []
            }

    # ===== LIMPIEZA =====

    async def cleanup_old_attended(self, days_old: int = 30) -> int:
        """
        Limpia intereses atendidos antiguos (background task).

        Args:
            days_old: Días de antigüedad para eliminar

        Returns:
            Número de registros eliminados

        Note:
            Este método es para tasks programados en background.
            No eliminar intereses pendientes (is_attended=False).
        """
        try:
            from sqlalchemy import delete

            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Find old attended interests
            stmt = select(UserInterest).where(
                and_(
                    UserInterest.is_attended == True,
                    UserInterest.attended_at < cutoff_date
                )
            )
            result = await self.session.execute(stmt)
            old_interests = result.scalars().all()

            count = len(old_interests)
            for interest in old_interests:
                await self.session.delete(interest)

            logger.info(f"Cleaned up {count} attended interests older than {days_old} days")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up old interests: {e}", exc_info=True)
            return 0

    # ===== UTILIDADES =====

    def _is_within_debounce_window(self, created_at: datetime) -> bool:
        """
        Verifica si un interés está dentro de la ventana de debounce.

        Args:
            created_at: Fecha de creación del interés

        Returns:
            True si está dentro de la ventana (menos de 5 minutos)
        """
        window_expiry = created_at + timedelta(minutes=self.DEBOUNCE_WINDOW_MINUTES)
        return datetime.utcnow() < window_expiry
