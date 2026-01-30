"""
Database URL parser and dialect detector.

Soporta SQLite y PostgreSQL con detección automática desde DATABASE_URL.
Auto-inyecta drivers cuando no están especificados en la URL.
"""
import logging
from enum import Enum
from typing import Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class DatabaseDialect(Enum):
    """Dialectos de base de datos soportados."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    UNSUPPORTED = "unsupported"


def parse_database_url(url: str) -> Tuple[DatabaseDialect, str]:
    """
    Parsea DATABASE_URL y detecta el dialecto de base de datos.

    Auto-inyecta el driver apropiado si no está especificado:
    - sqlite:// → sqlite+aiosqlite://
    - postgresql:// → postgresql+asyncpg://

    Args:
        url: URL de conexión a base de datos (ej: sqlite:///bot.db)

    Returns:
        Tuple[DatabaseDialect, str]: (dialeto detectado, URL con driver inyectado)

    Raises:
        ValueError: Si URL está vacía, es inválida o el dialecto no es soportado

    Examples:
        >>> dialect, url = parse_database_url("sqlite:///bot.db")
        >>> assert dialect == DatabaseDialect.SQLITE
        >>> assert "aiosqlite" in url

        >>> dialect, url = parse_database_url("postgresql://localhost/test")
        >>> assert dialect == DatabaseDialect.POSTGRESQL
        >>> assert "asyncpg" in url
    """
    # Validar que URL no esté vacía
    if not url or not url.strip():
        raise ValueError(
            "DATABASE_URL está vacío. "
            "Debe ser sqlite:///bot.db o postgresql://host/db"
        )

    url = url.strip()

    # Parsear URL para obtener el scheme
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
    except Exception as e:
        raise ValueError(f"DATABASE_URL inválido: {e}") from e

    # Validar que existe un scheme
    if not scheme:
        raise ValueError(
            "DATABASE_URL no tiene un esquema válido. "
            "Debe comenzar con 'sqlite://' o 'postgresql://'"
        )

    # Extraer dialecto base (sin el driver si existe)
    # ej: postgresql+asyncpg → postgresql
    base_scheme = scheme.split("+")[0]

    # Detectar dialecto e inyectar driver si es necesario
    if base_scheme == "sqlite":
        # SQLite detectado
        dialect = DatabaseDialect.SQLITE

        # Auto-inyectar aiosqlite si no está presente
        if "+" not in scheme:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            logger.debug("Auto-inyectado driver aiosqlite para SQLite")

        logger.info(f"🗄️ Dialecto detectado: SQLite")
        return dialect, url

    elif base_scheme == "postgresql":
        # PostgreSQL detectado
        dialect = DatabaseDialect.POSTGRESQL

        # Auto-inyectar asyncpg si no está presente
        if "+" not in scheme:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            logger.debug("Auto-inyectado driver asyncpg para PostgreSQL")

        logger.info(f"🐘 Dialecto detectado: PostgreSQL")
        return dialect, url

    else:
        # Dialecto no soportado
        dialect = DatabaseDialect.UNSUPPORTED
        raise ValueError(
            f"Dialecto de base de datos no soportado: '{base_scheme}'. "
            "Dialectos soportados: 'sqlite', 'postgresql'. "
            "Ejemplos válidos: "
            "'sqlite:///bot.db', "
            "'postgresql://user:pass@host:5432/dbname'"
        )


def is_production_database(url: str) -> bool:
    """
    Determina si la URL corresponde a una base de datos de producción.

    Considera PostgreSQL como producción y SQLite como desarrollo.

    Args:
        url: URL de conexión a base de datos

    Returns:
        True si es PostgreSQL (producción), False si es SQLite (desarrollo)

    Examples:
        >>> is_production_database("postgresql://localhost/test")
        True
        >>> is_production_database("sqlite:///bot.db")
        False
    """
    try:
        dialect, _ = parse_database_url(url)
        return dialect == DatabaseDialect.POSTGRESQL
    except ValueError:
        # Si la URL es inválida, asumir desarrollo (False)
        logger.warning(
            f"URL inválida en is_production_database(): {url}. "
            "Asumiendo desarrollo (False)."
        )
        return False
