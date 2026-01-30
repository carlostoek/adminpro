"""
Entry point del Bot de Administración VIP/Free.
Gestiona el ciclo de vida completo del bot en Termux.
"""
import asyncio
import logging
import sys
import signal
import threading
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramNetworkError
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

from config import Config
from bot.database import init_db, close_db
from bot.database.migrations import run_migrations_if_needed
from bot.background import start_background_tasks, stop_background_tasks
from bot.health.runner import start_health_server

# Flag global para señalizar shutdown
_shutdown_requested = False

# Configurar logging
logger = logging.getLogger(__name__)


def _global_signal_handler(sig, frame):
    """Manejador global de señales para shutdown inmediato."""
    global _shutdown_requested
    logger.info(f"🛑 Señal {sig} recibida - iniciando shutdown...")
    _shutdown_requested = True


def should_use_webhook() -> bool:
    """
    Detecta si el bot debe ejecutarse en modo webhook.

    Returns:
        True si WEBHOOK_MODE=webhook, False para polling
    """
    return Config.WEBHOOK_MODE == "webhook"


async def _get_bot_info_with_retry(bot: Bot, max_retries: int = 2, timeout: int = 5) -> dict | None:
    """
    Obtiene información del bot con reintentos rápidos.

    Args:
        bot: Instancia del bot
        max_retries: Número máximo de reintentos
        timeout: Timeout en segundos para cada intento

    Returns:
        Dict con info del bot o None si falla después de reintentos
    """
    for attempt in range(1, max_retries + 1):
        try:
            bot_info = await asyncio.wait_for(
                bot.get_me(request_timeout=timeout),
                timeout=timeout + 1
            )
            logger.info(f"✅ Bot verificado: @{bot_info.username}")
            return bot_info
        except (TelegramNetworkError, asyncio.TimeoutError) as e:
            logger.warning(f"⚠️ Intento {attempt}/{max_retries} falló: {type(e).__name__}")
            if attempt < max_retries:
                await asyncio.sleep(1)  # Espera corta: 1s
            else:
                logger.warning("⚠️ No se pudo verificar bot. Continuando sin verificación...")
                return None
        except Exception as e:
            logger.error(f"❌ Error al obtener info del bot: {e}")
            return None


