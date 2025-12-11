"""
Entry point del Bot de Administración VIP/Free.
Gestiona el ciclo de vida completo del bot en Termux.
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from bot.database import init_db, close_db

# Configurar logging
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Callback ejecutado al iniciar el bot.

    Tareas:
    - Validar configuración
    - Inicializar base de datos
    - Registrar handlers y middlewares
    - Notificar a admins que el bot está online

    Args:
        bot: Instancia del bot
        dispatcher: Instancia del dispatcher
    """
    logger.info("🚀 Iniciando bot...")

    # Validar configuración
    if not Config.validate():
        logger.error("❌ Configuración inválida. Revisa tu archivo .env")
        sys.exit(1)

    logger.info(Config.get_summary())

    # Inicializar base de datos
    try:
        await init_db()
    except Exception as e:
        logger.error(f"❌ Error al inicializar BD: {e}")
        sys.exit(1)

    # TODO: Registrar handlers (ONDA 1 - Fases siguientes)
    # from bot.handlers import register_all_handlers
    # register_all_handlers(dispatcher)

    # TODO: Registrar middlewares (ONDA 1 - Fase 1.3)
    # from bot.middlewares import DatabaseMiddleware, AdminAuthMiddleware
    # dispatcher.update.middleware(DatabaseMiddleware())
    # dispatcher.message.middleware(AdminAuthMiddleware())

    # Notificar a admins que el bot está online
    bot_info = await bot.get_me()
    startup_message = (
        f"✅ Bot <b>@{bot_info.username}</b> iniciado correctamente\n\n"
        f"🤖 ID: <code>{bot_info.id}</code>\n"
        f"📝 Nombre: {bot_info.first_name}\n"
        f"🔧 Versión: ONDA 1 (MVP)\n\n"
        f"Usa /admin para gestionar los canales."
    )

    for admin_id in Config.ADMIN_USER_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=startup_message,
                parse_mode="HTML"
            )
            logger.info(f"📨 Notificación enviada a admin {admin_id}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo notificar a admin {admin_id}: {e}")

    logger.info("✅ Bot iniciado y listo para recibir mensajes")


async def on_shutdown(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Callback ejecutado al cerrar el bot (graceful shutdown).

    Tareas:
    - Cerrar base de datos
    - Detener background tasks
    - Notificar a admins que el bot está offline
    - Limpiar recursos

    Args:
        bot: Instancia del bot
        dispatcher: Instancia del dispatcher
    """
    logger.info("🛑 Cerrando bot...")

    # Notificar a admins
    shutdown_message = "🛑 Bot detenido correctamente"

    for admin_id in Config.ADMIN_USER_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=shutdown_message
            )
        except Exception as e:
            logger.warning(f"⚠️ No se pudo notificar shutdown a admin {admin_id}: {e}")

    # TODO: Detener background tasks (ONDA 1 - Fase 1.4)
    # from bot.background.tasks import stop_background_tasks
    # await stop_background_tasks()

    # Cerrar base de datos
    await close_db()

    logger.info("✅ Bot cerrado correctamente")


async def main() -> None:
    """
    Función principal que ejecuta el bot.

    Configuración:
    - Bot con parse_mode HTML por defecto
    - MemoryStorage para FSM (ligero, apropiado para Termux)
    - Dispatcher con callbacks de startup/shutdown
    - Polling con timeout de 30s (apropiado para Termux)
    """
    # Crear instancia del bot
    bot = Bot(
        token=Config.BOT_TOKEN,
        parse_mode="HTML"  # HTML por defecto para mensajes
    )

    # Crear storage para FSM (estados de conversación)
    storage = MemoryStorage()

    # Crear dispatcher
    dp = Dispatcher(storage=storage)

    # Registrar callbacks de lifecycle
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        # Iniciar polling (long polling con timeout de 30s)
        logger.info("🔄 Iniciando polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            timeout=30,  # Timeout apropiado para conexiones inestables en Termux
            drop_pending_updates=True  # Ignorar updates pendientes del pasado
        )
    except KeyboardInterrupt:
        logger.info("⌨️ Interrupción por teclado (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Error crítico en polling: {e}", exc_info=True)
    finally:
        # Cleanup
        await bot.session.close()
        logger.info("🔌 Sesión del bot cerrada")


if __name__ == "__main__":
    """
    Punto de entrada del script.

    Uso:
        python main.py

    Para ejecutar en background (Termux):
        nohup python main.py > bot.log 2>&1 &
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario")
    except Exception as e:
        logger.critical(f"💥 Error fatal: {e}", exc_info=True)
        sys.exit(1)
