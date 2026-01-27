"""
User Management Service - Gestión de usuarios y acciones administrativas.

Servicio para gestionar usuarios del sistema: ver información, cambiar roles,
bloquear/desbloquear, expulsar de canales, con validación de permisos y
auditoría de cambios.
"""
import logging
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import User, VIPSubscriber, UserRoleChangeLog, UserInterest
from bot.database.enums import UserRole, RoleChangeReason
from bot.services.role_change import RoleChangeService

logger = logging.getLogger(__name__)

# Pagination constants
USER_LIST_PAGE_SIZE = 20


class UserManagementService:
    """
    Servicio para gestión de usuarios y acciones administrativas.

    Responsabilidades:
    - Obtener información detallada de usuario (rol, suscripción, historial)
    - Cambiar rol de usuario con auditoría
    - Bloquear/desbloquear usuario (placeholder - requiere migración de BD)
    - Expulsar usuario de canales (VIP/Free)
    - Listar usuarios con filtros y paginación
    - Validar permisos (super admin, self-action prevention)

    Permisos:
    - Super admin: Primer admin en Config.ADMIN_USER_IDS
    - Admin-on-admin: Solo super admin puede modificar otros admins
    - Self-actions: Admins no pueden bloquearse/expulsarse a sí mismos

    Patrón de auditoría:
    - Todos los cambios de rol se registran en UserRoleChangeLog
    - Cambios por admin incluyen changed_by (user_id del admin)
    - Cambios automáticos usan changed_by=0 (SYSTEM)
    """

    def __init__(self, session: AsyncSession, bot):
        """
        Inicializar UserManagementService.

        Args:
            session: Sesión de base de datos SQLAlchemy async
            bot: Instancia del bot de Telegram
        """
        self.session = session
        self.bot = bot
        logger.debug("✅ UserManagementService inicializado")

    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene información detallada de un usuario.

        Usa eager loading para evitar N+1 queries y problemas de lazy loading
        fuera del contexto async.

        Args:
            user_id: ID del usuario de Telegram

        Returns:
            Diccionario con información del usuario o None si no existe:
            - user_id: ID del usuario
            - username: Username (puede ser None)
            - first_name: Nombre
            - last_name: Apellido (puede ser None)
            - role: Rol actual (UserRole enum)
            - created_at: Fecha de registro
            - updated_at: Última actualización
            - vip_subscription: Dict con info de suscripción VIP si existe
            - interests_count: Número de intereses registrados
            - role_changes: Lista de cambios de rol (últimos 5)
        """
        try:
            # Get user with eager-loaded interests relationship to prevent N+1 queries
            # and MissingGreenlet errors from lazy loading outside async context
            stmt = select(User).options(
                selectinload(User.interests)
            ).where(User.user_id == user_id)

            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            # Get VIP subscription - use eager loading via VIPSubscriber.user relationship
            # This prevents MissingGreenlet error when accessing vip_sub.user later
            vip_stmt = select(VIPSubscriber).options(
                selectinload(VIPSubscriber.user)
            ).where(
                VIPSubscriber.user_id == user_id
            ).order_by(desc(VIPSubscriber.join_date))
            vip_result = await self.session.execute(vip_stmt)
            vip_sub = vip_result.scalar_one_or_none()

            # Get interests count from eager-loaded relationship
            interests_count = len(user.interests) if user.interests else 0

            # Get role changes (last 5) - no relationship defined, use separate query
            changes_stmt = select(UserRoleChangeLog).where(
                UserRoleChangeLog.user_id == user_id
            ).order_by(desc(UserRoleChangeLog.changed_at)).limit(5)
            changes_result = await self.session.execute(changes_stmt)
            role_changes = changes_result.scalars().all()

            return {
                "user_id": user.user_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "vip_subscription": {
                    "expires_at": vip_sub.expiry_date,
                    "is_active": vip_sub.expiry_date > datetime.utcnow() if vip_sub and vip_sub.expiry_date else False,
                    "token_used": vip_sub.token_used if vip_sub else None
                } if vip_sub else None,
                "interests_count": interests_count,
                "role_changes": [
                    {
                        "from_role": change.previous_role,
                        "to_role": change.new_role,
                        "reason": change.reason,
                        "changed_by": change.changed_by,
                        "changed_at": change.changed_at
                    }
                    for change in role_changes
                ]
            }

        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}", exc_info=True)
            return None

    async def change_user_role(
        self,
        user_id: int,
        new_role: UserRole,
        changed_by: int
    ) -> Tuple[bool, str]:
        """
        Cambia el rol de un usuario con auditoría.

        Args:
            user_id: ID del usuario a modificar
            new_role: Nuevo rol (UserRole enum)
            changed_by: ID del admin que realiza el cambio

        Returns:
            Tupla (success, message):
            - success: True si se cambió correctamente
            - message: Mensaje de éxito o error
        """
        try:
            # Validate permissions first
            can_modify, error_msg = await self._can_modify_user(
                target_user_id=user_id,
                admin_user_id=changed_by
            )

            if not can_modify:
                return (False, error_msg)

            # Get user
            stmt = select(User).where(User.user_id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return (False, "Usuario no encontrado")

            # Store old role
            old_role = user.role

            # Check if same role
            if old_role == new_role:
                return (True, f"El usuario ya tiene el rol {new_role.value}")

            # Update role
            user.role = new_role
            user.updated_at = datetime.utcnow()

            # Log change via RoleChangeService
            role_change_service = RoleChangeService(self.session)
            await role_change_service.log_role_change(
                user_id=user_id,
                new_role=new_role,
                changed_by=changed_by,
                reason=RoleChangeReason.MANUAL_CHANGE,
                previous_role=old_role,
                change_source="ADMIN_PANEL"
            )

            logger.info(
                f"Role changed: user {user_id} {old_role.value} -> {new_role.value} "
                f"by admin {changed_by}"
            )

            return (True, f"Rol cambiado de {old_role.value} a {new_role.value}")

        except Exception as e:
            logger.error(
                f"Error changing role for user {user_id} to {new_role.value}: {e}",
                exc_info=True
            )
            return (False, f"Error al cambiar rol: {str(e)}")

    async def block_user(
        self,
        user_id: int,
        blocked_by: int,
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Bloquea a un usuario (impide usar el bot).

        Nota: Implementación futura requerirá agregar campo 'is_blocked' a User model.
        Por ahora, esta función es un placeholder que retorna error.

        Args:
            user_id: ID del usuario a bloquear
            blocked_by: ID del admin que bloquea
            reason: Razón del bloqueo (opcional)

        Returns:
            Tupla (success, message)
        """
        # Validate permissions
        can_modify, error_msg = await self._can_modify_user(
            target_user_id=user_id,
            admin_user_id=blocked_by
        )

        if not can_modify:
            return (False, error_msg)

        # TODO: Implement when User.is_blocked field is added
        # For now, return placeholder message
        logger.warning(f"Block user called for {user_id} by {blocked_by} - not yet implemented")
        return (False, "Función de bloqueo será implementada en próxima versión (requiere migración de BD)")

    async def unblock_user(
        self,
        user_id: int,
        unblocked_by: int
    ) -> Tuple[bool, str]:
        """
        Desbloquea a un usuario.

        Nota: Implementación futura requerirá agregar campo 'is_blocked' a User model.
        Por ahora, esta función es un placeholder que retorna error.

        Args:
            user_id: ID del usuario a desbloquear
            unblocked_by: ID del admin que desbloquea

        Returns:
            Tupla (success, message)
        """
        # Validate permissions
        can_modify, error_msg = await self._can_modify_user(
            target_user_id=user_id,
            admin_user_id=unblocked_by
        )

        if not can_modify:
            return (False, error_msg)

        # TODO: Implement when User.is_blocked field is added
        logger.warning(f"Unblock user called for {user_id} by {unblocked_by} - not yet implemented")
        return (False, "Función de desbloqueo será implementada en próxima versión (requiere migración de BD)")

    async def expel_user_from_channels(
        self,
        user_id: int,
        expelled_by: int
    ) -> Tuple[bool, str, List[str]]:
        """
        Expulsa a un usuario de los canales VIP y Free.

        Maneja expulsión atómica: si falla la expulsión de un canal,
        intenta deshacer las expulsiones anteriores para mantener consistencia.

        Args:
            user_id: ID del usuario a expulsar
            expelled_by: ID del admin que expulsa

        Returns:
            Tupla (success, message, expelled_from):
            - success: True si se expulsó de todos los canales disponibles
            - message: Mensaje con resultado
            - expelled_from: Lista de canales de los que se expulsó (para rollback)
        """
        from bot.services.channel import ChannelService

        channel_service = ChannelService(self.session, self.bot)
        expelled_from = []
        errors = []
        vip_channel_id = None
        free_channel_id = None

        try:
            # Validate permissions
            can_modify, error_msg = await self._can_modify_user(
                target_user_id=user_id,
                admin_user_id=expelled_by
            )

            if not can_modify:
                return (False, error_msg, [])

            # Get channel IDs
            vip_channel_id = await channel_service.get_vip_channel_id()
            free_channel_id = await channel_service.get_free_channel_id()

            # Collect available channels
            channels_to_expel = []
            if vip_channel_id:
                channels_to_expel.append(("VIP", vip_channel_id))
            if free_channel_id:
                channels_to_expel.append(("Free", free_channel_id))

            if not channels_to_expel:
                return (False, "No hay canales configurados para expulsar", [])

            # Expel from all channels (atomic attempt)
            for channel_name, channel_id in channels_to_expel:
                try:
                    await self.bot.ban_chat_member(
                        chat_id=channel_id,
                        user_id=user_id
                    )
                    expelled_from.append(channel_name)
                    logger.info(f"✅ User {user_id} expelled from {channel_name} by admin {expelled_by}")
                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"{channel_name}: {error_msg}")
                    logger.warning(f"⚠️ Could not expel user {user_id} from {channel_name}: {e}")

            # Handle partial failure - rollback expulsions
            if errors and expelled_from:
                logger.warning(f"⚠️ Partial expulsion failure for user {user_id}, rolling back...")
                await self._rollback_expulsion(user_id, vip_channel_id, free_channel_id, expelled_from)
                return (
                    False,
                    f"Expulsión fallida. Errores: {'; '.join(errors)}. "
                    f"Se deshicieron las expulsiones parciales.",
                    []
                )

            # No channels available or all failed
            if not expelled_from:
                error_detail = "; ".join(errors) if errors else "El usuario no es miembro de los canales"
                return (False, f"No se pudo expulsar al usuario: {error_detail}", [])

            channels_str = ", ".join(expelled_from)
            return (True, f"Usuario expulsado de: {channels_str}", expelled_from)

        except Exception as e:
            logger.error(f"❌ Error expelling user {user_id}: {e}", exc_info=True)
            # Rollback on unexpected error
            if expelled_from:
                await self._rollback_expulsion(user_id, vip_channel_id, free_channel_id, expelled_from)
            return (False, f"Error al expulsar usuario: {str(e)}", [])

    async def _rollback_expulsion(
        self,
        user_id: int,
        vip_channel_id: Optional[str],
        free_channel_id: Optional[str],
        expelled_from: List[str]
    ) -> None:
        """
        Deshace expulsiones parciales en caso de fallo.

        Intenta unban al usuario de los canales donde ya se expulsó.
        Es "best effort" - si falla el rollback, se loguea pero no se lanza excepción.

        Args:
            user_id: ID del usuario
            vip_channel_id: ID del canal VIP
            free_channel_id: ID del canal Free
            expelled_from: Lista de canales de los que se expulsó (nombres)
        """
        channels_map = {
            "VIP": vip_channel_id,
            "Free": free_channel_id
        }

        for channel_name in expelled_from:
            channel_id = channels_map.get(channel_name)
            if not channel_id:
                continue

            try:
                await self.bot.unban_chat_member(
                    chat_id=channel_id,
                    user_id=user_id,
                    only_if_banned=True
                )
                logger.info(f"↩️ Rolled back expulsion of user {user_id} from {channel_name}")
            except Exception as e:
                logger.error(f"❌ Failed to rollback expulsion for user {user_id} from {channel_name}: {e}")

    async def get_user_list(
        self,
        role: Optional[UserRole] = None,
        limit: int = 20,
        offset: int = 0,
        sort_newest_first: bool = True
    ) -> Tuple[List[User], int]:
        """
        Obtiene lista de usuarios con filtros y paginación.

        Args:
            role: Filtrar por rol (None = todos)
            limit: Máximo de registros a retornar
            offset: Registro inicial (para paginación)
            sort_newest_first: True para más recientes primero

        Returns:
            Tupla (users, total_count):
            - users: Lista de objetos User
            - total_count: Total de registros (sin paginar)
        """
        try:
            # Build base query for count
            count_stmt = select(func.count(User.user_id))
            if role is not None:
                count_stmt = count_stmt.where(User.role == role)

            # Execute count
            count_result = await self.session.execute(count_stmt)
            total_count = count_result.scalar_one() or 0

            # Build query for users
            stmt = select(User)

            # Apply filter
            if role is not None:
                stmt = stmt.where(User.role == role)

            # Apply sorting
            if sort_newest_first:
                stmt = stmt.order_by(desc(User.created_at))
            else:
                stmt = stmt.order_by(User.created_at)

            # Apply pagination
            stmt = stmt.limit(limit).offset(offset)

            # Execute
            result = await self.session.execute(stmt)
            users = result.scalars().all()

            logger.debug(
                f"Retrieved {len(users)} users (total: {total_count}, role: {role})"
            )

            return (users, total_count)

        except Exception as e:
            logger.error(f"Error getting user list: {e}", exc_info=True)
            return ([], 0)

    async def search_users(
        self,
        query: str,
        limit: int = 10
    ) -> List[User]:
        """
        Busca usuarios por username o user_id.

        Args:
            query: Query de búsqueda (username o user_id como string)
            limit: Máximo de resultados

        Returns:
            Lista de usuarios coincidentes
        """
        try:
            # Try to parse as user_id
            try:
                user_id = int(query)
                id_stmt = select(User).where(User.user_id == user_id)
                id_result = await self.session.execute(id_stmt)
                user = id_result.scalar_one_or_none()
                if user:
                    return [user]
            except ValueError:
                pass  # Not a number, search by username

            # Search by username
            username_query = f"%{query}%"
            stmt = select(User).where(
                User.username.ilike(username_query)
            ).limit(limit)

            result = await self.session.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error searching users with query '{query}': {e}", exc_info=True)
            return []

    def is_super_admin(self, user_id: int) -> bool:
        """
        Verifica si un usuario es el super admin.

        El super admin es el primer admin en Config.ADMIN_USER_IDS.

        Args:
            user_id: ID del usuario a verificar

        Returns:
            True si es el super admin
        """
        from config import Config

        if not Config.ADMIN_USER_IDS:
            return False

        return user_id == Config.ADMIN_USER_IDS[0]

    async def _can_modify_user(
        self,
        target_user_id: int,
        admin_user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Valida si un admin puede modificar a un usuario.

        Reglas:
        1. Admin no puede modificarse a sí mismo
        2. Solo super admin puede modificar otros admins

        Args:
            target_user_id: ID del usuario a modificar
            admin_user_id: ID del admin que intenta modificar

        Returns:
            Tupla (can_modify, error_message):
            - can_modify: True si tiene permiso
            - error_message: Mensaje de error si no tiene permiso
        """
        # Self-action prevention
        if target_user_id == admin_user_id:
            return (False, "No puedes realizar esta acción sobre ti mismo")

        # Get target user
        stmt = select(User).where(User.user_id == target_user_id)
        result = await self.session.execute(stmt)
        target_user = result.scalar_one_or_none()

        if not target_user:
            return (False, "Usuario no encontrado")

        # Admin-on-admin: only super admin can modify other admins
        if target_user.role == UserRole.ADMIN:
            if not self.is_super_admin(admin_user_id):
                return (False, "Solo el super admin puede modificar otros administradores")

        return (True, None)

    async def get_user_role(self, user_id: int) -> Optional[UserRole]:
        """
        Obtiene el rol de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            UserRole o None si no existe
        """
        try:
            stmt = select(User).where(User.user_id == user_id)
            result = await self.session.execute(stmt)
            user = result.scalar_one_or_none()
            return user.role if user else None
        except Exception as e:
            logger.error(f"Error getting role for user {user_id}: {e}", exc_info=True)
            return None
