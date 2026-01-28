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
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.database.enums import ContentCategory
from bot.middlewares import DatabaseMiddleware
from config import Config

logger = logging.getLogger(__name__)

# Create router
vip_callbacks_router = Router()

# Apply middleware to this router (required for container injection)
vip_callbacks_router.callback_query.middleware(DatabaseMiddleware())


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


# Register SPECIFIC handlers BEFORE GENERIC ones to avoid pattern matching conflicts
# "user:packages:back" must be registered before "user:packages:{id}"

@vip_callbacks_router.callback_query(lambda c: c.data == "user:packages:back")
async def handle_packages_back_to_list(callback: CallbackQuery, container):
    """
    Vuelve al listado de paquetes VIP (desde vista de detalle o confirmación).

    Reutiliza handle_vip_premium() para consistencia.

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    await handle_vip_premium(callback, container)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("user:packages:back:"))
async def handle_packages_back_with_role(callback: CallbackQuery, container):
    """
    Vuelve al listado de paquetes desde confirmación de interés (con user_role).

    Callback data format: "user:packages:back:{user_role}"

    Ignora el user_role y siempre vuelve al listado VIP (router VIP).

    Args:
        callback: CallbackQuery de Telegram
        container: ServiceContainer inyectado por middleware
    """
    await handle_vip_premium(callback, container)


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("user:packages:"))
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
            logger.warning(f"⚠️ Usuario VIP {user.id} solicitó paquete inexistente: {package_id}")
            return

        # Get session context for message variations
        session_ctx = container.message.get_session_context(container)

        # Generate detail view using UserMenuMessages
        text, keyboard = container.message.user.menu.package_detail_view(
            package=package,
            user_role="VIP",
            user_id=user.id,
            session_history=session_ctx
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


@vip_callbacks_router.callback_query(lambda c: c.data and c.data.startswith("user:package:interest:"))
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

            # Send admin notification (reuse existing function)
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
            text, keyboard = container.message.user.flows.package_interest_confirmation(
                user_name=user.first_name or "Usuario",
                package_name=package.name,
                user_role="VIP",
                user_id=user.id,
                session_history=session_ctx
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

            # Send admin notification (INTEREST-03, INTEREST-04 requirements)
            await _send_admin_interest_notification(
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


async def _send_admin_interest_notification(
    bot,
    container,
    user,
    package,
    interest,
    user_role: str
):
    """
    Envía notificación privada a todos los admins sobre nuevo interés.

    Args:
        bot: Instancia del bot
        container: ServiceContainer
        user: Usuario de Telegram (callback.from_user)
        package: Objeto ContentPackage
        interest: Objeto UserInterest
        user_role: "VIP" o "Free"
    """
    try:
        # Get all admin user IDs from config (environment variable)
        admin_ids = Config.ADMIN_USER_IDS

        if not admin_ids:
            logger.warning("⚠️ No admins configured for interest notifications")
            return

        # Format user info
        username = f"@{user.username}" if user.username else f"usuario {user.id}"
        user_link = f"tg://user?id={user.id}"

        # Format package info
        package_type_emoji = {
            "VIP_PREMIUM": "💎",
            "VIP_CONTENT": "👑",
            "FREE_CONTENT": "🌸"
        }.get(package.category.value if hasattr(package.category, 'value') else str(package.category), "📦")

        # Build notification message in Lucien's voice
        notification_text = (
            f"🎩 <b>Lucien:</b> <i>Nueva expresión de interés detectada...</i>\n\n"
            f"<b>👤 Visitante:</b> {username} ({user_role})\n"
            f"<b>📦 Tesoro de interés:</b> {package_type_emoji} {package.name}\n"
            f"<b>📝 Descripción:</b> {package.description or 'Sin descripción'}\n"
        )

        if package.price is not None:
            notification_text += f"<b>💰 Precio:</b> ${package.price:.2f}"
        else:
            notification_text += "<b>💰 Precio:</b> Gratuito"

        if package.category:
            type_text = {
                "VIP_PREMIUM": "Premium Exclusivo",
                "VIP_CONTENT": "Contenido VIP",
                "FREE_CONTENT": "Contenido Gratuito"
            }.get(package.category.value, str(package.category))
            notification_text += f"\n<b>🏷️ Tipo:</b> {type_text}"

        notification_text += (
            f"\n\n<b>⏰ Momento:</b> {interest.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"<i>Diana, un miembro del círculo ha mostrado interés en uno de sus tesoros...</i>"
        )

        # Create inline keyboard with action buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Ver Todos los Intereses",
                    callback_data=f"admin:interests:list:pending"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Marcar como Atendido",
                    callback_data=f"admin:interest:attend:{interest.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Mensaje al Usuario",
                    url=user_link
                ),
                InlineKeyboardButton(
                    text="🚫 Bloquear Contacto",
                    callback_data=f"admin:user:block_contact:{user.id}"
                )
            ]
        ])

        # Send notification to all admins
        sent_count = 0
        failed_admins = []

        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                sent_count += 1
                logger.debug(f"📤 Interest notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(
                    f"❌ Failed to send interest notification to admin {admin_id}: {e}"
                )
                failed_admins.append(admin_id)

        logger.info(
            f"📢 Interest notification sent to {sent_count}/{len(admin_ids)} admins "
            f"(user: {user.id}, package: {package.id}, role: {user_role})"
        )

        if failed_admins:
            logger.warning(
                f"⚠️ Failed to send to admins: {failed_admins} "
                f"(may have blocked the bot or deleted chat)"
            )

    except Exception as e:
        logger.error(f"Error sending admin interest notification: {e}", exc_info=True)


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
