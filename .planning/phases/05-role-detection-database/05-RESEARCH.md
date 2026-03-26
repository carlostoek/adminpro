# Phase 5: Role Detection & Database Foundation - Research

**Researched:** 2026-01-24
**Domain:** SQLAlchemy 2.0 async models, role detection middleware, content package CRUD
**Confidence:** HIGH

## Summary

Phase 5 involves implementing automatic role detection (Admin/VIP/Free), creating database models for content packages and user interests, and building a ContentService for CRUD operations. The research confirms that the existing codebase already has foundational patterns established: UserRole enum, UserService, SubscriptionService with VIP status checking, and a mature async SQLAlchemy 2.0 setup with proper session management.

Key technical decisions from existing patterns:
1. **Role Detection**: Stateless function checking conditions in priority order (Admin > VIP > Free)
2. **Database Models**: Follow existing patterns in `bot/database/models.py` with relationships and indexes
3. **Service Pattern**: Follow SubscriptionService pattern (async methods, session injection via constructor)
4. **Middleware Integration**: Role detection via middleware that injects detected role into handler data

**Primary recommendation:** Build on existing UserService and SubscriptionService patterns, add role detection middleware that leverages `Config.is_admin()` and `subscription.is_vip_active()`, create ContentPackage/UserInterest models following established SQLAlchemy 2.0 async patterns, implement ContentService mirroring SubscriptionService structure.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.25 | Async ORM with models, relationships, indexes | Existing codebase uses 2.0.25 with async engine, AsyncSession, async_sessionmaker - industry standard for Python async DB |
| aiosqlite | 0.19.0 | Async SQLite driver for SQLAlchemy | Required driver for SQLite async operations, already in use |
| Aiogram | 3.4.1 | Telegram bot framework with middleware support | Existing framework, BaseMiddleware pattern for role detection |
| python-dotenv | 1.0.0 | Environment configuration | Already in use for Config.ADMIN_USER_IDS |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Decimal | (stdlib) | Price fields in ContentPackage | For monetary values - SQLAlchemy Numeric type maps to Python Decimal |
| secrets | (stdlib) | Token generation (existing pattern) | Already used in SubscriptionService for secure token generation |
| enum | (stdlib) | UserRole enum (already exists) | Already defined in bot/database/enums.py |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy 2.0.25 | SQLAlchemy 1.4 | 1.4 lacks modern async syntax (select(), scalar_one_or_none), 2.0 has better type hints |
| Numeric for price | Float for price | Float has precision issues with money, Numeric is standard for currency |
| is_active boolean | deleted_at timestamp | Soft delete with boolean simpler than timestamp-based soft delete, sufficient for this use case |

**Installation:**
```bash
# All dependencies already installed
pip install sqlalchemy==2.0.25 aiosqlite==0.19.0 aiogram==3.4.1 python-dotenv==1.0.0
```

## Architecture Patterns

### Recommended Project Structure

```
bot/
├── database/
│   ├── models.py          # Add: ContentPackage, UserInterest, UserRoleChangeLog
│   └── enums.py           # Existing: UserRole enum
├── services/
│   ├── container.py       # Add: content_service property
│   ├── role_service.py    # NEW: RoleDetectionService
│   ├── content.py         # NEW: ContentService
│   └── subscription.py    # Existing: is_vip_active() for VIP detection
├── middlewares/
│   ├── role_detection.py  # NEW: RoleDetectionMiddleware
│   └── admin_auth.py      # Existing: Config.is_admin() pattern
└── handlers/
    ├── user/
    │   └── menu.py        # Add: Role-based menu handlers (Phase 6)
    └── admin/
        └── content.py     # Add: Content management handlers (Phase 7)
```

### Pattern 1: Role Detection Service (Stateless Function)

**What:** Lightweight service that calculates user role based on existing data sources without storing state.

**When to use:** Called on every user interaction to determine current role dynamically.

