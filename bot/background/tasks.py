"""
Background Tasks - Tareas programadas automáticas.

Tareas:
- Expulsión de VIPs expirados del canal
- Procesamiento de cola Free (envío de invite links)
- Limpieza de datos antiguos
- Limpieza de solicitudes expiradas al inicio (post-restart)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from bot.database import get_session
from bot.database.models import FreeChannelRequest
from bot.services.container import ServiceContainer
from config import Config

logger = logging.getLogger(__name__)

# Scheduler global
_scheduler: Optional[AsyncIOScheduler] = None


async def expire_and_kick_vip_subscribers(bot: Bot):
    """
    Tarea: Expulsar suscriptores VIP expirados del canal.

    Proceso:
    1. Marca como expirados los suscriptores cuya fecha pasó
    2. Loguea cambios de rol (VIP → FREE) en UserRoleChangeLog
    3. Expulsa del canal VIP a los expirados
    4. Loguea resultados

    Args:
        bot: Instancia del bot de Telegram
    """
    logger.info("🔄 Ejecutando tarea: Expulsión VIP expirados")

    try:
        async with get_session() as session:
            container = ServiceContainer(session, bot)

            # Verificar que canal VIP está configurado
            vip_channel_id = await container.channel.get_vip_channel_id()

            if not vip_channel_id:
                logger.warning("⚠️ Canal VIP no configurado, saltando expulsión")
                return

            # Marcar como expirados y loguear cambios de rol
            expired_count = await container.subscription.expire_vip_subscribers(container=container)

            if expired_count > 0:
                logger.info(f"✅ {expired_count} VIP(s) expirados y cambios de rol logueados")

                # Expulsar del canal
                kicked_count, already_kicked, failed_count = await container.subscription.kick_expired_vip_from_channel(
                    vip_channel_id
                )

                logger.info(
                    f"✅ VIP kick results: {kicked_count} newly kicked, "
                    f"{already_kicked} already out, {failed_count} failed (will retry)"
                )
            else:
                logger.info("✅ No hay VIPs para expirar")

    except Exception as e:
        logger.error(f"❌ Error en tarea de expulsión VIP: {e}", exc_info=True)


async def process_free_queue(bot: Bot):
    """
    Tarea: Procesar cola de solicitudes Free.

    Proceso:
    1. Busca solicitudes que cumplieron el tiempo de espera
    2. Aprueba automáticamente usando approve_chat_join_request() de Telegram
    3. Marca solicitudes como procesadas
    4. Loguea resultados

    Args:
        bot: Instancia del bot de Telegram
    """
    logger.info("🔄 Ejecutando tarea: Procesamiento cola Free")

    try:
        async with get_session() as session:
            container = ServiceContainer(session, bot)

            # Verificar que canal Free está configurado
            free_channel_id = await container.channel.get_free_channel_id()

            if not free_channel_id:
                logger.warning("⚠️ Canal Free no configurado, saltando procesamiento")
                return

            # Obtener tiempo de espera configurado
            wait_time = await container.config.get_wait_time()

            # Aprobar solicitudes usando Telegram API
            success_count, error_count = await container.subscription.approve_ready_free_requests(
                wait_time_minutes=wait_time,
                free_channel_id=free_channel_id
            )

            if success_count == 0 and error_count == 0:
                logger.debug("✓ No hay solicitudes Free listas para procesar")
                return

            logger.info(
                f"✅ Cola Free procesada: {success_count} aprobadas, {error_count} errores"
            )

    except Exception as e:
        logger.error(f"❌ Error en tarea de procesamiento Free: {e}", exc_info=True)


async def cleanup_old_data(bot: Bot):
    """
    Tarea: Limpieza de datos antiguos.

    Proceso:
    1. Elimina solicitudes Free procesadas hace más de 30 días
    2. (Futuro: Limpiar tokens expirados muy antiguos)

    Args:
        bot: Instancia del bot
    """
    logger.info("🔄 Ejecutando tarea: Limpieza de datos antiguos")

    try:
        async with get_session() as session:
            container = ServiceContainer(session, bot)

            # Limpiar solicitudes Free antiguas
            deleted_count = await container.subscription.cleanup_old_free_requests(
                days_old=30
            )

            if deleted_count > 0:
                logger.info(f"🗑️ {deleted_count} solicitud(es) Free antiguas eliminadas")
            else:
                logger.debug("✓ No hay datos antiguos para limpiar")

    except Exception as e:
        logger.error(f"❌ Error en tarea de limpieza: {e}", exc_info=True)


async def expire_streaks(bot: Bot):
    """
    Tarea: Expiración de rachas diarias a medianoche UTC.

    Proceso:
    1. Resetea rachas DAILY_GIFT donde last_claim_date < hoy UTC
    2. Resetea rachas REACTION donde last_reaction_date < hoy UTC
    3. Preserva longest_streak como registro histórico
    4. Loguea resumen con conteos

    Ejecuta automáticamente a las 00:00 UTC cada día.

    Args:
        bot: Instancia del bot de Telegram
    """
    logger.info("🔄 Ejecutando tarea: Expiración de rachas")

    try:
        async with get_session() as session:
            container = ServiceContainer(session, bot)

            # Process daily gift streak expirations
            daily_reset_count = await container.streak.process_streak_expirations()

            # Process reaction streak expirations
            reaction_reset_count = await container.streak.process_reaction_streak_expirations()

            # Log summary
            if daily_reset_count > 0 or reaction_reset_count > 0:
                logger.info(
                    f"✅ Rachas expiradas: {daily_reset_count} diarias, "
                    f"{reaction_reset_count} de reacciones"
                )
            else:
                logger.debug("✓ No hay rachas expiradas para procesar")

    except Exception as e:
        logger.error(f"❌ Error en tarea de expiración de rachas: {e}", exc_info=True)


async def cleanup_expired_requests_after_restart(bot: Bot):
    """
    Limpia solicitudes Free pendientes que probablemente expiraron durante un reinicio.

    PROBLEMA: Los ChatJoinRequest de Telegram expiran después de ~10 minutos.
    Si el bot se reinicia, las solicitudes pendientes en BD pueden ya no ser válidas
    en Telegram, causando errores cuando se intentan procesar.

    SOLUCIÓN: Al iniciar el bot, marcar como procesadas las solicitudes que:
    - Tienen más de 15 minutos sin procesar
    - Aún no han sido procesadas

    Esto evita errores innecesarios y logs de error confusos.

    Args:
        bot: Instancia del bot de Telegram

    Returns:
        int: Cantidad de solicitudes marcadas como expiradas
    """
    logger.info("🔄 Verificando solicitudes pendientes post-reinicio...")

    try:
        async with get_session() as session:
            # Buscar solicitudes pendientes con más de 15 minutos de antigüedad
            # (Los ChatJoinRequest de Telegram expiran después de ~10 minutos)
            # Usar naive UTC para compatibilidad con PostgreSQL TIMESTAMP WITHOUT TIME ZONE
            cutoff_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)

            result = await session.execute(
                select(FreeChannelRequest).where(
                    FreeChannelRequest.processed == False,
                    FreeChannelRequest.request_date <= cutoff_time
                )
            )
            old_requests = result.scalars().all()

            if not old_requests:
                logger.info("✅ No hay solicitudes pendientes potencialmente expiradas")
                return 0

            # Marcar como procesadas (expiradas)
            expired_count = 0
            for request in old_requests:
                request.processed = True
                request.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)
                expired_count += 1
                logger.info(
                    f"🧹 Solicitud marcada como expirada (post-reinicio): "
                    f"user {request.user_id} (creada hace {request.minutes_since_request():.0f} min)"
                )

            await session.commit()

            logger.info(
                f"✅ {expired_count} solicitud(es) marcada(s) como expiradas post-reinicio. "
                f"Los usuarios deberán solicitar nuevamente si aún no están en el canal."
            )

            return expired_count

    except Exception as e:
        logger.error(f"❌ Error en limpieza post-reinicio: {e}", exc_info=True)
        return 0


async def start_background_tasks(bot: Bot):
    """
    Inicia el scheduler con todas las tareas programadas.

    Configuración:
    - Expulsión VIP: Cada 60 minutos (configurable)
    - Procesamiento Free: Cada 5 minutos (o según wait_time)
    - Limpieza: Cada 24 horas (diaria a las 3 AM)
    - Limpieza post-reinicio: Al inicio del bot

    Args:
        bot: Instancia del bot de Telegram
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("⚠️ Scheduler ya está corriendo")
        return

    logger.info("🚀 Iniciando background tasks...")

    # LIMPIEZA POST-REINICIO: Marcar solicitudes antiguas como expiradas
    # Esto evita errores cuando el bot se reinicia y hay solicitudes pendientes
    # que ya expiraron en Telegram (ChatJoinRequest expira después de ~10 min)
    await cleanup_expired_requests_after_restart(bot)

    _scheduler = AsyncIOScheduler(timezone="UTC")

    # Tarea 1: Expulsión VIP expirados
    # Frecuencia: Cada 60 minutos (Config.CLEANUP_INTERVAL_MINUTES)
    _scheduler.add_job(
        expire_and_kick_vip_subscribers,
        trigger=IntervalTrigger(minutes=Config.CLEANUP_INTERVAL_MINUTES, timezone="UTC"),
        args=[bot],
        id="expire_vip",
        name="Expulsar VIPs expirados",
        replace_existing=True,
        max_instances=1,  # No permitir múltiples instancias simultáneas
        misfire_grace_time=300,  # 5 minutes grace time
        coalesce=True  # Coalesce missed jobs into one
    )
    logger.info(
        f"✅ Tarea programada: Expulsión VIP (cada {Config.CLEANUP_INTERVAL_MINUTES} min)"
    )

    # Tarea 2: Procesamiento cola Free
    # Frecuencia: Cada 5 minutos (Config.PROCESS_FREE_QUEUE_MINUTES)
    _scheduler.add_job(
        process_free_queue,
        trigger=IntervalTrigger(minutes=Config.PROCESS_FREE_QUEUE_MINUTES, timezone="UTC"),
        args=[bot],
        id="process_free_queue",
        name="Procesar cola Free",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,  # 1 minute grace time
        coalesce=True  # Coalesce missed jobs into one
    )
    logger.info(
        f"✅ Tarea programada: Cola Free (cada {Config.PROCESS_FREE_QUEUE_MINUTES} min)"
    )

    # Tarea 3: Limpieza de datos antiguos
    # Frecuencia: Diaria a las 3 AM UTC
    _scheduler.add_job(
        cleanup_old_data,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        args=[bot],
        id="cleanup_old_data",
        name="Limpieza de datos antiguos",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,  # 1 hour grace time
        coalesce=True  # Coalesce missed jobs into one
    )
    logger.info("✅ Tarea programada: Limpieza (diaria 3 AM UTC)")

    # Tarea 4: Expiración de rachas diarias
    # Frecuencia: Diaria a medianoche UTC (00:00)
    _scheduler.add_job(
        expire_streaks,
        trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
        args=[bot],
        id="expire_streaks",
        name="Expiración de rachas diarias",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,  # 1 hour grace time
        coalesce=True  # Coalesce missed jobs into one
    )
    logger.info("✅ Tarea programada: Expiración de rachas (medianoche UTC)")

    # Iniciar scheduler
    _scheduler.start()
    logger.info("✅ Background tasks iniciados correctamente")


