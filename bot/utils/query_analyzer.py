"""
Query Analyzer Utility - Detección de N+1 queries y análisis de rendimiento.

Este módulo proporciona herramientas para:
- Detectar patrones N+1 query
- Analizar queries SQL ejecutadas
- Sugerir optimizaciones
- Monitorear rendimiento de queries
"""

import functools
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar
from collections import defaultdict

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class QueryInfo:
    """Información sobre una query ejecutada."""
    statement: str
    parameters: tuple
    duration_ms: float
    timestamp: float
    caller: str = ""  # Nombre de la función que ejecutó la query

    def __repr__(self) -> str:
        return f"<QueryInfo(duration={self.duration_ms:.2f}ms, stmt={self.statement[:50]}...)>"


@dataclass
class NPlusOnePattern:
    """Patrón N+1 detectado."""
    base_query: str
    related_queries: List[str]
    count: int
    suggestion: str

    def __repr__(self) -> str:
        return f"<NPlusOnePattern(count={self.count}, base={self.base_query[:50]}...)>"


@dataclass
class AnalysisResult:
    """Resultado del análisis de queries."""
    queries: List[QueryInfo] = field(default_factory=list)
    total_queries: int = 0
    total_time_ms: float = 0.0
    slow_queries: List[QueryInfo] = field(default_factory=list)
    n_plus_one_patterns: List[NPlusOnePattern] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def summary(self) -> str:
        """Resumen del análisis en texto."""
        lines = [
            f"Total queries: {self.total_queries}",
            f"Total time: {self.total_time_ms:.2f}ms",
            f"Slow queries (>>100ms): {len(self.slow_queries)}",
            f"N+1 patterns detected: {len(self.n_plus_one_patterns)}",
        ]
        if self.suggestions:
            lines.append("\nSuggestions:")
            for suggestion in self.suggestions[:5]:
                lines.append(f"  • {suggestion}")
        return "\n".join(lines)


