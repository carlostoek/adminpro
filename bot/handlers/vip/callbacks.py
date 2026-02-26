"""
VIP Callback Handlers - Gestión de interacciones del menú VIP.

Responsabilidades:
- Manejar callback "vip:premium" - mostrar sección premium
- Manejar callback "vip:free_content" - VIP accediendo a contenido Free
- Manejar callback "vip:packages:*" - navegación de paquetes VIP
- Manejar callback "vip:free:packages:*" - VIP viendo paquetes Free
- Manejar callback "vip:package:interest:*" - registrar interés VIP
- Manejar callback "menu:back" - volver al menú principal VIP
- Manejar callback "menu:exit" - cerrar menú

Pattern: Sigue estructura de admin callbacks con router separado.
"""
import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.database.enums import ContentCategory, UserRole
from bot.handlers.utils import send_admin_interest_notification, require_vip

logger = logging.getLogger(__name__)

# Create router
vip_callbacks_router = Router()

# DatabaseMiddleware is applied globally in main.py - no local middleware needed


@vip_callbacks_router.callback_query(lambda c: c.data == "vip:premium")
async def handle_vip_premium(callback: CallbackQuery, container):
    """
    Muestra sección premium con paquetes VIP_PREMIUM.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    logger.info(f"🔍 VIP PREMIUM callback: data={callback.data}, container={container is not None}")
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    # VALIDACIÓN: Solo VIP/Admin puede acceder
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
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


@vip_callbacks_router.callback_query(lambda c: c.data == "vip:free_content")
async def handle_vip_free_content(callback: CallbackQuery, container):
    """
    Muestra contenido Free a un usuario VIP.

    Permite que los usuarios VIP accedan al contenido Free desde su menú.
    Reutiliza la lógica de free_content_section pero con callbacks vip:free:*

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    # VALIDACIÓN: Solo VIP/Admin puede acceder
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
        return

    try:
        # Get active FREE_CONTENT packages
        packages = await container.content.get_active_packages(
            category=ContentCategory.FREE_CONTENT,
            limit=20
        )

        # Get session context for message variations
        session_ctx = container.message.get_session_context(container)

        # Generate Free content section for VIP using dedicated method
        text, keyboard = container.message.user.menu.vip_free_content_section(
            user_name=user.first_name or "miembro",
            packages=packages,
            user_id=user.id,
            session_history=session_ctx
        )

        # Update message with Free content section
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

        logger.info(f"🌸 Sección Free mostrada a VIP {user.id} ({len(packages)} paquetes)")

    except Exception as e:
        logger.error(f"Error mostrando contenido Free a VIP {user.id}: {e}")
        await callback.answer("⚠️ Error cargando promos", show_alert=True)


# Register SPECIFIC handlers BEFORE GENERIC ones to avoid pattern matching conflicts
# "vip:packages:back" must be registered before "vip:packages:{id}"

@vip_callbacks_router.callback_query(lambda c: c.data == "vip:packages:back")
async def handle_packages_back_to_list(callback: CallbackQuery, container):
    """
    Vuelve al listado de paquetes VIP (desde vista de detalle o confirmación).

    Reutiliza handle_vip_premium() para consistencia.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    await handle_vip_premium(callback, container)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("vip:packages:back:"))
async def handle_packages_back_with_role(callback: CallbackQuery, container):
    """
    Vuelve al listado de paquetes desde confirmación de interés (con user_role y source_section).

    Callback data formats:
    - "vip:packages:back:{user_role}" (legacy, defaults to premium)
    - "vip:packages:back:{user_role}:{source_section}" (new, source_section="premium" or "free")

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    try:
        # Parse callback data to extract source_section
        # Format: vip:packages:back:VIP:source_section or vip:packages:back:VIP
        parts = callback.data.split(":")

        # Check if source_section is provided (new format)
        if len(parts) >= 5:
            source_section = parts[4]
            if source_section == "free":
                await handle_vip_free_content(callback, container)
                return
            # If premium or unknown, fall through to premium handler

        # Default: return to premium section
        await handle_vip_premium(callback, container)

    except Exception as e:
        logger.error(f"Error parsing back callback {callback.data}: {e}")
        # Fallback to premium section on error
        await handle_vip_premium(callback, container)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("vip:packages:"))
