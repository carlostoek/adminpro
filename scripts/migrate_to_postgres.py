#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script

Migra todos los datos desde SQLite a PostgreSQL sin pérdida.
Soporta validación de datos, dry-run y generación de reportes.

Uso:
    python scripts/migrate_to_postgres.py --source bot.db --target postgresql://...
    python scripts/migrate_to_postgres.py --source bot.db --target postgresql://... --dry-run
    python scripts/migrate_to_postgres.py --source bot.db --target postgresql://... --validate-only
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    """Reporte de migración."""
    start_time: datetime
    end_time: Optional[datetime] = None
    source_db: str = ""
    target_db: str = ""
    dry_run: bool = False
    tables_migrated: List[str] = field(default_factory=list)
    tables_failed: List[str] = field(default_factory=list)
    row_counts: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # table: (source, target)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el reporte a diccionario."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time else None
            ),
            "source_db": self.source_db,
            "target_db": self.target_db,
            "dry_run": self.dry_run,
            "tables_migrated": self.tables_migrated,
            "tables_failed": self.tables_failed,
            "row_counts": self.row_counts,
            "errors": self.errors,
            "success": len(self.tables_failed) == 0 and len(self.errors) == 0
        }

    def to_json(self, indent: int = 2) -> str:
        """Convierte el reporte a JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def summary(self) -> str:
        """Resumen del reporte en texto."""
        lines = [
            "=" * 60,
            "MIGRATION REPORT",
            "=" * 60,
            f"Source: {self.source_db}",
            f"Target: {self.target_db}",
            f"Dry Run: {self.dry_run}",
            f"Start: {self.start_time}",
        ]

        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
            lines.append(f"End: {self.end_time}")
            lines.append(f"Duration: {duration:.2f}s")

        lines.extend([
            "-" * 60,
            "TABLES MIGRATED:",
        ])

        for table in self.tables_migrated:
            counts = self.row_counts.get(table, (0, 0))
            lines.append(f"  ✓ {table}: {counts[0]} -> {counts[1]} rows")

        if self.tables_failed:
            lines.extend([
                "-" * 60,
                "TABLES FAILED:",
            ])
            for table in self.tables_failed:
                lines.append(f"  ✗ {table}")

        if self.errors:
            lines.extend([
                "-" * 60,
                "ERRORS:",
            ])
            for error in self.errors:
                lines.append(f"  • {error}")

        lines.append("=" * 60)
        return "\n".join(lines)


class DatabaseMigrator:
    """
    Migrador de base de datos SQLite a PostgreSQL.

    Características:
    - Migración ordenada respetando dependencias
    - Validación de conteos de filas
    - Soporte para dry-run
    - Reporte detallado en JSON
    """

    # Orden de migración (tablas sin FK primero, luego dependientes)
    MIGRATION_ORDER = [
        "bot_config",           # Singleton, no dependencies
        "users",                # Base table
        "subscription_plans",   # No FK dependencies
        "invitation_tokens",    # Depends on subscription_plans
        "vip_subscribers",      # Depends on users, invitation_tokens
        "free_channel_requests", # Depends on users
        "content_packages",     # No FK dependencies
        "user_interests",       # Depends on users, content_packages
        "user_role_change_log", # Depends on users
    ]

    def __init__(self, source_url: str, target_url: str, dry_run: bool = False):
        """
        Inicializa el migrador.

        Args:
            source_url: URL de SQLite (sqlite:///bot.db)
            target_url: URL de PostgreSQL (postgresql+asyncpg://...)
            dry_run: Si True, no escribe datos
        """
        self.source_url = source_url
        self.target_url = target_url
        self.dry_run = dry_run
        self.report = MigrationReport(
            start_time=datetime.utcnow(),
            source_db=source_url,
            target_db=target_url,
            dry_run=dry_run
        )

        # Engines síncronos para migración
        self.source_engine = None
        self.target_engine = None

    async def setup(self):
        """Configura las conexiones a bases de datos."""
        # Source: SQLite (síncrono)
        self.source_engine = create_engine(
            self.source_url.replace("sqlite+aiosqlite://", "sqlite://").replace("asyncpg", ""),
            echo=False
        )

        # Target: PostgreSQL (síncrono para migración)
        # Convertir asyncpg URL a psycopg2 URL
        target_sync = self.target_url.replace("postgresql+asyncpg://", "postgresql://")
        target_sync = target_sync.replace("postgresql+psycopg2://", "postgresql://")

        self.target_engine = create_engine(target_sync, echo=False)

        logger.info(f"🔌 Connected to source: {self.source_url}")
        logger.info(f"🔌 Connected to target: {self.target_url}")

    async def migrate(self) -> MigrationReport:
        """
        Ejecuta la migración completa.

        Returns:
            MigrationReport con resultados
        """
        logger.info("🚀 Starting migration...")
        logger.info(f"   Dry run: {self.dry_run}")

        try:
            await self.setup()

            # Verificar conexiones
            if not await self._verify_connections():
                self.report.errors.append("Failed to verify database connections")
                return self.report

            # Migrar cada tabla en orden
            for table_name in self.MIGRATION_ORDER:
                await self._migrate_table(table_name)

            # Validar migración
            await self.validate_migration()

        except Exception as e:
            logger.exception("Migration failed")
            self.report.errors.append(str(e))

        finally:
            self.report.end_time = datetime.utcnow()
            await self.cleanup()

        return self.report

    async def _verify_connections(self) -> bool:
        """Verifica que ambas bases de datos son accesibles."""
        try:
            # Verificar source
            with self.source_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()

            # Verificar target
            with self.target_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()

            logger.info("✅ Database connections verified")
            return True

        except Exception as e:
            logger.error(f"❌ Connection verification failed: {e}")
            return False

    async def _migrate_table(self, table_name: str):
        """
        Migra una tabla específica.

        Args:
            table_name: Nombre de la tabla a migrar
        """
        logger.info(f"📦 Migrating table: {table_name}")

        try:
            # Obtener datos de source
            source_data = await self._fetch_table_data(table_name)
            source_count = len(source_data)

            logger.info(f"   Source rows: {source_count}")

            if self.dry_run:
                logger.info(f"   [DRY-RUN] Would insert {source_count} rows")
                self.report.tables_migrated.append(table_name)
                self.report.row_counts[table_name] = (source_count, 0)
                return

            # Limpiar tabla target
            await self._clear_target_table(table_name)

            # Insertar datos
            if source_data:
                await self._insert_data(table_name, source_data)

            # Verificar conteo
            target_count = await self._count_target_rows(table_name)
            self.report.row_counts[table_name] = (source_count, target_count)

            if source_count == target_count:
                logger.info(f"   ✅ Migrated: {source_count} rows")
                self.report.tables_migrated.append(table_name)
            else:
                error = f"Row count mismatch: {source_count} -> {target_count}"
                logger.error(f"   ❌ {error}")
                self.report.tables_failed.append(table_name)
                self.report.errors.append(f"{table_name}: {error}")

        except Exception as e:
            logger.exception(f"   ❌ Failed to migrate {table_name}")
            self.report.tables_failed.append(table_name)
            self.report.errors.append(f"{table_name}: {str(e)}")

    async def _fetch_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Obtiene todos los datos de una tabla SQLite."""
        with self.source_engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.mappings().all()
            return [dict(row) for row in rows]

    async def _clear_target_table(self, table_name: str):
        """Limpia la tabla en PostgreSQL."""
        with self.target_engine.connect() as conn:
            # Deshabilitar FK checks temporalmente
            # Nota: Sin CASCADE para evitar borrado accidental de datos relacionados
            conn.execute(text(f"TRUNCATE TABLE {table_name}"))
            conn.commit()

    async def _insert_data(self, table_name: str, data: List[Dict[str, Any]]):
        """Inserta datos en PostgreSQL."""
        if not data:
            return

        with self.target_engine.connect() as conn:
            # Construir INSERT
            columns = list(data[0].keys())
            col_names = ", ".join(columns)
            placeholders = ", ".join([f":{col}" for col in columns])

            insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

            # Insertar en batch
            batch_size = 100
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                conn.execute(text(insert_sql), batch)

            conn.commit()

    async def _count_target_rows(self, table_name: str) -> int:
        """Cuenta filas en tabla target."""
        with self.target_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()

    async def validate_migration(self) -> bool:
        """
        Valida que la migración fue exitosa.

        Returns:
            True si todas las validaciones pasan
        """
        logger.info("🔍 Validating migration...")

        all_valid = True

        for table_name in self.MIGRATION_ORDER:
            if table_name in self.report.tables_failed:
                continue

            source_count = await self._count_source_rows(table_name)
            target_count = await self._count_target_rows(table_name)

            if source_count != target_count:
                logger.error(
                    f"   ❌ {table_name}: Count mismatch ({source_count} != {target_count})"
                )
                all_valid = False
            else:
                logger.info(f"   ✅ {table_name}: {source_count} rows match")

        return all_valid

    async def _count_source_rows(self, table_name: str) -> int:
        """Cuenta filas en tabla source."""
        with self.source_engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()

    async def cleanup(self):
        """Limpia recursos."""
        if self.source_engine:
            self.source_engine.dispose()
        if self.target_engine:
            self.target_engine.dispose()


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Migrate SQLite database to PostgreSQL"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="SQLite database URL (sqlite:///bot.db or sqlite+aiosqlite:///bot.db)"
    )
    parser.add_argument(
        "--target",
        required=True,
        help="PostgreSQL database URL (postgresql+asyncpg://user:pass@host/db)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without writing data"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing migration (no data transfer)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file for JSON report"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging"
    )

    return parser.parse_args()


async def main():
    """Función principal."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Crear migrador
    migrator = DatabaseMigrator(
        source_url=args.source,
        target_url=args.target,
        dry_run=args.dry_run or args.validate_only
    )

    # Ejecutar migración
    if args.validate_only:
        logger.info("🔍 Running validation only...")
        await migrator.setup()
        await migrator.validate_migration()
        await migrator.cleanup()
    else:
        report = await migrator.migrate()

        # Imprimir reporte
        print()
        print(report.summary())

        # Guardar reporte JSON si se solicitó
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report.to_json())
            logger.info(f"📄 Report saved to: {args.output}")

        # Exit code basado en éxito
        if report.tables_failed or report.errors:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