class QueryAnalyzer:
    """
    Analizador de queries con detección de N+1.

    Uso:
        analyzer = QueryAnalyzer()
        with analyzer.analyze():
            # Código a analizar
            result = await session.execute(query)
    """

    # Umbral para considerar una query lenta (ms)
    SLOW_QUERY_THRESHOLD = 100.0

    # Umbral para detectar N+1 (queries similares en secuencia)
    N_PLUS_ONE_THRESHOLD = 5

    def __init__(self):
        self.queries: List[QueryInfo] = []
        self._active = False
        self._listeners = []

    def _attach_listeners(self, session: Optional[AsyncSession] = None):
        """Attach SQLAlchemy event listeners para monitorear queries."""
        if not session:
            return

        try:
            from unittest.mock import MagicMock, NonCallableMagicMock

            bind = getattr(session, 'bind', None)
            if bind is None or isinstance(bind, (MagicMock, NonCallableMagicMock)):
                return

            sync_engine = getattr(bind, 'sync_engine', None)
            if sync_engine is None or isinstance(sync_engine, (MagicMock, NonCallableMagicMock)):
                return

            if hasattr(sync_engine, 'dispatch') and not isinstance(sync_engine.dispatch, (MagicMock, NonCallableMagicMock)):
                @event.listens_for(sync_engine, "before_cursor_execute")
                def on_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                    context._query_start_time = time.perf_counter()
                    context._query_statement = statement

                @event.listens_for(sync_engine, "after_cursor_execute")
                def on_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                    if hasattr(context, '_query_start_time'):
                        duration = (time.perf_counter() - context._query_start_time) * 1000
                        query_info = QueryInfo(
                            statement=statement,
                            parameters=parameters if parameters else (),
                            duration_ms=duration,
                            timestamp=time.time()
                        )
                        self.queries.append(query_info)

                        # Log slow queries immediately
                        if duration > self.SLOW_QUERY_THRESHOLD:
                            logger.warning(
                                f"🐌 Slow query detected: {duration:.2f}ms - {statement[:100]}..."
                            )

                self._listeners = [
                    (sync_engine, "before_cursor_execute", on_before_cursor_execute),
                    (sync_engine, "after_cursor_execute", on_after_cursor_execute)
                ]
        except (AttributeError, TypeError, ImportError):
            pass

    def _detach_listeners(self):
        """Detach event listeners."""
        for engine, event_name, fn in self._listeners:
            try:
                event.remove(engine, event_name, fn)
            except Exception:
                pass
        self._listeners = []

    @contextmanager
    def analyze(self, session: Optional[AsyncSession] = None):
        """
        Context manager para analizar queries.

        Args:
            session: Sesión SQLAlchemy opcional para monitorear

        Yields:
            QueryAnalyzer: self para acceder a resultados
        """
        self.queries = []
        self._active = True

        if session:
            self._attach_listeners(session)

        try:
            yield self
        finally:
            self._active = False
            self._detach_listeners()

    def analyze_results(self) -> AnalysisResult:
        """
        Analiza las queries recolectadas y genera resultados.

        Returns:
            AnalysisResult con estadísticas y sugerencias
        """
        if not self.queries:
            return AnalysisResult()

        total_time = sum(q.duration_ms for q in self.queries)
        slow_queries = [q for q in self.queries if q.duration_ms > self.SLOW_QUERY_THRESHOLD]

        # Detectar patrones N+1
        n_plus_one_patterns = self._detect_n_plus_one_patterns()

        # Generar sugerencias
        suggestions = self._generate_suggestions(slow_queries, n_plus_one_patterns)

        return AnalysisResult(
            queries=self.queries,
            total_queries=len(self.queries),
            total_time_ms=total_time,
            slow_queries=slow_queries,
            n_plus_one_patterns=n_plus_one_patterns,
            suggestions=suggestions
        )

    def _detect_n_plus_one_patterns(self) -> List[NPlusOnePattern]:
        """
        Detecta patrones N+1 en las queries ejecutadas.

        Un patrón N+1 ocurre cuando:
        1. Se hace una query base para obtener N registros
        2. Se hacen N queries adicionales (una por cada registro)

        Returns:
            Lista de patrones N+1 detectados
        """
        patterns = []

        # Agrupar queries por tipo (simplificado)
        query_groups = defaultdict(list)
        for query in self.queries:
            # Extraer tabla principal de la query
            stmt_lower = query.statement.lower()
            if "from " in stmt_lower:
                table = stmt_lower.split("from ")[1].split()[0].strip('"')
                query_groups[table].append(query)

        # Detectar patrones: una query seguida de muchas similares
        for table, queries in query_groups.items():
            if len(queries) >= self.N_PLUS_ONE_THRESHOLD:
                # Verificar si hay un patrón de 1 + N
                base_query = queries[0].statement
                related = [q.statement for q in queries[1:]]

                pattern = NPlusOnePattern(
                    base_query=base_query,
                    related_queries=related,
                    count=len(queries) - 1,
                    suggestion=f"Consider using selectinload() for '{table}' relationship"
                )
                patterns.append(pattern)

                logger.warning(
                    f"⚠️ N+1 pattern detected: {len(queries) - 1} queries to '{table}' "
                    f"after initial query. {pattern.suggestion}"
                )

        return patterns

    def _generate_suggestions(
        self,
        slow_queries: List[QueryInfo],
        n_plus_one_patterns: List[NPlusOnePattern]
    ) -> List[str]:
        """Genera sugerencias de optimización."""
        suggestions = []

        # Sugerencias para queries lentas
        if slow_queries:
            suggestions.append(
                f"{len(slow_queries)} slow queries detected. "
                "Consider adding indexes or optimizing query logic."
            )

        # Sugerencias para N+1
        for pattern in n_plus_one_patterns:
            suggestions.append(pattern.suggestion)

        # Sugerencias generales
        if len(self.queries) > 50:
            suggestions.append(
                f"High query count ({len(self.queries)}). "
                "Consider caching or batching operations."
            )

        return suggestions


