"""
Configuración centralizada del bot con carga de variables de entorno.
Validación automática de configuración requerida.
"""
import os
import sys
import logging
from typing import List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """
    Configuración global del bot.

    Carga variables de entorno y proporciona valores por defecto.
    Valida que la configuración mínima esté presente.
    """

    # ===== TELEGRAM =====
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Admin IDs: lista de user IDs con permisos de administración
    # Formato en .env: "123456,789012,345678"
    ADMIN_USER_IDS: List[int] = []

    # ===== DATABASE =====
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///bot.db"
    )

    # ===== CHANNELS =====
    # Se configuran desde el bot, no desde .env (opcionales)
    VIP_CHANNEL_ID: Optional[str] = os.getenv("VIP_CHANNEL_ID", None)
    FREE_CHANNEL_ID: Optional[str] = os.getenv("FREE_CHANNEL_ID", None)

    # ===== BOT SETTINGS =====
    DEFAULT_WAIT_TIME_MINUTES: int = int(
        os.getenv("DEFAULT_WAIT_TIME_MINUTES", "5")
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ===== LIMITS (Optimizados para Termux) =====
    # Máximo de suscriptores VIP antes de alertar
    MAX_VIP_SUBSCRIBERS: int = int(
        os.getenv("MAX_VIP_SUBSCRIBERS", "1000")
    )

    # Tamaño máximo de token (caracteres)
    TOKEN_LENGTH: int = 16

    # Duración por defecto de tokens (horas)
    DEFAULT_TOKEN_DURATION_HOURS: int = 24

    # ===== BACKGROUND TASKS =====
    # Intervalo de limpieza de VIPs expirados (minutos)
    CLEANUP_INTERVAL_MINUTES: int = int(
        os.getenv("CLEANUP_INTERVAL_MINUTES", "60")
    )

    # Intervalo de procesamiento de cola Free (minutos)
    PROCESS_FREE_QUEUE_MINUTES: int = int(
        os.getenv("PROCESS_FREE_QUEUE_MINUTES", "5")
    )

    @classmethod
    def load_admin_ids(cls):
        """
        Carga y parsea los IDs de administradores desde ADMIN_USER_IDS.

        Formato esperado en .env: "123456,789012,345678"
        """
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")

        if not admin_ids_str:
            logger.error("❌ ADMIN_USER_IDS no configurado en .env")
            return []

        try:
            # Split por comas, strip espacios, convertir a int
            cls.ADMIN_USER_IDS = [
                int(uid.strip())
                for uid in admin_ids_str.split(",")
                if uid.strip()
            ]
            logger.info(f"✅ {len(cls.ADMIN_USER_IDS)} admin(s) configurado(s)")
            return cls.ADMIN_USER_IDS
        except ValueError as e:
            logger.error(f"❌ Error parseando ADMIN_USER_IDS: {e}")
            return []

    @classmethod
    def validate(cls) -> bool:
        """
        Valida que la configuración mínima esté presente.

        Requerido:
        - BOT_TOKEN
        - Al menos 1 ADMIN_USER_ID

        Returns:
            True si configuración es válida, False en caso contrario
        """
        errors = []

        # Validar BOT_TOKEN
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN no configurado en .env")
        elif len(cls.BOT_TOKEN) < 20:
            errors.append("BOT_TOKEN parece inválido (muy corto)")

        # Validar ADMIN_USER_IDS
        cls.load_admin_ids()
        if not cls.ADMIN_USER_IDS:
            errors.append("ADMIN_USER_IDS no configurado o inválido en .env")

        # Validar DATABASE_URL
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL no configurado")

        # Validar DEFAULT_WAIT_TIME_MINUTES
        if cls.DEFAULT_WAIT_TIME_MINUTES < 1:
            errors.append("DEFAULT_WAIT_TIME_MINUTES debe ser >= 1")

        # Reportar errores
        if errors:
            logger.error("❌ Errores de configuración:")
            for error in errors:
                logger.error(f"  - {error}")
            return False

        logger.info("✅ Configuración validada correctamente")
        return True

    @classmethod
    def setup_logging(cls):
        """
        Configura el sistema de logging según LOG_LEVEL.

        Niveles soportados: DEBUG, INFO, WARNING, ERROR, CRITICAL
        """
        numeric_level = getattr(logging, cls.LOG_LEVEL.upper(), None)

        if not isinstance(numeric_level, int):
            logger.warning(f"LOG_LEVEL inválido: {cls.LOG_LEVEL}, usando INFO")
            numeric_level = logging.INFO

        # Formato de logs
        log_format = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )

        logger.info(f"📝 Logging configurado: nivel {cls.LOG_LEVEL}")

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """
        Verifica si un user_id es administrador.

        Args:
            user_id: ID de usuario de Telegram

        Returns:
            True si es admin, False en caso contrario
        """
        return user_id in cls.ADMIN_USER_IDS

    @classmethod
    def get_summary(cls) -> str:
        """
        Retorna un resumen de la configuración actual (para logging).

        Oculta información sensible como el token completo.
        """
        token_preview = (
            f"{cls.BOT_TOKEN[:10]}..."
            if cls.BOT_TOKEN
            else "NO CONFIGURADO"
        )

        return f"""
╔════════════════════════════════════════╗
║     CONFIGURACIÓN DEL BOT              ║
╚════════════════════════════════════════╝
🤖 Bot Token: {token_preview}
👤 Admins: {len(cls.ADMIN_USER_IDS)} configurado(s)
💾 Database: {cls.DATABASE_URL}
📺 Canal VIP: {cls.VIP_CHANNEL_ID or 'No configurado'}
📺 Canal Free: {cls.FREE_CHANNEL_ID or 'No configurado'}
⏱️  Tiempo espera: {cls.DEFAULT_WAIT_TIME_MINUTES} min
📝 Log level: {cls.LOG_LEVEL}
        """.strip()


# ===== INICIALIZACIÓN AUTOMÁTICA =====
# Configurar logging al importar el módulo
Config.setup_logging()

# Validar configuración (pero no fallar el import)
if not Config.validate():
    logger.warning(
        "⚠️ Configuración incompleta. "
        "Edita .env antes de ejecutar el bot."
    )