**Example:**
```python
# bot/services/role_service.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.enums import UserRole
from config import Config

class RoleDetectionService:
    """Service para detectar rol de usuario (Admin/VIP/Free)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def detect_user_role(self, user_id: int) -> UserRole:
        """
        Detecta rol actual del usuario.

        Prioridad: Admin > VIP > Free (first match wins)

        Args:
            user_id: ID de Telegram del usuario

        Returns:
            UserRole: Rol detectado
        """
        # 1. Check Admin (highest priority)
        if Config.is_admin(user_id):
            return UserRole.ADMIN

        # 2. Check VIP (active subscription)
        # Import lazily to avoid circular dependency
        from bot.services.subscription import SubscriptionService
        from aiogram import Bot
        # Note: Need bot instance - will be injected via container

        subscription_service = SubscriptionService(self.session, bot)
        if await subscription_service.is_vip_active(user_id):
            return UserRole.VIP

        # 3. Default to Free
        return UserRole.FREE
```

### Pattern 2: Middleware for Role Injection

**What:** Aiogram BaseMiddleware that detects role before handler execution and injects into data dictionary.

**When to use:** Applied globally or to specific routers to provide role context to all handlers.

**Example:**
```python
# bot/middlewares/role_detection.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from bot.services.role_service import RoleDetectionService

class RoleDetectionMiddleware(BaseMiddleware):
    """
    Middleware que detecta e inyecta el rol del usuario.

    Uso:
        dp.message.middleware(RoleDetectionMiddleware())
        dp.callback_query.middleware(RoleDetectionMiddleware())

    Inyecta en data["user_role"]:
        - UserRole.ADMIN para admins
        - UserRole.VIP para suscriptores activos
        - UserRole.FREE para resto
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Extraer user del evento
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return await handler(event, data)

        # Obtener sesión del data dictionary
        session = data.get("session")
        if session is None:
            # No hay sesión - ejecutar handler sin role injection
            return await handler(event, data)

        # Detectar rol e inyectar
        role_service = RoleDetectionService(session)
        user_role = await role_service.detect_user_role(user.id)

        data["user_role"] = user_role
        data["user_id"] = user.id

        return await handler(event, data)
```

### Pattern 3: SQLAlchemy 2.0 Async Model with Relationships

**What:** Modern SQLAlchemy 2.0 async model with Mapped[] types, relationships, and composite indexes.

**When to use:** All new database models for consistency with existing codebase.

**Example:**
```python
# bot/database/models.py (additions)
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger, ForeignKey, Numeric, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database.enums import UserRole

class ContentPackage(Base):
    """Paquete de contenido (VIP/Free/Premium)."""

    __tablename__ = "content_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)  # Decimal for currency

    # Classification
    category: Mapped[str] = mapped_column(SQLEnum(ContentCategory), nullable=False, default=ContentCategory.FREE_CONTENT)
    type: Mapped[str] = mapped_column(SQLEnum(PackageType), nullable=False, default=PackageType.STANDARD)

    # Media
    media_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # State
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    interests: Mapped[List["UserInterest"]] = relationship(
        "UserInterest",
        back_populates="package",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index('idx_category_active', 'category', 'is_active'),
        Index('idx_type_active', 'type', 'is_active'),
    )

class UserInterest(Base):
    """Registro de interés de usuario en un paquete."""

    __tablename__ = "user_interests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Keys
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    package_id: Mapped[int] = mapped_column(Integer, ForeignKey("content_packages.id"), nullable=False, index=True)

    # State
    is_attended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    attended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", uselist=False, lazy="selectin")
    package: Mapped["ContentPackage"] = relationship("ContentPackage", uselist=False, lazy="selectin")

    # Composite index for deduplication queries
    __table_args__ = (
        Index('idx_user_package_attended', 'user_id', 'package_id', 'is_attended'),
    )

class UserRoleChangeLog(Base):
    """Registro de cambios de rol de usuario (auditoría)."""

    __tablename__ = "user_role_change_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Role change
    previous_role: Mapped[Optional[str]] = mapped_column(SQLEnum(UserRole), nullable=True)
    new_role: Mapped[str] = mapped_column(SQLEnum(UserRole), nullable=False)

    # Metadata
    changed_by: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)  # Admin or SYSTEM
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    change_source: Mapped[str] = mapped_column(String(50), nullable=False)  # ADMIN_PANEL, SYSTEM, API

    # Timestamp
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Indexes
    __table_args__ = (
        Index('idx_user_changed_at', 'user_id', 'changed_at'),
        Index('idx_changed_by_changed_at', 'changed_by', 'changed_at'),
    )
```

