---
phase: 05-role-detection-database
plan: 02
type: execute
wave: 2
depends_on: [05-01]
files_modified:
  - bot/database/enums.py
  - bot/database/models.py
  - bot/database/engine.py
autonomous: true

must_haves:
  truths:
    - "Sistema puede almacenar paquetes de contenido con categorías (FREE/VIP/PREMIUM)"
    - "Usuarios pueden marcar interés en paquetes específicos (sin duplicados)"
    - "Sistema registra cambios de rol con razón y auditoría completa"
    - "Paquetes tienen precios con precisión decimal (para moneda)"
    - "Consultas por categoría/estado son eficientes (índices compuestos)"
    - "Intereses de usuario están deduplicados automáticamente"
    - "Historial de cambios de rol permite auditoría de quién hizo qué y por qué"
  artifacts:
    - path: "bot/database/enums.py"
      provides: "ContentCategory, PackageType, RoleChangeReason enums"
      exports: ["ContentCategory", "PackageType", "RoleChangeReason"]
      min_lines: 60
    - path: "bot/database/models.py"
      provides: "ContentPackage, UserInterest, UserRoleChangeLog SQLAlchemy models"
      contains: "class ContentPackage", "class UserInterest", "class UserRoleChangeLog"
      min_lines: 200 (new code)
    - path: "bot/database/engine.py"
      provides: "create_tables() function to create new tables"
      contains: "def create_tables" or "Base.metadata.create_all"
      min_lines: 20 (new or modified)
  key_links:
    - from: "bot/database/models.py (UserInterest)"
      to: "bot/database/models.py (ContentPackage)"
      via: "SQLAlchemy relationship"
      pattern: "relationship\([\"']ContentPackage[\"']"
    - from: "bot/database/models.py (UserInterest)"
      to: "bot/database/models.py (User)"
      via: "ForeignKey user_id"
      pattern: "ForeignKey\([\"']users\.user_id[\"']"
    - from: "bot/database/models.py (UserRoleChangeLog)"
      to: "bot/database/enums.py"
      via: "UserRole and RoleChangeReason enums"
      pattern: "Enum\(UserRole\)"
---

<objective>
Create database models for content packages (ContentPackage), user interests (UserInterest), and role change audit log (UserRoleChangeLog) with proper indexes, relationships, and constraints following existing SQLAlchemy 2.0 async patterns.

Purpose: Enable content management and interest tracking system - CONTENT-01, CONTENT-02 requirements
Output: Working database models with migrations ready to create tables
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/05-role-detection-database/05-CONTEXT.md
@.planning/phases/05-role-detection-database/05-RESEARCH.md

# Existing patterns to follow
@bot/database/models.py (existing models: BotConfig, User, VIPSubscriber, InvitationToken, FreeChannelRequest)
@bot/database/enums.py (existing UserRole enum)
@bot/database/engine.py (existing engine, session factory, create_tables pattern)
@bot/services/subscription.py (SubscriptionService using models)
</context>

<tasks>

<task type="auto">
  <name>Add content and role change enums to enums.py</name>
  <files>bot/database/enums.py</files>
  <action>
Modify bot/database/enums.py to add ContentCategory, PackageType, and RoleChangeReason enums:

Add after the UserRole class (after line 52):

