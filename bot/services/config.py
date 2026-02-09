"""
Config Service - Gestión de configuración global del bot.

Responsabilidades:
- Obtener/actualizar configuración de BotConfig (singleton)
- Gestionar tiempo de espera Free
- Gestionar reacciones de canales
- Validar que configuración está completa
- Configuración de economía (fórmula de niveles, besitos)
"""
import logging
import math
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import BotConfig

logger = logging.getLogger(__name__)


def _sanitize_db_url(url: Optional[str]) -> str:
    """Sanitiza una URL de base de datos ocultando credenciales.

    Args:
        url: URL completa de la base de datos

    Returns:
        URL con credenciales ocultas (ej: "postgresql://user:***@host/db")
    """
    if not url:
        return "No configurado"

    try:
        parsed = urlparse(url)

        if parsed.password:
            # Reconstruir URL sin password
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"

            sanitized = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return sanitized

        return url
    except Exception:
        # Si falla el parsing, mostrar versión muy truncada
        return f"{url[:10]}..." if len(url) > 10 else url


class ConfigService:
    """
    Service para gestionar configuración global del bot.

    BotConfig es singleton (1 solo registro con id=1).
    Todos los métodos operan sobre ese registro.
    """

    def __init__(self, session: AsyncSession):
        """
        Inicializa el service.

        Args:
            session: Sesión de base de datos
        """
        self.session = session
        logger.debug("✅ ConfigService inicializado")

    # ===== GETTERS =====

    async def get_config(self) -> BotConfig:
        """
        Obtiene la configuración del bot (singleton).

        Returns:
            BotConfig: Configuración global

        Raises:
            RuntimeError: Si BotConfig no existe (no debería pasar)
        """
        config = await self.session.get(BotConfig, 1)

        if config is None:
            raise RuntimeError(
                "BotConfig no encontrado. "
                "Ejecuta init_db() para crear la configuración inicial."
            )

        return config

    async def get_wait_time(self) -> int:
        """
        Obtiene el tiempo de espera para canal Free (en minutos).

        Returns:
            Tiempo de espera en minutos
        """
        config = await self.get_config()
        return config.wait_time_minutes

    async def get_vip_channel_id(self) -> Optional[str]:
        """
        Obtiene el ID del canal VIP configurado.

        Returns:
            ID del canal, o None si no configurado
        """
        config = await self.get_config()
        return config.vip_channel_id if config.vip_channel_id else None

    async def get_free_channel_id(self) -> Optional[str]:
        """
        Obtiene el ID del canal Free configurado.

        Returns:
            ID del canal, o None si no configurado
        """
        config = await self.get_config()
        return config.free_channel_id if config.free_channel_id else None

    async def get_vip_reactions(self) -> List[str]:
        """
        Obtiene las reacciones configuradas para el canal VIP.

        Returns:
            Lista de emojis (ej: ["👍", "❤️", "🔥"])
        """
        config = await self.get_config()
        return config.vip_reactions if config.vip_reactions else []

    async def get_free_reactions(self) -> List[str]:
        """
        Obtiene las reacciones configuradas para el canal Free.

        Returns:
            Lista de emojis
        """
        config = await self.get_config()
        return config.free_reactions if config.free_reactions else []

    async def get_subscription_fees(self) -> Dict[str, float]:
        """
        Obtiene las tarifas de suscripción configuradas.

        Returns:
            Dict con tarifas (ej: {"monthly": 10, "yearly": 100})
        """
        config = await self.get_config()
        return config.subscription_fees if config.subscription_fees else {}

    async def get_social_instagram(self) -> Optional[str]:
        """
        Get Instagram handle or URL.

        Returns:
            Instagram handle or URL, or None if not configured
        """
        config = await self.get_config()
        return config.social_instagram if config.social_instagram else None

    async def get_social_tiktok(self) -> Optional[str]:
        """
        Get TikTok handle or URL.

        Returns:
            TikTok handle or URL, or None if not configured
        """
        config = await self.get_config()
        return config.social_tiktok if config.social_tiktok else None

    async def get_social_x(self) -> Optional[str]:
        """
        Get X/Twitter handle or URL.

        Returns:
            X/Twitter handle or URL, or None if not configured
        """
        config = await self.get_config()
        return config.social_x if config.social_x else None

    async def get_free_channel_invite_link(self) -> Optional[str]:
        """
        Get stored Free channel invite link.

        Returns:
            Invite link for Free channel, or None if not configured
        """
        config = await self.get_config()
        return config.free_channel_invite_link if config.free_channel_invite_link else None

    async def get_social_media_links(self) -> dict[str, str]:
        """
        Get all configured social media links as dictionary.

        Returns:
            Dict with keys 'instagram', 'tiktok', 'x' for configured platforms only.
            Example: {'instagram': '@diana', 'tiktok': '@diana_tiktok'}
            (Unconfigured platforms omitted)

        Voice Rationale:
            Enables easy iteration for keyboard generation.
            Omitting None values simplifies UI logic.
        """
        config = await self.get_config()
        links = {}

        if config.social_instagram:
            links['instagram'] = config.social_instagram
        if config.social_tiktok:
            links['tiktok'] = config.social_tiktok
        if config.social_x:
            links['x'] = config.social_x

        return links

    # ===== SETTERS =====

    async def set_wait_time(self, minutes: int) -> None:
        """
        Actualiza el tiempo de espera para canal Free.

        Args:
            minutes: Tiempo en minutos (debe ser >= 1)

        Raises:
            ValueError: Si minutes < 1
        """
        if minutes < 1:
            raise ValueError("Tiempo de espera debe ser al menos 1 minuto")

        config = await self.get_config()
        old_value = config.wait_time_minutes
        config.wait_time_minutes = minutes

        await self.session.commit()

        logger.info(
            f"⏱️ Tiempo de espera Free actualizado: "
            f"{old_value} min → {minutes} min"
        )

    async def set_vip_reactions(self, reactions: List[str]) -> None:
        """
        Actualiza las reacciones del canal VIP.

        Args:
            reactions: Lista de emojis (ej: ["👍", "❤️"])

        Raises:
            ValueError: Si la lista está vacía o tiene más de 10 elementos
        """
        if not reactions:
            raise ValueError("Debe haber al menos 1 reacción")

        if len(reactions) > 10:
            raise ValueError("Máximo 10 reacciones permitidas")

        config = await self.get_config()
        config.vip_reactions = reactions

        await self.session.commit()

        logger.info(f"✅ Reacciones VIP actualizadas: {', '.join(reactions)}")

    async def set_free_reactions(self, reactions: List[str]) -> None:
        """
        Actualiza las reacciones del canal Free.

        Args:
            reactions: Lista de emojis

        Raises:
            ValueError: Si la lista está vacía o tiene más de 10 elementos
        """
        if not reactions:
            raise ValueError("Debe haber al menos 1 reacción")

        if len(reactions) > 10:
            raise ValueError("Máximo 10 reacciones permitidas")

        config = await self.get_config()
        config.free_reactions = reactions

        await self.session.commit()

        logger.info(f"✅ Reacciones Free actualizadas: {', '.join(reactions)}")

    async def set_subscription_fees(self, fees: Dict[str, float]) -> None:
        """
        Actualiza las tarifas de suscripción.

        Args:
            fees: Dict con tarifas (ej: {"monthly": 10, "yearly": 100})

        Raises:
            ValueError: Si fees está vacío o contiene valores negativos
        """
        if not fees:
            raise ValueError("Debe haber al menos 1 tarifa configurada")

        # Validar que todos los valores sean positivos
        for key, value in fees.items():
            if value < 0:
                raise ValueError(f"Tarifa '{key}' no puede ser negativa: {value}")

        config = await self.get_config()
        config.subscription_fees = fees

        await self.session.commit()

        logger.info(f"💰 Tarifas actualizadas: {fees}")

    async def set_social_instagram(self, handle: str) -> None:
        """
        Set Instagram handle or URL.

        Args:
            handle: Instagram handle (e.g., "@diana") or full URL

        Raises:
            ValueError: If handle is empty or only whitespace
        """
        if not handle or not handle.strip():
            raise ValueError("Instagram handle cannot be empty")

        config = await self.get_config()
        config.social_instagram = handle.strip()

        await self.session.commit()

        logger.info(f"📸 Instagram actualizado: {handle.strip()}")

    async def set_social_tiktok(self, handle: str) -> None:
        """
        Set TikTok handle or URL.

        Args:
            handle: TikTok handle (e.g., "@diana_tiktok") or full URL

        Raises:
            ValueError: If handle is empty or only whitespace
        """
        if not handle or not handle.strip():
            raise ValueError("TikTok handle cannot be empty")

        config = await self.get_config()
        config.social_tiktok = handle.strip()

        await self.session.commit()

        logger.info(f"🎵 TikTok actualizado: {handle.strip()}")

    async def set_social_x(self, handle: str) -> None:
        """
        Set X/Twitter handle or URL.

        Args:
            handle: X/Twitter handle (e.g., "@diana_x") or full URL

        Raises:
            ValueError: If handle is empty or only whitespace
        """
        if not handle or not handle.strip():
            raise ValueError("X handle cannot be empty")

        config = await self.get_config()
        config.social_x = handle.strip()

        await self.session.commit()

        logger.info(f"🐦 X actualizado: {handle.strip()}")

    async def set_free_channel_invite_link(self, link: str) -> None:
        """
        Set Free channel invite link for approval messages.

        Args:
            link: Invite link for Free channel

        Raises:
            ValueError: If link is empty or only whitespace
        """
        if not link or not link.strip():
            raise ValueError("Invite link cannot be empty")

        config = await self.get_config()
        config.free_channel_invite_link = link.strip()

        await self.session.commit()

        logger.info(f"🔗 Invite link Free actualizado")

    # ===== VALIDACIÓN =====

    async def is_fully_configured(self) -> bool:
        """
        Verifica si el bot está completamente configurado.

        Configuración completa requiere:
        - Canal VIP configurado
        - Canal Free configurado
        - Tiempo de espera > 0

        Returns:
            True si configuración está completa, False si no
        """
        config = await self.get_config()

        if not config.vip_channel_id:
            return False

        if not config.free_channel_id:
            return False

        if config.wait_time_minutes < 1:
            return False

        return True

    async def get_config_status(self) -> Dict[str, any]:
        """
        Obtiene el estado de la configuración (para dashboard).

        Returns:
            Dict con información de configuración:
            {
                "is_configured": bool,
                "vip_channel_id": str | None,
                "free_channel_id": str | None,
                "wait_time_minutes": int,
                "vip_reactions_count": int,
                "free_reactions_count": int,
                "missing": List[str]  # Lista de elementos faltantes
            }
        """
        config = await self.get_config()

        missing = []

        if not config.vip_channel_id:
            missing.append("Canal VIP")

        if not config.free_channel_id:
            missing.append("Canal Free")

        if config.wait_time_minutes < 1:
            missing.append("Tiempo de espera")

        return {
            "is_configured": len(missing) == 0,
            "vip_channel_id": config.vip_channel_id,
            "free_channel_id": config.free_channel_id,
            "wait_time_minutes": config.wait_time_minutes,
            "vip_reactions_count": len(config.vip_reactions) if config.vip_reactions else 0,
            "free_reactions_count": len(config.free_reactions) if config.free_reactions else 0,
            "missing": missing
        }

    # ===== UTILIDADES =====

    async def reset_to_defaults(self) -> None:
        """
        Resetea la configuración a valores por defecto.

        ADVERTENCIA: Esto elimina la configuración de canales.
        Solo usar en caso de necesitar resetear completamente.
        """
        config = await self.get_config()

        config.vip_channel_id = None
        config.free_channel_id = None
        config.wait_time_minutes = 5
        config.vip_reactions = []
        config.free_reactions = []
        config.subscription_fees = {"monthly": 10, "yearly": 100}

        await self.session.commit()

        logger.warning("⚠️ Configuración reseteada a valores por defecto")

    async def get_config_summary(self) -> str:
        """
        Retorna un resumen de la configuración en formato texto.

        Útil para mostrar en mensajes de Telegram.

        Returns:
            String formateado con información de configuración
        """
        config = await self.get_config()
        status = await self.get_config_status()

        vip_status = "✅ Configurado" if config.vip_channel_id else "❌ No configurado"
        free_status = "✅ Configurado" if config.free_channel_id else "❌ No configurado"

        summary = f"""
📊 <b>Estado de Configuración</b>

<b>Canal VIP:</b> {vip_status}
{f"ID: <code>{config.vip_channel_id}</code>" if config.vip_channel_id else ""}

<b>Canal Free:</b> {free_status}
{f"ID: <code>{config.free_channel_id}</code>" if config.free_channel_id else ""}

<b>Tiempo de Espera:</b> {config.wait_time_minutes} minutos

<b>Reacciones VIP:</b> {len(config.vip_reactions) if config.vip_reactions else 0} configuradas
<b>Reacciones Free:</b> {len(config.free_reactions) if config.free_reactions else 0} configuradas
        """.strip()

        if not status["is_configured"]:
            summary += f"\n\n⚠️ <b>Faltante:</b> {', '.join(status['missing'])}"

        return summary

    # ===== ECONOMY CONFIGURATION =====

    async def get_level_formula(self) -> str:
        """Get current level progression formula.

        Returns:
            Formula string using total_earned variable
        """
        config = await self.get_config()
        return config.level_formula

    def _validate_formula_syntax(self, formula: str) -> Tuple[bool, str]:
        """Validate formula syntax without executing it.

        Args:
            formula: Formula string to validate

        Returns:
            (is_valid, error_message)
        """
        # Allowed tokens pattern
        allowed_pattern = r'^[\w\s+\-*/().]+$'
        if not re.match(allowed_pattern, formula):
            return False, "Formula contains invalid characters"

        # Check for allowed identifiers only
        # Extract all words from formula
        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', formula)
        allowed_words = {'total_earned', 'sqrt', 'floor'}

        for word in words:
            if word not in allowed_words:
                return False, f"Unknown identifier: {word}"

        return True, ""

    def _test_formula_evaluation(self, formula: str) -> Tuple[bool, int, str]:
        """Test formula evaluation with sample values.

        Args:
            formula: Formula string to test

        Returns:
            (success, result, error_message)
        """
        try:
            safe_dict = {
                'sqrt': math.sqrt,
                'floor': math.floor,
                'total_earned': 0
            }

            # Test with total_earned = 0
            result_0 = eval(formula, {"__builtins__": {}}, safe_dict.copy())
            if not isinstance(result_0, (int, float)):
                return False, 0, "Formula must evaluate to a number"
            if result_0 < 1:
                return False, 0, f"Formula must produce level >= 1, got {result_0}"

            # Test with total_earned = 100
            safe_dict['total_earned'] = 100
            result_100 = eval(formula, {"__builtins__": {}}, safe_dict.copy())
            if result_100 < 1:
                return False, 0, f"Formula must produce level >= 1, got {result_100}"

            # Test with total_earned = 10000
            safe_dict['total_earned'] = 10000
            result_10000 = eval(formula, {"__builtins__": {}}, safe_dict.copy())
            if result_10000 < 1:
                return False, 0, f"Formula must produce level >= 1, got {result_10000}"

            return True, int(result_0), ""

        except Exception as e:
            return False, 0, f"Formula evaluation error: {str(e)}"

    async def set_level_formula(self, formula: str) -> Tuple[bool, str]:
        """Set level progression formula.

        Args:
            formula: Formula string using total_earned variable
                     Supported: sqrt, floor, +, -, *, /, (, )

        Returns:
            (success, message)
        """
        # Validate syntax
        is_valid, error_msg = self._validate_formula_syntax(formula)
        if not is_valid:
            return False, f"invalid_syntax: {error_msg}"

        # Test evaluation
        success, _, eval_error = self._test_formula_evaluation(formula)
        if not success:
            return False, f"invalid_syntax: {eval_error}"

        # Save to config
        config = await self.get_config()
        config.level_formula = formula
        await self.session.commit()

        logger.info(f"📊 Level formula updated: {formula}")
        return True, "formula_updated"

    # Economy value getters

    async def get_besitos_per_reaction(self) -> int:
        """Get besitos awarded per reaction."""
        config = await self.get_config()
        return config.besitos_per_reaction

    async def get_besitos_daily_gift(self) -> int:
        """Get besitos awarded for daily gift."""
        config = await self.get_config()
        return config.besitos_daily_gift

    async def get_besitos_daily_streak_bonus(self) -> int:
        """Get besitos awarded for daily streak bonus."""
        config = await self.get_config()
        return config.besitos_daily_streak_bonus

    async def get_max_reactions_per_day(self) -> int:
        """Get maximum reactions allowed per day per user."""
        config = await self.get_config()
        return config.max_reactions_per_day

    # Economy value setters

    async def set_besitos_per_reaction(self, value: int) -> Tuple[bool, str]:
        """Set besitos awarded per reaction.

        Args:
            value: Must be > 0

        Returns:
            (success, message)
        """
        if value <= 0:
            return False, "value_must_be_positive"

        config = await self.get_config()
        config.besitos_per_reaction = value
        await self.session.commit()

        logger.info(f"💰 besitos_per_reaction updated: {value}")
        return True, "value_updated"

    async def set_besitos_daily_gift(self, value: int) -> Tuple[bool, str]:
        """Set besitos awarded for daily gift.

        Args:
            value: Must be > 0

        Returns:
            (success, message)
        """
        if value <= 0:
            return False, "value_must_be_positive"

        config = await self.get_config()
        config.besitos_daily_gift = value
        await self.session.commit()

        logger.info(f"🎁 besitos_daily_gift updated: {value}")
        return True, "value_updated"

    async def set_besitos_daily_streak_bonus(self, value: int) -> Tuple[bool, str]:
        """Set besitos awarded for daily streak bonus.

        Args:
            value: Must be > 0

        Returns:
            (success, message)
        """
        if value <= 0:
            return False, "value_must_be_positive"

        config = await self.get_config()
        config.besitos_daily_streak_bonus = value
        await self.session.commit()

        logger.info(f"🔥 besitos_daily_streak_bonus updated: {value}")
        return True, "value_updated"

    async def set_max_reactions_per_day(self, value: int) -> Tuple[bool, str]:
        """Set maximum reactions allowed per day per user.

        Args:
            value: Must be > 0

        Returns:
            (success, message)
        """
        if value <= 0:
            return False, "value_must_be_positive"

        config = await self.get_config()
        config.max_reactions_per_day = value
        await self.session.commit()

        logger.info(f"⚡ max_reactions_per_day updated: {value}")
        return True, "value_updated"