### Pattern 4: ContentService with CRUD Operations

**What:** Service layer following SubscriptionService pattern with async CRUD methods.

**When to use:** All database operations for content packages (create, read, update, delete, list).

**Example:**
```python
# bot/services/content.py
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.models import ContentPackage, UserInterest

class ContentService:
    """Servicio para gestión de paquetes de contenido."""

    def __init__(self, session: AsyncSession):
        self.session = session
        logger.debug("✅ ContentService inicializado")

    async def create_package(
        self,
        name: str,
        description: str,
        category: ContentCategory,
        price: Optional[float] = None,
        media_url: Optional[str] = None,
        package_type: PackageType = PackageType.STANDARD
    ) -> ContentPackage:
        """Crea un nuevo paquete de contenido."""
        package = ContentPackage(
            name=name,
            description=description,
            category=category,
            price=price,
            media_url=media_url,
            type=package_type,
            is_active=True
        )
        self.session.add(package)
        # No commit - handler manages transaction
        logger.info(f"✅ Paquete creado: {name}")
        return package

    async def get_package(self, package_id: int) -> Optional[ContentPackage]:
        """Obtiene paquete por ID."""
        result = await self.session.execute(
            select(ContentPackage).where(ContentPackage.id == package_id)
        )
        return result.scalar_one_or_none()

    async def list_packages(
        self,
        category: Optional[ContentCategory] = None,
        is_active: bool = True,
        limit: int = 100
    ) -> List[ContentPackage]:
        """Lista paquetes con filtros."""
        query = select(ContentPackage).order_by(ContentPackage.created_at.desc())

        if category:
            query = query.where(ContentPackage.category == category)
        if is_active is not None:
            query = query.where(ContentPackage.is_active == is_active)

        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_package(
        self,
        package_id: int,
        **kwargs
    ) -> Optional[ContentPackage]:
        """Actualiza paquete (campos opcionales via kwargs)."""
        package = await self.get_package(package_id)
        if not package:
            return None

        for key, value in kwargs.items():
            if hasattr(package, key):
                setattr(package, key, value)

        package.updated_at = datetime.utcnow()
        # No commit
        logger.info(f"✅ Paquete actualizado: {package_id}")
        return package

    async def toggle_package_active(self, package_id: int) -> Optional[ContentPackage]:
        """Alterna estado activo/inactivo (soft delete)."""
        package = await self.get_package(package_id)
        if not package:
            return None

        package.is_active = not package.is_active
        package.updated_at = datetime.utcnow()
        # No commit
        logger.info(f"✅ Paquete {'activado' if package.is_active else 'desactivado'}: {package_id}")
        return package
```

### Anti-Patterns to Avoid