async def on_startup_webhook(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Callback de startup específico para modo webhook.

    Configura el webhook antes de iniciar el servidor.
    """
    logger.info("🚀 Iniciando bot en modo WEBHOOK...")

    # Validar configuración
    if not Config.validate():
        logger.error("❌ Configuración inválida. Revisa tu archivo .env")
        sys.exit(1)

    logger.info(Config.get_summary())

    # Ejecutar migraciones automáticas
    try:
        await run_migrations_if_needed()
    except Exception as e:
        logger.error(f"❌ Error ejecutando migraciones: {e}")
        sys.exit(1)

    # Inicializar base de datos
    try:
        await init_db()
    except Exception as e:
        logger.error(f"❌ Error al inicializar BD: {e}")
        sys.exit(1)

    # Iniciar background tasks
    start_background_tasks(bot)

    # Configurar webhook
    webhook_url = f"{Config.WEBHOOK_BASE_URL}{Config.WEBHOOK_PATH}"
    logger.info(f"🔗 Configurando webhook: {webhook_url}")

    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=Config.WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        logger.info("✅ Webhook configurado correctamente")
    except Exception as e:
        logger.error(f"❌ Error configurando webhook: {e}")
        sys.exit(1)

    # Iniciar health check API
    try:
        health_task = await start_health_server()
        if health_task is not None:
            dispatcher.workflow_data['health_task'] = health_task
            logger.info("✅ Health check API iniciado")
        else:
            logger.warning("⚠️ Health API no disponible - bot continúa sin health checks")
            logger.warning("   Esto no afecta la funcionalidad del bot")
    except Exception as e:
        logger.error(f"❌ Error iniciando health API: {e}")
        logger.warning("⚠️ Bot continuará sin health check endpoint")


async def on_startup(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Callback ejecutado al iniciar el bot.

    Tareas:
    - Validar configuración
    - Inicializar base de datos
    - Iniciar background tasks
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

    # Ejecutar migraciones automáticas (producción)
    # En producción, esto corre "alembic upgrade head" automáticamente
    # En desarrollo, omite este paso (developer debe correr manualmente)
    try:
        await run_migrations_if_needed()
    except Exception as e:
        logger.error(f"❌ Error ejecutando migraciones: {e}")
        logger.error(
            "💥 El bot no puede iniciar sin migraciones exitosas. "
            "Fix the migration issue and restart."
        )
        sys.exit(1)

    # Inicializar base de datos
    try:
        await init_db()
    except Exception as e:
        logger.error(f"❌ Error al inicializar BD: {e}")
        sys.exit(1)

    # Iniciar background tasks
    start_background_tasks(bot)

    # Iniciar health check API (corre concurrentemente con el bot)
    # Testing: Verified concurrent execution with health API responding to HTTP requests
    # - Health API starts on HEALTH_PORT (8000) without blocking bot startup
    # - Both services share the same asyncio event loop
    # - Health endpoint returns valid JSON (e.g., {"status": "unhealthy", "components": {...}})
    # - Graceful shutdown stops both services cleanly (5s timeout)
    try:
        health_task = await start_health_server()
        logger.info("✅ Health check API iniciado")
    except Exception as e:
        logger.error(f"❌ Error iniciando health API: {e}")
        logger.warning("⚠️ Bot continuará sin health check endpoint")
        health_task = None

    # Store health task for graceful shutdown
    dispatcher.workflow_data['health_task'] = health_task

    # Notificar a admins que el bot está online (con reintentos)
    bot_info = await _get_bot_info_with_retry(bot)

    if bot_info:
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
    else:
        logger.warning("⚠️ Bot iniciado pero sin verificación de conectividad. Revisa tu conexión de red.")

    logger.info("✅ Bot iniciado y listo para recibir mensajes")


async def on_shutdown(bot: Bot, dispatcher: Dispatcher) -> None:
    """
    Callback ejecutado al cerrar el bot (graceful shutdown).

    Tareas:
    - Cerrar base de datos
    - Detener background tasks
    - Notificar a admins que el bot está offline (con timeout)
    - Limpiar recursos

    Args:
        bot: Instancia del bot
        dispatcher: Instancia del dispatcher
    """
    logger.info("🛑 Cerrando bot...")

    # Activar timeout de emergencia por si el shutdown se cuelga
    _activate_shutdown_timeout()

    # Detener background tasks (sin bloquear)
    stop_background_tasks()

    # Detener health check API usando función explícita
    logger.info("🛑 Deteniendo health check API...")
    try:
        from bot.health.runner import stop_health_server
        await stop_health_server()
        logger.info("✅ Health API detenida correctamente")
    except Exception as e:
        logger.warning(f"⚠️ Error deteniendo health API: {e}")

    # Notificar a admins (con timeout para no bloquear shutdown)
    shutdown_message = "🛑 Bot detenido correctamente"

    for admin_id in Config.ADMIN_USER_IDS:
        try:
            await asyncio.wait_for(
                bot.send_message(chat_id=admin_id, text=shutdown_message),
                timeout=5  # Timeout de 5s para cada notificación
            )
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Timeout notificando shutdown a admin {admin_id}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo notificar shutdown a admin {admin_id}: {e}")

    # Cerrar base de datos
    await close_db()

    # Cancelar cualquier tarea pendiente que pueda bloquear el shutdown
    pending_tasks = [task for task in asyncio.all_tasks()
                     if task is not asyncio.current_task() and not task.done()]
    if pending_tasks:
        logger.info(f"🧹 Cancelando {len(pending_tasks)} tareas pendientes...")
        for task in pending_tasks:
            task.cancel()
        # Esperar un poco pero no bloquear indefinidamente
        await asyncio.sleep(0.1)

    logger.info("✅ Bot cerrado correctamente")


async def main() -> None:
    """
    Función principal que ejecuta el bot.

    Soporta dos modos:
    - Polling: Bot hace requests a Telegram (default para desarrollo)
    - Webhook: Telegram envía updates al bot (óptimo para Railway)
    """
    # Crear instancia del bot con sesión customizada
    # AiohttpSession timeout: 10s para shutdown responsivo
    # NOTA: Este es el timeout para request HTTP, NO para handlers
    # Los handlers pueden tardar más tiempo, esto es solo para conexiones HTTP
    # Un timeout más corto permite que el bot responda a Ctrl+C rápidamente
    session = AiohttpSession(timeout=10)

    bot = Bot(
        token=Config.BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(
            parse_mode="HTML"  # HTML por defecto para mensajes
        )
    )

    # Crear storage para FSM (estados de conversación)
    storage = MemoryStorage()

    # Crear dispatcher
    dp = Dispatcher(storage=storage)

    # Registrar middlewares ANTES de los handlers (orden crítico)
    from bot.middlewares import DatabaseMiddleware, RoleDetectionMiddleware
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(RoleDetectionMiddleware())
    # AdminAuthMiddleware se aplica solo al router admin (ver bot/handlers/admin/main.py)

    # Registrar handlers DESPUÉS de los middlewares
    from bot.handlers import register_all_handlers
    register_all_handlers(dp)

    # Detectar modo de operación
    use_webhook = should_use_webhook()

    if use_webhook:
        logger.info("🔄 Iniciando en modo WEBHOOK...")
        # Registrar callbacks de webhook
        dp.startup.register(on_startup_webhook)
        dp.shutdown.register(on_shutdown)

        # Iniciar webhook server
        try:
            await dp.start_webhook(
                bot,
                webhook_path=Config.WEBHOOK_PATH,
                host=Config.WEBHOOK_HOST,
                port=Config.PORT,
                secret_token=Config.WEBHOOK_SECRET
            )
        except KeyboardInterrupt:
            logger.info("⌨️ Interrupción por teclado (Ctrl+C) - Deteniendo webhook...")
        except Exception as e:
            logger.error(f"❌ Error crítico en webhook: {e}", exc_info=True)
        finally:
            # Llamar explícitamente al shutdown para cleanup limpio
            logger.info("🧹 Ejecutando shutdown del dispatcher...")
            try:
                await dp.emit_shutdown()
            except Exception as e:
                logger.warning(f"⚠️ Error en shutdown del dispatcher: {e}")

            # Cerrar sesión del bot
            logger.info("🧹 Cerrando sesión del bot...")
            try:
                await bot.session.close()
                logger.info("✅ Sesión del bot cerrada correctamente")
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando sesión: {e}")
            logger.info("👋 Bot detenido completamente")
    else:
        logger.info("🔄 Iniciando en modo POLLING...")
        # Registrar callbacks de polling
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Iniciar polling
        try:
            # Iniciar polling con timeout de 10s para shutdown responsivo
            # Balance entre:
            # - Shutdown rápido (Ctrl+C funciona en ~10s)
            # - Conexiones inestables (timeout suficiente para redes lentas)
            # - Eficiencia (no hacer requests muy frecuentes)
            logger.info("🔄 Iniciando polling...")
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                timeout=10,  # 10s timeout para shutdown responsivo (era 30)
                drop_pending_updates=True,  # Ignorar updates pendientes del pasado
                relax_timeout=True  # Reduce requests frecuentes
            )
        except KeyboardInterrupt:
            logger.info("⌨️ Interrupción por teclado (Ctrl+C) - Deteniendo bot...")
            logger.info("⏱️ Cerrando sesión HTTP (puede tomar hasta 10s)...")
        except Exception as e:
            logger.error(f"❌ Error crítico en polling: {e}", exc_info=True)
        finally:
            # Llamar explícitamente al shutdown para cleanup limpio
            logger.info("🧹 Ejecutando shutdown del dispatcher...")
            try:
                await dp.emit_shutdown()
            except Exception as e:
                logger.warning(f"⚠️ Error en shutdown del dispatcher: {e}")

            # Cerrar sesión del bot
            logger.info("🧹 Cerrando sesión del bot...")
            try:
                await bot.session.close()
                logger.info("✅ Sesión del bot cerrada correctamente")
            except Exception as e:
                logger.warning(f"⚠️ Error cerrando sesión: {e}")
            logger.info("👋 Bot detenido completamente")


_shutdown_timeout_active = False


def _activate_shutdown_timeout():
    """
    Activa timeout de emergencia para forzar salida si el shutdown se cuelga.
    Esta función debe llamarse solo cuando se inicia el shutdown.
    """
    global _shutdown_timeout_active

    if _shutdown_timeout_active:
        return

    _shutdown_timeout_active = True

    def force_exit_after_timeout():
        """Fuerza salida si pasa demasiado tiempo en shutdown."""
        import time
        time.sleep(15)  # Dar 15s para shutdown limpio
        logger.critical("💥 TIMEOUT CRÍTICO: Forzando salida del proceso...")
        os._exit(1)  # Salida forzada

    # Registrar timeout thread (daemon para no bloquear)
    timeout_thread = threading.Thread(target=force_exit_after_timeout, daemon=True)
    timeout_thread.start()
    logger.info("⏱️ Timeout de shutdown activado (15s)")


if __name__ == "__main__":
    """
    Punto de entrada del script.

    Uso:
        python main.py

    Para ejecutar en background (Termux):
        nohup python main.py > bot.log 2>&1 &
    """
    # Registrar manejadores de señales para shutdown limpio
    signal.signal(signal.SIGINT, _global_signal_handler)
    signal.signal(signal.SIGTERM, _global_signal_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot detenido por el usuario")
    except Exception as e:
        logger.critical(f"💥 Error fatal: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Asegurar salida limpia
        logger.info("🛑 Finalizando...")
        # Forzar cierre de cualquier tarea pendiente
        try:
            pending = asyncio.all_tasks()
            for task in pending:
                if not task.done():
                    task.cancel()
        except Exception:
            pass
        sys.exit(0)
