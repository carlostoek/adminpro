"""
Modelos de base de datos para el bot VIP/Free.

Tablas:
- bot_config: Configuración global del bot (singleton)
- users: Usuarios del sistema con roles (FREE/VIP/ADMIN)
- vip_subscribers: Suscriptores del canal VIP
- invitation_tokens: Tokens de invitación generados
- free_channel_requests: Solicitudes de acceso al canal Free
- subscription_plans: Planes de suscripción/tarifas configurables
- content_packages: Paquetes de contenido (FREE/VIP/PREMIUM)
- user_interests: Intereses de usuario en paquetes de contenido
- user_role_change_log: Auditoría de cambios de rol
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    BigInteger, JSON, ForeignKey, Index, Float, Enum, Numeric, desc
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from bot.database.base import Base
from bot.database.enums import UserRole, ContentCategory, RoleChangeReason, PackageType, TransactionType, StreakType, ContentType, ContentTier, RewardType, RewardConditionType, RewardStatus

logger = logging.getLogger(__name__)


class BotConfig(Base):
    """
    Configuración global del bot (tabla singleton - solo 1 registro).

    Almacena:
    - IDs de canales VIP y Free
    - Configuración de tiempo de espera
    - Configuración de reacciones
    - Tarifas de suscripción
    """
    __tablename__ = "bot_config"

    id = Column(Integer, primary_key=True, default=1)

    # Canales
    vip_channel_id = Column(String(50), nullable=True)  # ID del canal VIP
    free_channel_id = Column(String(50), nullable=True)  # ID del canal Free

    # Configuración
    wait_time_minutes = Column(Integer, default=5)  # Tiempo espera Free

    # Reacciones (JSON arrays de emojis)
    vip_reactions = Column(JSON, default=list)   # ["👍", "❤️", "🔥"]
    free_reactions = Column(JSON, default=list)  # ["👍", "👎"]

    # Tarifas (JSON object)
    subscription_fees = Column(
        JSON,
        default=lambda: {"monthly": 10, "yearly": 100}
    )

    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Social Media Links (Phase 10)
    social_instagram = Column(String(200), nullable=True)  # Instagram handle or URL
    social_tiktok = Column(String(200), nullable=True)     # TikTok handle or URL
    social_x = Column(String(200), nullable=True)          # X/Twitter handle or URL
    free_channel_invite_link = Column(String(500), nullable=True)  # Stored invite link for Free channel

    # Economy Configuration (Phase 19 - Wave 3)
    level_formula = Column(String(255), default="floor(sqrt(total_earned / 100)) + 1")
    besitos_per_reaction = Column(Integer, default=5)
    besitos_daily_gift = Column(Integer, default=50)
    besitos_daily_streak_bonus = Column(Integer, default=10)
    max_reactions_per_day = Column(Integer, default=20)

    # Streak Configuration (Phase 21)
    besitos_daily_base = Column(Integer, default=20)  # Base besitos for daily claim
    besitos_streak_bonus_per_day = Column(Integer, default=2)  # Bonus per streak day
    besitos_streak_bonus_max = Column(Integer, default=50)  # Maximum streak bonus
    streak_display_format = Column(String(50), default="🔥 {days} days")  # Display format

    def __repr__(self):
        return (
            f"<BotConfig(vip={self.vip_channel_id}, "
            f"free={self.free_channel_id}, wait={self.wait_time_minutes}min)>"
        )


class User(Base):
    """
    Modelo de usuario del sistema.

    Representa un usuario que ha interactuado con el bot.
    Almacena información básica y su rol actual.

    Attributes:
        user_id: ID único de Telegram (Primary Key)
        username: Username de Telegram (puede ser None)
        first_name: Nombre del usuario
        last_name: Apellido (puede ser None)
        role: Rol actual del usuario (FREE/VIP/ADMIN)
        created_at: Fecha de primer contacto con el bot
        updated_at: Última actualización de datos

    Relaciones:
        vip_subscription: Suscripción VIP si existe
        free_requests: Solicitudes al canal Free
    """

    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.FREE
    )
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relaciones (se definen después en VIPSubscriber y FreeChannelRequest)
    # interests relationship added in UserInterest model (back_populates)
    interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        """Retorna nombre completo del usuario."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    @property
    def mention(self) -> str:
        """Retorna mention HTML del usuario."""
        return f'<a href="tg://user?id={self.user_id}">{self.full_name}</a>'

    @property
    def is_admin(self) -> bool:
        """Verifica si el usuario es admin."""
        return self.role == UserRole.ADMIN

    @property
    def is_vip(self) -> bool:
        """Verifica si el usuario es VIP."""
        return self.role == UserRole.VIP

    @property
    def is_free(self) -> bool:
        """Verifica si el usuario es Free."""
        return self.role == UserRole.FREE

    def __repr__(self) -> str:
        return (
            f"<User(user_id={self.user_id}, username='{self.username}', "
            f"role={self.role.value})>"
        )


