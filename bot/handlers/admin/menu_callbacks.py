"""
Menu Callbacks Handlers - Conecta los callbacks del menú principal con handlers existentes.

Este módulo resuelve el problema de "No handler" para los botones del menú admin
conectando los callbacks definidos en menu.py con los handlers existentes en otros módulos.
"""
import logging
from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.container import ServiceContainer
from bot.utils.keyboards import create_inline_keyboard

logger = logging.getLogger(__name__)


async def callback_vip_management(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a menú VIP (usa handler existente admin:vip).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"👑 Usuario {callback.from_user.id} abriendo gestión VIP desde menú")

    try:
        # Redirigir al handler existente admin:vip
        from bot.handlers.admin.vip import callback_vip_menu
        await callback_vip_menu(callback, session)
    except ImportError as e:
        logger.error(f"❌ Error importando handler VIP: {e}")
        await callback.answer("❌ Error al cargar menú VIP", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_vip_management: {e}", exc_info=True)
        await callback.answer("❌ Error al abrir menú VIP", show_alert=True)


async def callback_list_vips(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a listado de suscriptores VIP (usa handler existente vip:list_subscribers).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📊 Usuario {callback.from_user.id} listando VIPs desde menú")

    try:
        # Redirigir al handler existente vip:list_subscribers
        from bot.handlers.admin.management import callback_list_vip_subscribers
        await callback_list_vip_subscribers(callback, session)
    except ImportError as e:
        logger.error(f"❌ Error importando handler listado VIP: {e}")
        await callback.answer("❌ Error al cargar listado VIP", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_list_vips: {e}", exc_info=True)
        await callback.answer("❌ Error al listar VIPs", show_alert=True)


async def callback_generate_vip_token(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a generación de token VIP (usa handler existente vip:generate_token).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"🔑 Usuario {callback.from_user.id} generando token VIP desde menú")

    try:
        # Redirigir al handler existente vip:generate_token_select_plan
        from bot.handlers.admin.vip import callback_generate_token_select_plan
        await callback_generate_token_select_plan(callback, session)
    except ImportError as e:
        logger.error(f"❌ Error importando handler generación de token VIP: {e}")
        await callback.answer("❌ Error al generar token VIP", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_generate_vip_token: {e}", exc_info=True)
        await callback.answer("❌ Error al generar token", show_alert=True)


async def callback_content_management(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a gestión de contenido (usa handler existente admin:content).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📦 Usuario {callback.from_user.id} abriendo gestión de contenido desde menú")

    try:
        # Redirigir al handler existente admin:content en content.py
        from bot.handlers.admin.content import callback_content_menu
        await callback_content_menu(callback, session)
    except ImportError as e:
        logger.error(f"❌ Error importando handler gestión de contenido: {e}")
        await callback.answer("❌ Error al cargar menú de contenido", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_content_management: {e}", exc_info=True)
        await callback.answer("❌ Error al abrir menú de contenido", show_alert=True)


async def callback_create_package(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a creación de paquete (usa handler existente admin:content:create:start).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"➕ Usuario {callback.from_user.id} creando paquete desde menú")

    try:
        # Primero ir al menú de contenido
        await callback_content_management(callback, session)
    except Exception as e:
        logger.error(f"❌ Error en callback_create_package: {e}", exc_info=True)
        await callback.answer("❌ Error al crear paquete", show_alert=True)


async def callback_list_packages(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a listado de paquetes (usa handler existente admin:content:list).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"📋 Usuario {callback.from_user.id} listando paquetes desde menú")

    try:
        # Redirigir al handler existente admin:content:list
        from bot.handlers.admin.content import callback_content_list
        await callback_content_list(callback, session)
    except ImportError as e:
        logger.error(f"❌ Error importando handler listado de paquetes: {e}")
        await callback.answer("❌ Error al cargar listado de paquetes", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_list_packages: {e}", exc_info=True)
        await callback.answer("❌ Error al listar paquetes", show_alert=True)


async def callback_free_queue(callback: CallbackQuery, session: AsyncSession):
    """
    Redirige a visualización de cola Free (usa handler existente free:view_queue).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"🆓 Usuario {callback.from_user.id} viendo cola Free desde menú")

    try:
        # Redirigir al handler existente free:view_queue
        from bot.handlers.admin.management import callback_view_free_queue
        await callback_view_free_queue(callback, session)
    except ImportError as e:
        logger.error(f"❌ Error importando handler cola Free: {e}")
        await callback.answer("❌ Error al cargar cola Free", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_free_queue: {e}", exc_info=True)
        await callback.answer("❌ Error al ver cola Free", show_alert=True)


async def callback_process_free(callback: CallbackQuery, session: AsyncSession):
    """
    Procesa la cola Free (función por implementar).

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"✅ Usuario {callback.from_user.id} procesando cola Free desde menú")

    try:
        container = ServiceContainer(session, callback.bot)

        # Procesar cola Free
        processed = await container.subscription.process_free_queue(
            wait_time_minutes=await container.config.get_wait_time()
        )

        if processed:
            await callback.answer(
                f"✅ Procesadas {len(processed)} solicitudes Free",
                show_alert=True
            )

            # Actualizar mensaje
            text = (
                f"✅ <b>Cola Free Procesada</b>\n\n"
                f"Se procesaron <b>{len(processed)}</b> solicitudes.\n\n"
                f"Los usuarios han sido invitados al canal Free."
            )

            keyboard = create_inline_keyboard([
                [{"text": "🔄 Ver Cola Actualizada", "callback_data": "admin:free_queue"}],
                [{"text": "🔙 Volver al Menú", "callback_data": "admin:main"}]
            ])

            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.answer(
                "ℹ️ No hay solicitudes listas para procesar",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"❌ Error procesando cola Free: {e}", exc_info=True)
        await callback.answer(
            "❌ Error al procesar cola Free",
            show_alert=True
        )


async def callback_interests_pending(callback: CallbackQuery, session: AsyncSession):
    """
    Redirect to pending interests list (from admin notification button).

    This handler is needed because the notification sends callbacks
    to the main admin_router, not the interests sub-router.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"🔔 Admin {callback.from_user.id} viewing pending interests from notification")

    try:
        # Redirect to interests list handler with "pending" filter
        from bot.handlers.admin.interests import callback_interests_list

        # Simulate callback with correct data
        from unittest.mock import Mock
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.message = callback.message
        mock_callback.from_user = callback.from_user
        mock_callback.bot = callback.bot
        mock_callback.data = "admin:interests:list:pending"

        await callback_interests_list(mock_callback, session)
        await callback.answer()
    except ImportError as e:
        logger.error(f"❌ Error importando interests handler: {e}")
        await callback.answer("❌ Error al cargar lista de intereses", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_interests_pending: {e}", exc_info=True)
        await callback.answer("❌ Error al ver intereses pendientes", show_alert=True)


async def callback_interest_attend_from_notification(callback: CallbackQuery, session: AsyncSession):
    """
    Redirect to mark attended (from admin notification button).

    This handler is needed because the notification sends callbacks
    to the main admin_router, not the interests sub-router.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    logger.debug(f"✅ Admin {callback.from_user.id} marking interest as attended from notification")

    try:
        # Redirect to attend confirmation handler
        from bot.handlers.admin.interests import callback_interest_attend_confirm

        # Simulate callback with correct data
        from unittest.mock import Mock
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.message = callback.message
        mock_callback.from_user = callback.from_user
        mock_callback.bot = callback.bot
        mock_callback.data = callback.data

        await callback_interest_attend_confirm(mock_callback, session)
        await callback.answer()
    except ImportError as e:
        logger.error(f"❌ Error importando interests handler: {e}")
        await callback.answer("❌ Error al cargar confirmación", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error en callback_interest_attend_from_notification: {e}", exc_info=True)
        await callback.answer("❌ Error al marcar interés", show_alert=True)


async def callback_user_block_contact(callback: CallbackQuery, session: AsyncSession):
    """
    Block user from contact features (from admin notification button).

    Note: Full implementation deferred to Phase 9 (User Management).
    This is a placeholder for now.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    try:
        user_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"⚠️ Invalid user_id in callback: {callback.data}")
        await callback.answer("❌ ID de usuario inválido", show_alert=True)
        return

    logger.info(f"🚫 Admin {callback.from_user.id} attempted to block contact for user {user_id} (not yet implemented)")

    # TODO: Implement contact blocking in Phase 9
    await callback.answer(
        "⚠️ Función de bloqueo será implementada en Phase 9 (Gestión de Usuarios)",
        show_alert=True
    )


def register_menu_callbacks(router):
    """
    Registra todos los handlers de callbacks del menú en el router.

    Args:
        router: Router de admin donde registrar los handlers
    """
    # Registrar cada handler con su callback correspondiente usando router.callback_query.register
    router.callback_query.register(callback_vip_management, F.data == "admin:vip_management")
    router.callback_query.register(callback_list_vips, F.data == "admin:list_vips")
    router.callback_query.register(callback_generate_vip_token, F.data == "admin:generate_vip_token")
    router.callback_query.register(callback_content_management, F.data == "admin:content_management")
    router.callback_query.register(callback_create_package, F.data == "admin:create_package")
    router.callback_query.register(callback_list_packages, F.data == "admin:list_packages")
    router.callback_query.register(callback_free_queue, F.data == "admin:free_queue")
    router.callback_query.register(callback_process_free, F.data == "admin:process_free")

    # Register interest notification callback handlers
    router.callback_query.register(callback_interests_pending, F.data == "admin:interests:list:pending")
    router.callback_query.register(callback_interest_attend_from_notification, F.data.startswith("admin:interest:attend:"))
    router.callback_query.register(callback_user_block_contact, F.data.startswith("admin:user:block_contact:"))

    logger.info("✅ Handlers de callbacks del menú registrados")