@contextmanager
def analyze_queries(session: Optional[AsyncSession] = None):
    """
    Context manager de conveniencia para análisis de queries.

    Uso:
        with analyze_queries(session) as analyzer:
            # Código a analizar
            pass
        result = analyzer.analyze_results()
        print(result.summary())

    Args:
        session: Sesión SQLAlchemy opcional

    Yields:
        QueryAnalyzer: Instancia del analizador
    """
    analyzer = QueryAnalyzer()
    with analyzer.analyze(session) as a:
        yield a


class QueryOptimizationSuggestions:
    """
    Helper class con sugerencias específicas de optimización.
    """

    @staticmethod
    def suggest_eager_loading(relationship_name: str) -> str:
        """Sugiere usar eager loading para una relación."""
        return (
            f"Use selectinload({relationship_name}) to avoid N+1 queries. "
            f"Example: query.options(selectinload(Model.{relationship_name}))"
        )

    @staticmethod
    def suggest_indexing(columns: List[str], table: str) -> str:
        """Sugiere crear un índice."""
        cols_str = ", ".join(columns)
        return (
            f"Consider adding index on ({cols_str}) for table '{table}'. "
            f"Migration: op.create_index('idx_name', '{table}', [{cols_str}])"
        )

    @staticmethod
    def suggest_batch_loading(batch_size: int = 100) -> str:
        """Sugiere usar batch loading."""
        return (
            f"Use batch loading with yield_per({batch_size}) for large result sets. "
            f"Example: query.yield_per({batch_size})"
        )

    @staticmethod
    def suggest_query_caching(cache_key: str) -> str:
        """Sugiere usar caching."""
        return (
            f"Consider caching results for '{cache_key}'. "
            f"Use Redis or in-memory cache with TTL."
        )


def detect_n_plus_one_in_service(func: F) -> F:
    """
    Decorator para detectar N+1 queries en métodos de service.

    Uso:
        @detect_n_plus_one_in_service
        async def get_users_with_details(self, ...):
            # Este método será monitoreado para N+1
            ...

    Args:
        func: Función async a decorar

    Returns:
        Función decorada
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Obtener session de los argumentos (usualmente self.session)
        session = None
        if args and hasattr(args[0], 'session'):
            session = args[0].session

        analyzer = QueryAnalyzer()

        with analyzer.analyze(session):
            result = await func(*args, **kwargs)

        # Analizar y loggear si hay problemas
        analysis = analyzer.analyze_results()

        if analysis.n_plus_one_patterns:
            func_name = func.__name__
            logger.warning(
                f"⚠️ N+1 pattern detected in {func_name}(): "
                f"{len(analysis.n_plus_one_patterns)} patterns found"
            )
            for pattern in analysis.n_plus_one_patterns:
                logger.warning(f"  - {pattern.suggestion}")

        if analysis.slow_queries:
            func_name = func.__name__
            logger.warning(
                f"🐌 Slow queries detected in {func_name}(): "
                f"{len(analysis.slow_queries)} queries > 100ms"
            )

        return result

    return wrapper


# ===== UTILITY FUNCTIONS =====

def get_eager_load_options(model_class, *relationship_paths: str) -> List[Any]:
    """
    Genera opciones de eager loading para múltiples relaciones.

    Uso:
        options = get_eager_load_options(VIPSubscriber, "user", "token.plan")
        query = select(VIPSubscriber).options(*options)

    Args:
        model_class: Clase del modelo SQLAlchemy
        relationship_paths: Rutas de relaciones a cargar (ej: "user", "token.plan")

    Returns:
        Lista de opciones para query.options()
    """
    options = []
    for path in relationship_paths:
        parts = path.split(".")
        current_attr = model_class
        for part in parts:
            current_attr = getattr(current_attr, part)
        options.append(selectinload(current_attr))
    return options
