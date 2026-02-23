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


class StreakType(str, Enum):
    """
    Tipos de rachas en el sistema de gamificación.

    Tipos:
        DAILY_GIFT: Racha de reclamos diarios de regalo
        REACTION: Racha de días consecutivos con reacciones
    """

    DAILY_GIFT = "DAILY_GIFT"
    REACTION = "REACTION"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tipo de racha."""
        names = {
            StreakType.DAILY_GIFT: "Regalo Diario",
            StreakType.REACTION: "Reacciones"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji del tipo de racha."""
        emojis = {
            StreakType.DAILY_GIFT: "🎁",
            StreakType.REACTION: "🔥"
        }
        return emojis[self]


class ContentType(str, Enum):
    """
    Tipos de contenido para ContentSet.

    Tipos:
        PHOTO_SET: Set de fotos
        VIDEO: Video individual
        AUDIO: Audio/Nota de voz
        MIXED: Contenido mixto (fotos + video)
    """

    PHOTO_SET = "photo_set"
    VIDEO = "video"
    AUDIO = "audio"
    MIXED = "mixed"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tipo de contenido."""
        names = {
            ContentType.PHOTO_SET: "Set de Fotos",
            ContentType.VIDEO: "Video",
            ContentType.AUDIO: "Audio",
            ContentType.MIXED: "Mixto"
        }
        return names[self]


class ContentTier(str, Enum):
    """
    Niveles de tier para contenido y productos.

    Tiers:
        FREE: Contenido gratuito
        VIP: Contenido para suscriptores VIP
        PREMIUM: Contenido exclusivo de alto valor
        GIFT: Contenido de regalo/promocional
    """

    FREE = "free"
    VIP = "vip"
    PREMIUM = "premium"
    GIFT = "gift"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tier."""
        names = {
            ContentTier.FREE: "Gratis",
            ContentTier.VIP: "VIP",
            ContentTier.PREMIUM: "Premium",
            ContentTier.GIFT: "Regalo"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji del tier."""
        emojis = {
            ContentTier.FREE: "🌸",
            ContentTier.VIP: "⭐",
            ContentTier.PREMIUM: "💎",
            ContentTier.GIFT: "🎁"
        }
        return emojis[self]


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
        EARN_SHOP_REFUND: Reembolso de compra en tienda
        SPEND_SHOP: Gasto en tienda
        SPEND_ADMIN: Gasto por ajuste de administrador
    """

    EARN_REACTION = "EARN_REACTION"
    EARN_DAILY = "EARN_DAILY"
    EARN_STREAK = "EARN_STREAK"
    EARN_REWARD = "EARN_REWARD"
    EARN_ADMIN = "EARN_ADMIN"
    EARN_SHOP_REFUND = "EARN_SHOP_REFUND"
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
            TransactionType.EARN_SHOP_REFUND: "Reembolso de Tienda",
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


class RewardType(str, Enum):
    """
    Tipos de recompensas en el sistema.

    Tipos:
        BESITOS: Recompensa en moneda virtual (besitos)
        CONTENT: Desbloqueo de contenido (ContentSet)
        BADGE: Insignia de logro (cosmética)
        VIP_EXTENSION: Extensión de suscripción VIP
    """

    BESITOS = "BESITOS"
    CONTENT = "CONTENT"
    BADGE = "BADGE"
    VIP_EXTENSION = "VIP_EXTENSION"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tipo de recompensa."""
        names = {
            RewardType.BESITOS: "Besitos",
            RewardType.CONTENT: "Contenido",
            RewardType.BADGE: "Insignia",
            RewardType.VIP_EXTENSION: "Extensión VIP"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji del tipo de recompensa."""
        emojis = {
            RewardType.BESITOS: "💰",
            RewardType.CONTENT: "🎁",
            RewardType.BADGE: "🏆",
            RewardType.VIP_EXTENSION: "⭐"
        }
        return emojis[self]


class RewardConditionType(str, Enum):
    """
    Tipos de condiciones para desbloquear recompensas.

    Condiciones:
        STREAK_LENGTH: Racha actual >= valor
        TOTAL_POINTS: total_earned >= valor
        LEVEL_REACHED: nivel >= valor
        BESITOS_SPENT: total_spent >= valor
        FIRST_PURCHASE: Ha hecho al menos una compra en tienda
        FIRST_DAILY_GIFT: Ha reclamado regalo diario al menos una vez
        FIRST_REACTION: Ha reaccionado al contenido al menos una vez
        NOT_VIP: Usuario no es VIP (condición de exclusión)
        NOT_CLAIMED_BEFORE: No ha reclamado esta recompensa antes
    """

    STREAK_LENGTH = "STREAK_LENGTH"
    TOTAL_POINTS = "TOTAL_POINTS"
    LEVEL_REACHED = "LEVEL_REACHED"
    BESITOS_SPENT = "BESITOS_SPENT"
    FIRST_PURCHASE = "FIRST_PURCHASE"
    FIRST_DAILY_GIFT = "FIRST_DAILY_GIFT"
    FIRST_REACTION = "FIRST_REACTION"
    NOT_VIP = "NOT_VIP"
    NOT_CLAIMED_BEFORE = "NOT_CLAIMED_BEFORE"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del tipo de condición."""
        names = {
            RewardConditionType.STREAK_LENGTH: "Racha de días",
            RewardConditionType.TOTAL_POINTS: "Puntos totales",
            RewardConditionType.LEVEL_REACHED: "Nivel alcanzado",
            RewardConditionType.BESITOS_SPENT: "Besitos gastados",
            RewardConditionType.FIRST_PURCHASE: "Primera compra",
            RewardConditionType.FIRST_DAILY_GIFT: "Primer regalo diario",
            RewardConditionType.FIRST_REACTION: "Primera reacción",
            RewardConditionType.NOT_VIP: "No VIP",
            RewardConditionType.NOT_CLAIMED_BEFORE: "No reclamado antes"
        }
        return names[self]

    @property
    def requires_value(self) -> bool:
        """Retorna True si la condición requiere un valor numérico."""
        return self in {
            RewardConditionType.STREAK_LENGTH,
            RewardConditionType.TOTAL_POINTS,
            RewardConditionType.LEVEL_REACHED,
            RewardConditionType.BESITOS_SPENT
        }

    @property
    def is_event_based(self) -> bool:
        """Retorna True si la condición está basada en eventos (presencia)."""
        return self in {
            RewardConditionType.FIRST_PURCHASE,
            RewardConditionType.FIRST_DAILY_GIFT,
            RewardConditionType.FIRST_REACTION
        }

    @property
    def is_exclusion(self) -> bool:
        """Retorna True si es una condición de exclusión."""
        return self in {
            RewardConditionType.NOT_VIP,
            RewardConditionType.NOT_CLAIMED_BEFORE
        }


class RewardStatus(str, Enum):
    """
    Estados de una recompensa para un usuario.

    Estados:
        LOCKED: Condiciones no cumplidas
        UNLOCKED: Condiciones cumplidas, disponible para reclamar
        CLAIMED: Ya reclamada
        EXPIRED: Ventana de reclamo expirada
    """

    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    CLAIMED = "CLAIMED"
    EXPIRED = "EXPIRED"

    def __str__(self) -> str:
        """Retorna valor string del enum."""
        return self.value

    @property
    def display_name(self) -> str:
        """Retorna nombre legible del estado."""
        names = {
            RewardStatus.LOCKED: "Bloqueada",
            RewardStatus.UNLOCKED: "Desbloqueada",
            RewardStatus.CLAIMED: "Reclamada",
            RewardStatus.EXPIRED: "Expirada"
        }
        return names[self]

    @property
    def emoji(self) -> str:
        """Retorna emoji del estado."""
        emojis = {
            RewardStatus.LOCKED: "🔒",
            RewardStatus.UNLOCKED: "🔓",
            RewardStatus.CLAIMED: "✅",
            RewardStatus.EXPIRED: "⏰"
        }
        return emojis[self]
