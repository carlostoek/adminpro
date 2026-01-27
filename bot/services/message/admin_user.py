"""
Admin User Management Messages - Lucien's voice for user management interface.

Mensajes para gestión de usuarios: menú, listas, vista detallada, confirmaciones.
"""
import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.message.base import BaseMessageProvider
from bot.database.enums import UserRole
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)


class AdminUserMessages(BaseMessageProvider):
    """
    Proveedor de mensajes para gestión de usuarios.

    Responsabilidades:
    - Mensajes para menú de gestión de usuarios
    - Listas de usuarios con badges de rol (👑 Admin, 💎 VIP, 👤 Free)
    - Vista detallada de usuario con tabs (Overview, Subscription, Activity, Interests)
    - Confirmaciones para acciones administrativas
    - Mensajes de éxito/error

    Terminología de Lucien:
    - "Gestión de Usuarios" - User management
    - "custodios" - Admins
    - "miembros del círculo" - VIP users
    - "visitantes del jardín" - Free users
    - "sancionar" - Block
    - "expulsar" - Expel

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI

    Examples:
        >>> provider = AdminUserMessages()
        >>> text, kb = provider.users_menu(
        ...     total_users=100,
        ...     vip_count=25,
        ...     free_count=70,
        ...     admin_count=5
        ... )
        >>> 'Gestión de Usuarios' in text and 'custodio' in text.lower()
        True
    """

    ROLE_EMOJIS = {
        UserRole.ADMIN: "👑",
        UserRole.VIP: "💎",
        UserRole.FREE: "👤"
    }

    ROLE_NAMES = {
        UserRole.ADMIN: "Administrador",
        UserRole.VIP: "VIP",
        UserRole.FREE: "Free"
    }

    def users_menu(
        self,
        total_users: int,
        vip_count: int,
        free_count: int,
        admin_count: int,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje del menú principal de gestión de usuarios.

        Args:
            total_users: Total de usuarios
            vip_count: Cantidad de VIP
            free_count: Cantidad de Free
            admin_count: Cantidad de admins
            user_id: Optional user ID for session-aware selection
            session_history: Optional session history for context

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Habitantes del jardín" (garden inhabitants) for users.
            "Custodio" (custodian) for admin role.
            Stats breakdown with elegant formatting.
        """
        # Weighted greeting variations
        greetings = [
            ("Los habitantes del jardín aguardan su atención...", 0.5),
            ("El registro de visitantes y miembros del círculo...", 0.3),
            ("La censo de almas en el reino de Diana...", 0.2),
        ]

        greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="users_menu",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b> <i>{greeting}</i>"

        body = (
            f"<b>📋 Gestión de Usuarios</b>\n\n"
            f"👥 <b>Total:</b> {total_users} usuarios\n"
            f"💎 <b>VIP:</b> {vip_count} miembros del círculo\n"
            f"👤 <b>Free:</b> {free_count} visitantes del jardín\n"
            f"👑 <b>Admins:</b> {admin_count} custodios\n\n"
            f"<i>Seleccione una acción para comenzar, custodio.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._users_menu_keyboard()
        return text, keyboard

    def users_list(
        self,
        users: List[Any],
        page: int,
        total_pages: int,
        filter_type: str,
        total_count: int
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de lista de usuarios con paginación.

        Args:
            users: Lista de usuarios (con atributos user_id, username, first_name, role)
            page: Página actual
            total_pages: Total de páginas
            filter_type: Tipo de filtro (all, vip, free)
            total_count: Total de usuarios con este filtro

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            Filter names in Spanish: "Todos", "VIP", "Free".
            User links using tg://user?id= format for clickability.
            Role badges for quick identification.
        """
        filter_names = {
            "all": "Todos",
            "vip": "VIP",
            "free": "Free"
        }

        filter_title = filter_names.get(filter_type, "Todos")

        header = f"🎩 <b>Lucien:</b>\n\n"

        body = (
            f"👥 <b>Usuarios: {filter_title}</b>\n\n"
            f"<i>Página {page}/{total_pages} • {total_count} encontrados</i>\n\n"
        )

        # Build user list
        if users:
            lines = []
            for user in users:
                role_emoji = self.ROLE_EMOJIS.get(user.role, "❓")
                username_display = user.username if user.username else f"id{user.user_id}"
                name_display = user.first_name or "Sin nombre"
                lines.append(
                    f"{role_emoji} <a href='tg://user?id={user.user_id}'>{name_display}</a> "
                    f"(@{username_display})"
                )
            body += "\n".join(lines)
        else:
            body += "<i>No hay usuarios para mostrar.</i>"

        text = header + body
        keyboard = self._users_list_keyboard(users, page, total_pages, filter_type)
        return text, keyboard

    def user_detail_overview(
        self,
        user_info: Dict[str, Any]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Pestaña de resumen del perfil de usuario.

        Args:
            user_info: Diccionario con información del usuario

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Perfil de Usuario" with role badge prominent.
            Comprehensive user info display.
            Tabbed navigation for different aspects.
        """
        user_id = user_info["user_id"]
        username = user_info.get("username") or f"id{user_id}"
        first_name = user_info.get("first_name", "N/A")
        last_name = user_info.get("last_name", "")
        role = user_info["role"]
        created_at = user_info.get("created_at", datetime.now())

        role_emoji = self.ROLE_EMOJIS.get(role, "❓")
        role_name = self.ROLE_NAMES.get(role, "Desconocido")

        name_display = f"{first_name} {last_name}".strip() or first_name

        header = f"🎩 <b>Lucien:</b>\n\n<i>El perfil del habitante seleccionado...</i>"

        body = (
            f"👤 <b>Perfil de Usuario</b>\n\n"
            f"{role_emoji} <b>Rol:</b> {role_name}\n"
            f"🆔 <b>ID:</b> {user_id}\n"
            f"👤 <b>Nombre:</b> {name_display}\n"
            f"📝 <b>Username:</b> @{username}\n"
            f"📅 <b>Miembro desde:</b> {created_at.strftime('%d/%m/%Y %H:%M')}\n\n"
            f"<i>Use las pestañas para ver más detalles.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._user_detail_keyboard(user_id)
        return text, keyboard

    def user_detail_subscription(
        self,
        user_info: Dict[str, Any]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Pestaña de suscripción del perfil de usuario.

        Args:
            user_info: Diccionario con información del usuario

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            VIP subscription details with expiry and token info.
            "Suscripción VIP" with elegant formatting.
            Graceful handling for non-VIP users.
        """
        user_id = user_info["user_id"]
        role = user_info.get("role")
        vip_sub = user_info.get("vip_subscription")

        header = f"🎩 <b>Lucien:</b>\n\n<i>Los detalles del círculo exclusivo...</i>"

        if role == UserRole.VIP and vip_sub:
            expires_at = vip_sub.get("expires_at", datetime.now())
            is_active = vip_sub.get("is_active", False)
            token_used = vip_sub.get("token_used")

            status = "✅ Activa" if is_active else "⏳ Expirada"
            status_emoji = "✅" if is_active else "⏳"

            body = (
                f"💎 <b>Suscripción VIP</b>\n\n"
                f"{status_emoji} <b>Estado:</b> {status}\n"
                f"📅 <b>Expira:</b> {expires_at.strftime('%d/%m/%Y %H:%M')}\n"
                f"🎫 <b>Token usado:</b> {token_used if token_used else 'N/A'}\n\n"
                f"<i>Use las pestañas para ver más detalles.</i>"
            )
        else:
            body = (
                f"💎 <b>Suscripción VIP</b>\n\n"
                f"<i>Este usuario no tiene suscripción VIP activa.</i>\n\n"
                f"<i>Use las pestañas para ver más detalles.</i>"
            )

        text = self._compose(header, body)
        keyboard = self._user_detail_keyboard(user_id)
        return text, keyboard

    def user_detail_activity(
        self,
        user_info: Dict[str, Any]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Pestaña de actividad del perfil de usuario.

        Args:
            user_info: Diccionario con información del usuario

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Actividad del Usuario" showing role change history.
            Timeline format for changes.
            Reason display in human-readable format.
        """
        user_id = user_info["user_id"]
        role_changes = user_info.get("role_changes", [])
        updated_at = user_info.get("updated_at", datetime.now())

        header = f"🎩 <b>Lucien:</b>\n\n<i>El rastro de pasos en el jardín...</i>"

        body = (
            f"📝 <b>Actividad del Usuario</b>\n\n"
            f"🕒 <b>Última actualización:</b> {updated_at.strftime('%d/%m/%Y %H:%M')}\n\n"
        )

        if role_changes:
            body += "<b>Cambios de rol recientes:</b>\n\n"
            for change in role_changes:
                from_role = change.get("from_role")
                to_role = change.get("to_role")
                reason = change.get("reason", "UNKNOWN")
                changed_at = change.get("changed_at", datetime.now())

                from_role_str = from_role.value if from_role else "N/A"
                to_role_str = to_role.value if to_role else "N/A"
                # Handle reason as either enum or string
                if hasattr(reason, 'value'):
                    reason_str = reason.value.replace("_", " ").title()
                else:
                    reason_str = str(reason).replace("_", " ").title() if reason else "Desconocido"
                changed_at_str = changed_at.strftime('%d/%m/%Y %H:%M')

                body += f"• {from_role_str} → {to_role_str}\n"
                body += f"  <i>Razón: {reason_str}</i>\n"
                body += f"  <i>{changed_at_str}</i>\n\n"
        else:
            body += "<i>Sin cambios de rol registrados.</i>\n\n"

        body += "<i>Use las pestañas para ver más detalles.</i>"

        text = self._compose(header, body)
        keyboard = self._user_detail_keyboard(user_id)
        return text, keyboard

    def user_detail_interests(
        self,
        user_info: Dict[str, Any],
        interests: List[Any]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Pestaña de intereses del perfil de usuario.

        Args:
            user_info: Diccionario con información del usuario
            interests: Lista de intereses del usuario

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Intereses del Usuario" showing package interests.
            "Manifestaciones de interés" terminology.
            Status indicators for attended/pending.
        """
        user_id = user_info["user_id"]
        interests_count = user_info.get("interests_count", len(interests))

        header = f"🎩 <b>Lucien:</b>\n\n<i>Las curiosidades manifestadas...</i>"

        body = (
            f"⭐ <b>Intereses del Usuario</b>\n\n"
            f"📊 <b>Total:</b> {interests_count} interés(es)\n\n"
        )

        if interests:
            body += "<b>Intereses recientes:</b>\n\n"
            for interest in interests[:10]:  # Show last 10
                package = interest.package if hasattr(interest, 'package') else None
                package_name = package.name if package else "Paquete eliminado"
                created_at = interest.created_at if hasattr(interest, 'created_at') else datetime.now()
                is_attended = interest.is_attended if hasattr(interest, 'is_attended') else False

                created_at_str = created_at.strftime('%d/%m/%Y %H:%M')
                status = "✅ Atendido" if is_attended else "⏳ Pendiente"

                body += f"• {package_name}\n"
                body += f"  <i>{status} • {created_at_str}</i>\n\n"
        else:
            body += "<i>Sin intereses registrados.</i>\n\n"

        body += "<i>Use las pestañas para ver más detalles.</i>"

        text = self._compose(header, body)
        keyboard = self._user_detail_keyboard(user_id)
        return text, keyboard

    def change_role_confirm(
        self,
        user_info: Dict[str, Any],
        new_role: UserRole
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de confirmación para cambio de rol.

        Args:
            user_info: Diccionario con información del usuario
            new_role: Nuevo rol a asignar

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            Clear before/after comparison.
            "¿Confirmar este cambio?" for confirmation.
            Mention of audit trail.
        """
        user_id = user_info["user_id"]
        username = user_info.get("username") or f"id{user_id}"
        first_name = user_info.get("first_name", "Usuario")
        current_role = user_info.get("role")

        role_emoji_current = self.ROLE_EMOJIS.get(current_role, "❓")
        role_emoji_new = self.ROLE_EMOJIS.get(new_role, "❓")
        role_name_new = self.ROLE_NAMES.get(new_role, "Desconocido")

        current_role_str = current_role.value if current_role else "N/A"

        header = f"🎩 <b>Lucien:</b>\n\n<i>Una decisión que requiere confirmación...</i>"

        body = (
            f"🔄 <b>Cambiar Rol de Usuario</b>\n\n"
            f"👤 <b>Usuario:</b> {first_name} (@{username})\n"
            f"🆔 <b>ID:</b> {user_id}\n\n"
            f"{role_emoji_current} <b>Rol actual:</b> {current_role_str}\n"
            f"{role_emoji_new} <b>Nuevo rol:</b> {role_name_new}\n\n"
            f"<i>¿Confirmar este cambio? La acción quedará registrada en el historial.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._change_role_confirm_keyboard(user_id, new_role)
        return text, keyboard

    def role_change_success(
        self,
        user_info: Dict[str, Any],
        old_role: UserRole,
        new_role: UserRole
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de éxito para cambio de rol.

        Args:
            user_info: Diccionario con información del usuario
            old_role: Rol anterior
            new_role: Nuevo rol asignado

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            Celebration of successful change.
            "Ahora es..." emphasizes new status.
            Notification mention.
        """
        user_id = user_info["user_id"]
        username = user_info.get("username") or f"id{user_id}"
        first_name = user_info.get("first_name", "Usuario")

        role_emoji = self.ROLE_EMOJIS.get(new_role, "✅")
        role_name = self.ROLE_NAMES.get(new_role, new_role.value if new_role else "Usuario")

        header = f"🎩 <b>Lucien:</b>\n\n<i>El cambio ha sido efectuado...</i>"

        body = (
            f"✅ <b>Rol Cambiado Exitosamente</b>\n\n"
            f"{role_emoji} <b>{first_name}</b> (@{username}) ahora es <b>{role_name}</b>.\n\n"
            f"<i>El usuario ha sido notificado del cambio.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._role_change_success_keyboard(user_id)
        return text, keyboard

    def expel_confirm(
        self,
        user_info: Dict[str, Any]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de confirmación para expulsar usuario.

        Args:
            user_info: Diccionario con información del usuario

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Expulsar Usuario" with clear explanation.
            "Remover de todos los canales" explains action scope.
            User retains bot access warning.
        """
        user_id = user_info["user_id"]
        username = user_info.get("username") or f"id{user_id}"
        first_name = user_info.get("first_name", "Usuario")
        role = user_info.get("role")

        role_emoji = self.ROLE_EMOJIS.get(role, "❓")
        role_name = self.ROLE_NAMES.get(role, "Desconocido")

        header = f"🎩 <b>Lucien:</b>\n\n<i>Una medida que requiere confirmación...</i>"

        body = (
            f"🚫 <b>Expulsar Usuario</b>\n\n"
            f"👤 <b>Usuario:</b> {first_name} (@{username})\n"
            f"🆔 <b>ID:</b> {user_id}\n"
            f"{role_emoji} <b>Rol:</b> {role_name}\n\n"
            f"<i>Esta acción removerá al usuario de todos los canales (VIP y Free). "
            f"El usuario aún podrá usar el bot, pero no tendrá acceso a los canales.</i>\n\n"
            f"<i>¿Confirmar esta acción?</i>"
        )

        text = self._compose(header, body)
        keyboard = self._expel_confirm_keyboard(user_id)
        return text, keyboard

    def expel_success(
        self,
        user_info: Dict[str, Any],
        expelled_from: List[str]
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de éxito para expulsión.

        Args:
            user_info: Diccionario con información del usuario
            expelled_from: Lista de canales de los que fue expulsado

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Usuario Expulsado" with channel list.
            "Ha sido removido de" passive voice.
            Notification mention.
        """
        user_id = user_info["user_id"]
        username = user_info.get("username") or f"id{user_id}"
        first_name = user_info.get("first_name", "Usuario")

        channels_str = ", ".join(expelled_from) if expelled_from else "canales"

        header = f"🎩 <b>Lucien:</b>\n\n<i>La medida ha sido ejecutada...</i>"

        body = (
            f"✅ <b>Usuario Expulsado</b>\n\n"
            f"<b>{first_name}</b> (@{username}) ha sido removido de: {channels_str}.\n\n"
            f"<i>El usuario ha sido notificado de la acción.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._expel_success_keyboard()
        return text, keyboard

    def user_search_prompt(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de prompt para búsqueda de usuario.

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Buscar Usuario" with clear instructions.
            Examples for guidance.
            /skip alternative for cancellation.
        """
        header = f"🎩 <b>Lucien:</b>\n\n<i>Buscar un habitante del jardín...</i>"

        body = (
            f"🔍 <b>Buscar Usuario</b>\n\n"
            f"<i>Por favor, ingrese el username o ID del usuario que desea buscar.</i>\n\n"
            f"Ejemplos:\n"
            f"• @username\n"
            f"• username\n"
            f"• 123456789\n\n"
            f"<i>Escriba /cancel para cancelar la búsqueda.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._user_search_prompt_keyboard()
        return text, keyboard

    def user_search_results(
        self,
        users: List[Any],
        query: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de resultados de búsqueda.

        Args:
            users: Lista de usuarios encontrados
            query: Query de búsqueda

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            "Resultados de búsqueda" with query display.
            Direct links to user profiles.
            Max 5 results for readability.
        """
        header = f"🎩 <b>Lucien:</b>\n\n<i>Los resultados de la búsqueda...</i>"

        body = (
            f'🔍 <b>Resultados: "{query}"</b>\n\n'
            f"<i>{len(users)} encontrado(s)</i>\n\n"
        )

        # Build user list
        if users:
            lines = []
            for user in users:
                role_emoji = self.ROLE_EMOJIS.get(user.role, "❓")
                username_display = user.username if user.username else f"id{user.user_id}"
                name_display = user.first_name or "Sin nombre"
                lines.append(
                    f"{role_emoji} <a href='tg://user?id={user.user_id}'>{name_display}</a> "
                    f"(@{username_display})"
                )
            body += "\n".join(lines)
        else:
            body += "<i>No se encontraron usuarios.</i>"

        text = header + body
        keyboard = self._user_search_results_keyboard(users)
        return text, keyboard

    def action_error(
        self,
        message: str
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Mensaje de error para acción administrativa.

        Args:
            message: Mensaje de error

        Returns:
            Tupla (text, keyboard)

        Voice Rationale:
            Apologetic error tone.
            "Inténtelo de nuevo" encouragement.
            Contact support option for persistent issues.
        """
        header = f"🎩 <b>Lucien:</b>\n\n<i>Un contratiempo inesperado...</i>"

        body = (
            f"❌ <b>Error</b>\n\n"
            f"{message}\n\n"
            f"<i>Por favor, inténtelo de nuevo o contacte al super admin si el problema persiste.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._action_error_keyboard()
        return text, keyboard

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _users_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for users menu."""
        return create_inline_keyboard([
            [
                {"text": "🔍 Buscar Usuario", "callback_data": "admin:users:search"},
                {"text": "👥 Ver Todos", "callback_data": "admin:users:list:all"}
            ],
            [
                {"text": "💎 Solo VIP", "callback_data": "admin:users:list:vip"},
                {"text": "👤 Solo Free", "callback_data": "admin:users:list:free"}
            ],
            [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}],
        ])

    def _users_list_keyboard(self, users: List[Any], page: int, total_pages: int, filter_type: str) -> InlineKeyboardMarkup:
        """Generate keyboard for paginated users list with profile buttons."""
        buttons = []

        # User buttons (one per row)
        for user in users:
            role_emoji = self.ROLE_EMOJIS.get(user.role, "❓")
            name_display = user.first_name or "Sin nombre"
            # Truncate name if too long for button
            if len(name_display) > 20:
                name_display = name_display[:17] + "..."
            buttons.append([
                {
                    "text": f"{role_emoji} {name_display} - Ver Perfil",
                    "callback_data": f"admin:user:view:{user.user_id}:overview"
                }
            ])

        # Separator
        buttons.append([{"text": "─" * 15, "callback_data": "admin:users:noop"}])

        # Pagination row
        nav_buttons = []
        if page > 1:
            nav_buttons.append({"text": "⬅️ Anterior", "callback_data": f"admin:users:page:{page-1}:{filter_type}"})
        if total_pages > 1:
            nav_buttons.append({"text": f"{page}/{total_pages}", "callback_data": "admin:users:noop"})
        if page < total_pages:
            nav_buttons.append({"text": "➡️ Siguiente", "callback_data": f"admin:users:page:{page+1}:{filter_type}"})

        if nav_buttons:
            buttons.append(nav_buttons)

        # Filter row
        buttons.append([
            {"text": "🔍 Filtros", "callback_data": f"admin:users:filters:{filter_type}"},
            {"text": "🔙 Volver", "callback_data": "admin:users:menu"}
        ])

        return create_inline_keyboard(buttons)

    def _user_detail_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate keyboard for user detail view with tabs."""
        return create_inline_keyboard([
            [
                {"text": "📊 Resumen", "callback_data": f"admin:user:view:{user_id}:overview"},
                {"text": "💎 Suscripción", "callback_data": f"admin:user:view:{user_id}:subscription"}
            ],
            [
                {"text": "📝 Actividad", "callback_data": f"admin:user:view:{user_id}:activity"},
                {"text": "⭐ Intereses", "callback_data": f"admin:user:view:{user_id}:interests"}
            ],
            [
                {"text": "🔄 Cambiar Rol", "callback_data": f"admin:user:role:{user_id}"},
                {"text": "🚫 Bloquear", "callback_data": f"admin:user:block:{user_id}"}
            ],
            [
                {"text": "🚪 Expulsar", "callback_data": f"admin:user:expel:{user_id}"}
            ],
            [{"text": "🔙 Volver a la Lista", "callback_data": "admin:users:list:all"}],
        ])

    def _change_role_confirm_keyboard(self, user_id: int, new_role: UserRole) -> InlineKeyboardMarkup:
        """Generate keyboard for role change confirmation."""
        return create_inline_keyboard([
            [
                {"text": "✅ Confirmar", "callback_data": f"admin:user:role:confirm:{user_id}:{new_role.value}"},
                {"text": "❌ Cancelar", "callback_data": f"admin:user:view:{user_id}:overview"}
            ],
        ])

    def _role_change_success_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate keyboard for role change success."""
        return create_inline_keyboard([
            [
                {"text": "🔙 Volver al Perfil", "callback_data": f"admin:user:view:{user_id}:overview"},
                {"text": "👥 Volver a Lista", "callback_data": "admin:users:list:all"}
            ],
        ])

    def _expel_confirm_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """Generate keyboard for expel confirmation."""
        return create_inline_keyboard([
            [
                {"text": "✅ Expulsar", "callback_data": f"admin:user:expel:confirm:{user_id}"},
                {"text": "❌ Cancelar", "callback_data": f"admin:user:view:{user_id}:overview"}
            ],
        ])

    def _expel_success_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for expel success."""
        return create_inline_keyboard([
            [{"text": "👥 Volver a Lista", "callback_data": "admin:users:list:all"}],
        ])

    def _user_search_prompt_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for search prompt."""
        return create_inline_keyboard([
            [{"text": "❌ Cancelar", "callback_data": "admin:users:menu"}],
        ])

    def _user_search_results_keyboard(self, users: List[Any]) -> InlineKeyboardMarkup:
        """Generate keyboard for search results."""
        buttons = []

        if users:
            # Add view buttons for each user
            for user in users[:5]:  # Max 5 results
                name_display = user.first_name or f"id{user.user_id}"
                buttons.append([
                    {"text": f"👤 Ver {name_display}", "callback_data": f"admin:user:view:{user.user_id}:overview"}
                ])

        buttons.extend([
            [{"text": "🔍 Nueva Búsqueda", "callback_data": "admin:users:search"}],
            [{"text": "🔙 Volver", "callback_data": "admin:users:menu"}],
        ])

        return create_inline_keyboard(buttons)

    def _action_error_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for action error."""
        return create_inline_keyboard([
            [{"text": "🔙 Volver al Menú", "callback_data": "admin:users:menu"}],
        ])