def stop_background_tasks():
    """
    Detiene el scheduler y todas las tareas programadas.

    Debe llamarse en el shutdown del bot para cleanup limpio.
    Con wait=False para permitir shutdown rápido incluso si hay jobs.
    """
    global _scheduler

    if _scheduler is None:
        logger.warning("⚠️ Scheduler no está corriendo")
        return

    logger.info("🛑 Deteniendo background tasks...")

    try:
        # wait=False para shutdown rápido sin bloquear
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("✅ Background tasks detenidos")
    except Exception as e:
        logger.warning(f"⚠️ Error deteniendo scheduler: {e}")
        _scheduler = None


def get_scheduler_status() -> dict:
    """
    Obtiene el estado actual del scheduler de background tasks.

    Returns:
        Dict con info del scheduler:
        {
            "running": bool,
            "jobs_count": int,
            "jobs": [
                {
                    "id": str,
                    "name": str,
                    "next_run_time": datetime or None,
                    "trigger": str
                }
            ]
        }

    Examples:
        >>> status = get_scheduler_status()
        >>> if status["running"]:
        ...     print(f"{status['jobs_count']} jobs activos")
    """
    if _scheduler is None:
        return {
            "running": False,
            "jobs_count": 0,
            "jobs": []
        }

    jobs_info = []
    for job in _scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "name": job.name or job.id,
            "next_run_time": job.next_run_time,
            "trigger": str(job.trigger)
        })

    return {
        "running": _scheduler.running,
        "jobs_count": len(jobs_info),
        "jobs": jobs_info
    }