```python
class ContentCategory(str, Enum):
    """
    Categorías de contenido para paquetes.

    Categorías:
        FREE_CONTENT: Contenido gratuito (acceso para todos)
        VIP_CONTENT: Contenido VIP (requiere suscripción activa)
        VIP_PREMIUM: Contenido premium VIP (contenido exclusivo de alto valor)
    """

    FREE_CONTENT = "free_content"
    VIP_CONTENT = "vip_content"
    VIP_PREMIUM = "vip_premium"

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

    STANDARD = "standard"
    BUNDLE = "bundle"
    COLLECTION = "collection"

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
        MANUAL_CHANGE: Cambio manual de rol por admin
        SYSTEM_AUTOMATIC: Cambio automático por el sistema
    """

    ADMIN_GRANTED = "admin_granted"
    ADMIN_REVOKED = "admin_revoked"
    VIP_PURCHASED = "vip_purchased"
    VIP_REDEEMED = "vip_redeemed"
    VIP_EXPIRED = "vip_expired"
    VIP_EXTENDED = "vip_extended"
    MANUAL_CHANGE = "manual_change"
    SYSTEM_AUTOMATIC = "system_automatic"

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
            RoleChangeReason.MANUAL_CHANGE: "Cambio Manual",
            RoleChangeReason.SYSTEM_AUTOMATIC: "Automático"
        }
        return names[self]
```

Key requirements:
- Follow existing UserRole enum pattern (str, Enum inheritance)
- Add display_name property for user-friendly names
- Add emoji property where applicable (ContentCategory)
- Add __str__ method returning self.value
- Add comprehensive docstrings
- Spanish display names (consistent with existing codebase)
  </action>
  <verify>
# Check new enums exist and work correctly
python -c "
from bot.database.enums import ContentCategory, PackageType, RoleChangeReason

# Verify enums exist
assert ContentCategory.FREE_CONTENT is not None
assert PackageType.STANDARD is not None
assert RoleChangeReason.VIP_REDEEMED is not None

# Verify string conversion
assert str(ContentCategory.FREE_CONTENT) == 'free_content'
assert str(PackageType.BUNDLE) == 'bundle'

# Verify properties
assert ContentCategory.FREE_CONTENT.display_name == 'Contenido Gratuito'
assert ContentCategory.FREE_CONTENT.emoji == '🆓'
assert RoleChangeReason.VIP_REDEEMED.display_name == 'VIP Canjeado'

print('✅ New enums verified')
"
  </verify>
  <done>
ContentCategory, PackageType, and RoleChangeReason enums exist with display_name and emoji properties
  </done>
</task>

<task type="auto">
  <name>Add ContentPackage model to models.py</name>
  <files>bot/database/models.py</files>
  <action>
Add ContentPackage model to bot/database/models.py after the existing models (after FreeChannelRequest, around line 220):

```python
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

    id = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic info
    name = mapped_column(String(200), nullable=False)
    description = mapped_column(Text, nullable=True)

    # Price (Numeric for currency precision - NOT Float)
    from sqlalchemy import Numeric
    price = mapped_column(Numeric(10, 2), nullable=True)

    # Classification
    from bot.database.enums import ContentCategory, PackageType
    category = mapped_column(
        Enum(ContentCategory),
        nullable=False,
        default=ContentCategory.FREE_CONTENT
    )
    type = mapped_column(
        Enum(PackageType),
        nullable=False,
        default=PackageType.STANDARD
    )

    # Media
    media_url = mapped_column(String(500), nullable=True)

    # State
    is_active = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
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
            f"category={self.category.value}, is_active={self.is_active})>"
        )

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_content_category_active', 'category', 'is_active'),
        Index('idx_content_type_active', 'type', 'is_active'),
    )
```

Key requirements:
- Use mapped_column() (SQLAlchemy 2.0 style)
- Use Numeric(10, 2) for price (NOT Float - precision matters for currency)
- Add default values for category and type enums
- Add is_active with index=True for filtering active packages
- Add created_at and updated_at timestamps (updated_at with onupdate)
- Add relationship to UserInterest (back_populates)
- Add composite indexes: (category, is_active) and (type, is_active)
- Follow existing model patterns (VIPSubscriber, BotConfig)
- Add __repr__ for debugging
- Add comprehensive docstring
  </action>
  <verify>
# Check ContentPackage model structure
python -c "
from bot.database.models import ContentPackage
from bot.database.enums import ContentCategory
import inspect

# Verify model exists
assert ContentPackage is not None

# Verify table name
assert ContentPackage.__tablename__ == 'content_packages'