class SubscriptionPlan(Base):
    """
    Modelo de planes de suscripción/tarifas.

    Representa un plan que el admin configura con nombre, duración y precio.
    Los tokens VIP se generan vinculados a un plan específico.

    Attributes:
        id: ID único del plan
        name: Nombre del plan (ej: "Plan Mensual", "Plan Anual")
        duration_days: Duración en días del plan
        price: Precio del plan (en USD u otra moneda)
        currency: Símbolo de moneda (default: "$")
        active: Si el plan está activo (visible para generar tokens)
        created_at: Fecha de creación
        created_by: User ID del admin que creó el plan

    Relaciones:
        tokens: Tokens generados con este plan
    """
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)  # Numeric evita pérdida de precisión (Float es inseguro para dinero)
    currency = Column(String(10), nullable=False, default="$")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    created_by = Column(BigInteger, nullable=False)

    # Relación con tokens
    tokens = relationship(
        "InvitationToken",
        back_populates="plan",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<SubscriptionPlan(id={self.id}, name='{self.name}', "
            f"days={self.duration_days}, price={self.price})>"
        )


class InvitationToken(Base):
    """
    Tokens de invitación generados por administradores.

    Cada token:
    - Es único (16 caracteres alfanuméricos)
    - Tiene duración limitada (expira después de X horas)
    - Se marca como "usado" al ser canjeado
    - Registra quién lo generó y quién lo usó
    - Puede estar asociado a un plan de suscripción
    """
    __tablename__ = "invitation_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Token único
    token = Column(String(16), unique=True, nullable=False, index=True)

    # Generación
    generated_by = Column(BigInteger, nullable=False)  # User ID del admin
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    duration_hours = Column(Integer, default=24, nullable=False)  # Duración en horas

    # Uso
    used = Column(Boolean, default=False, nullable=False, index=True)
    used_by = Column(BigInteger, nullable=True)  # User ID que canjeó
    used_at = Column(DateTime, nullable=True)

    # Plan asociado (nullable para compatibilidad con tokens antiguos)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    plan = relationship("SubscriptionPlan", back_populates="tokens")

    # Relación: 1 Token → Many Subscribers
    subscribers = relationship(
        "VIPSubscriber",
        back_populates="token",
        cascade="all, delete-orphan"
    )

    # Índice compuesto para queries de tokens no usados
    __table_args__ = (
        Index('idx_token_used_created', 'used', 'created_at'),
    )

    def is_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        from datetime import timedelta
        expiry_time = self.created_at + timedelta(hours=self.duration_hours)
        return datetime.now(timezone.utc).replace(tzinfo=None) > expiry_time

    def is_valid(self) -> bool:
        """Verifica si el token es válido (no usado y no expirado)"""
        return not self.used and not self.is_expired()

    def __repr__(self):
        status = "USADO" if self.used else ("EXPIRADO" if self.is_expired() else "VÁLIDO")
        return f"<Token({self.token[:8]}... - {status})>"


class VIPSubscriber(Base):
    """
    Suscriptores del canal VIP.

    Cada suscriptor:
    - Canjeó un token de invitación
    - Tiene fecha de expiración
    - Puede estar activo o expirado
    - Progresa por ritual de entrada en 3 etapas (Phase 13)

    Etapa de entrada (vip_entry_stage):
    - 1: Confirmación de activación
    - 2: Alineación de expectativas
    - 3: Entrega de enlace de acceso
    - NULL: Ritual completado (acceso concedido)

    Campos de ritual:
    - vip_entry_stage: Etapa actual (1-3) o NULL (completado)
    - vip_entry_token: Token único para enlace de etapa 3
    - invite_link_sent_at: Timestamp de generación de enlace
    """
    __tablename__ = "vip_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Usuario
    user_id = Column(BigInteger, ForeignKey("users.user_id"), unique=True, nullable=False, index=True)  # ID Telegram

    # Suscripción
    join_date = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    expiry_date = Column(DateTime, nullable=False)  # Fecha de expiración
    status = Column(
        String(20),
        default="active",
        nullable=False,
        index=True
    )  # "active" o "expired"

    # VIP Entry Ritual Fields (Phase 13)
    vip_entry_stage = Column(Integer, nullable=True, default=1, index=True)  # 1, 2, 3, or NULL (complete)
    vip_entry_token = Column(String(64), unique=True, nullable=True)  # One-time token for Stage 3 link
    invite_link_sent_at = Column(DateTime, nullable=True)  # When Stage 3 link was generated

    # Token usado
    token_id = Column(Integer, ForeignKey("invitation_tokens.id"), nullable=False)
    token = relationship("InvitationToken", back_populates="subscribers")

    # Usuario (relación inversa)
    user = relationship("User", uselist=False, lazy="selectin")

    # Índice compuesto para buscar activos próximos a expirar
    __table_args__ = (
        Index('idx_status_expiry', 'status', 'expiry_date'),
        Index('idx_vip_entry_stage', 'vip_entry_stage'),  # Phase 13: Stage lookup optimization
    )

    def is_expired(self) -> bool:
        """Verifica si la suscripción ha expirado"""
        return datetime.now(timezone.utc).replace(tzinfo=None) > self.expiry_date

    def days_remaining(self) -> int:
        """Retorna días restantes de suscripción (negativo si expirado)"""
        delta = self.expiry_date - datetime.now(timezone.utc).replace(tzinfo=None)
        return delta.days

    def __repr__(self):
        days = self.days_remaining()
        return f"<VIPSubscriber(user={self.user_id}, status={self.status}, days={days})>"


class FreeChannelRequest(Base):
    """
    Solicitudes de acceso al canal Free (cola de espera).

    Cada solicitud:
    - Se crea cuando un usuario solicita acceso
    - Se procesa después de N minutos de espera
    - Se marca como "procesada" al enviar invitación
    """
    __tablename__ = "free_channel_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Usuario
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)  # ID Telegram
    user = relationship("User", uselist=False, lazy="selectin")

    # Solicitud
    request_date = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Índice compuesto para queries de pendientes por fecha
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'request_date'),
        Index('idx_processed_date', 'processed', 'request_date'),
    )

    def minutes_since_request(self) -> int:
        """Retorna minutos transcurridos desde la solicitud"""
        delta = datetime.now(timezone.utc).replace(tzinfo=None) - self.request_date
        return int(delta.total_seconds() / 60)

    def is_ready(self, wait_time_minutes: int) -> bool:
        """Verifica si la solicitud cumplió el tiempo de espera"""
        return self.minutes_since_request() >= wait_time_minutes

    def __repr__(self):
        status = "PROCESADA" if self.processed else f"PENDIENTE ({self.minutes_since_request()}min)"
        return f"<FreeRequest(user={self.user_id}, {status})>"


