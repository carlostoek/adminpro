"""
Admin Interest Messages Provider - Interest management UI messages.

Provides messages for viewing and managing user interests in content packages.
All messages maintain Lucien's sophisticated mayordomo voice from docs/guia-estilo.md.
"""
import logging
from typing import Tuple, List, Optional, Dict, Any
from datetime import datetime

from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)


class AdminInterestMessages(BaseMessageProvider):
    """
    Admin interest management messages provider.

    Voice Characteristics:
    - Admin = "custodio" or "guardián"
    - Interests = "expresiones de interés" or "manifestaciones de curiosidad"
    - Users = "visitantes" (Free) or "miembros del círculo" (VIP)
    - Packages = "tesoros" or "colecciones"
    - Uses "usted", never "tú"
    - Emoji 🔔 always present for interest-related messages

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI

    Interest List Pattern:
    - Default: Newest first (most recent at top)
    - Filters: Pending only, Attended only, By package type
    - Pagination: 10 items per page
    - Empty state: Friendly message with "No hay intereses pendientes"

    Examples:
        >>> provider = AdminInterestMessages()
        >>> text, kb = provider.interests_menu(
        ...     pending_count=5,
        ...     total_count=23
        ... )
        >>> '🔔' in text and 'pendientes' in text.lower()
        True
    """

    def interests_menu(
        self,
        pending_count: int = 0,
        total_count: int = 0,
        user_id: Optional[int] = None,
        session_history: Optional["SessionMessageHistory"] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main interests management menu.

        Args:
            pending_count: Number of pending interests
            total_count: Total number of interests
            user_id: Optional user ID for session-aware selection
            session_history: Optional session history for context

        Returns:
            Tuple of (text, keyboard) for interests menu

        Voice Rationale:
            "Manifestaciones de interés" sounds elegant for "interests".
            "Pendientes de atención" for pending interests.
            References "tesoros" for packages to maintain narrative.

        Examples:
            >>> text, kb = provider.interests_menu(pending_count=5, total_count=23)
            >>> '🔔' in text and '5' in text and 'pendientes' in text.lower()
            True
        """
        # Weighted greeting variations
        greetings = [
            ("Los registros de curiosidad de los visitantes...", 0.5),
            ("Las manifestaciones de interés en el reino...", 0.3),
            ("El registro de interacciones con nuestros tesoros...", 0.2),
        ]

        greeting = self._choose_variant(
            [g[0] for g in greetings],
            weights=[g[1] for g in greetings],
            user_id=user_id,
            method_name="interests_menu",
            session_history=session_history
        )

        header = f"🎩 <b>Lucien:</b> <i>{greeting}</i>"

        # Conditional body based on counts
        if pending_count > 0:
            body = (
                f"<b>🔔 Gestión de Intereses</b>\n\n"
                f"⏳ <b>Pendientes de atención:</b> {pending_count}\n"
                f"📊 <b>Total registrado:</b> {total_count}\n\n"
                f"<i>Varios visitantes han mostrado curiosidad por los tesoros de Diana. "
                f"¿Desea revisar las manifestaciones pendientes, custodio?</i>"
            )
        else:
            body = (
                f"<b>🔔 Gestión de Intereses</b>\n\n"
                f"✅ <b>Todo está atendido:</b> No hay intereses pendientes\n"
                f"📊 <b>Total histórico:</b> {total_count}\n\n"
                f"<i>El reino está en orden. Puede revisar el histórico si lo desea.</i>"
            )

        text = self._compose(header, body)
        keyboard = self._interests_menu_keyboard(pending_count > 0)
        return text, keyboard

    def interests_list(
        self,
        interests: List[Any],
        page: int = 1,
        total_pages: int = 1,
        filter_type: str = "all",
        user_id: Optional[int] = None
    ) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate paginated interests list.

        Args:
            interests: List of UserInterest objects
            page: Current page number (1-indexed)
            total_pages: Total number of pages
            filter_type: Current filter (all, pending, attended, vip_premium, vip_content, free_content)

        Returns:
            Tuple of (text, keyboard) with interest list

        Voice Rationale:
            "Registro de manifestaciones" for interest list.
            Filter names in Spanish: "Pendientes", "Atendidos", "Todos".
            User role: "Miembro VIP" or "Visitante Free".

        Examples:
            >>> text, kb = provider.interests_list(
            ...     interests=[interest1, interest2],
            ...     page=1,
            ...     total_pages=2
            ... )
            >>> 'Página 1/2' in text
            True
        """
        # Header based on filter
        filter_titles = {
            "all": "📋 Todos los Intereses",
            "pending": "⏳ Intereses Pendientes",
            "attended": "✅ Intereses Atendidos",
            "vip_premium": "💎 Premium",
            "vip_content": "🛋️ El Diván",
            "free_content": "🌸 Promos"
        }

        title = filter_titles.get(filter_type, "📋 Intereses")

        # Build interest list
        if not interests:
            body = self._interests_empty_message(filter_type)
        else:
            items = []
            for idx, interest in enumerate(interests, start=(page - 1) * 10 + 1):
                user = interest.user
                package = interest.package

                # Format user
                username = f"@{user.username}" if user.username else f"Usuario {user.user_id}"
                user_role = "👑 VIP" if hasattr(user, 'role') and hasattr(user.role, 'value') and user.role.value == "VIP" else "🌸 Free"

                # Format package
                pkg_category_str = str(package.category) if hasattr(package, 'category') and package.category else "UNKNOWN"
                pkg_emoji = {
                    "VIP_PREMIUM": "💎",
                    "VIP_CONTENT": "🛋️",
                    "FREE_CONTENT": "🌸"
                }.get(pkg_category_str, "📦")

                # Format status
                status_icon = "⏳" if not interest.is_attended else "✅"
                time_str = interest.created_at.strftime("%d/%m %H:%M") if hasattr(interest, 'created_at') and interest.created_at else "N/A"

                item_text = (
                    f"{status_icon} <b>#{idx}</b> {username} ({user_role})\n"
                    f"    {pkg_emoji} {package.name}\n"
                    f"    🕒 {time_str}"
                )

                items.append(item_text)

            body = (
                f"{title}\n\n"
                f"{chr(10).join(items)}\n\n"
                f"<i>Página {page}/{total_pages}</i>"
            )

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._interests_list_keyboard(page, total_pages, filter_type)
        return text, keyboard

    def interests_empty(self, filter_type: str = "all") -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate empty state message when no interests match filter.

        Args:
            filter_type: Current filter (affects message content)

        Returns:
            Tuple of (text, keyboard) with friendly empty state

        Examples:
            >>> text, kb = provider.interests_empty("pending")
            >>> 'vacío' in text.lower() or 'sin intereses' in text.lower()
            True
        """
        filter_messages = {
            "pending": "No hay intereses pendientes de atención en este momento.",
            "attended": "No hay intereses atendidos con este filtro aún.",
            "vip_premium": "Nadie ha mostrado interés en los tesoros Premium aún.",
            "vip_content": "No hay intereses registrados en El Diván.",
            "free_content": "No hay intereses en promos."
        }

        message = filter_messages.get(
            filter_type,
            "No se encontraron intereses con los filtros seleccionados."
        )

        body = (
            f"<b>🔔 Registro Vacío</b>\n\n"
            f"<i>{message}</i>\n\n"
            f"<i>¿Desea revisar otras categorías, custodio?</i>"
        )

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._interests_empty_keyboard()
        return text, keyboard

    def interest_detail(self, interest: Any) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate detailed view of single interest.

        Args:
            interest: UserInterest object with loaded user and package relationships

        Returns:
            Tuple of (text, keyboard) with full interest details

        Examples:
            >>> text, kb = provider.interest_detail(interest)
            >>> 'Detalles' in text or 'Información' in text
            True
        """
        user = interest.user
        package = interest.package

        # Format user info
        username_display = f"@{user.username}" if user.username else "Sin username"
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Sin nombre"
        user_role = "👑 Miembro VIP" if hasattr(user, 'role') and hasattr(user.role, 'value') and user.role.value == "VIP" else "🌸 Visitante Free"

        # Format package info
        pkg_category_str = str(package.category) if hasattr(package, 'category') and package.category else "UNKNOWN"
        pkg_type_emoji = {
            "VIP_PREMIUM": "💎 Premium",
            "VIP_CONTENT": "🛋️ El Diván",
            "FREE_CONTENT": "🌸 Promos"
        }.get(pkg_category_str, "📦")

        # Format status
        if interest.is_attended:
            attended_time = interest.attended_at.strftime('%d/%m/%Y %H:%M') if hasattr(interest, 'attended_at') and interest.attended_at else "N/A"
            status = f"✅ <b>Atendido</b> el {attended_time}"
        else:
            status = "⏳ <b>Pendiente de atención</b>"

        # Build detail text
        body = (
            f"<b>🔔 Detalles del Interés</b>\n\n"
            f"<b>👤 Usuario:</b>\n"
            f"   {full_name} ({username_display})\n"
            f"   ID: {user.user_id}\n"
            f"   {user_role}\n\n"
            f"<b>📦 Paquete de Interés:</b>\n"
            f"   {pkg_type_emoji}\n"
            f"   <b>{package.name}</b>\n"
        )

        if hasattr(package, 'description') and package.description:
            body += f"   📝 {package.description}\n"

        if hasattr(package, 'price') and package.price is not None:
            body += f"   💰 ${package.price:.2f}\n"

        created_time = interest.created_at.strftime('%d/%m/%Y %H:%M') if hasattr(interest, 'created_at') and interest.created_at else "N/A"
        body += (
            f"\n<b>📊 Estado:</b> {status}\n"
            f"<b>🕒 Registrado:</b> {created_time}\n\n"
            f"<i>ID de registro: #{interest.id}</i>"
        )

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._interest_detail_keyboard(interest.id, interest.is_attended)
        return text, keyboard

    def interests_filters(self, current_filter: str = "all") -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate filter selection message.

        Args:
            current_filter: Currently active filter

        Returns:
            Tuple of (text, keyboard) with filter options

        Examples:
            >>> text, kb = provider.interests_filters("pending")
            >>> 'filtro' in text.lower() or 'filtrar' in text.lower()
            True
        """
        body = (
            f"<b>🔍 Filtros de Intereses</b>\n\n"
            f"<i>Seleccione un criterio para filtrar el registro de manifestaciones...</i>\n\n"
        )

        filter_descriptions = {
            "all": "📋 <b>Todos</b> - Muestra todos los intereses",
            "pending": "⏳ <b>Pendientes</b> - Solo intereses sin atender",
            "attended": "✅ <b>Atendidos</b> - Solo intereses ya atendidos",
            "vip_premium": "💎 <b>Premium</b> - Solo tesoros Premium",
            "vip_content": "🛋️ <b>El Diván</b> - Solo contenido para suscriptores",
            "free_content": "🌸 <b>Promos</b> - Solo promociones"
        }

        for filter_key, description in filter_descriptions.items():
            icon = "✅" if filter_key == current_filter else "⚪"
            body += f"{icon} {description}\n"

        body += f"\n<i>Filtro actual: <b>{current_filter.upper()}</b></i>"

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._interests_filters_keyboard()
        return text, keyboard

    def interests_stats(self, stats: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate interests statistics display.

        Args:
            stats: Dict from InterestService.get_interest_stats() with:
                - total_pending: int
                - total_attended: int
                - by_package_type: Dict[str, int]
                - recent_interests: List[UserInterest]

        Returns:
            Tuple of (text, keyboard) with statistics

        Examples:
            >>> stats = await service.get_interest_stats()
            >>> text, kb = provider.interests_stats(stats)
            >>> 'Estadísticas' in text or 'Resumen' in text
            True
        """
        pending = stats.get("total_pending", 0)
        attended = stats.get("total_attended", 0)
        total = pending + attended
        by_type = stats.get("by_package_type", {})
        recent = stats.get("recent_interests", [])

        body = (
            f"<b>📊 Estadísticas de Intereses</b>\n\n"
            f"📈 <b>Total Registrado:</b> {total}\n"
            f"⏳ <b>Pendientes:</b> {pending}\n"
            f"✅ <b>Atendidos:</b> {attended}\n\n"
        )

        # By package type
        if by_type:
            body += "<b>🏷️ Por Tipo de Paquete:</b>\n"
            type_names = {
                "VIP_PREMIUM": "💎 Premium",
                "VIP_CONTENT": "🛋️ El Diván",
                "FREE_CONTENT": "🌸 Promos"
            }
            for pkg_type, count in by_type.items():
                name = type_names.get(pkg_type, pkg_type)
                body += f"   {name}: {count}\n"
            body += "\n"

        # Recent interests
        if recent:
            body += "<b>🕒 Manifestaciones Recientes:</b>\n"
            for idx, interest in enumerate(recent[:5], 1):
                username = f"@{interest.user.username}" if hasattr(interest, 'user') and interest.user and hasattr(interest.user, 'username') and interest.user.username else f"User {interest.user.user_id if hasattr(interest, 'user') and interest.user else 'N/A'}"
                time_str = interest.created_at.strftime("%d/%m %H:%M") if hasattr(interest, 'created_at') and interest.created_at else "N/A"
                package_name = interest.package.name if hasattr(interest, 'package') and interest.package else "N/A"
                body += f"   {idx}. {username} - {package_name} ({time_str})\n"

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._interests_stats_keyboard()
        return text, keyboard

    def mark_attended_confirm(self, interest: Any) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate confirmation dialog for marking interest as attended.

        Args:
            interest: UserInterest object

        Returns:
            Tuple of (text, keyboard) with confirmation

        Examples:
            >>> text, kb = provider.mark_attended_confirm(interest)
            >>> '¿marcar' in text.lower() or 'confirmar' in text.lower()
            True
        """
        username = f"@{interest.user.username}" if hasattr(interest, 'user') and interest.user and hasattr(interest.user, 'username') and interest.user.username else f"Usuario {interest.user.user_id if hasattr(interest, 'user') and interest.user else 'N/A'}"
        package_name = interest.package.name if hasattr(interest, 'package') and interest.package else "N/A"

        body = (
            f"<b>✅ Marcar como Atendido</b>\n\n"
            f"<i>¿Confirma que desea marcar esta manifestación como atendida?</i>\n\n"
            f"<b>Usuario:</b> {username}\n"
            f"<b>Paquete:</b> {package_name}\n\n"
            f"<i>El interés será archivado y removido de la lista principal.</i>"
        )

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._mark_attended_confirm_keyboard(interest.id)
        return text, keyboard

    def mark_attended_success(self, interest: Any) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate success message after marking as attended.

        Args:
            interest: UserInterest object (now attended)

        Returns:
            Tuple of (text, keyboard) with success confirmation

        Examples:
            >>> text, kb = provider.mark_attended_success(interest)
            >>> '✅' in text or 'atendido' in text.lower()
            True
        """
        username = f"@{interest.user.username}" if hasattr(interest, 'user') and interest.user and hasattr(interest.user, 'username') and interest.user.username else f"Usuario {interest.user.user_id if hasattr(interest, 'user') and interest.user else 'N/A'}"
        package_name = interest.package.name if hasattr(interest, 'package') and interest.package else "N/A"
        time_str = interest.attended_at.strftime("%H:%M") if hasattr(interest, 'attended_at') and interest.attended_at else "ahora"

        body = (
            f"<b>✅ Interés Marcado como Atendido</b>\n\n"
            f"<i>La manifestación de curiosidad ha sido registrada como atendida.</i>\n\n"
            f"<b>Usuario:</b> {username}\n"
            f"<b>Paquete:</b> {package_name}\n"
            f"<b>Hora de atención:</b> {time_str}\n\n"
            f"<i>El registro ha sido archivado correctamente.</i>"
        )

        text = f"🎩 <b>Lucien:</b>\n\n{body}"
        keyboard = self._mark_attended_success_keyboard()
        return text, keyboard

    # ===== PRIVATE HELPER METHODS =====

    def _interests_empty_message(self, filter_type: str) -> str:
        """Generate empty state message body for list view."""
        filter_messages = {
            "pending": "No hay intereses pendientes de atención en este momento.",
            "attended": "No hay intereses atendidos con este filtro aún.",
            "vip_premium": "Nadie ha mostrado interés en los tesoros Premium aún.",
            "vip_content": "No hay intereses registrados en El Diván.",
            "free_content": "No hay intereses en promos.",
            "all": "No se encontraron intereses con los filtros seleccionados."
        }
        message = filter_messages.get(
            filter_type,
            "No se encontraron intereses con los filtros seleccionados."
        )
        return f"<i>{message}</i>"

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _interests_menu_keyboard(self, has_pending: bool) -> InlineKeyboardMarkup:
        """Generate keyboard for interests menu."""
        buttons = [
            [{"text": "⏳ Ver Pendientes", "callback_data": "admin:interests:list:pending"}],
            [{"text": "📊 Ver Estadísticas", "callback_data": "admin:interests:stats"}],
            [{"text": "🔍 Cambiar Filtro", "callback_data": "admin:interests:filters"}],
            [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}]
        ]
        return create_inline_keyboard(buttons)

    def _interests_list_keyboard(self, page: int, total_pages: int, filter_type: str) -> InlineKeyboardMarkup:
        """Generate keyboard for paginated interests list."""
        buttons = []

        # Filter row
        buttons.append([{"text": "🔍 Filtros", "callback_data": f"admin:interests:filters:{filter_type}"}])

        # Pagination row
        nav_buttons = []
        if page > 1:
            nav_buttons.append({"text": "⬅️ Anterior", "callback_data": f"admin:interests:page:{page-1}:{filter_type}"})
        if page < total_pages:
            nav_buttons.append({"text": "➡️ Siguiente", "callback_data": f"admin:interests:page:{page+1}:{filter_type}"})
        if nav_buttons:
            buttons.append(nav_buttons)

        # Navigation
        buttons.extend([
            [{"text": "📊 Estadísticas", "callback_data": "admin:interests:stats"}],
            [{"text": "🔙 Volver al Menú", "callback_data": "admin:interests"}]
        ])

        return create_inline_keyboard(buttons)

    def _interest_detail_keyboard(self, interest_id: int, is_attended: bool) -> InlineKeyboardMarkup:
        """Generate keyboard for interest detail view."""
        buttons = []

        if not is_attended:
            buttons.append([
                {"text": "✅ Marcar como Atendido", "callback_data": f"admin:interest:attend:{interest_id}"}
            ])

        buttons.extend([
            [{"text": "🔙 Volver a la Lista", "callback_data": "admin:interests:list:all"}]
        ])

        return create_inline_keyboard(buttons)

    def _interests_empty_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for empty state."""
        return create_inline_keyboard([
            [{"text": "🔍 Cambiar Filtro", "callback_data": "admin:interests:filters"}],
            [{"text": "🔙 Volver al Menú", "callback_data": "admin:interests"}],
        ])

    def _interests_filters_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for filter selection."""
        return create_inline_keyboard([
            [
                {"text": "📋 Todos", "callback_data": "admin:interests:list:all"},
                {"text": "⏳ Pendientes", "callback_data": "admin:interests:list:pending"}
            ],
            [
                {"text": "✅ Atendidos", "callback_data": "admin:interests:list:attended"},
                {"text": "💎 Premium", "callback_data": "admin:interests:list:vip_premium"}
            ],
            [
                {"text": "🛋️ El Diván", "callback_data": "admin:interests:list:vip_content"},
                {"text": "🌸 Promos", "callback_data": "admin:interests:list:free_content"}
            ],
            [{"text": "🔙 Volver al Menú", "callback_data": "admin:interests"}],
        ])

    def _interests_stats_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for stats view."""
        return create_inline_keyboard([
            [{"text": "🔄 Actualizar", "callback_data": "admin:interests:stats"}],
            [{"text": "🔙 Volver al Menú", "callback_data": "admin:interests"}],
        ])

    def _mark_attended_confirm_keyboard(self, interest_id: int) -> InlineKeyboardMarkup:
        """Generate keyboard for mark attended confirmation."""
        return create_inline_keyboard([
            [
                {"text": "✅ Sí, Marcar", "callback_data": f"admin:interest:confirm_attend:{interest_id}"},
                {"text": "❌ Cancelar", "callback_data": f"admin:interest:view:{interest_id}"}
            ],
        ])

    def _mark_attended_success_keyboard(self) -> InlineKeyboardMarkup:
        """Generate keyboard for mark attended success."""
        return create_inline_keyboard([
            [{"text": "🔙 Volver a la Lista", "callback_data": "admin:interests:list:all"}],
        ])
