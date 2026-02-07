"""
Free Callback Handlers - Gestión de interacciones del menú Free.

Responsabilidades:
- Manejar callback "free:approved:enter" - enviar menú tras aprobación
- Manejar callback "menu:free:content" - mostrar sección "Mi Contenido"
- Manejar callback "menu:free:vip" - mostrar información del canal VIP
- Manejar callback "menu:free:social" - mostrar redes sociales/contenido gratuito
- Manejar interés en paquetes FREE_CONTENT
- Navegación (volver, salir)

Pattern: Sigue estructura de VIP callbacks con router separado.
"""
import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.database.enums import ContentCategory
from bot.handlers.utils import send_admin_interest_notification
from bot.middlewares import DatabaseMiddleware

logger = logging.getLogger(__name__)

# Create router
free_callbacks_router = Router()

# Apply middleware to this router (required for container injection)
free_callbacks_router.callback_query.middleware(DatabaseMiddleware())


@free_callbacks_router.callback_query(lambda c: c.data == "free:approved:enter")
async def handle_free_approved_enter(callback: CallbackQuery, container):
    """
    Maneja el clic en "Ingresar al canal" desde el mensaje de aprobación.

    Envía el menú Free al usuario cuando hace clic en el botón
    después de ser aceptado en el canal.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Confirmar recepción del callback
        await callback.answer("✅ Bienvenido a Los Kinkys")

        # Preparar data para el menú
        data = {"container": container}

        # Enviar el menú Free
        from .menu import show_free_menu
        await show_free_menu(
            callback.message,
            data,
            user_id=user.id,
            user_first_name=user.first_name
        )

        logger.info(f"🆓 Menú Free enviado a usuario aprobado {user.id}")

    except Exception as e:
        logger.error(f"Error enviando menú Free a usuario aprobado {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando el menú", show_alert=True)


# Register SPECIFIC handlers BEFORE GENERIC ones to avoid pattern matching conflicts
# "user:packages:back" must be registered before "user:packages:{id}"

@free_callbacks_router.callback_query(lambda c: c.data == "free:packages:back")
async def handle_packages_back_to_list(callback: CallbackQuery, container):
    """
    Vuelve al listado de paquetes Free (desde vista de detalle o confirmación).

    Reutiliza handle_free_content() para consistencia.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    await handle_free_content(callback, container)