class UserInterest(Base):
    """
    Registro de interés de usuario en un paquete de contenido.

    Registra cuando un usuario marca "Me interesa" en un paquete.
    Implementa deduplicación: si el usuario ya marcó interés, se actualiza created_at.

    Attributes:
        id: ID único del registro (Primary Key)
        user_id: ID del usuario (Foreign Key to users)
        package_id: ID del paquete (Foreign Key to content_packages)
        is_attended: Si el admin ya atendió este interés
        attended_at: Fecha en que el admin marcó como atendido
        created_at: Fecha de creación (actualizado en re-clicks)

    Relaciones:
        user: Usuario que marcó interés
        package: Paquete de interés
    """

    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Keys (with foreign keys)
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    package_id = Column(
        Integer,
        ForeignKey("content_packages.id", ondelete="CASCADE"),
        nullable=True,  # NULL = interés en suscripción VIP (no asociado a paquete)
        index=True
    )

    # State
    is_attended = Column(Boolean, nullable=False, default=False, index=True)
    attended_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    user = relationship("User", back_populates="interests")
    package = relationship("ContentPackage", back_populates="interests")

    def __repr__(self):
        return (
            f"<UserInterest(id={self.id}, user_id={self.user_id}, "
            f"package_id={self.package_id}, is_attended={self.is_attended})>"
        )

    # Unique constraint for deduplication + composite index for queries
    __table_args__ = (
        # Unique constraint: one interest per user-package pair
        Index('idx_interest_user_package', 'user_id', 'package_id', unique=True),
        # Composite index for "attended interests by user" queries
        Index('idx_interest_user_package_attended', 'user_id', 'package_id', 'is_attended'),
    )


class UserRoleChangeLog(Base):
    """
    Registro de auditoría para cambios de rol de usuario.

    Registra todos los cambios de rol con razón y metadata.
    Permite auditar quién hizo qué cambio y por qué.

    Attributes:
        id: ID único del registro (Primary Key)
        user_id: ID del usuario que cambió de rol
        previous_role: Rol anterior del usuario (None para nuevos usuarios)
        new_role: Nuevo rol del usuario
        changed_by: ID del admin que hizo el cambio (or SYSTEM for automatic)
        reason: Razón del cambio (RoleChangeReason enum)
        change_source: Origen del cambio (ADMIN_PANEL, SYSTEM, API)
        metadata: Información adicional JSON (opcional)
        changed_at: Fecha y hora del cambio
    """

    __tablename__ = "user_role_change_log"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User
    user_id = Column(BigInteger, nullable=False, index=True)

    # Role change
    previous_role = Column(Enum(UserRole), nullable=True)  # None for new users
    new_role = Column(Enum(UserRole), nullable=False)

    # Metadata
    changed_by = Column(BigInteger, nullable=False, index=True)  # Admin ID or 0 for SYSTEM
    reason = Column(Enum(RoleChangeReason), nullable=False)
    change_source = Column(String(50), nullable=False)  # 'ADMIN_PANEL', 'SYSTEM', 'API'
    change_metadata = Column(JSON, nullable=True)  # Optional: {"duration_hours": 24, "token": "ABC..."}

    # Timestamp
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)

    def __repr__(self):
        return (
            f"<UserRoleChangeLog(id={self.id}, user_id={self.user_id}, "
            f"previous_role={self.previous_role if self.previous_role else None}, "
            f"new_role={self.new_role}, reason={self.reason})>"
        )

    # Indexes for audit trail queries
    __table_args__ = (
        # Composite index for "user's role history" queries (most recent first)
        Index('idx_role_log_user_changed_at', 'user_id', 'changed_at'),
        # Composite index for "changes made by admin" queries
        Index('idx_role_log_changed_by_changed_at', 'changed_by', 'changed_at'),
    )


