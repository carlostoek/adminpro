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

    # ===== ENVIRONMENT =====
    # Entorno: "production" o "development" (default: development)
    ENV: str = os.getenv("ENV", "development")

    # ===== WEBHOOK CONFIGURATION =====
    # Modo de operación: "polling" (default) o "webhook" (Railway)
    # Polling: El bot hace requests a Telegram (bueno para desarrollo local)
    # Webhook: Telegram envía updates al bot (bueno para producción en Railway)
    WEBHOOK_MODE: str = os.getenv("WEBHOOK_MODE", "polling").lower()

    # Puerto donde el bot escucha (solo usado en webhook mode)
    # Railway asigna este puerto automáticamente
    PORT: int = int(os.getenv("PORT", "8000"))

    # Secret token para validar webhooks de Telegram (seguridad)
    # Genera uno seguro para producción: python -c "import secrets; print(secrets.token_urlsafe(32))"
    WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET", None)

    # Webhook path (URL path donde Telegram envía updates)
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")

    # Base URL para webhook (ej: https://your-app.railway.app)
    # Railway asigna RAILWAY_PUBLIC_DOMAIN automáticamente
    WEBHOOK_BASE_URL: str = os.getenv("WEBHOOK_BASE_URL", "")

    # Host donde el servidor web escucha (default: 0.0.0.0)
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")

    # ===== DATABASE =====
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///bot.db"
    )

    # ===== CHANNELS =====
    # Se configuran desde el bot, no desde .env (opcionales)
    VIP_CHANNEL_ID: Optional[str] = os.getenv("VIP_CHANNEL_ID", None)
    FREE_CHANNEL_ID: Optional[str] = os.getenv("FREE_CHANNEL_ID", None)

    # ===== CREATOR =====
    # Telegram username de Diana para botón de contacto directo (ej: "diana_artista")
    # Usado en enlaces tg://resolve?username= para chat directo
    CREATOR_USERNAME: Optional[str] = os.getenv("CREATOR_USERNAME", None)

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

    # ===== FREE CHANNEL SETTINGS =====
    # Ventana anti-spam para solicitudes Free (minutos)
    # Previene que usuarios soliciten acceso repetidamente en corto tiempo
    FREE_REQUEST_SPAM_WINDOW_MINUTES: int = int(
        os.getenv("FREE_REQUEST_SPAM_WINDOW_MINUTES", "5")
    )

    # ===== HEALTH CHECK =====
    # Puerto para el endpoint de health check (FastAPI)
    # Default: 8000 (no debe colisionar con otros servicios)
    HEALTH_PORT: int = int(os.getenv("HEALTH_PORT", "8000"))

    # Host para el health check API
    # Default: "0.0.0.0" (acepta conexiones externas, necesario para Railway)
    HEALTH_HOST: str = os.getenv("HEALTH_HOST", "0.0.0.0")

    @classmethod
    def validate_required_vars(cls) -> tuple[bool, list[str]]:
        """
        Valida que TODAS las variables de entorno requeridas estén configuradas.

        Returns:
            Tuple de (is_valid, missing_vars)
            - is_valid: True si todas las variables requeridas están presentes
            - missing_vars: Lista de nombres de variables faltantes
        """
        required_vars = {
            "BOT_TOKEN": cls.BOT_TOKEN,
            "DATABASE_URL": cls.DATABASE_URL,
        }

        # Validar que Admin IDs estén configurados
        cls.load_admin_ids()
        if not cls.ADMIN_USER_IDS:
            required_vars["ADMIN_USER_IDS"] = None

        missing = [name for name, value in required_vars.items() if not value]

        if missing:
            logger.error(f"❌ Variables requeridas faltantes: {', '.join(missing)}")
            return False, missing

        logger.info("✅ Todas las variables requeridas están configuradas")
        return True, []

    @classmethod
    def validate_database_url(cls) -> bool:
        """
        Valida que DATABASE_URL tiene un formato soportado.

        Returns:
            True si el formato es válido, False en caso contrario
        """
        try:
            from bot.database.dialect import parse_database_url
            dialect, _ = parse_database_url(cls.DATABASE_URL)
            logger.info(f"✅ DATABASE_URL dialect detectado: {dialect.value}")
            return True
        except ValueError as e:
            logger.error(f"❌ DATABASE_URL inválido: {e}")
            return False

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
        - DATABASE_URL con formato válido

        Returns:
            True si configuración es válida, False en caso contrario
        """
        errors = []

        # Validar variables requeridas
        is_valid, missing = cls.validate_required_vars()
        if not is_valid:
            errors.append(f"Faltan variables requeridas: {', '.join(missing)}")

        # Validar formato de BOT_TOKEN
        if cls.BOT_TOKEN and len(cls.BOT_TOKEN) < 20:
            errors.append("BOT_TOKEN parece inválido (muy corto)")

        # Validar DATABASE_URL
        if cls.DATABASE_URL and not cls.validate_database_url():
            errors.append("DATABASE_URL tiene formato inválido")

        # Validar DEFAULT_WAIT_TIME_MINUTES
        if cls.DEFAULT_WAIT_TIME_MINUTES < 1:
            errors.append("DEFAULT_WAIT_TIME_MINUTES debe ser >= 1")

        # Validar WEBHOOK_MODE
        if cls.WEBHOOK_MODE not in ["polling", "webhook"]:
            errors.append(f"WEBHOOK_MODE inválido: '{cls.WEBHOOK_MODE}'. Debe ser 'polling' o 'webhook'")

        # Validar PORT si está en webhook mode
        if cls.WEBHOOK_MODE == "webhook":
            if not (1 <= cls.PORT <= 65535):
                errors.append(f"PORT inválido: {cls.PORT}. Debe estar entre 1 y 65535")

        # Validar WEBHOOK_SECRET en webhook mode (opcional pero recomendado)
        if cls.WEBHOOK_MODE == "webhook" and not cls.WEBHOOK_SECRET:
            logger.warning("⚠️ WEBHOOK_SECRET no configurado en modo webhook. Se recomienda para seguridad.")

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

        webhook_info = ""
        if cls.WEBHOOK_MODE == "webhook":
            webhook_url = f"{cls.WEBHOOK_BASE_URL}{cls.WEBHOOK_PATH}" if cls.WEBHOOK_BASE_URL else f"port {cls.PORT}"
            webhook_info = f"\n🔗 Webhook: {webhook_url}"

        return f"""
╔════════════════════════════════════════╗
║     CONFIGURACIÓN DEL BOT              ║
╚════════════════════════════════════════╝
🌍 Ambiente: {cls.ENV.upper()}
🔄 Modo: {cls.WEBHOOK_MODE.upper()}{webhook_info}
🤖 Bot Token: {token_preview}
👤 Admins: {len(cls.ADMIN_USER_IDS)} configurado(s)
💾 Database: {cls.DATABASE_URL}
📺 Canal VIP: {cls.VIP_CHANNEL_ID or 'No configurado'}
📺 Canal Free: {cls.FREE_CHANNEL_ID or 'No configurado'}
⏱️  Tiempo espera: {cls.DEFAULT_WAIT_TIME_MINUTES} min
🏥 Health API: http://{cls.HEALTH_HOST}:{cls.HEALTH_PORT}/health
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
