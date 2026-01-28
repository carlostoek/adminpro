"""
Enums para el sistema.

Define enumeraciones usadas en los modelos.
"""
from enum import Enum


class UserRole(str, Enum):
    """
    Roles de usuario en el sistema.

    Roles:
        FREE: Usuario con acceso al canal Free (default)
        VIP: Usuario con suscripción VIP activa
        ADMIN: Administrador del bot

    Transiciones automáticas:
        - Nuevo usuario → FREE
        - Activar token VIP → VIP
        - Expirar suscripción → FREE
        - Asignación manual → ADMIN
    """

    FREE = "FREE"
    VIP = "VIP"
    ADMIN = "ADMIN"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del rol."""
        names = {
            UserRole.FREE: "Usuario Free",
            UserRole.VIP: "Usuario VIP",
            UserRole.ADMIN: "Administrador"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji del rol."""
        emojis = {
            UserRole.FREE: "🆓",
            UserRole.VIP: "⭐",
            UserRole.ADMIN: "👑"
        }
        return emojis[self]


class ContentCategory(str, Enum):
    """
    Categorías de contenido para paquetes.

    Categorías:
        FREE_CONTENT: Contenido gratuito (acceso para todos)
        VIP_CONTENT: Contenido VIP (requiere suscripción activa)
        VIP_PREMIUM: Contenido premium VIP (contenido exclusivo de alto valor)
    """

    FREE_CONTENT = "FREE_CONTENT"
    VIP_CONTENT = "VIP_CONTENT"
    VIP_PREMIUM = "VIP_PREMIUM"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible de la categoría."""
        names = {
            ContentCategory.FREE_CONTENT: "Contenido Gratuito",
            ContentCategory.VIP_CONTENT: "Contenido VIP",
            ContentCategory.VIP_PREMIUM: "VIP Premium"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji de la categoría."""
        emojis = {
            ContentCategory.FREE_CONTENT: "🆓",
            ContentCategory.VIP_CONTENT: "⭐",
            ContentCategory.VIP_PREMIUM: "💎"
        }
        return emojis[self]


class PackageType(str, Enum):
    """
    Tipos de paquetes de contenido.

    Tipos:
        STANDARD: Paquete estándar (sin variaciones)
        BUNDLE: Paquete con múltiples items agrupados
        COLLECTION: Colección de contenido relacionado
    """

    STANDARD = "STANDARD"
    BUNDLE = "BUNDLE"
    COLLECTION = "COLLECTION"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tipo."""
        names = {
            PackageType.STANDARD: "Estándar",
            PackageType.BUNDLE: "Paquete",
            PackageType.COLLECTION: "Colección"
        }
        return names[self]


class RoleChangeReason(str, Enum):
    """
    Razones para cambios de rol de usuario.

    Razones:
        ADMIN_GRANTED: Usuario promovido a admin manualmente
        ADMIN_REVOKED: Admin degradado a usuario regular
        VIP_PURCHASED: Usuario compró suscripción VIP
        VIP_REDEEMED: Usuario canjeó token de invitación VIP
        VIP_EXPIRED: Suscripción VIP expiró por tiempo
        VIP_EXTENDED: Suscripción VIP extendida por admin
        VIP_ENTRY_COMPLETED: Usuario completó flujo ritualizado de entrada VIP (Phase 13)
        MANUAL_CHANGE: Cambio manual de rol por admin
        SYSTEM_AUTOMATIC: Cambio automático por el sistema
    """

    ADMIN_GRANTED = "ADMIN_GRANTED"
    ADMIN_REVOKED = "ADMIN_REVOKED"
    VIP_PURCHASED = "VIP_PURCHASED"
    VIP_REDEEMED = "VIP_REDEEMED"
    VIP_EXPIRED = "VIP_EXPIRED"
    VIP_EXTENDED = "VIP_EXTENDED"
    VIP_ENTRY_COMPLETED = "VIP_ENTRY_COMPLETED"
    MANUAL_CHANGE = "MANUAL_CHANGE"
    SYSTEM_AUTOMATIC = "SYSTEM_AUTOMATIC"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible de la razón."""
        names = {
            RoleChangeReason.ADMIN_GRANTED: "Admin Otorgado",
            RoleChangeReason.ADMIN_REVOKED: "Admin Revocado",
            RoleChangeReason.VIP_PURCHASED: "VIP Comprado",
            RoleChangeReason.VIP_REDEEMED: "VIP Canjeado",
            RoleChangeReason.VIP_EXPIRED: "VIP Expirado",
            RoleChangeReason.VIP_EXTENDED: "VIP Extendido",
            RoleChangeReason.VIP_ENTRY_COMPLETED: "Entrada VIP Completada",
            RoleChangeReason.MANUAL_CHANGE: "Cambio Manual",
            RoleChangeReason.SYSTEM_AUTOMATIC: "Automático"
        }
        return names[self]
