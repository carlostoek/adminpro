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
        FREE_CONTENT: Promos (promociones para usuarios)
        VIP_CONTENT: El Diván (contenido para suscriptores VIP)
        VIP_PREMIUM: Premium (contenido exclusivo de alto valor)
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
            ContentCategory.FREE_CONTENT: "Promos",
            ContentCategory.VIP_CONTENT: "El Diván",
            ContentCategory.VIP_PREMIUM: "Premium"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji de la categoría."""
        emojis = {
            ContentCategory.FREE_CONTENT: "🌸",
            ContentCategory.VIP_CONTENT: "🛋️",
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


class TransactionType(str, Enum):
    """
    Tipos de transacciones en el sistema de economía.

    Categorías:
        EARN_*: Transacciones de ganancia (besitos entrantes)
        SPEND_*: Transacciones de gasto (besitos salientes)

    Tipos:
        EARN_REACTION: Ganancia por reaccionar a contenido
        EARN_DAILY: Ganancia por reclamar regalo diario
        EARN_STREAK: Ganancia por mantener racha
        EARN_REWARD: Ganancia por completar logro/recompensa
        EARN_ADMIN: Ganancia otorgada por administrador
        SPEND_SHOP: Gasto en tienda
        SPEND_ADMIN: Gasto por ajuste de administrador
    """

    EARN_REACTION = "EARN_REACTION"
    EARN_DAILY = "EARN_DAILY"
    EARN_STREAK = "EARN_STREAK"
    EARN_REWARD = "EARN_REWARD"
    EARN_ADMIN = "EARN_ADMIN"
    SPEND_SHOP = "SPEND_SHOP"
    SPEND_ADMIN = "SPEND_ADMIN"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tipo de transacción."""
        names = {
            TransactionType.EARN_REACTION: "Reacción",
            TransactionType.EARN_DAILY: "Regalo Diario",
            TransactionType.EARN_STREAK: "Racha",
            TransactionType.EARN_REWARD: "Recompensa",
            TransactionType.EARN_ADMIN: "Otorgado por Admin",
            TransactionType.SPEND_SHOP: "Compra en Tienda",
            TransactionType.SPEND_ADMIN: "Ajuste por Admin"
        }
        return names[self]

    @property
    def is_earn(self) -> bool:
        """Retorna True si es una transacción de ganancia."""
        return self.value.startswith("EARN_")

    @property
    def is_spend(self) -> bool:
        """Retorna True si es una transacción de gasto."""
        return self.value.startswith("SPEND_")
