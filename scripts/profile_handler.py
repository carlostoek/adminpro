#!/usr/bin/env python3
"""
CLI Handler Profiler

Profilea handlers especificos del bot para identificar
bottlenecks de rendimiento.

Uso:
    python scripts/profile_handler.py bot.handlers.admin.main.cmd_admin
    python scripts/profile_handler.py bot.handlers.user.start.cmd_start --iterations=5
    python scripts/profile_handler.py --list
"""

import argparse
import asyncio
import importlib
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.utils.profiler import AsyncProfiler, ProfileResult


def import_handler(handler_path: str):
    """Importa un handler por su path completo."""
    module_path, func_name = handler_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


def list_available_handlers():
    """Lista handlers disponibles para profiling."""
    handlers = [
        "bot.handlers.admin.main.cmd_admin",
        "bot.handlers.admin.vip.cmd_vip_panel",
        "bot.handlers.admin.free.cmd_free_panel",
        "bot.handlers.admin.users.cmd_users",
        "bot.handlers.user.start.cmd_start",
        "bot.handlers.user.vip_entry.cmd_vip",
        "bot.handlers.user.free_flow.cmd_free",
    ]
    print("Handlers disponibles:")
    for h in handlers:
        print(f"  - {h}")


async def profile_handler(
    handler_path: str,
    iterations: int = 1,
    output_format: str = "text"
) -> ProfileResult:
    """
    Profilea un handler especifico.

    Args:
        handler_path: Path completo al handler (module.submodule.func)
        iterations: Numero de veces a ejecutar
        output_format: 'text', 'html', o 'json'

    Returns:
        ProfileResult con estadisticas agregadas
    """
    handler = import_handler(handler_path)
    profiler = AsyncProfiler()

    print(f"Profileando {handler_path} ({iterations} iteraciones)...")

    # Import required modules for database setup
    import os
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./profile_test.db'

    from bot.database.engine import init_db, get_session
    from bot.database.models import Base
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    # Create fresh database for profiling
    engine = create_async_engine(
        'sqlite+aiosqlite:///./profile_test.db',
        poolclass=NullPool,
        echo=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    results = []
    for i in range(iterations):
        print(f"  Iteracion {i + 1}/{iterations}...")

        # Create fresh session for each iteration
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import async_sessionmaker

        AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

        async with AsyncSessionLocal() as session:
            # Seed BotConfig if needed
            from bot.database.models import BotConfig
            from sqlalchemy import text

            config_result = await session.execute(
                text("SELECT 1 FROM bot_config WHERE id = 1")
            )
            if not config_result.scalar():
                bot_config = BotConfig(
                    id=1,
                    wait_time_minutes=60,
                    vip_channel_id=None,
                    free_channel_id=None,
                    vip_reactions="🔥,💎",
                    free_reactions="👍",
                    subscription_fees='{"monthly": 9.99, "quarterly": 24.99, "yearly": 79.99}'
                )
                session.add(bot_config)
                await session.commit()

            # Mock objects for handler
            from unittest.mock import AsyncMock, MagicMock

            mock_message = MagicMock()
            mock_message.from_user.id = 123456
            mock_message.from_user.username = "test_user"
            mock_message.from_user.first_name = "Test"
            mock_message.from_user.last_name = "User"
            mock_message.answer = AsyncMock()
            mock_message.bot = AsyncMock()

            result = await profiler.profile_async(
                handler,
                mock_message,
                session=session
            )
            results.append(result)

    # Cleanup database
    await engine.dispose()
    import os
    if os.path.exists('./profile_test.db'):
        os.remove('./profile_test.db')

    # Aggregate results
    aggregated = ProfileResult(
        duration_ms=sum(r.duration_ms for r in results) / len(results),
        query_count=max(r.query_count for r in results),
        query_time_ms=sum(r.query_time_ms for r in results) / len(results),
        top_functions=results[0].top_functions,  # Use first iteration's functions
        text_output=results[0].text_output,
        html_output=results[0].html_output
    )

    return aggregated


def print_results(result: ProfileResult, format_type: str):
    """Imprime resultados en el formato solicitado."""
    if format_type == "text":
        print("\n" + "=" * 60)
        print("RESULTADOS DEL PROFILING")
        print("=" * 60)
        print(result.summary(limit=10))

        if result.text_output:
            print("\n" + "-" * 60)
            print("DETALLE COMPLETO:")
            print("-" * 60)
            # Print first 50 lines
            lines = result.text_output.split("\n")[:50]
            print("\n".join(lines))

    elif format_type == "html":
        output_file = "profile_report.html"
        if result.html_output:
            Path(output_file).write_text(result.html_output)
            print(f"Reporte HTML guardado: {output_file}")
        else:
            print("No hay output HTML disponible")

    elif format_type == "json":
        import json
        data = {
            "duration_ms": result.duration_ms,
            "query_count": result.query_count,
            "query_time_ms": result.query_time_ms,
            "top_functions": result.top_functions
        }
        print(json.dumps(data, indent=2))


async def main():
    parser = argparse.ArgumentParser(
        description="Profilea handlers del bot de Telegram"
    )
    parser.add_argument(
        "handler",
        nargs="?",
        help="Path completo al handler (ej: bot.handlers.admin.main.cmd_admin)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Listar handlers disponibles"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Numero de iteraciones (default: 1)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "html", "json"],
        default="text",
        help="Formato de salida"
    )
    parser.add_argument(
        "--output",
        help="Archivo de salida (para HTML)"
    )

    args = parser.parse_args()

    if args.list:
        list_available_handlers()
        return

    if not args.handler:
        parser.print_help()
        return

    try:
        result = await profile_handler(
            args.handler,
            iterations=args.iterations,
            output_format=args.format
        )
        print_results(result, args.format)

        if args.output and args.format == "html" and result.html_output:
            Path(args.output).write_text(result.html_output)
            print(f"\nGuardado en: {args.output}")

    except ImportError as e:
        print(f"Error importando handler: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error durante profiling: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
