"""
Middleware de validación de IPs para webhooks de Telegram.

Protege contra spoofing de webhooks validando que las peticiones
provengan exclusivamente de las IPs oficiales de Telegram.

Documentación oficial:
https://core.telegram.org/bots/webhooks

Vulnerabilidad corregida: ALTA-006
"""
import ipaddress
import logging
from typing import Optional

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

logger = logging.getLogger(__name__)


class TelegramIPValidationMiddleware:
    """
    Middleware para validar que las peticiones de webhook provengan
    de las IPs oficiales de Telegram.

    IPs oficiales de Telegram para webhooks (documentadas):
    - 149.154.160.0/20
    - 91.108.4.0/22

    Referencia: https://core.telegram.org/bots/webhooks

    Attributes:
        telegram_networks: Lista de redes IPv4/IPv6 autorizadas
        trust_x_forwarded_for: Si se debe confiar en header X-Forwarded-For
                               (útil cuando está detrás de proxy/load balancer)
    """

    # Rangos de IPs oficiales de Telegram para webhooks
    # Documentados en: https://core.telegram.org/bots/webhooks
    TELEGRAM_IP_RANGES = [
        # IPv4 ranges
        "149.154.160.0/20",
        "91.108.4.0/22",
        # IPv6 ranges (si aplica en el futuro)
        # "2001:67c:4e8::/48",
    ]

    def __init__(self, trust_x_forwarded_for: bool = False):
        """
        Inicializa el middleware de validación de IPs.

        Args:
            trust_x_forwarded_for: Si True, usa el header X-Forwarded-For
                                   para obtener la IP real del cliente.
                                   Útil cuando el bot está detrás de un
                                   proxy o load balancer (Railway, etc.)
        """
        self.telegram_networks = [
            ipaddress.ip_network(network)
            for network in self.TELEGRAM_IP_RANGES
        ]
        self.trust_x_forwarded_for = trust_x_forwarded_for
        logger.info(
            f"🔒 TelegramIPValidationMiddleware inicializado "
            f"(trust_x_forwarded_for={trust_x_forwarded_for})"
        )

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extrae la IP del cliente de la petición.

        Si trust_x_forwarded_for es True, intenta obtener la IP real
        desde el header X-Forwarded-For (útil detrás de proxies).

        Args:
            request: Petición HTTP entrante

        Returns:
            IP del cliente como string, o None si no se puede determinar
        """
        if self.trust_x_forwarded_for:
            # Cuando está detrás de un proxy, la IP real viene en X-Forwarded-For
            # Formato: "client, proxy1, proxy2" - tomamos el primero (cliente real)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Tomar la primera IP (la del cliente original)
                client_ip = forwarded_for.split(",")[0].strip()
                logger.debug(f"📡 IP desde X-Forwarded-For: {client_ip}")
                return client_ip

            # Fallback a X-Real-IP (algunos proxies usan este header)
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                logger.debug(f"📡 IP desde X-Real-IP: {real_ip}")
                return real_ip

        # IP directa de la conexión
        peername = request.transport.get_extra_info("peername")
        if peername:
            client_ip = peername[0]
            logger.debug(f"📡 IP directa: {client_ip}")
            return client_ip

        return None

    def _is_telegram_ip(self, ip_str: str) -> bool:
        """
        Verifica si una IP pertenece a los rangos oficiales de Telegram.

        Args:
            ip_str: Dirección IP como string

        Returns:
            True si la IP está en los rangos autorizados de Telegram
        """
        try:
            ip = ipaddress.ip_address(ip_str)

            # Verificar contra todas las redes de Telegram
            for network in self.telegram_networks:
                if ip in network:
                    return True

            return False
        except ValueError:
            # IP inválida
            logger.warning(f"⚠️ IP inválida recibida: {ip_str}")
            return False

    async def __call__(
        self,
        request: Request,
        handler
    ) -> Response:
        """
        Procesa la petición validando la IP de origen.

        Args:
            request: Petición HTTP entrante
            handler: Handler siguiente en la cadena

        Returns:
            Response del handler si la IP es válida,
            403 Forbidden si la IP no está autorizada
        """
        client_ip = self._get_client_ip(request)

        if not client_ip:
            logger.error("❌ No se pudo determinar la IP del cliente")
            return web.Response(
                status=403,
                text="Forbidden: Unable to determine client IP"
            )

        if not self._is_telegram_ip(client_ip):
            logger.warning(
                f"🚫 Acceso denegado a webhook desde IP no autorizada: {client_ip}"
            )
            return web.Response(
                status=403,
                text="Forbidden: IP not authorized"
            )

        logger.debug(f"✅ Acceso permitido desde IP de Telegram: {client_ip}")
        return await handler(request)


class TelegramIPValidationFilter:
    """
    Filtro simple para validar IPs de Telegram sin middleware completo.

    Útil para integración directa en handlers específicos.
    """

    TELEGRAM_IP_RANGES = [
        "149.154.160.0/20",
        "91.108.4.0/22",
    ]

    def __init__(self):
        self.telegram_networks = [
            ipaddress.ip_network(network)
            for network in self.TELEGRAM_IP_RANGES
        ]

    def is_valid_ip(self, ip_str: str) -> bool:
        """
        Verifica si una IP está en los rangos autorizados de Telegram.

        Args:
            ip_str: Dirección IP como string

        Returns:
            True si la IP es válida
        """
        try:
            ip = ipaddress.ip_address(ip_str)
            return any(ip in network for network in self.telegram_networks)
        except ValueError:
            return False
