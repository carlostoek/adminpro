"""
Engine SQLAlchemy Async y factory de sesiones.
Soporte multi-dialecto: SQLite y PostgreSQL con detección automática.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text

from config import Config
from bot.database.base import Base
from bot.database.models import BotConfig
from bot.database.dialect import parse_database_url, DatabaseDialect

logger = logging.getLogger(__name__)

# ===== ENGINE GLOBAL =====
# Se inicializa una vez al llamar init_db()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Retorna el engine de SQLAlchemy (debe estar inicializado).

    Raises:
        RuntimeError: Si el engine no ha sido inicializado con init_db()
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine no inicializado. "
            "Llama a init_db() primero."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Retorna el factory de sesiones (debe estar inicializado).

    Raises:
        RuntimeError: Si el factory no ha sido inicializado con init_db()
    """
    if _session_factory is None:
        raise RuntimeError(
            "Session factory no inicializado. "
            "Llama a init_db() primero."
        )
    return _session_factory


class SessionContextManager:
    """Context manager para AsyncSession con manejo de errores."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
                logger.error(f"❌ Error en sesión de BD: {exc_val}")
        finally:
            await self.session.close()


def get_session() -> SessionContextManager:
    """
    Retorna un context manager para una sesión de base de datos.

    Uso:
        async with get_session() as session:
            # usar session
            # commit automático si no hay error
            # rollback automático si hay error

    Returns:
        SessionContextManager: Context manager de sesión
    """
    factory = get_session_factory()
    session = factory()
    return SessionContextManager(session)


def create_async_engine_with_logging(
    db_url: str,
    dialect: DatabaseDialect,
    debug_mode: bool = False
) -> AsyncEngine:
    """
    Crea un AsyncEngine con configuración de logging opcional.

    Args:
        db_url: URL de conexión a la base de datos
        dialect: Dialecto de base de datos (SQLite o PostgreSQL)
        debug_mode: Si True, habilita logging de queries SQL

    Returns:
        AsyncEngine configurado
    """
    # Configurar logging de SQLAlchemy si está en debug mode
    if debug_mode:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        echo = True
        logger.info("🐛 SQL query logging enabled (debug mode)")
    else:
        echo = False

    # Crear engine según dialecto
    if dialect == DatabaseDialect.POSTGRESQL:
        return create_async_engine(
            db_url,
            echo=echo,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args={
                "timeout": 30,
                "command_timeout": 30
            }
        )
    elif dialect == DatabaseDialect.SQLITE:
        engine = create_async_engine(
            db_url,
            echo=echo,
            poolclass=NullPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            }
        )
        return engine
    else:
        raise ValueError(f"Dialecto no soportado: {dialect.value}")


async def init_db(debug_mode: bool = False) -> None:
    """
    Inicializa el engine con detección automática de dialecto.

    Soporta SQLite y PostgreSQL con configuraciones optimizadas:
    - SQLite: WAL mode, NullPool, optimizaciones Termux
    - PostgreSQL: QueuePool, pool_pre_ping, timeouts

    Detecta el dialecto desde Config.DATABASE_URL automáticamente.

    Args:
        debug_mode: Si True, habilita logging detallado de queries SQL
    """
    global _engine, _session_factory

    logger.info("🔧 Inicializando base de datos...")

    # Detectar dialecto desde DATABASE_URL
    try:
        dialect, db_url = parse_database_url(Config.DATABASE_URL)
        logger.info(f"🔍 Dialecto detectado desde DATABASE_URL: {dialect.value}")
    except ValueError as e:
        logger.error(f"❌ Error detectando dialecto: {e}")
        raise

    # Crear engine según dialecto
    if dialect == DatabaseDialect.POSTGRESQL:
        _engine = await _create_postgresql_engine(db_url, debug_mode=debug_mode)
    elif dialect == DatabaseDialect.SQLITE:
        _engine = await _create_sqlite_engine(db_url, debug_mode=debug_mode)
    else:
        raise ValueError(
            f"Dialecto no soportado: {dialect.value}. "
            "Use 'sqlite://' o 'postgresql://'"
        )

    # Crear todas las tablas
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tablas creadas/verificadas")

    # Crear session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False  # No refrescar objetos después de commit
    )

    # Crear registro inicial de BotConfig (singleton)
    await _ensure_bot_config_exists()

    logger.info("✅ Base de datos inicializada correctamente")


async def _create_postgresql_engine(url: str, debug_mode: bool = False) -> AsyncEngine:
    """
    Crea un AsyncEngine optimizado para PostgreSQL.

    Configuración:
    - QueuePool con pool_size=5, max_overflow=10
    - pool_pre_ping=True para validar conexiones
    - timeout=30, command_timeout=30

    Args:
        url: URL de conexión PostgreSQL con asyncpg driver
        debug_mode: Si True, habilita logging de queries SQL

    Returns:
        AsyncEngine configurado para PostgreSQL
    """
    logger.info("🐘 Configurando PostgreSQL engine...")

    engine = create_async_engine(
        url,
        echo=debug_mode,  # Logging de queries si debug_mode=True
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Validar conexiones antes de usar
        connect_args={
            "timeout": 30,
            "command_timeout": 30
        }
    )

    logger.info(
        "✅ PostgreSQL engine configurado "
        f"(pool_size=5, max_overflow=10, pool_pre_ping=True, debug={debug_mode})"
    )

    return engine


async def _create_sqlite_engine(url: str, debug_mode: bool = False) -> AsyncEngine:
    """
    Crea un AsyncEngine optimizado para SQLite.

    Configuración para Termux:
    - WAL mode (Write-Ahead Logging) para mejor concurrencia
    - NORMAL synchronous (balance performance/seguridad)
    - Cache de 64MB
    - NullPool (SQLite no necesita connection pooling)

    Args:
        url: URL de conexión SQLite con aiosqlite driver
        debug_mode: Si True, habilita logging de queries SQL

    Returns:
        AsyncEngine configurado para SQLite
    """
    logger.info("🗄️ Configurando SQLite engine...")

    engine = create_async_engine(
        url,
        echo=debug_mode,  # Logging de queries si debug_mode=True
        poolclass=NullPool,  # SQLite no necesita pool
        connect_args={
            "check_same_thread": False,  # Necesario para async
            "timeout": 30  # Timeout generoso para Termux
        }
    )

    # Configurar SQLite para mejor performance en Termux
    async with engine.begin() as conn:
        # WAL mode: permite lecturas concurrentes mientras se escribe
        await conn.execute(text("PRAGMA journal_mode=WAL"))

        # NORMAL: fsync solo en checkpoints críticos (más rápido)
        await conn.execute(text("PRAGMA synchronous=NORMAL"))

        # Cache de 64MB (mejora performance de queries)
        await conn.execute(text("PRAGMA cache_size=-64000"))

        # Foreign keys habilitadas
        await conn.execute(text("PRAGMA foreign_keys=ON"))

        logger.info(f"✅ SQLite configurado (WAL mode, cache 64MB, debug={debug_mode})")

    return engine


async def _ensure_bot_config_exists() -> None:
    """
    Crea el registro inicial de BotConfig si no existe.

    BotConfig es singleton: solo debe haber 1 registro (id=1).
    """
    async with get_session() as session:
        # Verificar si ya existe
        result = await session.get(BotConfig, 1)

        if result is None:
            # Crear registro inicial
            config = BotConfig(
                id=1,
                vip_channel_id=Config.VIP_CHANNEL_ID,
                free_channel_id=Config.FREE_CHANNEL_ID,
                wait_time_minutes=Config.DEFAULT_WAIT_TIME_MINUTES,
                vip_reactions=[],
                free_reactions=[],
                subscription_fees={"monthly": 10, "yearly": 100},
                free_channel_invite_link=Config.FREE_CHANNEL_INVITE_LINK
            )
            session.add(config)
            await session.commit()
            logger.info("✅ BotConfig inicial creado")
            if Config.FREE_CHANNEL_INVITE_LINK:
                logger.info(f"🔗 Invite link Free configurado: {Config.FREE_CHANNEL_INVITE_LINK}")
        else:
            logger.info("✅ BotConfig ya existe")

            # Sincronizar invite link desde variable de entorno si está definida
            if Config.FREE_CHANNEL_INVITE_LINK:
                if result.free_channel_invite_link != Config.FREE_CHANNEL_INVITE_LINK:
                    result.free_channel_invite_link = Config.FREE_CHANNEL_INVITE_LINK
                    await session.commit()
                    logger.info(
                        f"🔗 Invite link Free actualizado desde env: "
                        f"{Config.FREE_CHANNEL_INVITE_LINK}"
                    )
                else:
                    logger.debug("🔗 Invite link Free ya está sincronizado")


async def close_db() -> None:
    """
    Cierra el engine de base de datos (cleanup al apagar el bot).
    """
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("🔌 Base de datos cerrada")
        _engine = None
        _session_factory = None