class ContentPackage(Base):
    """
    Paquete de contenido para el sistema.

    Representa un paquete de contenido que puede ser:
    - Gratuito (acceso para todos)
    - VIP (requiere suscripción activa)
    - Premium (contenido exclusivo de alto valor)

    Attributes:
        id: ID único del paquete (Primary Key)
        name: Nombre del paquete (ej: "Pack Fotos Enero")
        description: Descripción detallada del contenido
        price: Precio en moneda base (Decimal para precisión)
        is_active: Estado activo/inactivo (soft delete)
        category: Categoría (FREE_CONTENT, VIP_CONTENT, VIP_PREMIUM)
        type: Tipo de paquete (STANDARD, BUNDLE, COLLECTION)
        media_url: URL del contenido (opcional)
        created_at: Fecha de creación
        updated_at: Última actualización (auto onupdate)

    Relaciones:
        interests: Lista de usuarios interesados en este paquete
    """

    __tablename__ = "content_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)

    # Price (Numeric for currency precision - NOT Float)
    price = Column(Numeric(10, 2), nullable=True)

    # Classification
    category = Column(
        Enum(ContentCategory),
        nullable=False,
        default=ContentCategory.FREE_CONTENT
    )
    type = Column(
        Enum(PackageType),
        nullable=False,
        default=PackageType.STANDARD
    )

    # Media
    media_url = Column(String(500), nullable=True)

    # State
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    interests = relationship(
        "UserInterest",
        back_populates="package",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<ContentPackage(id={self.id}, name='{self.name}', "
            f"category={self.category}, is_active={self.is_active})>"
        )

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_content_category_active', 'category', 'is_active'),
        Index('idx_content_type_active', 'type', 'is_active'),
    )