# Verify key attributes exist
attrs = ['id', 'name', 'description', 'price', 'category', 'type', 'is_active', 'created_at', 'updated_at']
for attr in attrs:
    assert hasattr(ContentPackage, attr), f'Missing attribute: {attr}'

# Verify relationship
assert hasattr(ContentPackage, 'interests'), 'Missing interests relationship'

print('✅ ContentPackage model verified')
"
  </verify>
  <done>
ContentPackage model exists with all required fields, Numeric price, indexes, and UserInterest relationship
  </done>
</task>

<task type="auto">
  <name>Add UserInterest model to models.py</name>
  <files>bot/database/models.py</files>
  <action>
Add UserInterest model to bot/database/models.py after ContentPackage:

```python
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

    id = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Keys (with foreign keys)
    user_id = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    package_id = mapped_column(
        Integer,
        ForeignKey("content_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # State
    is_attended = mapped_column(Boolean, nullable=False, default=False, index=True)
    attended_at = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates=None)
    package = relationship("ContentPackage", back_populates="interests")

    def __repr__(self):
        return (
            f"<UserInterest(id={self.id}, user_id={self.user_id}, "
            f"package_id={self.package_id}, is_attended={self.is_attended})>"
        )

    # Unique constraint for deduplication + composite index for queries
    __table_args__ = (
        # Unique constraint: one interest per user-package pair
        # Note: Handler should check existence before inserting
        Index('idx_interest_user_package', 'user_id', 'package_id', unique=True),
        # Composite index for "attended interests by user" queries
        Index('idx_interest_user_package_attended', 'user_id', 'package_id', 'is_attended'),
    )
```

Note: Add back_populates to User model if you want bidirectional relationship:
In User model, add: interests = relationship("UserInterest", back_populates="user")

Key requirements:
- Use mapped_column() (SQLAlchemy 2.0 style)
- Add Foreign Keys with ondelete="CASCADE" for cleanup
- Add indexes on user_id and package_id
- Add unique composite index (user_id, package_id) for deduplication
- Add composite index (user_id, package_id, is_attended) for attended queries
- Add created_at timestamp (updated on re-clicks in service layer)
- Add is_attended boolean with index
- Add attended_at nullable timestamp
- Add relationships to User and ContentPackage
- Follow existing model patterns
- Add __repr__ for debugging
- Add comprehensive docstring
  </action>
  <verify>
# Check UserInterest model structure
python -c "
from bot.database.models import UserInterest
import inspect

# Verify model exists
assert UserInterest is not None

# Verify table name
assert UserInterest.__tablename__ == 'user_interests'

# Verify key attributes exist
attrs = ['id', 'user_id', 'package_id', 'is_attended', 'attended_at', 'created_at']
for attr in attrs:
    assert hasattr(UserInterest, attr), f'Missing attribute: {attr}'

# Verify relationships
assert hasattr(UserInterest, 'user'), 'Missing user relationship'
assert hasattr(UserInterest, 'package'), 'Missing package relationship'

print('✅ UserInterest model verified')
"
  </verify>
  <done>
UserInterest model exists with unique constraint (user_id, package_id), indexes, and relationships
  </done>
</task>

<task type="auto">
  <name>Add UserRoleChangeLog model to models.py</name>
  <files>bot/database/models.py</files>
  <action>
Add UserRoleChangeLog model to bot/database/models.py after UserInterest:

```python
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

    id = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User
    user_id = mapped_column(BigInteger, nullable=False, index=True)

    # Role change
    from bot.database.enums import UserRole, RoleChangeReason
    previous_role = mapped_column(Enum(UserRole), nullable=True)  # None for new users
    new_role = mapped_column(Enum(UserRole), nullable=False)

    # Metadata
    changed_by = mapped_column(BigInteger, nullable=False, index=True)  # Admin ID or 0 for SYSTEM
    reason = mapped_column(Enum(RoleChangeReason), nullable=False)
    change_source = mapped_column(String(50), nullable=False)  # 'ADMIN_PANEL', 'SYSTEM', 'API'
    metadata = mapped_column(JSON, nullable=True)  # Optional: {"duration_hours": 24, "token": "ABC..."}

    # Timestamp
    changed_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<UserRoleChangeLog(id={self.id}, user_id={self.user_id}, "
            f"previous_role={self.previous_role.value if self.previous_role else None}, "
            f"new_role={self.new_role.value}, reason={self.reason.value})>"
        )

    # Indexes for audit trail queries
    __table_args__ = (
        # Composite index for "user's role history" queries (most recent first)
        Index('idx_role_log_user_changed_at', 'user_id', 'changed_at'),
        # Composite index for "changes made by admin" queries
        Index('idx_role_log_changed_by_changed_at', 'changed_by', 'changed_at'),
    )
```

Key requirements:
- Use mapped_column() (SQLAlchemy 2.0 style)
- Add index on user_id and changed_by
- Add composite index (user_id, changed_at) for user history queries
- Add composite index (changed_by, changed_at) for admin audit queries
- Use Enum for UserRole and RoleChangeReason
- Store previous_role as nullable (None for new users)
- Add changed_at timestamp with index
- Add change_source field ('ADMIN_PANEL', 'SYSTEM', 'API')
- Add metadata JSON field for optional context
- Follow existing model patterns
- Add __repr__ for debugging
- Add comprehensive docstring
  </action>
  <verify>
# Check UserRoleChangeLog model structure
python -c "
from bot.database.models import UserRoleChangeLog
from bot.database.enums import UserRole, RoleChangeReason
import inspect

# Verify model exists
assert UserRoleChangeLog is not None

# Verify table name
assert UserRoleChangeLog.__tablename__ == 'user_role_change_log'

# Verify key attributes exist
attrs = ['id', 'user_id', 'previous_role', 'new_role', 'changed_by', 'reason', 'change_source', 'metadata', 'changed_at']
for attr in attrs:
    assert hasattr(UserRoleChangeLog, attr), f'Missing attribute: {attr}'

print('✅ UserRoleChangeLog model verified')
"
  </verify>
  <done>
UserRoleChangeLog model exists with audit fields, indexes for queries, and metadata support
  </done>
</task>

<task type="auto">
  <name>Update database engine to create new tables</name>
  <files>bot/database/engine.py</files>
  <action>
Modify bot/database/engine.py to ensure new tables are created:

Option 1: If create_tables() function exists, verify it uses Base.metadata.create_all():
- The function should already create all tables defined in models.py
- No changes needed if using Base.metadata.create_all(bind=engine)

Option 2: If tables are created manually, add new models:
- Add ContentPackage, UserInterest, UserRoleChangeLog to table creation list

Best practice: Add a migration helper function:

```python
async def create_content_tables():
    """
    Crea las tablas nuevas para el sistema de contenido.

    Esta función es idempotente - se puede ejecutar múltiples veces.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_table)
        # O especificar tablas:
        # await conn.run_sync(ContentPackage.__table__.create)
        # await conn.run_sync(UserInterest.__table__.create)
        # await conn.run_sync(UserRoleChangeLog.__table__.create)
    logger.info("✅ Tablas de contenido creadas")
```

Key requirements:
- Use SQLAlchemy 2.0 async pattern (async with engine.begin())
- Tables should be created automatically by Base.metadata.create_all()
- Add logging for table creation
- Idempotent (can run multiple times without error)
  </action>
  <verify>
# Verify tables can be created
python -c "
import asyncio
from bot.database.engine import engine, get_session
from bot.database.models import Base, ContentPackage, UserInterest, UserRoleChangeLog

async def test_tables():
    # This will create all tables (including new ones)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print('✅ Tables created successfully')

    # Verify tables exist by checking metadata
    tables = Base.metadata.tables.keys()
    assert 'content_packages' in tables, 'Missing content_packages table'
    assert 'user_interests' in tables, 'Missing user_interests table'
    assert 'user_role_change_log' in tables, 'Missing user_role_change_log table'

    print('✅ All new tables exist in metadata')

