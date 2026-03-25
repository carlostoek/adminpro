"""
Simulation Service - Permite a admins simular comportamiento de otros roles.

Responsabilidades:
- Almacenar contexto de simulación en memoria (aislado por admin)
- Resolver el rol efectivo considerando simulación activa
- Proveer punto único de verdad para role checks (resolve_user_context)

Pattern: Singleton store + Service con lazy loading
Safety: Solo admins pueden simular (verificación via Config.is_admin)
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.enums import SimulationMode, UserRole
from config import Config

if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)


@dataclass
class ResolvedUserContext:
    """
    Contexto resuelto de un usuario considerando simulación.

    Este dataclass es el punto único de verdad para determinar
    el rol y datos efectivos de un usuario.

    Attributes:
        user_id: ID de Telegram del usuario
        real_role: Rol real del usuario según la base de datos
        simulated_role: Rol simulado (si está en modo simulación)
        is_simulating: True si hay una simulación activa
        simulated_balance: Balance simulado (opcional)
        simulated_subscription_status: Estado de suscripción simulado (opcional)
        activated_at: Cuándo se activó la simulación
        expires_at: Cuándo expira la simulación (TTL)
    """

    user_id: int
    real_role: UserRole
    simulated_role: Optional[UserRole] = None
    is_simulating: bool = False
    simulated_balance: Optional[int] = None
    simulated_subscription_status: Optional[str] = None
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def effective_role(self) -> UserRole:
        """
        Retorna el rol efectivo considerando simulación.

        Returns:
            UserRole: Rol simulado si está activo, sino el rol real
        """
        if self.is_simulating and self.simulated_role is not None:
            return self.simulated_role
        return self.real_role

    def effective_balance(self, real_balance: int) -> int:
        """
        Retorna el balance efectivo considerando simulación.

        Args:
            real_balance: Balance real del usuario desde la BD

        Returns:
            int: Balance simulado si está seteado, sino el real
        """
        if self.is_simulating and self.simulated_balance is not None:
            return self.simulated_balance
        return real_balance

    def effective_subscription_status(self, real_status: Optional[str] = None) -> Optional[str]:
        """
        Retorna el estado de suscripción efectivo considerando simulación.

        Args:
            real_status: Estado real de suscripción desde la BD

        Returns:
            str: Estado simulado si está seteado, sino el real
        """
        if self.is_simulating and self.simulated_subscription_status is not None:
            return self.simulated_subscription_status
        return real_status

    def time_remaining(self) -> Optional[int]:
        """
        Retorna segundos restantes de simulación.

        Returns:
            int: Segundos restantes, o None si no está simulando
        """
        if not self.is_simulating or self.expires_at is None:
            return None
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

    def to_dict(self) -> dict:
        """
        Convierte el contexto a diccionario para serialización.

        Returns:
            dict: Representación del contexto
        """
        return {
            "user_id": self.user_id,
            "real_role": self.real_role.value,
            "simulated_role": self.simulated_role.value if self.simulated_role else None,
            "is_simulating": self.is_simulating,
            "simulated_balance": self.simulated_balance,
            "simulated_subscription_status": self.simulated_subscription_status,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "effective_role": self.effective_role().value,
            "time_remaining": self.time_remaining()
        }


class SimulationStore:
    """
    Almacenamiento en memoria de contextos de simulación.

    Singleton pattern - una única instancia compartida.
    Aislamiento por admin: cada admin tiene su propio contexto.
    TTL automático: las simulaciones expiran después de 30 minutos.

    Thread-safe: asyncio-safe ya que es single-threaded.
    """

    _instance: Optional["SimulationStore"] = None
    _initialized: bool = False

    # TTL por defecto: 30 minutos
    DEFAULT_TTL_MINUTES = 30

    def __new__(cls) -> "SimulationStore":
        """Singleton pattern - retorna instancia única."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializa el store (solo una vez)."""
        if SimulationStore._initialized:
            return

        # Dict: admin_user_id -> ResolvedUserContext
        self._contexts: dict[int, ResolvedUserContext] = {}
        self._ttl_minutes = self.DEFAULT_TTL_MINUTES

        SimulationStore._initialized = True
        logger.debug("✅ SimulationStore inicializado (singleton)")

    def activate_simulation(
        self,
        admin_id: int,
        mode: SimulationMode,
        balance: Optional[int] = None,
        subscription_status: Optional[str] = None
    ) -> ResolvedUserContext:
        """
        Activa simulación para un admin.

        Args:
            admin_id: ID del admin que simula
            mode: Modo de simulación (VIP/FREE/REAL)
            balance: Balance simulado (opcional)
            subscription_status: Estado de suscripción simulado (opcional)

        Returns:
            ResolvedUserContext: Contexto creado/actualizado
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self._ttl_minutes)

        # Determinar rol simulado
        simulated_role = mode.simulated_role if mode != SimulationMode.REAL else None
        is_simulating = mode != SimulationMode.REAL

        context = ResolvedUserContext(
            user_id=admin_id,
            real_role=UserRole.ADMIN,  # Los que simulan siempre son admins
            simulated_role=simulated_role,
            is_simulating=is_simulating,
            simulated_balance=balance if is_simulating else None,
            simulated_subscription_status=subscription_status if is_simulating else None,
            activated_at=now,
            expires_at=expires if is_simulating else None
        )

        self._contexts[admin_id] = context

        logger.info(
            f"🎭 Simulación activada para admin {admin_id}: "
            f"modo={mode.value}, rol={simulated_role.value if simulated_role else 'N/A'}, "
            f"TTL={self._ttl_minutes}min"
        )

        return context

    def deactivate_simulation(self, admin_id: int) -> bool:
        """
        Desactiva simulación para un admin.

        Args:
            admin_id: ID del admin

        Returns:
            bool: True si había simulación activa y se desactivó
        """
        if admin_id not in self._contexts:
            return False

        context = self._contexts[admin_id]
        was_simulating = context.is_simulating

        # Marcar como no simulando
        context.is_simulating = False
        context.simulated_role = None
        context.simulated_balance = None
        context.simulated_subscription_status = None
        context.expires_at = None

        # Opcional: podríamos eliminar el contexto completamente
        # del self._contexts[admin_id]
        # Pero mantenerlo permite ver historial

        logger.info(f"🎭 Simulación desactivada para admin {admin_id}")
        return was_simulating

    def get_context(self, admin_id: int) -> Optional[ResolvedUserContext]:
        """
        Obtiene el contexto de simulación de un admin.

        Args:
            admin_id: ID del admin

        Returns:
            ResolvedUserContext o None si no existe
        """
        context = self._contexts.get(admin_id)

        if context is None:
            return None

        # Verificar si expiró
        if context.is_simulating and context.expires_at:
            if datetime.now(timezone.utc) > context.expires_at:
                logger.debug(f"⏰ Simulación expirada para admin {admin_id}")
                context.is_simulating = False
                context.simulated_role = None

        return context

    def is_simulating(self, admin_id: int) -> bool:
        """
        Verifica si un admin está en modo simulación.

        Args:
            admin_id: ID del admin

        Returns:
            bool: True si está simulando y no ha expirado
        """
        context = self.get_context(admin_id)
        if context is None:
            return False
        return context.is_simulating

    def cleanup_expired(self) -> int:
        """
        Limpia contextos expirados.

        Returns:
            int: Número de contextos limpiados
        """
        now = datetime.now(timezone.utc)
        expired_ids = []

        for admin_id, context in self._contexts.items():
            if context.is_simulating and context.expires_at:
                if now > context.expires_at:
                    expired_ids.append(admin_id)

        for admin_id in expired_ids:
            self.deactivate_simulation(admin_id)

        if expired_ids:
            logger.info(f"🧹 Cleanup: {len(expired_ids)} simulaciones expiradas eliminadas")

        return len(expired_ids)

    def get_all_active(self) -> list[ResolvedUserContext]:
        """
        Retorna todas las simulaciones activas.

        Returns:
            list: Contextos activos (no expirados)
        """
        active = []
        for context in self._contexts.values():
            if context.is_simulating:
                # Verificar que no haya expirado
                if context.expires_at and datetime.now(timezone.utc) <= context.expires_at:
                    active.append(context)
        return active


class SimulationService:
    """
    Servicio de simulación de roles para admins.

    Permite a los administradores ver y probar el bot como si fueran
    usuarios VIP o Free, sin modificar sus datos reales.

    Safety:
        - Solo admins pueden simular (verificación via Config.is_admin)
        - Simulación expira automáticamente (TTL 30 min)
        - Datos simulados aislados por admin

    Usage:
        container = ServiceContainer(session, bot)
        context = await container.simulation.resolve_user_context(admin_id)

        if context.effective_role() == UserRole.VIP:
            # Mostrar menú VIP
    """

    # Store singleton compartido entre instancias
    _store: SimulationStore = SimulationStore()

    def __init__(self, session: AsyncSession, bot: Optional["Bot"] = None):
        """
        Inicializa el servicio de simulación.

        Args:
            session: Sesión de base de datos SQLAlchemy
            bot: Instancia del Bot de Aiogram (opcional)
        """
        self.session = session
        self.bot = bot
        logger.debug("✅ SimulationService inicializado")

    async def resolve_user_context(self, user_id: int) -> ResolvedUserContext:
        """
        Resuelve el contexto completo de un usuario.

        Este es el PUNTO ÚNICO DE VERDAD para determinar el rol
        y datos efectivos de cualquier usuario.

        Lógica:
            1. Si es admin y tiene simulación activa: retorna contexto simulado
            2. Si es admin sin simulación: retorna contexto real (ADMIN)
            3. Si no es admin: retorna contexto real (VIP/FREE)

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            ResolvedUserContext: Contexto resuelto con rol efectivo
        """
        # Verificar si es admin
        is_admin = Config.is_admin(user_id)

        if is_admin:
            # Revisar si tiene simulación activa
            stored_context = self._store.get_context(user_id)

            if stored_context and stored_context.is_simulating:
                logger.debug(
                    f"🎭 Admin {user_id} resolviendo con simulación: "
                    f"{stored_context.simulated_role.value if stored_context.simulated_role else 'N/A'}"
                )
                return stored_context

            # Admin sin simulación - retornar contexto real
            return ResolvedUserContext(
                user_id=user_id,
                real_role=UserRole.ADMIN,
                is_simulating=False
            )

        # No es admin - detectar rol real desde la BD
        real_role = await self._detect_real_role(user_id)

        return ResolvedUserContext(
            user_id=user_id,
            real_role=real_role,
            is_simulating=False
        )

    async def _detect_real_role(self, user_id: int) -> UserRole:
        """
        Detecta el rol real de un usuario desde la base de datos.

        Args:
            user_id: ID del usuario

        Returns:
            UserRole: Rol detectado (VIP o FREE)
        """
        # Import local para evitar circular dependency
        from bot.services.subscription import SubscriptionService

        subscription_service = SubscriptionService(self.session, bot=self.bot)
        is_vip = await subscription_service.is_vip_active(user_id)

        if is_vip:
            return UserRole.VIP
        return UserRole.FREE

    async def start_simulation(
        self,
        admin_id: int,
        mode: SimulationMode,
        balance: Optional[int] = None,
        subscription_status: Optional[str] = None
    ) -> tuple[bool, str, Optional[ResolvedUserContext]]:
        """
        Inicia simulación para un admin.

        Args:
            admin_id: ID del admin que quiere simular
            mode: Modo de simulación (VIP/FREE)
            balance: Balance simulado (opcional)
            subscription_status: Estado de suscripción simulado (opcional)

        Returns:
            tuple: (success, message, context)
        """
        # Verificar que sea admin
        if not Config.is_admin(admin_id):
            logger.warning(f"🚫 Usuario {admin_id} intentó simular sin ser admin")
            return False, "Solo los administradores pueden usar el modo simulación", None

        # No permitir modo REAL como simulación (no tiene sentido)
        if mode == SimulationMode.REAL:
            # Desactivar simulación actual si existe
            self._store.deactivate_simulation(admin_id)
            return True, "Modo real restaurado (sin simulación)", self._store.get_context(admin_id)

        # Activar simulación
        context = self._store.activate_simulation(
            admin_id=admin_id,
            mode=mode,
            balance=balance,
            subscription_status=subscription_status
        )

        role_name = mode.simulated_role.display_name if mode.simulated_role else "N/A"
        return True, f"Simulación activada: {role_name}", context

    async def stop_simulation(self, admin_id: int) -> tuple[bool, str]:
        """
        Detiene la simulación para un admin.

        Args:
            admin_id: ID del admin

        Returns:
            tuple: (success, message)
        """
        if not Config.is_admin(admin_id):
            return False, "No tienes permisos para esta acción"

        was_active = self._store.deactivate_simulation(admin_id)

        if was_active:
            return True, "Simulación desactivada. Ahora ves el bot como admin."
        return True, "No había simulación activa."

    async def get_simulation_status(self, admin_id: int) -> dict:
        """
        Obtiene el estado de simulación de un admin.

        Args:
            admin_id: ID del admin

        Returns:
            dict: Estado completo de simulación
        """
        context = self._store.get_context(admin_id)

        if context is None or not context.is_simulating:
            return {
                "is_simulating": False,
                "mode": SimulationMode.REAL.value,
                "real_role": UserRole.ADMIN.value,
                "effective_role": UserRole.ADMIN.value,
                "time_remaining": None
            }

        return {
            "is_simulating": True,
            "mode": self._get_mode_from_role(context.simulated_role).value,
            "real_role": context.real_role.value,
            "effective_role": context.effective_role().value,
            "simulated_balance": context.simulated_balance,
            "simulated_subscription_status": context.simulated_subscription_status,
            "time_remaining": context.time_remaining(),
            "activated_at": context.activated_at.isoformat() if context.activated_at else None
        }

    def _get_mode_from_role(self, role: Optional[UserRole]) -> SimulationMode:
        """
        Convierte un UserRole a SimulationMode.

        Args:
            role: Rol de usuario

        Returns:
            SimulationMode: Modo correspondiente
        """
        if role == UserRole.VIP:
            return SimulationMode.VIP
        elif role == UserRole.FREE:
            return SimulationMode.FREE
        return SimulationMode.REAL

    async def cleanup_expired_simulations(self) -> int:
        """
        Limpia simulaciones expiradas.

        Returns:
            int: Número de simulaciones limpiadas
        """
        return self._store.cleanup_expired()

    def get_store(self) -> SimulationStore:
        """
        Retorna el store singleton (para testing/debugging).

        Returns:
            SimulationStore: Instancia del store
        """
        return self._store
