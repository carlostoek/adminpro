"""
VIP Callback Handlers - Gestión de interacciones del menú VIP.

Responsabilidades:
- Manejar callback "vip:premium" - mostrar sección premium
- Manejar callback "interest:package:{id}" - registrar interés en paquete
- Manejar callback "menu:back" - volver al menú principal VIP
- Manejar callback "menu:exit" - cerrar menú

Pattern: Sigue estructura de admin callbacks con router separado.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.database.enums import ContentCategory

logger = logging.getLogger(__name__)

# Create router
vip_callbacks_router = Router()


@vip_callbacks_router.callback_query(lambda c: c.data == "vip:premium")
async def handle_vip_premium(callback: CallbackQuery, **kwargs):
    """
    Muestra sección premium con paquetes VIP_PREMIUM.

    Args:
        callback: CallbackQuery de Telegram
        **kwargs: Data del handler (container, session, etc.)
    """
    data = kwargs.get("data", {})
    container = data.get("container")
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Get active VIP_PREMIUM packages
        packages = await container.content.get_active_packages(
            category=ContentCategory.VIP_PREMIUM,
            limit=20
        )

        # Get session context for message variations
        session_ctx = container.message.get_session_context(container)

        # Generate premium section message with dynamic package buttons
        text, keyboard = container.message.user.menu.vip_premium_section(
            user_name=user.first_name,
            packages=packages,
            user_id=user.id,
            session_history=session_ctx
        )

        # Update message with premium section
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

        logger.info(f"⭐ Sección premium mostrada a {user.id} ({len(packages)} paquetes)")

    except Exception as e:
        logger.error(f"Error mostrando sección premium a {user.id}: {e}")
        await callback.answer("⚠️ Error cargando contenido premium", show_alert=True)


@vip_callbacks_router.callback_query(lambda c: c.data == "vip:status")
async def handle_vip_status(callback: CallbackQuery, **kwargs):
    """
    Muestra el estado de la membresía VIP del usuario.

    Args:
        callback: CallbackQuery de Telegram
        **kwargs: Data del handler (container, session, etc.)
    """
    data = kwargs.get("data", {})
    container = data.get("container")
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Get VIP subscription info
        subscriber = await container.subscription.get_vip_subscriber(user.id)

        if subscriber and subscriber.expires_at:
            expiry_date = subscriber.expires_at.strftime("%d de %B de %Y")
            status_text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El estado de su membresía en el círculo exclusivo...</i>\n\n"
                f"<b>⭐ Estado de la Membresía VIP</b>\n\n"
                f"<b>Miembro:</b> {user.first_name or 'Visitante'}\n"
                f"<b>Estado:</b> ✅ Activa\n"
                f"<b>Expira:</b> {expiry_date}\n\n"
                f"<i>Su acceso al sanctum está asegurado hasta la fecha indicada.</i>"
            )
        elif subscriber:
            # Permanent membership
            status_text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>El estado de su membresía en el círculo exclusivo...</i>\n\n"
                f"<b>⭐ Estado de la Membresía VIP</b>\n\n"
                f"<b>Miembro:</b> {user.first_name or 'Visitante'}\n"
                f"<b>Estado:</b> ✅ Permanente\n"
                f"<b>Expira:</b> Nunca\n\n"
                f"<i>Su acceso al sanctum es eterno.</i>"
            )
        else:
            status_text = (
                f"🎩 <b>Lucien:</b>\n\n"
                f"<i>Parece que hay un confusión con su estatus...</i>\n\n"
                f"<b>⭐ Estado de la Membresía VIP</b>\n\n"
                f"<b>Miembro:</b> {user.first_name or 'Visitante'}\n"
                f"<b>Estado:</b> ❌ No encontrada\n\n"
                f"<i>Por favor, contacte a los custodios del sanctum.</i>"
            )

        # Create navigation keyboard using helper
        from bot.utils.keyboards import create_content_with_navigation

        # Empty content + navigation only (back and exit)
        keyboard = create_content_with_navigation(
            content_buttons=[],
            back_text="⬅️ Volver al Menú VIP",
            back_callback="menu:back"
        )

        await callback.message.edit_text(
            status_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

        logger.info(f"⭐ Estado VIP mostrado a {user.id}")

    except Exception as e:
        logger.error(f"Error mostrando estado VIP a {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando estado de membresía", show_alert=True)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("interest:package:"))
async def handle_package_interest(callback: CallbackQuery, **kwargs):
    """
    Registra interés de usuario en paquete específico.

    Callback data format: "interest:package:{package_id}"

    Args:
        callback: CallbackQuery de Telegram
        **kwargs: Data del handler (container, session, etc.)
    """
    data = kwargs.get("data", {})
    container = data.get("container")
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Create UserInterest record
        from bot.database.models import UserInterest
        from sqlalchemy import select

        # Get session from handler data (injected by DatabaseMiddleware)
        session = data.get("session")
        if not session:
            await callback.answer("⚠️ Error: sesión de base de datos no disponible", show_alert=True)
            return

        # Check if interest already exists for this user+package
        stmt = select(UserInterest).where(
            UserInterest.user_id == user.id,
            UserInterest.package_id == package_id
        )
        result = await session.execute(stmt)
        existing_interest = result.scalar_one_or_none()

        if existing_interest:
            # Update timestamp for existing interest
            existing_interest.created_at = datetime.utcnow()
            logger.info(f"❤️ Usuario {user.id} actualizó interés en paquete {package_id}")
            # Admin notification (VIPMENU-03 requirement)
            logger.info(f"📢 ADMIN NOTIFICATION: Usuario VIP {user.id} ({user.first_name}) actualizó interés en paquete {package_id}")
        else:
            # Create new interest record
            interest = UserInterest(
                user_id=user.id,
                package_id=package_id,
                is_attended=False,
                attended_at=None,
                created_at=datetime.utcnow()
            )
            session.add(interest)
            logger.info(f"❤️ Usuario {user.id} interesado en paquete {package_id} (nuevo registro)")
            # Admin notification (VIPMENU-03 requirement)
            logger.info(f"📢 ADMIN NOTIFICATION: Nuevo interés de usuario VIP {user.id} ({user.first_name}) en paquete {package_id}")

        # Show success feedback
        await callback.answer(
            "✅ Tu interés ha sido registrado. Diana será notificada.",
            show_alert=True
        )

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error registrando interés para {user.id}: {e}")
        await callback.answer("⚠️ Error registrando interés", show_alert=True)


@vip_callbacks_router.callback_query(lambda c: c.data == "menu:back")
async def handle_menu_back(callback: CallbackQuery, **kwargs):
    """
    Vuelve al menú principal VIP.

    Args:
        callback: CallbackQuery de Telegram
        **kwargs: Data del handler (container, session, etc.)
    """
    data = kwargs.get("data", {})
    container = data.get("container")
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Re-show VIP menu (reusing show_vip_menu logic)
        from .menu import show_vip_menu
        await show_vip_menu(callback.message, data)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error volviendo al menú VIP para {user.id}: {e}")
        await callback.answer("⚠️ Error volviendo al menú", show_alert=True)


@vip_callbacks_router.callback_query(lambda c: c.data == "menu:exit")
async def handle_menu_exit(callback: CallbackQuery):
    """
    Cierra el menú (elimina mensaje).

    Args:
        callback: CallbackQuery de Telegram
    """
    try:
        await callback.message.delete()
        await callback.answer("Menú cerrado")
    except Exception as e:
        logger.error(f"Error cerrando menú para {callback.from_user.id}: {e}")
        await callback.answer("⚠️ Error cerrando menú", show_alert=True)


__all__ = ["vip_callbacks_router"]