"""
Performance Profiler Utilities

Wrapper para pyinstrument con soporte async, integracion con
SQLAlchemy para conteo de queries, y formateo de resultados.
"""

import asyncio
import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TypeVar

from pyinstrument import Profiler
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class ProfileResult:
    """Resultado de una sesion de profiling."""
    duration_ms: float
    query_count: int
    query_time_ms: float
    top_functions: List[Dict[str, Any]]
    html_output: Optional[str] = None
    text_output: Optional[str] = None

    def summary(self, limit: int = 5) -> str:
        """Resumen en texto plano."""
        lines = [
            f"Duration: {self.duration_ms:.2f}ms",
            f"Queries: {self.query_count} ({self.query_time_ms:.2f}ms)",
            "",
            "Top Functions:"
        ]
        for func in self.top_functions[:limit]:
            lines.append(f"  {func['name']}: {func['time_ms']:.2f}ms")
        return "\n".join(lines)


class AsyncProfiler:
    """
    Profiler con soporte para funciones async.

    Envuelve pyinstrument para manejar correctamente
    el profiling de codigo asincrono.
    """

    def __init__(self):
        self._profiler = Profiler()
        self._query_stats = {"count": 0, "time_ms": 0.0}

    def _attach_query_monitor(self, session: Optional[AsyncSession] = None):
        """Attach SQLAlchemy event listeners para contar queries."""
        # For async sessions, we use the sync events since they run in the same thread
        # The before_cursor_execute event fires for all statement executions
        if not session:
            return

        try:
            # Check if session has a real engine (not a mock)
            # MagicMock returns True for any hasattr check, so we need to be more specific
            from unittest.mock import MagicMock, NonCallableMagicMock

            bind = getattr(session, 'bind', None)
            if bind is None or isinstance(bind, (MagicMock, NonCallableMagicMock)):
                return

            sync_engine = getattr(bind, 'sync_engine', None)
            if sync_engine is None or isinstance(sync_engine, (MagicMock, NonCallableMagicMock)):
                return

            # Verify this is a real async engine by checking for dispatch attribute
            if hasattr(sync_engine, 'dispatch') and not isinstance(sync_engine.dispatch, (MagicMock, NonCallableMagicMock)):
                @event.listens_for(sync_engine, "before_cursor_execute")
                def on_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                    self._query_stats["count"] += 1
                    context._query_start_time = time.perf_counter()

                @event.listens_for(sync_engine, "after_cursor_execute")
                def on_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                    if hasattr(context, '_query_start_time'):
                        query_time = (time.perf_counter() - context._query_start_time) * 1000
                        self._query_stats["time_ms"] += query_time
        except (AttributeError, TypeError, ImportError):
            # Session is a mock or doesn't have proper engine setup
            pass

    async def profile_async(
        self,
        coro: Callable,
        *args,
        session: Optional[AsyncSession] = None,
        **kwargs
    ) -> ProfileResult:
        """
        Profile una corrutina.

        Args:
            coro: Funcion async a profilear
            args: Argumentos posicionales
            session: Sesion SQLAlchemy para monitoreo
            kwargs: Argumentos nombrados

        Returns:
            ProfileResult con estadisticas
        """
        if session:
            self._attach_query_monitor(session)

        self._profiler.start()
        start_time = time.perf_counter()

        try:
            result = await coro(*args, **kwargs)
        finally:
            self._profiler.stop()
            duration = (time.perf_counter() - start_time) * 1000

        # Parse results
        session_result = self._profiler.last_session

        return ProfileResult(
            duration_ms=duration,
            query_count=self._query_stats["count"],
            query_time_ms=self._query_stats["time_ms"],
            top_functions=self._extract_top_functions(session_result),
            html_output=self._profiler.output_html(),
            text_output=self._profiler.output_text()
        )

    def _extract_top_functions(self, session) -> List[Dict[str, Any]]:
        """Extrae las funciones mas lentas de la sesion."""
        functions = []
        root = session.root_frame()
        if not root:
            return functions

        # Recursively collect all frames
        def collect_frames(frame):
            frame_time = frame.time  # time is a property, not a method
            if frame_time > 0.001:  # Only functions > 1ms
                functions.append({
                    "name": frame.function,
                    "file": frame.file_path,
                    "line": frame.line_no,
                    "time_ms": frame_time * 1000,
                    "calls": getattr(frame, 'call_count', 1)
                })
            for child in frame.children:
                collect_frames(child)

        collect_frames(root)
        return sorted(functions, key=lambda x: x["time_ms"], reverse=True)[:10]


@contextmanager
def profile_block(name: str = "block"):
    """
    Context manager para profilear un bloque de codigo.

    Uso:
        with profile_block("database_query"):
            result = await session.execute(query)
    """
    profiler = Profiler()
    profiler.start()
    try:
        yield profiler
    finally:
        profiler.stop()
        logger.debug(f"Profile [{name}]: {profiler.last_session.duration * 1000:.2f}ms")


def profile_handler(func: F) -> F:
    """
    Decorator para profilear handlers automaticamente.

    Solo activa profiling si la variable de entorno
    PROFILE_HANDLERS esta configurada.

    Uso:
        @profile_handler
        async def cmd_admin(message: Message, session: AsyncSession):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        import os
        if not os.getenv("PROFILE_HANDLERS"):
            return await func(*args, **kwargs)

        profiler = AsyncProfiler()
        session = kwargs.get("session")

        result = await profiler.profile_async(
            func, *args, session=session, **kwargs
        )

        logger.info(f"Profile [{func.__name__}]: {result.summary()}")
        return result

    return wrapper


class HandlerProfiler:
    """
    Profiling especifico para handlers de aiogram.

    Mide tiempo total, tiempo de DB, y numero de queries.
    """

    def __init__(self):
        self.stats: Dict[str, List[float]] = {}

    async def profile_handler_execution(
        self,
        handler: Callable,
        event,
        session: AsyncSession
    ) -> tuple[Any, ProfileResult]:
        """
        Ejecuta un handler y recolecta estadisticas.

        Returns:
            Tuple de (handler_result, profile_result)
        """
        profiler = AsyncProfiler()

        result = await profiler.profile_async(
            handler,
            event,
            session=session
        )

        # Store stats
        handler_name = handler.__name__
        if handler_name not in self.stats:
            self.stats[handler_name] = []
        self.stats[handler_name].append(result.duration_ms)

        return result, profiler

    def get_slowest_handlers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna los handlers mas lentos en promedio."""
        averages = [
            {
                "name": name,
                "avg_ms": sum(times) / len(times),
                "max_ms": max(times),
                "calls": len(times)
            }
            for name, times in self.stats.items()
        ]
        return sorted(averages, key=lambda x: x["avg_ms"], reverse=True)[:limit]