- **Storing role in middleware state**: Role should be calculated fresh each time from database, not cached in middleware. Users can change roles during active session.
- **Hardcoding role logic in handlers**: Centralize role detection in RoleDetectionService, don't duplicate VIP checking logic across multiple handlers.
- **Float for currency**: Use SQLAlchemy Numeric type (maps to Decimal), not float, to avoid precision issues with monetary values.
- **Missing composite indexes**: UserInterest needs (user_id, package_id) composite index to prevent duplicate interest records and efficient queries.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Role detection logic | Custom Admin/VIP/Free checks in handlers | RoleDetectionService.is_vip_active(), Config.is_admin() | Duplicates existing logic, inconsistent behavior, hard to maintain |
| Session management | Manual session/commit/rollback in each handler | SessionContextManager (engine.py) with async with | Already exists, handles commit/rollback automatically, prevents resource leaks |
| Decimal price handling | Custom string-to-float conversion with rounding | SQLAlchemy Numeric(10, 2) column type | Handles precision correctly, maps to Python Decimal, standard for currency |
| Async session injection | Pass session as parameter to each method | Constructor injection (SubscriptionService pattern) | Consistent with existing services, cleaner API, easier testing |
| Database indexes | Manual index creation in migration scripts | SQLAlchemy Index in __table_args__ | Declarative, consistent with existing models, created automatically |

**Key insight:** The codebase already has mature patterns for async database operations, service layer, and middleware. Phase 5 should extend these patterns rather than reinventing them.

## Common Pitfalls

### Pitfall 1: Role Caching in Middleware

**What goes wrong:** Middleware caches detected role in user session or state, role becomes stale when user's VIP subscription expires or they get promoted to admin.

**Why it happens:** Developer tries to optimize by avoiding database query on each handler call, stores role in FSM state or middleware cache.

**How to avoid:** Always calculate role fresh from database sources (Config.is_admin(), SubscriptionService.is_vip_active()). Role detection is fast (2 queries max), caching complexity not worth minimal performance gain.

**Warning signs:** Role doesn't update after admin changes user's role, or expired VIP still sees VIP menu.

### Pitfall 2: Missing Composite Indexes on UserInterest

**What goes wrong:** Duplicate interest records for same user-package pair, slow queries checking if user already interested.

**Why it happens:** Only single-column indexes created (user_id, package_id), missing composite index for deduplication queries.

**How to avoid:** Always create composite index on (user_id, package_id, is_attended) for UserInterest model, enables efficient deduplication and attended interest queries.

**Warning signs:** Slow queries when checking existing interests, duplicate rows in user_interests table.

### Pitfall 3: Float Type for Price Fields

**What goes wrong:** Price calculations have rounding errors ($10.01 becomes $10.00999999), inconsistent comparisons fail.

**Why it happens:** Using Python float or SQLAlchemy Float type for currency, which has binary floating-point precision issues.

**How to avoid:** Always use SQLAlchemy Numeric(precision=10, scale=2) for price fields, maps to Python Decimal type with exact decimal arithmetic.

**Warning signs:** Price comparisons fail, formatting shows incorrect decimals, accounting discrepancies.

### Pitfall 4: Commit in Service Methods

**What goes wrong:** Partial updates if transaction fails mid-operation, unable to rollback related operations.

**Why it happens:** Service methods call await session.commit(), handlers lose transaction control.

**How to avoid:** Follow SubscriptionService pattern - services add/modify objects but DON'T commit, let handlers manage transaction with SessionContextManager.

**Warning signs:** Can't rollback multi-step operations, database has partial updates on errors.

### Pitfall 5: Forgetting updated_at on ContentPackage

**What goes wrong:** Can't track when content was last modified, no audit trail for price changes.

**Why it happens:** Only created_at timestamp included, missing onupdate trigger for updated_at.

**How to avoid:** Always include updated_at with default=datetime.utcnow, onupdate=datetime.utcnow (see existing BotConfig model for pattern).

**Warning signs:** No way to determine recency of changes, stale caches not invalidated.

## Code Examples

Verified patterns from existing codebase:

### Checking User Role (Existing Pattern)

```python
# Source: /data/data/com.termux/files/home/repos/c1/bot/services/subscription.py
async def is_vip_active(self, user_id: int) -> bool:
    """
    Verifica si un usuario tiene suscripción VIP activa.

    Args:
        user_id: ID del usuario

    Returns:
        True si VIP activo, False si no
    """
    subscriber = await self.get_vip_subscriber(user_id)

    if subscriber is None:
        return False

    if subscriber.status != "active":
        return False

    if subscriber.is_expired():
        return False

    return True
```

