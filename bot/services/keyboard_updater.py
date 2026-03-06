"""
Keyboard Update Service - Batching de actualizaciones de teclado para reacciones.

Responsabilidades:
- Acumular actualizaciones de teclado de reacciones
- Aplicar batching según el tiempo transcurrido desde la publicación:
  * Primeros 5 minutos: cada 5 reacciones
  * Después de 5 minutos: cada 2 reacciones
  * Máximo 5 minutos sin actualizar (para limpiar huérfanas)
- Evitar flood control de Telegram

Patrones:
- Singleton con estado compartido
- Debounce adaptativo basado en tiempo
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, func

from bot.utils.keyboards import get_reaction_keyboard, DEFAULT_REACTIONS
from bot.database.engine import get_session
from bot.database.models import UserReaction

logger = logging.getLogger(__name__)


@dataclass
class PendingUpdate:
    """Representa una actualización pendiente de teclado."""
    content_id: int
    channel_id: str
    reaction_count: int = 1  # Contador de reacciones acumuladas
    first_reaction_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_reaction_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class KeyboardUpdateService:
    """
    Servicio de batching para actualizaciones de teclado de reacciones.

    Estrategia:
    - Fase inicial (0-5 min): batch de 5 reacciones
    - Fase normal (>5 min): batch de 2 reacciones
    - Timeout máximo: 5 minutos (forzar actualización)

    Uso:
        service = KeyboardUpdateService(bot)
        await service.schedule_update(content_id, channel_id, container)
    """

    # Umbrales de batching
    INITIAL_PHASE_MINUTES = 5
    INITIAL_PHASE_BATCH_SIZE = 5  # Cada 5 reacciones
    NORMAL_PHASE_BATCH_SIZE = 2   # Cada 2 reacciones
    MAX_DELAY_SECONDS = 300       # 5 minutos máximo sin actualizar

    def __init__(self, bot: Bot):
        """
        Inicializa el servicio.

        Args:
            bot: Instancia del bot de Telegram
        """
        self.bot = bot
        self._pending: Dict[str, PendingUpdate] = {}  # key: "{channel_id}:{content_id}"
        self._timers: Dict[str, asyncio.Task] = {}    # key -> timer task
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)

    def _make_key(self, channel_id: str, content_id: int) -> str:
        """Genera clave única para un mensaje."""
        return f"{channel_id}:{content_id}"

    async def schedule_update(
        self,
        content_id: int,
        channel_id: str
    ) -> tuple[bool, str]:
        """
        Programa una actualización de teclado con batching.

        Args:
            content_id: ID del mensaje/contenido
            channel_id: ID del canal

        Returns:
            Tuple[bool, str]: (se_actualizó_ahora, mensaje_estado)
        """
        key = self._make_key(channel_id, content_id)
        now = datetime.now(timezone.utc)

        async with self._lock:
            if key in self._pending:
                # Ya hay una actualización pendiente, acumular
                pending = self._pending[key]
                pending.reaction_count += 1
                pending.last_reaction_at = now

                # Verificar si debemos aplicar ahora
                elapsed = (now - pending.first_reaction_at).total_seconds()
                batch_size = (
                    self.INITIAL_PHASE_BATCH_SIZE
                    if elapsed < (self.INITIAL_PHASE_MINUTES * 60)
                    else self.NORMAL_PHASE_BATCH_SIZE
                )

                if pending.reaction_count >= batch_size:
                    # Aplicar ahora
                    await self._apply_update(key)
                    return True, f"Teclado actualizado ({pending.reaction_count} reacciones)"
                else:
                    # Programar timer si no existe
                    await self._ensure_timer(key)
                    remaining = batch_size - pending.reaction_count
                    return False, f"Reacción #{pending.reaction_count}, falta(n) {remaining} para actualizar"
            else:
                # Nueva actualización
                self._pending[key] = PendingUpdate(
                    content_id=content_id,
                    channel_id=channel_id,
                    reaction_count=1,
                    first_reaction_at=now,
                    last_reaction_at=now
                )

                # Programar timer para timeout máximo
                await self._ensure_timer(key)
                return False, f"Primera reacción, acumulando para batch..."

    async def _ensure_timer(self, key: str):
        """Asegura que haya un timer programado para esta key."""
        if key not in self._timers or self._timers[key].done():
            self._timers[key] = asyncio.create_task(
                self._timer_callback(key)
            )

    async def _timer_callback(self, key: str):
        """Timer que fuerza actualización después de MAX_DELAY_SECONDS."""
        try:
            await asyncio.sleep(self.MAX_DELAY_SECONDS)

            async with self._lock:
                if key in self._pending:
                    self._logger.info(f"⏰ Timeout alcanzado para {key}, aplicando actualización")
                    await self._apply_update(key)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self._logger.error(f"Error en timer para {key}: {e}")

    async def _get_content_reactions(self, content_id: int, channel_id: str) -> Dict[str, int]:
        """
        Obtiene el conteo de reacciones por emoji para un contenido.
        Usa una sesión fresca para evitar problemas de stale data.

        Args:
            content_id: ID del contenido
            channel_id: ID del canal

        Returns:
            Dict[emoji, count]: Conteo de cada emoji
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(UserReaction.emoji, func.count(UserReaction.id))
                    .where(
                        UserReaction.content_id == content_id,
                        UserReaction.channel_id == channel_id
                    )
                    .group_by(UserReaction.emoji)
                )

                counts = {}
                for row in result.all():
                    counts[row[0]] = row[1]

                return counts
        except Exception as e:
            self._logger.error(f"Error obteniendo conteos de reacciones: {e}")
            return {}

    async def _apply_update(self, key: str):
        """Aplica la actualización del teclado."""
        if key not in self._pending:
            return

        pending = self._pending[key]

        try:
            # Obtener conteos actuales usando sesión fresca
            counts = await self._get_content_reactions(
                pending.content_id,
                pending.channel_id
            )

            self._logger.debug(f"Conteos obtenidos para {key}: {counts}")

            # Construir teclado
            keyboard = get_reaction_keyboard(
                content_id=pending.content_id,
                channel_id=pending.channel_id,
                current_counts=counts
            )

            # Aplicar en Telegram
            await self.bot.edit_message_reply_markup(
                chat_id=pending.channel_id,
                message_id=pending.content_id,
                reply_markup=keyboard
            )

            elapsed = (datetime.now(timezone.utc) - pending.first_reaction_at).total_seconds()
            self._logger.info(
                f"✅ Teclado actualizado: {key} "
                f"({pending.reaction_count} reacciones en {elapsed:.1f}s, "
                f"conteos: {counts})"
            )

        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                pass  # OK
            elif "flood control" in str(e).lower():
                self._logger.warning(f"⚠️ Flood control en {key}, reintentando en 5s...")
                # Reprogramar para reintentar
                asyncio.create_task(self._retry_update(key, delay=5))
                return  # No limpiar pending, se reintentará
            else:
                self._logger.debug(f"No se pudo actualizar teclado {key}: {e}")
        except Exception as e:
            self._logger.error(f"Error actualizando teclado {key}: {e}")
        finally:
            # Limpiar
            if key in self._pending:
                del self._pending[key]
            if key in self._timers:
                timer = self._timers.pop(key)
                if not timer.done():
                    timer.cancel()

    async def _retry_update(self, key: str, delay: int):
        """Reintenta la actualización después de un delay."""
        await asyncio.sleep(delay)
        async with self._lock:
            if key in self._pending:
                await self._apply_update(key)

    async def force_update(self, content_id: int, channel_id: str) -> bool:
        """
        Fuerza la actualización inmediata de un teclado específico.

        Args:
            content_id: ID del contenido
            channel_id: ID del canal

        Returns:
            True si se aplicó la actualización
        """
        key = self._make_key(channel_id, content_id)
        async with self._lock:
            if key in self._pending:
                await self._apply_update(key)
                return True
            return False

    async def get_stats(self) -> dict:
        """Retorna estadísticas del servicio."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            stats = {
                "pending_updates": len(self._pending),
                "pending_details": [
                    {
                        "key": key,
                        "reaction_count": p.reaction_count,
                        "elapsed_seconds": (now - p.first_reaction_at).total_seconds(),
                    }
                    for key, p in self._pending.items()
                ]
            }
            return stats


# Singleton global (se inicializa en main.py)
_keyboard_updater: Optional[KeyboardUpdateService] = None


def get_keyboard_updater() -> Optional[KeyboardUpdateService]:
    """Retorna la instancia global del servicio."""
    return _keyboard_updater


def set_keyboard_updater(service: KeyboardUpdateService):
    """Establece la instancia global del servicio."""
    global _keyboard_updater
    _keyboard_updater = service
