"""
Modelos de base de datos para el bot VIP/Free.

Tablas:
- bot_config: Configuración global del bot (singleton)
- vip_subscribers: Suscriptores del canal VIP
- invitation_tokens: Tokens de invitación generados
- free_channel_requests: Solicitudes de acceso al canal Free
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    BigInteger, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from bot.database.base import Base

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return (
            f"<BotConfig(vip={self.vip_channel_id}, "
            f"free={self.free_channel_id}, wait={self.wait_time_minutes}min)>"
        )


class InvitationToken(Base):
    """
    Tokens de invitación generados por administradores.

    Cada token:
    - Es único (16 caracteres alfanuméricos)
    - Tiene duración limitada (expira después de X horas)
    - Se marca como "usado" al ser canjeado
    - Registra quién lo generó y quién lo usó
    """
    __tablename__ = "invitation_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Token único
    token = Column(String(16), unique=True, nullable=False, index=True)

    # Generación
    generated_by = Column(BigInteger, nullable=False)  # User ID del admin
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_hours = Column(Integer, default=24, nullable=False)  # Duración en horas

    # Uso
    used = Column(Boolean, default=False, nullable=False, index=True)
    used_by = Column(BigInteger, nullable=True)  # User ID que canjeó
    used_at = Column(DateTime, nullable=True)

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
        return datetime.utcnow() > expiry_time

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
    """
    __tablename__ = "vip_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Usuario
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)  # ID Telegram

    # Suscripción
    join_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = Column(DateTime, nullable=False)  # Fecha de expiración
    status = Column(
        String(20),
        default="active",
        nullable=False,
        index=True
    )  # "active" o "expired"

    # Token usado
    token_id = Column(Integer, ForeignKey("invitation_tokens.id"), nullable=False)
    token = relationship("InvitationToken", back_populates="subscribers")

    # Índice compuesto para buscar activos próximos a expirar
    __table_args__ = (
        Index('idx_status_expiry', 'status', 'expiry_date'),
    )

    def is_expired(self) -> bool:
        """Verifica si la suscripción ha expirado"""
        return datetime.utcnow() > self.expiry_date

    def days_remaining(self) -> int:
        """Retorna días restantes de suscripción (negativo si expirado)"""
        delta = self.expiry_date - datetime.utcnow()
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
    user_id = Column(BigInteger, nullable=False, index=True)  # ID Telegram

    # Solicitud
    request_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False, nullable=False, index=True)
    processed_at = Column(DateTime, nullable=True)

    # Índice compuesto para queries de pendientes por fecha
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'request_date'),
        Index('idx_processed_date', 'processed', 'request_date'),
    )

    def minutes_since_request(self) -> int:
        """Retorna minutos transcurridos desde la solicitud"""
        delta = datetime.utcnow() - self.request_date
        return int(delta.total_seconds() / 60)

    def is_ready(self, wait_time_minutes: int) -> bool:
        """Verifica si la solicitud cumplió el tiempo de espera"""
        return self.minutes_since_request() >= wait_time_minutes

    def __repr__(self):
        status = "PROCESADA" if self.processed else f"PENDIENTE ({self.minutes_since_request()}min)"
        return f"<FreeRequest(user={self.user_id}, {status})>"