### Creating Indexes in SQLAlchemy 2.0

```python
# Source: /data/data/com.termux/files/home/repos/c1/bot/database/models.py
from sqlalchemy import Index

class VIPSubscriber(Base):
    # ... columns ...

    # Índice compuesto para buscar activos próximos a expirar
    __table_args__ = (
        Index('idx_status_expiry', 'status', 'expiry_date'),
    )
```

### Middleware Pattern (Existing AdminAuthMiddleware)

```python
# Source: /data/data/com.termux/files/home/repos/c1/bot/middlewares/admin_auth.py
class AdminAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Extraer user del event
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user is None:
            return await handler(event, data)

        # Verificar permiso
        if not Config.is_admin(user.id):
            # Enviar error y NO ejecutar handler
            return None

        # Ejecutar handler
        return await handler(event, data)
```

### Session Management Pattern

```python
# Source: /data/data/com.termux/files/home/repos/c1/bot/database/engine.py
class SessionContextManager:
    """Context manager para AsyncSession con manejo de errores."""

    async def __aenter__(self) -> AsyncSession:
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()

# Usage in handlers:
async with get_session() as session:
    # All database operations
    # Auto-commit on success, auto-rollback on error
```

### Service Pattern (No Commit in Methods)

```python
# Source: /data/data/com.termux/files/home/repos/c1/bot/services/subscription.py
async def generate_vip_token(self, generated_by: int, duration_hours: int = 24) -> InvitationToken:
    """Genera un token de invitación único."""

    # Create token
    token = InvitationToken(
        token=token_str,
        generated_by=generated_by,
        created_at=datetime.utcnow(),
        duration_hours=duration_hours,
        used=False
    )

    self.session.add(token)
    # No commit - dejar que el handler maneje la transacción

    logger.info(f"✅ Token VIP generado: {token.token}")
    return token
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy sync engine | SQLAlchemy 2.0 async (AsyncEngine, AsyncSession) | SQLAlchemy 1.4/2.0 (2021-2022) | Requires async/await throughout, better concurrency for bots |
| Float for prices | Numeric(10,2) for currency | Industry standard, always | Decimal precision for money, prevents rounding errors |
| Hardcoded role checks | Centralized RoleDetectionService | This phase | Single source of truth, consistent behavior |
| Manual session management | SessionContextManager with auto commit/rollback | Existing pattern (engine.py) | Prevents resource leaks, consistent error handling |

**Deprecated/outdated:**
- SQLAlchemy 1.x sync syntax: session.query(Model).filter_by() - replaced by select(Model).where()
- Manual transaction management (session.commit() in services) - use SessionContextManager pattern
- Role caching in middleware/FSM state - always calculate fresh from database

## Open Questions

Things that couldn't be fully resolved:

1. **UserRoleChangeLog event granularity**
   - What we know: Need to track role changes for audit
   - What's unclear: Should we track ALL role changes or just manual/admin-triggered ones? Automatic VIP expiry creates many log entries.
   - Recommendation: Track ALL role changes but add change_source field ('SYSTEM', 'ADMIN_PANEL', 'API') to filter, include reason field for context.

2. **ContentPackage updated_at necessity**
   - What we know: Existing BotConfig model has updated_at, ContentPackage doesn't
   - What's unclear: Do we need to track when packages are modified for caching/invalidation?
   - Recommendation: Include updated_at following BotConfig pattern, minimal overhead, enables future features like "recently modified" lists.

3. **Index strategy for query patterns**
   - What we know: UserInterest needs (user_id, package_id) composite index
   - What's unclear: What queries will we run? Need indexes for admin interest list by date? User's active interests?
   - Recommendation: Start with user_id, package_id, is_attended indexes, add timestamp indexes after Phase 8 when query patterns are known.

4. **Role change during active menu session**
   - What we know: User can change role while browsing menu (VIP expires, admin promotes)
   - What's unclear: Should menu refresh automatically or wait for next interaction?
   - Recommendation: Don't auto-refresh menus (complex state), recalculate role on each callback/message, menu updates on next user action.

## Sources

### Primary (HIGH confidence)

- **Existing codebase analysis**: /data/data/com.termux/files/home/repos/c1/
  - bot/database/models.py - Existing VIPSubscriber, User, InvitationToken models with relationships and indexes
  - bot/services/subscription.py - SubscriptionService with is_vip_active() pattern
  - bot/services/user.py - UserService with role change methods
  - bot/middlewares/admin_auth.py - AdminAuthMiddleware pattern for role-based access
  - bot/database/enums.py - UserRole enum definition
  - bot/database/engine.py - AsyncEngine, AsyncSession, SessionContextManager pattern
  - bot/services/container.py - ServiceContainer with lazy loading, constructor injection
  - config.py - Config.is_admin() method for admin detection

- **[Asynchronous SQLAlchemy 2: Step-by-Step Guide](https://dev.to/amverum/asynchronous-sqlalchemy-2-a-simple-step-by-step-guide-to-configuration-models-relationships-and-3ob3)** (June 2025)
  - Confirms SQLAlchemy 2.0 async patterns with select(), scalar_one_or_none(), Mapped[] types
  - Validates relationship definitions and lazy loading strategies

- **[SQLAlchemy Best Practices and Coding Standards](https://cursorrules.org/article/sqlalchemy-cursor-mdc-file)** (August 2025)
  - Confirms best practices for model organization, relationship definitions, index strategies

### Secondary (MEDIUM confidence)

- **[PostgreSQL Indexing with SQLAlchemy Guide](https://www.opcito.com/blogs/a-guide-to-postgresql-indexing-with-sqlalchemy)** (June 2024)
  - Composite index creation strategies, query optimization patterns
  - Note: Target is SQLite, but composite index concepts apply

- **[Ultimate Guide to SQLAlchemy Library in Python](https://deepnote.com/blog/ultimate-guide-to-sqlalchemy-library-in-python)** (August 2025)
  - Modern SQLAlchemy 2.0 usage patterns, async engine configuration

- **[How should I handle decimal in SQLAlchemy & SQLite](https://stackoverflow.com/questions/10355767/how-should-i-handle-decimal-in-sqlalchemy-sqlalchemy))** (Stack Overflow)
  - Confirms Numeric(10, 2) for price fields, Decimal vs Float for currency

### Tertiary (LOW confidence)

- **[Aiogram 3.4 Middleware Tutorial](https://www.youtube.com/watch?v=CFwQBhUd2Qc)** (YouTube)
  - Not verified due to format limitations, but title suggests relevant middleware patterns
  - Existing codebase already demonstrates working middleware pattern (AdminAuthMiddleware)

- **Web search results on role change tracking audit logs**: Rate-limited during search, unable to verify specific UserRoleChangeLog schema patterns against external sources. Recommendation based on general audit log best practices (user_id, previous_role, new_role, changed_by, timestamp, reason).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, confirmed by existing codebase analysis
- Architecture: HIGH - Patterns verified against existing services (SubscriptionService, UserService), confirmed by SQLAlchemy 2.0 documentation
- Pitfalls: HIGH - Identified from existing codebase patterns, standard SQLAlchemy best practices, common async/await mistakes

**Research date:** 2026-01-24
**Valid until:** 30 days (stable stack with established patterns, SQLAlchemy 2.0 and Aiogram 3.4 are mature)

---

**Phase:** 05 - Role Detection & Database Foundation
**Next:** Planner uses this research to create 05-01-PLAN.md, 05-02-PLAN.md, 05-03-PLAN.md