async def handle_package_detail(callback: CallbackQuery, container):
    """
    Muestra vista detallada de un paquete específico.

    Callback data format: "vip:packages:{package_id}"

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    # VALIDACIÓN: Solo VIP/Admin puede acceder
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Fetch package from ContentService
        package = await container.content.get_package(package_id)

        if not package:
            await callback.answer("⚠️ Paquete no encontrado", show_alert=True)
            logger.warning(f"⚠️ Usuario VIP {user.id} solicitó paquete inexistente: {package_id}")
            return

        # Get session context for message variations
        session_ctx = container.message.get_session_context(container)

        # Generate detail view using UserMenuMessages
        # Pass source_section="premium" to ensure back button returns to premium section
        text, keyboard = container.message.user.menu.package_detail_view(
            package=package,
            user_role="VIP",
            user_id=user.id,
            session_history=session_ctx,
            source_section="premium"
        )

        # Update message with detail view
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

        logger.info(f"📦 Vista detallada mostrada a usuario VIP {user.id}: {package.name}")

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error mostrando detalle de paquete para {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando detalles del paquete", show_alert=True)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("vip:package:interest:"))
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
       - Botones de navegación: "Regresar" (a listado) e "Inicio" (a menú VIP)
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

    # VALIDACIÓN: Solo VIP/Admin puede registrar interés
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Fetch package from ContentService
        package = await container.content.get_package(package_id)

        if not package:
            await callback.answer("⚠️ Paquete no encontrado", show_alert=True)
            logger.warning(f"⚠️ Usuario VIP {user.id} solicitó paquete inexistente: {package_id}")
            return

        # Register interest using InterestService (with deduplication)
        success, status, interest = await container.interest.register_interest(
            user_id=user.id,
            package_id=package_id
        )

        if success:
            # New interest or re-interest after debounce window
            logger.info(
                f"✅ Usuario VIP {user.id} ({user.first_name}) interesado en paquete {package_id} "
                f"(status: {status})"
            )

            # Send admin notification (using shared function)
            await send_admin_interest_notification(
                bot=callback.bot,
                container=container,
                user=user,
                package=interest.package,
                interest=interest,
                user_role="VIP"
            )

            # Get session context for message variations
            session_ctx = container.message.get_session_context(container)

            # Generate confirmation message with contact button
            # source_section="premium" ensures back button returns to premium section
            text, keyboard = container.message.user.flows.package_interest_confirmation(
                user_name=user.first_name or "Usuario",
                package_name=package.name,
                user_role="VIP",
                user_id=user.id,
                session_history=session_ctx,
                source_section="premium"
            )

            # Update message with confirmation
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
            await callback.answer("✅ Interés registrado")

        else:
            # Debounce window active - no notification, no message update
            if status == "debounce":
                logger.debug(
                    f"⏱️ Interés de usuario VIP {user.id} en paquete {package_id} "
                    f"ignorado (ventana de debounce activa)"
                )
                # Show subtle feedback (no alert, just toast)
                await callback.answer("✅ Interés registrado previamente")
            else:
                # Error occurred
                logger.error(
                    f"❌ Error registrando interés para usuario VIP {user.id}: {status}"
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


@vip_callbacks_router.callback_query(lambda c: c.data == "vip:status")
async def handle_vip_status(callback: CallbackQuery, container):
    """
    Muestra el estado de la membresía VIP del usuario.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    # VALIDACIÓN: Solo VIP/Admin puede ver estado VIP
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
        return

    try:
        # Get VIP subscription info
        subscriber = await container.subscription.get_vip_subscriber(user.id)

        if subscriber and subscriber.expiry_date:
            expiry_date = subscriber.expiry_date.strftime("%d de %B de %Y")
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
async def handle_package_interest(callback: CallbackQuery, container):
    """
    Registra interés de usuario en paquete y notifica a admins.

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
                f"✅ Usuario VIP {user.id} ({user.first_name}) interesado en paquete {package_id} "
                f"(status: {status})"
            )

            # Send admin notification (using shared function)
            await send_admin_interest_notification(
                bot=callback.bot,
                container=container,
                user=user,
                package=interest.package,
                interest=interest,
                user_role="VIP"
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
                    f"⏱️ Interés de usuario VIP {user.id} en paquete {package_id} "
                    f"ignorado (ventana de debounce activa)"
                )
                # Show subtle feedback (no alert, just toast)
                await callback.answer("✅ Interés registrado previamente")
            else:
                # Error occurred
                logger.error(
                    f"❌ Error registrando interés para usuario VIP {user.id}: {status}"
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


@vip_callbacks_router.callback_query(lambda c: c.data == "menu:vip:main")
async def handle_menu_vip_main(callback: CallbackQuery, container):
    """
    Vuelve al menú principal VIP (desde confirmación de interés).

    Reutiliza handle_menu_back() para consistencia con Phase 6.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    await handle_menu_back(callback, container)


@vip_callbacks_router.callback_query(lambda c: c.data == "menu:back")
async def handle_menu_back(callback: CallbackQuery, container):
    """
    Vuelve al menú principal VIP.

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
        # Re-show VIP menu (reusing show_vip_menu logic)
        # IMPORTANT: Pass user_id and user_first_name from callback, not from message
        # When bot edits its own messages, message.from_user is the bot, not the user
        from .menu import show_vip_menu
        await show_vip_menu(
            callback.message,
            data,
            user_id=user.id,
            user_first_name=user.first_name,
            edit_mode=True
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error volviendo al menú VIP para {user.id}: {e}")
        await callback.answer("⚠️ Error volviendo al menú", show_alert=True)


# DISABLED: Exit button removed from navigation (Quick Task 002)
# @vip_callbacks_router.callback_query(lambda c: c.data == "menu:exit")
# async def handle_menu_exit(callback: CallbackQuery):
#     """
#     Cierra el menú (elimina mensaje).
#
#     Args:
#         callback: CallbackQuery de Telegram
#     """
#     try:
#         await callback.message.delete()
#         await callback.answer("Menú cerrado")
#     except Exception as e:
#         logger.error(f"Error cerrando menú para {callback.from_user.id}: {e}")
#         await callback.answer("⚠️ Error cerrando menú", show_alert=True)