@free_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("free:packages:back:"))
async def handle_packages_back_with_role(callback: CallbackQuery, container):
    """
    Vuelve al listado de paquetes desde confirmación de interés (con user_role y source_section).

    Callback data formats:
    - "free:packages:back:{user_role}" (legacy)
    - "free:packages:back:{user_role}:{source_section}" (new)

    Siempre vuelve al listado Free (router Free).

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    # Free users always return to free content section
    # No need to parse source_section as Free users only have one section
    await handle_free_content(callback, container)


@free_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("free:packages:"))
async def handle_package_detail(callback: CallbackQuery, container):
    """
    Muestra vista detallada de un paquete específico.

    Callback data format: "user:packages:{package_id}"

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Fetch package from ContentService
        package = await container.content.get_package(package_id)

        if not package:
            await callback.answer("⚠️ Paquete no encontrado", show_alert=True)
            logger.warning(f"⚠️ Usuario Free {user.id} solicitó paquete inexistente: {package_id}")
            return

        # Get session context for message variations
        session_ctx = None
        try:
            session_ctx = container.message.get_session_context(container)
        except Exception as e:
            logger.warning(f"No se pudo obtener contexto de sesión para {user.id}: {e}")

        # Generate detail view using UserMenuMessages
        # Pass source_section="free" to ensure back button returns to free content section
        text, keyboard = container.message.user.menu.package_detail_view(
            package=package,
            user_role="Free",
            user_id=user.id,
            session_history=session_ctx,
            source_section="free"
        )

        # Update message with detail view
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

        logger.info(f"📦 Vista detallada mostrada a usuario Free {user.id}: {package.name}")

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error mostrando detalle de paquete para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando detalles del paquete", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("free:package:interest:"))
async def handle_package_interest_confirm(callback: CallbackQuery, container):
    """
    Registra interés en paquete y muestra mensaje de confirmación con contacto directo.

    Callback data format: "user:package:interest:{package_id}"

    Flujo:
    1. Extraer package_id del callback
    2. Fetch paquete desde ContentService
    3. Registrar interés usando InterestService (con deduplicación de 5 min)
    4. Si success=True:
       - Enviar notificación admin (reutilizar _send_admin_interest_notification)
       - Mostrar confirmación con botón "Escribirme" (tg://resolve link)
       - Botones de navegación: "Regresar" (a listado) e "Inicio" (a menú Free)
    5. Si success=False y status=="debounce":
       - Feedback sutil: "Interés registrado previamente"
       - NO actualizar mensaje ni enviar notificación
    6. Si success=False (error):
       - Mostrar alerta de error

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Fetch package from ContentService
        package = await container.content.get_package(package_id)

        if not package:
            await callback.answer("⚠️ Paquete no encontrado", show_alert=True)
            logger.warning(f"⚠️ Usuario Free {user.id} solicitó paquete inexistente: {package_id}")
            return

        # Register interest using InterestService (with deduplication)
        success, status, interest = await container.interest.register_interest(
            user_id=user.id,
            package_id=package_id
        )

        if success:
            # New interest or re-interest after debounce window
            logger.info(
                f"✅ Usuario Free {user.id} ({user.first_name}) interesado en paquete {package_id} "
                f"(status: {status})"
            )

            # Send admin notification (using shared function)
            await send_admin_interest_notification(
                bot=callback.bot,
                container=container,
                user=user,
                package=interest.package,
                interest=interest,
                user_role="Free"
            )

            # Get session context for message variations
            session_ctx = None
            try:
                session_ctx = container.message.get_session_context(container)
            except Exception as e:
                logger.warning(f"No se pudo obtener contexto de sesión para {user.id}: {e}")

            # Generate confirmation message with contact button
            # source_section="free" ensures back button returns to free content section
            text, keyboard = container.message.user.flows.package_interest_confirmation(
                user_name=user.first_name or "Usuario",
                package_name=package.name,
                user_role="Free",
                user_id=user.id,
                session_history=session_ctx,
                source_section="free"
            )

            # Update message with confirmation
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer("✅ Interés registrado")

        else:
            # Debounce window active - no notification, no message update
            if status == "debounce":
                logger.debug(
                    f"⏱️ Interés de usuario Free {user.id} en paquete {package_id} "
                    f"ignorado (ventana de debounce activa)"
                )
                # Show subtle feedback (no alert, just toast)
                await callback.answer("✅ Interés registrado previamente")
            else:
                # Error occurred
                logger.error(
                    f"❌ Error registrando interés para usuario Free {user.id}: {status}"
                )
                await callback.answer(
                    "⚠️ Error registrando interés",
                    show_alert=True
                )

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error registrando interés para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error registrando interés", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:content")
async def handle_free_content(callback: CallbackQuery, container):
    """
    Muestra sección "Mi Contenido" con paquetes FREE_CONTENT.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
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
        await callback.answer("⚠️ Error cargando promos", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:vip")
async def handle_vip_info(callback: CallbackQuery, container):
    """
    Muestra información sobre el canal VIP y suscripción.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
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

        # Texto fijo para El Diván según diseño
        message_text = (
            "🫦 <b>Diana:</b>\n\n"
            "💎 <b>El Diván de Diana</b> 💎\n"
            "No es para cualquiera.\n\n"
            "El Diván es mi espacio privado.\n"
            "Donde no actúo.\n"
            "Donde no filtro.\n"
            "Y donde no explico.\n\n"
            "Aquí no muestro \"un poco más\".\n"
            "Aquí me muestro completa.\n\n"
            "Lo que ocurre dentro:\n"
            "<b>Más de 3,000 archivos</b> (si, tres mil) entre fotos y videos que no existen fuera del Diván.\n"
            "<b>Contenido sin censura</b> que no vendo por separado.\n"
            "<b>Acceso preferente</b> a contenido Premium.\n"
            "<b>Descuento VIP</b> en contenido personalizado.\n"
            "<b>Historias privadas</b> que solo ve quien se atreve a quedarse.\n\n"
            "Acceso\n"
            "<b>$350 MXN</b> / 23 USD al mes.\n"
            "Sin pruebas.\n"
            "Sin recorridos.\n"
            "Sin curiosos.\n\n"
            "El Diván sigue intacto.\n"
            "Sin máscaras.\n"
            "Sin inocencia.\n\n"
            "Solo tú y yo…\n"
            "si sabes entrar sin hacer ruido."
        )

        # Create keyboard with "Me interesa" button and navigation
        from bot.utils.keyboards import create_content_with_navigation

        content_buttons = [
            [{"text": "⭐ Me interesa", "callback_data": "vip:subscription:interest"}]
        ]

        keyboard = create_content_with_navigation(
            content_buttons=content_buttons,
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
async def handle_social_media(callback: CallbackQuery):
    """
    Muestra redes sociales y contenido gratuito adicional.

    Args:
        callback: CallbackQuery de Telegram
    """
    user = callback.from_user

    try:
        # Solo cabecera y botones de redes sociales
        message_text = "🫦 <b>Diana:</b>\n\nMis redes"

        # Create keyboard with social media buttons
        from bot.utils.keyboards import create_content_with_navigation

        social_buttons = [
            [{"text": "📷 Instagram @srta.kinky", "url": "https://instagram.com/srta.kinky"}],
            [{"text": "📷 Instagram @ella.es.diana", "url": "https://instagram.com/ella.es.diana"}],
            [{"text": "🎵 TikTok @srtakinky", "url": "https://tiktok.com/@srtakinky"}],
            [{"text": "🐦 X @SrtaKinky", "url": "https://x.com/SrtaKinky"}],
        ]

        keyboard = create_content_with_navigation(
            content_buttons=social_buttons,
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
async def handle_package_interest(callback: CallbackQuery, container):
    """
    Registra interés de usuario en paquete FREE_CONTENT y notifica a admins.

    Reutiliza lógica de VIP callbacks para consistencia.

    Callback data format: "interest:package:{package_id}"

    Flujo:
    1. Extraer package_id del callback
    2. Registrar interés usando InterestService (con deduplicación de 5 min)
    3. Si success=True (nuevo o re-interés después de ventana):
       - Enviar notificación privada a todos los admins
       - Notificación incluye: usuario, link al perfil, paquete, timestamp
       - Botones inline: Ver todos, Marcar atendido, Mensaje usuario, Bloquear
    4. Si success=False (debounce):
       - No enviar notificación
       - Mostrar feedback sutil al usuario

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Register interest using InterestService (with deduplication)
        success, status, interest = await container.interest.register_interest(
            user_id=user.id,
            package_id=package_id
        )

        if success:
            # New interest or re-interest after debounce window
            logger.info(
                f"✅ Usuario Free {user.id} ({user.first_name}) interesado en paquete {package_id} "
                f"(status: {status})"
            )

            # Send admin notification (using shared function)
            await send_admin_interest_notification(
                bot=callback.bot,
                container=container,
                user=user,
                package=interest.package,
                interest=interest,
                user_role="Free"
            )

            # Show success feedback to user
            await callback.answer(
                "✅ Tu interés ha sido registrado. Diana será notificada.",
                show_alert=True
            )
        else:
            # Debounce window active - no notification
            if status == "debounce":
                logger.debug(
                    f"⏱️ Interés de usuario Free {user.id} en paquete {package_id} "
                    f"ignorado (ventana de debounce activa)"
                )
                # Show subtle feedback (no alert, just toast)
                await callback.answer("✅ Interés registrado previamente")
            else:
                # Error occurred
                logger.error(
                    f"❌ Error registrando interés para usuario Free {user.id}: {status}"
                )
                await callback.answer(
                    "⚠️ Error registrando interés",
                    show_alert=True
                )

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error registrando interés para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error registrando interés", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "menu:free:main")
async def handle_menu_back(callback: CallbackQuery, container):
    """
    Vuelve al menú principal Free.

    Este handler sirve tanto para "menu:free:main" (desde confirmación de interés)
    como para "menu:back" (desde otras secciones del menú Free).

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Build data dict for menu handler
        data = {"container": container}
        # IMPORTANT: Pass user_id and user_first_name from callback, not from message
        # When bot edits its own messages, message.from_user is the bot, not the user
        from .menu import show_free_menu
        await show_free_menu(
            callback.message,
            data,
            user_id=user.id,
            user_first_name=user.first_name,
            edit_mode=True
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error volviendo al menú Free para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error volviendo al menú", show_alert=True)


@free_callbacks_router.callback_query(lambda c: c.data == "vip:subscription:interest")
async def handle_vip_subscription_interest(callback: CallbackQuery, container, session):
    """
    Registra interés en suscripción VIP y notifica a administradores.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
        session: Sesión de base de datos inyectada por middleware
    """
    user = callback.from_user

    if not container or not session:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    try:
        # Verificar si ya existe interés reciente (ventana de 5 minutos)
        from datetime import datetime, timedelta
        from bot.database.models import UserInterest
        from sqlalchemy import select, and_

        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

        # Buscar interés reciente específico de suscripción VIP (package_id=None)
        result = await session.execute(
            select(UserInterest).where(
                and_(
                    UserInterest.user_id == user.id,
                    UserInterest.package_id == None,
                    UserInterest.created_at >= five_minutes_ago
                )
            )
        )
        existing_interest = result.scalar_one_or_none()

        if existing_interest:
            await callback.answer(
                "✅ Tu interés ya fue registrado. Diana será notificada.",
                show_alert=True
            )
            return

        # Crear registro de interés especial para suscripción VIP
        # Usamos package_id=None para indicar interés en suscripción general
        interest = UserInterest(
            user_id=user.id,
            package_id=None,  # None indica interés en suscripción VIP
            is_attended=False,
            attended_at=None,
            created_at=datetime.utcnow()
        )

        # Guardar en base de datos
        session.add(interest)
        await session.flush()  # Para obtener el ID

        # Notificar a administradores
        from bot.handlers.utils import send_admin_interest_notification

        # Crear objeto paquete ficticio para la notificación
        class VIPPackage:
            def __init__(self):
                self.name = "Suscripción VIP - El Diván"
                self.id = 0

        vip_package = VIPPackage()

        await send_admin_interest_notification(
            bot=callback.bot,
            container=container,
            user=user,
            package=vip_package,
            interest=interest,
            user_role="Free (Interés VIP)"
        )

        # Mostrar confirmación con botón "Escribirme" y navegación
        text, keyboard = container.message.user.flows.package_interest_confirmation(
            user_name=user.first_name or "Usuario",
            package_name="Suscripción VIP - El Diván",
            user_role="Free",
            user_id=user.id,
            source_section="vip"
        )

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer("✅ Interés registrado")

        logger.info(f"💎 Interés en suscripción VIP registrado: user {user.id}")

    except Exception as e:
        logger.error(f"Error registrando interés VIP para {user.id}: {e}", exc_info=True)
        await callback.answer(
            "⚠️ Error registrando interés. Intenta de nuevo más tarde.",
            show_alert=True
        )


# DISABLED: Exit button removed from navigation (Quick Task 002)
# @free_callbacks_router.callback_query(lambda c: c.data == "menu:exit")
# async def handle_menu_exit(callback: CallbackQuery):
#     """
#     Cierra el menú Free (elimina mensaje).
#
#     Args:
#         callback: CallbackQuery de Telegram
#     """
#     try:
#         await callback.message.delete()
#         await callback.answer("Menú cerrado")
#     except Exception as e:
#         logger.error(f"Error cerrando menú Free para {callback.from_user.id}: {e}", exc_info=True)
#         await callback.answer("⚠️ Error cerrando menú", show_alert=True)


__all__ = ["free_callbacks_router"]
