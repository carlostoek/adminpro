"""
Free Callback Handlers - Gestión de interacciones del menú Free.

Responsabilidades:
- Manejar callback "menu:free:content" - mostrar sección "Mi Contenido"
- Manejar callback "menu:free:vip" - mostrar información del canal VIP
- Manejar callback "menu:free:social" - mostrar redes sociales/contenido gratuito
- Manejar interés en paquetes FREE_CONTENT
- Navegación (volver, salir)

Pattern: Sigue estructura de VIP callbacks con router separado.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.database.enums import ContentCategory

logger = logging.getLogger(__name__)

# Create router
free_callbacks_router = Router()


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:content")
async def handle_free_content(callback: CallbackQuery, **kwargs):
    """
    Muestra sección "Mi Contenido" con paquetes FREE_CONTENT.

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
        # Get active FREE_CONTENT packages
        packages = await container.content.get_active_packages(
            category=ContentCategory.FREE_CONTENT,
            limit=20
        )

        # Get session context for message variations
        session_ctx = None
        try:
            session_ctx = container.message.get_session_context(container)
        except Exception as e:
            logger.warning(f"No se pudo obtener contexto de sesión para {user.id}: {e}")

        # Generate content section message with dynamic package buttons
        text, keyboard = container.message.user.menu.free_content_section(
            user_name=user.first_name or "visitante",
            packages=packages,
            user_id=user.id,
            session_history=session_ctx
        )

        # Update message with content section
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

        logger.info(f"🆓 Sección 'Mi Contenido' mostrada a {user.id} ({len(packages)} paquetes)")

    except Exception as e:
        logger.error(f"Error mostrando contenido Free a {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando contenido gratuito", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:vip")
async def handle_vip_info(callback: CallbackQuery, **kwargs):
    """
    Muestra información sobre el canal VIP y suscripción.

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
        # Get VIP channel info if configured
        vip_channel_id = None
        is_vip_configured = False

        try:
            vip_channel_id = await container.config.get_vip_channel_id()
            is_vip_configured = bool(vip_channel_id)
        except Exception as e:
            logger.warning(f"No se pudo verificar configuración VIP: {e}")

        # Create informative message about VIP benefits with Lucien's voice
        message_text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>El círculo exclusivo de Diana aguarda...</i>\n\n"
            f"<b>⭐ Canal VIP - El Círculo Exclusivo</b>\n\n"
        )

        if is_vip_configured:
            message_text += (
                f"<i>El sanctum está disponible para aquellos que posean "
                f"el token de acceso.</i>\n\n"
                f"<b>✨ Beneficios del Círculo:</b>\n"
                f"• Contenido exclusivo y anticipado\n"
                f"• Comunidad privada de miembros\n"
                f"• Acceso directo a Diana para consultas\n"
                f"• Contenido premium adicional\n"
                f"• Privilegios especiales y eventos\n\n"
                f"<i>Para unirse al círculo exclusivo, necesitará un "
                f"token de invitación de Diana.</i>"
            )
        else:
            message_text += (
                f"<i>El sanctum aún no ha sido configurado por los custodios.</i>\n\n"
                f"<i>Los beneficios del círculo exclusivo estarán disponibles "
                f"una vez que Diana active el canal.</i>"
            )

        # Create keyboard with navigation using helper
        from bot.utils.keyboards import create_content_with_navigation

        keyboard = create_content_with_navigation(
            content_buttons=[],
            back_text="⬅️ Volver al Menú Free",
            back_callback="menu:free:main"
        )

        await callback.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

        logger.info(f"🆓 Info VIP mostrada a {user.id}")

    except Exception as e:
        logger.error(f"Error mostrando info VIP a {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando información VIP", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:social")
async def handle_social_media(callback: CallbackQuery, **kwargs):
    """
    Muestra redes sociales y contenido gratuito adicional.

    Args:
        callback: CallbackQuery de Telegram
        **kwargs: Data del handler (container, session, etc.)
    """
    data = kwargs.get("data", {})
    container = data.get("container")
    user = callback.from_user

    try:
        # Create social media message with Lucien's voice
        message_text = (
            f"🎩 <b>Lucien:</b>\n\n"
            f"<i>Diana comparte fragmentos de su arte en estos jardines públicos...</i>\n\n"
            f"<b>🌸 Redes Sociales de Diana</b>\n\n"
            f"• <b>Instagram:</b> @diana_artista (muestras diarias)\n"
            f"• <b>TikTok:</b> @diana.creaciones (tutoriales rápidos)\n"
            f"• <b>YouTube:</b> Diana Creaciones (procesos completos)\n\n"
            f"<b>🎁 Contenido Gratuito Adicional</b>\n\n"
            f"• Blog: www.dianacreaciones.com/blog\n"
            f"• Newsletter: Suscripción gratuita\n"
            f"• Comunidad: Grupo público de Telegram\n\n"
            f"<i>Seguir a Diana en redes sociales puede acelerar "
            f"su acceso al canal Free.</i>"
        )

        # Create keyboard with navigation using helper
        from bot.utils.keyboards import create_content_with_navigation

        keyboard = create_content_with_navigation(
            content_buttons=[],
            back_text="⬅️ Volver al Menú Free",
            back_callback="menu:free:main"
        )

        await callback.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()

        logger.info(f"🆓 Redes sociales mostradas a {user.id}")

    except Exception as e:
        logger.error(f"Error mostrando redes sociales a {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando redes sociales", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("interest:package:"))
async def handle_package_interest(callback: CallbackQuery, **kwargs):
    """
    Registra interés de usuario en paquete FREE_CONTENT.

    Reutiliza lógica de VIP callbacks para consistencia.

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
            await callback.answer(
                "⚠️ Error: sesión de base de datos no disponible",
                show_alert=True
            )
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
            logger.info(f"❤️ Usuario Free {user.id} actualizó interés en paquete {package_id}")
            # Admin notification (for consistency with VIP)
            logger.info(
                f"📢 ADMIN NOTIFICATION: Usuario Free {user.id} ({user.first_name}) "
                f"actualizó interés en paquete {package_id}"
            )
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
            logger.info(f"❤️ Usuario Free {user.id} interesado en paquete {package_id} (nuevo registro)")
            # Admin notification (for consistency with VIP)
            logger.info(
                f"📢 ADMIN NOTIFICATION: Nuevo interés de usuario Free {user.id} "
                f"({user.first_name}) en paquete {package_id}"
            )

        # Show success feedback
        await callback.answer(
            "✅ Tu interés ha sido registrado. Diana será notificada.",
            show_alert=True
        )

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error registrando interés para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error registrando interés", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:main")
async def handle_menu_back(callback: CallbackQuery, **kwargs):
    """
    Vuelve al menú principal Free.

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
        from .menu import show_free_menu
        await show_free_menu(callback.message, data)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error volviendo al menú Free para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error volviendo al menú", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:exit")
async def handle_menu_exit(callback: CallbackQuery):
    """
    Cierra el menú Free (elimina mensaje).

    Args:
        callback: CallbackQuery de Telegram
    """
    try:
        await callback.message.delete()
        await callback.answer("Menú cerrado")
    except Exception as e:
        logger.error(f"Error cerrando menú Free para {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cerrando menú", show_alert=True)


__all__ = ["free_callbacks_router"]