# ===== VIP VIEWING FREE CONTENT HANDLERS =====
# These handlers allow VIP users to browse and interact with Free content

@vip_callbacks_router.callback_query(lambda c: c.data == "vip:free:packages:back")
async def handle_vip_free_packages_back(callback: CallbackQuery, container):
    """
    VIP returning from Free package detail back to Free content list.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    # Reuse the same handler as entering Free content
    await handle_vip_free_content(callback, container)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("vip:free:packages:"))
async def handle_vip_free_package_detail(callback: CallbackQuery, container):
    """
    Muestra vista detallada de un paquete Free a un usuario VIP.

    Callback data format: "vip:free:packages:{package_id}"

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    # VALIDACIÓN: Solo VIP/Admin puede acceder
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Fetch package from ContentService
        package = await container.content.get_package(package_id)

        if not package:
            await callback.answer("⚠️ Paquete no encontrado", show_alert=True)
            logger.warning(f"⚠️ VIP {user.id} solicitó paquete Free inexistente: {package_id}")
            return

        # Get session context for message variations
        session_ctx = container.message.get_session_context(container)

        # Generate detail view using UserMenuMessages with VIP context
        # Pass user_role="VIP" so the message uses VIP voice
        # Pass source_section="free" to ensure back button returns to free content section
        text, keyboard = container.message.user.menu.package_detail_view(
            package=package,
            user_role="VIP",
            user_id=user.id,
            session_history=session_ctx,
            source_section="free"
        )

        # Update message with detail view
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()

        logger.info(f"📦 VIP {user.id} viendo detalle de paquete Free: {package.name}")

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error mostrando detalle de paquete Free a VIP {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error cargando detalles del paquete", show_alert=True)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("vip:free:package:interest:"))
async def handle_vip_free_package_interest(callback: CallbackQuery, container):
    """
    VIP registrando interés en un paquete Free.

    Callback data format: "vip:free:package:interest:{package_id}"

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    user = callback.from_user

    if not container:
        await callback.answer("⚠️ Error: servicio no disponible", show_alert=True)
        return

    # VALIDACIÓN: Solo VIP/Admin puede registrar interés
    has_access = await require_vip(callback, container, redirect=True)
    if not has_access:
        return

    try:
        # Extract package ID from callback data
        package_id_str = callback.data.split(":")[-1]
        package_id = int(package_id_str)

        # Fetch package from ContentService
        package = await container.content.get_package(package_id)

        if not package:
            await callback.answer("⚠️ Paquete no encontrado", show_alert=True)
            logger.warning(f"⚠️ VIP {user.id} solicitó paquete Free inexistente: {package_id}")
            return

        # Register interest using InterestService (with deduplication)
        success, status, interest = await container.interest.register_interest(
            user_id=user.id,
            package_id=package_id
        )

        if success:
            # New interest or re-interest after debounce window
            logger.info(
                f"✅ VIP {user.id} ({user.first_name}) interesado en paquete Free {package_id} "
                f"(status: {status})"
            )

            # Send admin notification
            await _send_admin_interest_notification(
                bot=callback.bot,
                container=container,
                user=user,
                package=interest.package,
                interest=interest,
                user_role="VIP"
            )

            # Get session context for message variations
            session_ctx = container.message.get_session_context(container)

            # Generate confirmation message with contact button
            # source_section="free" ensures back button returns to free content section
            text, keyboard = container.message.user.flows.package_interest_confirmation(
                user_name=user.first_name or "Usuario",
                package_name=package.name,
                user_role="VIP",
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
                    f"⏱️ Interés de VIP {user.id} en paquete Free {package_id} "
                    f"ignorado (ventana de debounce activa)"
                )
                # Show subtle feedback (no alert, just toast)
                await callback.answer("✅ Interés registrado previamente")
            else:
                # Error occurred
                logger.error(
                    f"❌ Error registrando interés para VIP {user.id}: {status}"
                )
                await callback.answer(
                    "⚠️ Error registrando interés",
                    show_alert=True
                )

    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing package ID from callback {callback.data}: {e}")
        await callback.answer("⚠️ Error: ID de paquete inválido", show_alert=True)
    except Exception as e:
        logger.error(f"Error registrando interés para VIP {user.id}: {e}", exc_info=True)
        await callback.answer("⚠️ Error registrando interés", show_alert=True)


__all__ = ["vip_callbacks_router"]