asyncio.run(test_tables())
"
  </verify>
  <done>
Database tables ContentPackage, UserInterest, and UserRoleChangeLog can be created successfully
  </done>
</task>

</tasks>

<verification>
# Overall Phase 5-2 Verification

## 1. Model Structure Verification
```bash
# Test all models are properly defined
python -c "
from bot.database.models import ContentPackage, UserInterest, UserRoleChangeLog
from bot.database.enums import ContentCategory, PackageType, RoleChangeReason
from bot.database.engine import get_session
import asyncio

async def verify_models():
    async with get_session() as session:
        # Test: Create a ContentPackage instance
        pkg = ContentPackage(
            name='Test Package',
            description='Test description',
            category=ContentCategory.VIP_CONTENT,
            type=PackageType.STANDARD,
            is_active=True
        )
        assert pkg.name == 'Test Package'
        assert pkg.category == ContentCategory.VIP_CONTENT
        print('✅ ContentPackage instantiation works')

        # Test: UserInterest instance
        interest = UserInterest(
            user_id=123456,
            package_id=1,
            is_attended=False
        )
        assert interest.user_id == 123456
        print('✅ UserInterest instantiation works')

        # Test: UserRoleChangeLog instance
        log = UserRoleChangeLog(
            user_id=123456,
            new_role=UserRole.VIP,
            changed_by=789012,
            reason=RoleChangeReason.VIP_REDEEMED,
            change_source='ADMIN_PANEL'
        )
        assert log.new_role == UserRole.VIP
        print('✅ UserRoleChangeLog instantiation works')

asyncio.run(verify_models())
"
```

## 2. Database Schema Verification
```bash
# Verify tables and indexes in SQLite
sqlite3 bot.db ".schema content_packages"
sqlite3 bot.db ".schema user_interests"
sqlite3 bot.db ".schema user_role_change_log"

# Verify indexes exist
sqlite3 bot.db "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='content_packages'"
sqlite3 bot.db "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='user_interests'"
```

## 3. Price Field Type Verification
```bash
# Verify price is Numeric (not Float)
python -c "
from bot.database.models import ContentPackage
from sqlalchemy import Numeric, Float
import inspect

# Get the price column
price_col = ContentPackage.__table__.columns['price']
assert isinstance(price_col.type, Numeric), 'Price must be Numeric type'
assert not isinstance(price_col.type, Float), 'Price must not be Float type'
print('✅ Price field uses Numeric type (not Float)')
"
```
</verification>

<success_criteria>
1. ContentPackage model has all fields: id, name, description, price (Numeric), category, type, media_url, is_active, created_at, updated_at
2. ContentPackage has composite indexes: (category, is_active) and (type, is_active)
3. UserInterest model has unique constraint on (user_id, package_id) for deduplication
4. UserInterest has composite index: (user_id, package_id, is_attended)
5. UserRoleChangeLog model has audit fields: previous_role, new_role, changed_by, reason, change_source, metadata
6. UserRoleChangeLog has indexes for user history and admin audit queries
7. All models use mapped_column() (SQLAlchemy 2.0 style)
8. All models have relationships defined correctly
9. Database tables can be created without errors
10. Price field uses Numeric(10, 2) not Float (precision for currency)
</success_criteria>

<output>
After completion, create `.planning/phases/05-role-detection-database/05-02-SUMMARY.md` with:

1. Frontmatter with phase, plan, subsystem, dependencies, tech-stack, key-files, key-decisions, patterns-established, duration, completed date
2. Summary of database models created (ContentPackage, UserInterest, UserRoleChangeLog)
3. Schema details (indexes, constraints, relationships)
4. Any deviations from plan or discovered edge cases
5. Migration notes (how tables were created)
</output>