class UserGamificationProfile(Base):
    """
    Perfil de gamificación de usuario (sistema de economía).

    Almacena el balance de besitos, estadísticas lifetime y nivel
    del usuario en el sistema de gamificación.

    Attributes:
        id: ID único del perfil (Primary Key)
        user_id: ID del usuario (Foreign Key, único)
        balance: Besitos disponibles actualmente
        total_earned: Total de besitos ganados (lifetime)
        total_spent: Total de besitos gastados (lifetime)
        level: Nivel actual (cached, recalculable)
        created_at: Fecha de creación del perfil
        updated_at: Última actualización

    Relaciones:
        user: Usuario asociado (1:1)

    Notas:
        - El balance puede calcularse como: total_earned - total_spent
        - El nivel se cachea para queries rápidas de leaderboard
        - Se crea automáticamente al registrar un nuevo usuario
    """

    __tablename__ = "user_gamification_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User relationship (1:1)
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    user = relationship("User", uselist=False, lazy="selectin")

    # Economy fields
    balance = Column(Integer, nullable=False, default=0)
    total_earned = Column(Integer, nullable=False, default=0)
    total_spent = Column(Integer, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=1, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Index for leaderboard queries (ordered by level)
        Index('idx_gamification_level_balance', 'level', 'balance'),
    )

    def calculate_level(self, formula: str = "linear") -> int:
        """
        Calcula el nivel basado en total_earned.

        Args:
            formula: Fórmula de progresión ("linear" o "exponential")

        Returns:
            Nivel calculado (mínimo 1)

        Fórmulas:
            linear: level = 1 + (total_earned // 100)
            exponential: level = 1 + floor(sqrt(total_earned / 50))
        """
        if formula == "linear":
            # Cada 100 besitos = 1 nivel
            return max(1, 1 + (self.total_earned // 100))
        elif formula == "exponential":
            # Progresión más lenta al inicio, más rápida después
            import math
            return max(1, 1 + int(math.sqrt(self.total_earned / 50)))
        else:
            # Default: linear
            return max(1, 1 + (self.total_earned // 100))

    def update_level(self, formula: str = "linear") -> int:
        """
        Actualiza el nivel cacheado y retorna el nuevo valor.

        Args:
            formula: Fórmula de progresión

        Returns:
            Nuevo nivel calculado
        """
        self.level = self.calculate_level(formula)
        return self.level

    @property
    def next_level_threshold(self) -> int:
        """
        Retorna besitos necesarios para el siguiente nivel.

        Returns:
            Cantidad de besitos necesarios para subir de nivel
        """
        return (self.level * 100) - self.total_earned

    def __repr__(self) -> str:
        return (
            f"<UserGamificationProfile(user_id={self.user_id}, "
            f"balance={self.balance}, level={self.level})>"
        )


class Transaction(Base):
    """
    Registro de transacciones del sistema de economía.

    Audit trail completo de todos los movimientos de besitos.
    Cada cambio de balance genera una transacción registrada.

    Attributes:
        id: ID único de la transacción (Primary Key)
        user_id: ID del usuario afectado
        amount: Cantidad de besitos (positivo = ganancia, negativo = gasto)
        type: Tipo de transacción (TransactionType enum)
        reason: Descripción legible de la transacción
        metadata: Datos adicionales en JSON (admin_id, shop_item_id, etc.)
        created_at: Fecha y hora de la transacción

    Notas:
        - amount > 0: Usuario recibió besitos (EARN_*)
        - amount < 0: Usuario gastó besitos (SPEND_*)
        - metadata permite trazabilidad completa
        - Las transacciones NUNCA se borran (append-only)
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User affected
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Transaction details
    amount = Column(Integer, nullable=False)  # Positive = earn, negative = spend
    type = Column(
        Enum(TransactionType),
        nullable=False,
        index=True
    )
    reason = Column(String(255), nullable=False)  # Human readable description
    transaction_metadata = Column(JSON, nullable=True)  # Extra data: {"admin_id": 123, "shop_item_id": 456}

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)

    # Indexes for efficient queries
    __table_args__ = (
        # Composite index for user transaction history (most recent first)
        Index('idx_transaction_user_created', 'user_id', 'created_at'),
        # Composite index for analytics by type
        Index('idx_transaction_type_created', 'type', 'created_at'),
        # Composite index for filtering by user and type
        Index('idx_transaction_user_type', 'user_id', 'type'),
    )

    @property
    def is_earn(self) -> bool:
        """Retorna True si es una transacción de ganancia."""
        return self.amount > 0

    @property
    def is_spend(self) -> bool:
        """Retorna True si es una transacción de gasto."""
        return self.amount < 0

    @property
    def formatted_amount(self) -> str:
        """Retorna la cantidad formateada con signo."""
        if self.amount > 0:
            return f"+{self.amount}"
        return str(self.amount)

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, type={self.type.value})>"
        )


class UserReaction(Base):
    """
    Registro de reacciones de usuario a contenido de canales.

    Cada reacción:
    - Se vincula a un usuario y un mensaje de canal específico
    - Usa un emoji específico (solo UNA reacción por usuario/contenido)
    - Registra timestamp para rate limiting y análisis

    Attributes:
        id: ID único de la reacción
        user_id: ID del usuario que reaccionó
        content_id: ID del mensaje de canal al que se reaccionó
        emoji: Emoji usado para la reacción (ej: "❤️", "🔥")
        channel_id: ID del canal donde está el contenido
        created_at: Timestamp de la reacción

    Constraints:
        - Un usuario solo puede reaccionar UNA VEZ a cada contenido (con cualquier emoji)
        - Rate limiting: 30 segundos entre reacciones del mismo usuario
        - Límite diario: configurable (default 20 reacciones/día)
    """

    __tablename__ = "user_reactions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User who reacted
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Content being reacted to (Telegram message ID in channel)
    content_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(String(50), nullable=False, index=True)

    # Reaction details
    emoji = Column(String(10), nullable=False)  # Emoji used

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)

    # Indexes for efficient queries
    __table_args__ = (
        # Unique constraint: one reaction per user/content combination
        # This ensures a user can only react once to each content (with any emoji)
        Index('idx_user_content', 'user_id', 'content_id', unique=True),
        # Index for "user's recent reactions" queries (rate limiting)
        Index('idx_user_reactions_recent', 'user_id', 'created_at'),
        # Index for "reactions to content" queries
        Index('idx_content_reactions', 'channel_id', 'content_id', 'emoji'),
    )

    def __repr__(self) -> str:
        return (
            f"<UserReaction(id={self.id}, user_id={self.user_id}, "
            f"content_id={self.content_id}, emoji={self.emoji})>"
        )


class UserStreak(Base):
    """
    Modelo de rachas de usuario para el sistema de gamificación.

    Almacena el estado de rachas de usuarios para:
    - Regalo diario: Días consecutivos reclamando el regalo diario
    - Reacciones: Días consecutivos con al menos una reacción

    Attributes:
        id: ID único de la racha (Primary Key)
        user_id: ID del usuario (Foreign Key a users.user_id)
        streak_type: Tipo de racha (DAILY_GIFT o REACTION)
        current_streak: Días consecutivos actuales
        longest_streak: Récord máximo de días consecutivos
        last_claim_date: Fecha UTC del último reclamo (para DAILY_GIFT)
        last_reaction_date: Fecha UTC de la última reacción (para REACTION)
        created_at: Fecha de creación del registro
        updated_at: Última actualización

    Constraints:
        - Un usuario solo puede tener una racha de cada tipo
        - Índice compuesto para leaderboards por tipo de racha
    """

    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User relationship
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Streak type
    streak_type = Column(
        Enum(StreakType),
        nullable=False,
        index=True
    )

    # Streak counters
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)

    # Last activity dates
    last_claim_date = Column(DateTime, nullable=True)  # For DAILY_GIFT
    last_reaction_date = Column(DateTime, nullable=True)  # For REACTION

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Unique constraint: one streak per user per type
        Index('idx_user_streak_type', 'user_id', 'streak_type', unique=True),
        # Composite index for leaderboards (ordered by current streak)
        Index('idx_streak_type_current', 'streak_type', 'current_streak'),
    )

    def __repr__(self) -> str:
        return (
            f"<UserStreak(user_id={self.user_id}, type={self.streak_type.value}, "
            f"current={self.current_streak}, longest={self.longest_streak})>"
        )


class ContentSet(Base):
    """
    Conjunto de contenido para el sistema de tienda.

    Almacena múltiples archivos (file_ids de Telegram) como un conjunto
    que puede ser vendido o regalado a través del sistema de tienda.

    Attributes:
        id: ID único del conjunto (Primary Key)
        name: Nombre del conjunto (ej: "Pack Especial Febrero")
        description: Descripción detallada del contenido
        file_ids: Array de file_ids de Telegram para entrega
        content_type: Tipo de contenido (photo_set, video, audio, mixed)
        tier: Nivel de acceso (free, vip, premium, gift)
        category: Categoría opcional (teaser, welcome, milestone, gift)
        is_active: Si el conjunto está disponible
        created_at: Fecha de creación
        updated_at: Última actualización

    Relaciones:
        shop_products: Productos de tienda que venden este contenido
        user_accesses: Registros de acceso de usuarios a este contenido
    """

    __tablename__ = "content_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)

    # Content storage (Telegram file_ids)
    file_ids = Column(JSON, nullable=False, default=list)

    # Classification
    content_type = Column(
        Enum(ContentType),
        nullable=False,
        default=ContentType.PHOTO_SET
    )
    tier = Column(
        Enum(ContentTier),
        nullable=False,
        default=ContentTier.FREE
    )
    category = Column(String(50), nullable=True)  # teaser, welcome, milestone, gift

    # State
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    shop_products = relationship(
        "ShopProduct",
        back_populates="content_set",
        cascade="all, delete-orphan"
    )
    user_accesses = relationship(
        "UserContentAccess",
        back_populates="content_set",
        cascade="all, delete-orphan"
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Composite index for filtering by tier and active status
        Index('idx_content_set_tier_active', 'tier', 'is_active'),
        # Composite index for filtering by type and active status
        Index('idx_content_set_type_active', 'content_type', 'is_active'),
    )

    @property
    def file_count(self) -> int:
        """Retorna cantidad de archivos en el conjunto."""
        return len(self.file_ids)

    def __repr__(self) -> str:
        return (
            f"<ContentSet(id={self.id}, name='{self.name}', "
            f"tier={self.tier}, files={self.file_count})>"
        )


class ShopProduct(Base):
    """
    Producto de la tienda del sistema.

    Representa un item vendible en la tienda que está vinculado
    a un ContentSet. Incluye precios para usuarios FREE y VIP
    (con sistema de descuentos).

    Attributes:
        id: ID único del producto (Primary Key)
        name: Nombre del producto en la tienda
        description: Descripción de marketing
        content_set_id: ID del ContentSet asociado
        besitos_price: Precio en besitos para usuarios FREE
        vip_discount_percentage: Porcentaje de descuento VIP (0-100)
        vip_besitos_price: Precio VIP manual (opcional, auto-calculado si null)
        tier: Quién puede comprar este producto
        is_active: Si está disponible para compra
        sort_order: Orden en el catálogo
        purchase_count: Contador de compras (analytics)
        created_at: Fecha de creación
        updated_at: Última actualización

    Relaciones:
        content_set: ContentSet vinculado
        purchase_records: Registros de compra de usuarios
    """

    __tablename__ = "shop_products"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)

    # Content relationship
    content_set_id = Column(
        Integer,
        ForeignKey("content_sets.id"),
        nullable=False
    )

    # Pricing
    besitos_price = Column(Integer, nullable=False)
    vip_discount_percentage = Column(Integer, nullable=False, default=0)
    vip_besitos_price = Column(Integer, nullable=True)

    # Access control
    tier = Column(
        Enum(ContentTier),
        nullable=False,
        default=ContentTier.FREE
    )

    # State and ordering
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Analytics
    purchase_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    content_set = relationship(
        "ContentSet",
        back_populates="shop_products",
        lazy="selectin"
    )
    purchase_records = relationship(
        "UserContentAccess",
        back_populates="shop_product",
        cascade="all, delete-orphan"
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Composite index for active products by tier
        Index('idx_shop_product_active_tier', 'is_active', 'tier'),
        # Index for price sorting
        Index('idx_shop_product_price', 'besitos_price'),
        # Index for catalog ordering
        Index('idx_shop_product_sort', 'sort_order'),
    )

    @property
    def vip_price(self) -> int:
        """
        Retorna precio VIP calculado.

        Si vip_besitos_price está seteado, lo retorna.
        Si no, calcula besitos_price * (100 - vip_discount_percentage) // 100.
        """
        if self.vip_besitos_price is not None:
            return self.vip_besitos_price
        discount = self.besitos_price * self.vip_discount_percentage // 100
        return self.besitos_price - discount

    @property
    def has_vip_discount(self) -> bool:
        """Retorna True si tiene descuento VIP."""
        return self.vip_discount_percentage > 0

    def __repr__(self) -> str:
        return (
            f"<ShopProduct(id={self.id}, name='{self.name}', "
            f"price={self.besitos_price}, vip_price={self.vip_price})>"
        )


class UserContentAccess(Base):
    """
    Registro de acceso de usuario a contenido.

    Este modelo rastrea qué contenido ha recibido cada usuario
    y cómo lo obtuvo (compra, regalo, recompensa, narrativa).

    Attributes:
        id: ID único del registro (Primary Key)
        user_id: ID del usuario (Foreign Key a users)
        content_set_id: ID del ContentSet (Foreign Key)
        shop_product_id: ID del ShopProduct (null si fue regalo/recompensa)
        access_type: Tipo de acceso (shop_purchase, reward_claim, gift, narrative)
        besitos_paid: Cantidad pagada (null para regalos gratuitos)
        is_active: Si puede re-descargar el contenido
        accessed_at: Fecha de primera recepción
        expires_at: Fecha de expiración (opcional)
        access_metadata: Datos adicionales JSON

    Relaciones:
        user: Usuario que tiene acceso
        content_set: ContentSet al que tiene acceso
        shop_product: Producto de tienda (si aplica)

    Constraints:
        - Un usuario solo puede tener un registro por ContentSet
    """

    __tablename__ = "user_content_access"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User relationship
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Content relationship
    content_set_id = Column(
        Integer,
        ForeignKey("content_sets.id"),
        nullable=False,
        index=True
    )

    # Shop product (null if received via reward/gift)
    shop_product_id = Column(
        Integer,
        ForeignKey("shop_products.id"),
        nullable=True,
        index=True  # Índice para queries frecuentes por producto
    )

    # Access details
    # NOTA: access_type debería tener CHECK constraint. Valores permitidos:
    # 'shop_purchase', 'reward_claim', 'gift', 'narrative'
    # Pendiente migración para agregar constraint formal.
    access_type = Column(String(50), nullable=False)
    besitos_paid = Column(Integer, nullable=True)  # null for free rewards

    # State
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    accessed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at = Column(DateTime, nullable=True)

    # Metadata for extensibility
    access_metadata = Column(JSON, nullable=True)  # reward_id, gift_from_user_id, etc.

    # Relationships
    user = relationship("User", uselist=False, lazy="selectin")
    content_set = relationship(
        "ContentSet",
        back_populates="user_accesses",
        lazy="selectin"
    )
    shop_product = relationship(
        "ShopProduct",
        back_populates="purchase_records",
        lazy="selectin"
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Unique constraint: one access record per user/content combination
        Index('idx_user_content_access_user_content', 'user_id', 'content_set_id', unique=True),
        # Composite index for user access type queries
        Index('idx_user_content_access_type', 'user_id', 'access_type'),
        # Composite index for user access date queries
        Index('idx_user_content_access_date', 'user_id', 'accessed_at'),
    )

    @property
    def is_purchased(self) -> bool:
        """Retorna True si fue comprado en la tienda."""
        return self.access_type == "shop_purchase"

    @property
    def is_reward(self) -> bool:
        """Retorna True si fue obtenido como recompensa."""
        return self.access_type == "reward_claim"

    @property
    def is_expired(self) -> bool:
        """Retorna True si el acceso ha expirado."""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.now(timezone.utc).replace(tzinfo=None)

    def __repr__(self) -> str:
        return (
            f"<UserContentAccess(id={self.id}, user={self.user_id}, "
            f"content={self.content_set_id}, type={self.access_type})>"
        )


class Reward(Base):
    """
    Recompensa del sistema de logros.

    Representa una recompensa que los usuarios pueden desbloquear
    cumpliendo ciertas condiciones. Puede ser de diferentes tipos:
    besitos, contenido, insignia o extensión VIP.

    Attributes:
        id: ID único de la recompensa (Primary Key)
        name: Nombre de la recompensa
        description: Descripción detallada
        reward_type: Tipo de recompensa (RewardType enum)
        reward_value: Datos JSON específicos del tipo de recompensa
        is_repeatable: Si se puede reclamar múltiples veces
        is_secret: Si está oculta hasta desbloquearse
        claim_window_hours: Horas disponibles para reclamar tras desbloqueo
        is_active: Si está disponible en el sistema
        sort_order: Orden de visualización
        created_at: Fecha de creación
        updated_at: Última actualización

    Relaciones:
        conditions: Lista de condiciones para desbloquear (RewardCondition)
        user_rewards: Registros de usuarios con esta recompensa (UserReward)

    Ejemplos de reward_value:
        - BESITOS: {"amount": 100}
        - CONTENT: {"content_set_id": 123}
        - BADGE: {"badge_name": "streak_master", "emoji": "🔥"}
        - VIP_EXTENSION: {"days": 7}
    """

    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=True)

    # Reward type and value
    reward_type = Column(
        Enum(RewardType),
        nullable=False
    )
    reward_value = Column(JSON, nullable=False, default=dict)

    # Behavior flags
    is_repeatable = Column(Boolean, nullable=False, default=False)
    is_secret = Column(Boolean, nullable=False, default=False)
    claim_window_hours = Column(Integer, nullable=False, default=168)  # 7 days

    # State and ordering
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    conditions = relationship(
        "RewardCondition",
        back_populates="reward",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    user_rewards = relationship(
        "UserReward",
        back_populates="reward",
        cascade="all, delete-orphan"
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Composite index for active rewards by type
        Index('idx_reward_active_type', 'is_active', 'reward_type'),
        # Index for display ordering
        Index('idx_reward_sort', 'sort_order'),
    )

    def __repr__(self) -> str:
        return (
            f"<Reward(id={self.id}, name='{self.name}', "
            f"type={self.reward_type.value}, active={self.is_active})>"
        )


class RewardCondition(Base):
    """
    Condición para desbloquear una recompensa.

    Cada condición representa un requisito que debe cumplirse
    para que un usuario desbloquee la recompensa asociada.

    Attributes:
        id: ID único de la condición (Primary Key)
        reward_id: ID de la recompensa (Foreign Key)
        condition_type: Tipo de condición (RewardConditionType enum)
        condition_value: Valor numérico para comparación (opcional)
        condition_group: Grupo para lógica OR (0 = AND, >0 = OR)
        sort_order: Orden de evaluación
        created_at: Fecha de creación

    Relaciones:
        reward: Recompensa asociada

    Lógica de grupos:
        - Grupo 0: Todas las condiciones deben cumplirse (AND)
        - Grupo 1, 2, etc.: Al menos una del grupo debe cumplirse (OR)
    """

    __tablename__ = "reward_conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Reward relationship
    reward_id = Column(
        Integer,
        ForeignKey("rewards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Condition details
    condition_type = Column(
        Enum(RewardConditionType),
        nullable=False
    )
    condition_value = Column(Integer, nullable=True)  # Threshold value

    # Logic grouping
    condition_group = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    reward = relationship(
        "Reward",
        back_populates="conditions",
        lazy="selectin"
    )

    # Indexes for efficient queries
    __table_args__ = (
        # Index for reward conditions lookup
        Index('idx_condition_reward', 'reward_id'),
        # Index for condition type queries
        Index('idx_condition_type', 'condition_type'),
    )

    def __repr__(self) -> str:
        return (
            f"<RewardCondition(id={self.id}, reward={self.reward_id}, "
            f"type={self.condition_type.value}, group={self.condition_group})>"
        )


class UserReward(Base):
    """
    Registro de recompensa de usuario.

    Rastrea el progreso y estado de una recompensa específica
    para cada usuario. Incluye fechas de desbloqueo, reclamo
    y conteo para recompensas repetibles.

    Attributes:
        id: ID único del registro (Primary Key)
        user_id: ID del usuario (Foreign Key)
        reward_id: ID de la recompensa (Foreign Key)
        status: Estado actual (RewardStatus enum)
        unlocked_at: Fecha de desbloqueo (cuando se cumplieron condiciones)
        claimed_at: Fecha de reclamo
        expires_at: Fecha de expiración del reclamo
        claim_count: Cantidad de veces reclamada (para repetibles)
        last_claimed_at: Última fecha de reclamo
        created_at: Fecha de creación del registro
        updated_at: Última actualización

    Relaciones:
        reward: Recompensa asociada

    Constraints:
        - Un usuario solo puede tener un registro por recompensa
    """

    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User relationship
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Reward relationship
    reward_id = Column(
        Integer,
        ForeignKey("rewards.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status tracking
    status = Column(
        Enum(RewardStatus),
        nullable=False,
        default=RewardStatus.LOCKED
    )

    # Timestamps
    unlocked_at = Column(DateTime, nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Repeatable tracking
    claim_count = Column(Integer, nullable=False, default=0)
    last_claimed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    reward = relationship(
        "Reward",
        back_populates="user_rewards",
        lazy="selectin"
    )

    # Indexes and constraints
    __table_args__ = (
        # Unique constraint: one record per user-reward pair
        Index('idx_user_reward_user_reward', 'user_id', 'reward_id', unique=True),
        # Composite index for "my rewards" queries
        Index('idx_user_reward_user_status', 'user_id', 'status'),
        # Index for expiration processing
        Index('idx_user_reward_unlocked', 'unlocked_at'),
        # Index for finding expired rewards
        Index('idx_user_reward_expires', 'expires_at'),
    )

    @property
    def is_claimable(self) -> bool:
        """Retorna True si la recompensa puede ser reclamada."""
        if self.status != RewardStatus.UNLOCKED:
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            return False
        return True

    def __repr__(self) -> str:
        return (
            f"<UserReward(id={self.id}, user={self.user_id}, "
            f"reward={self.reward_id}, status={self.status.value})>"
        )
