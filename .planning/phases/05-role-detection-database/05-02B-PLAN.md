---
phase: 05-role-detection-database
plan: 02B
type: execute
wave: 3
depends_on: [05-02A]
files_modified:
  - bot/database/models.py
  - bot/database/engine.py
autonomous: true

must_haves:
  truths:
    - "Usuarios pueden marcar interés en paquetes específicos (sin duplicados)"
    - "Sistema registra cambios de rol con razón y auditoría completa"
    - "Intereses de usuario están deduplicados automáticamente"
    - "Historial de cambios de rol permite auditoría de quién hizo qué y por qué"
    - "Base de datos está lista para usar sin configuración manual de tablas"
  artifacts:
    - path: "bot/database/models.py"
      provides: "UserInterest, UserRoleChangeLog SQLAlchemy models"
      contains: "class UserInterest", "class UserRoleChangeLog"
      min_lines: 150 (new code)
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
Create UserInterest and UserRoleChangeLog database models with proper indexes, relationships, and constraints, and update database engine to create all tables automatically.

Purpose: Enable user interest tracking and role change audit logging - CONTENT-02, MENU-04 requirements
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

# Dependencies
@.planning/phases/05-role-detection-database/05-02A-SUMMARY.md (ContentPackage model and enums)

# Existing patterns to follow
@bot/database/models.py (existing models: BotConfig, User, VIPSubscriber, InvitationToken, FreeChannelRequest, ContentPackage)
@bot/database/enums.py (existing UserRole, ContentCategory, PackageType, RoleChangeReason enums)
@bot/database/engine.py (existing engine, session factory, create_tables pattern)
</context>

<tasks>

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
        # Note: Handler should check existence before inserting
        Index('idx_interest_user_package', 'user_id', 'package_id', unique=True),
        # Composite index for "attended interests by user" queries
        Index('idx_interest_user_package_attended', 'user_id', 'package_id', 'is_attended'),
    )
```

Important: Update User model to add bidirectional relationship:
In User model (bot/database/models.py), add this line after existing relationships:
```python
interests = relationship("UserInterest", back_populates="user", cascade="all, delete-orphan")
```

This enables bidirectional navigation from User to UserInterest.

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
Verify that bot/database/engine.py already creates all tables automatically:

1. Check that the `init_db()` function in engine.py includes `Base.metadata.create_all()` call
2. Verify that new models (ContentPackage, UserInterest, UserRoleChangeLog) will be automatically created
3. No changes needed if `init_db()` already uses `Base.metadata.create_all()`

The existing engine.py should have this pattern in `init_db()`:
```python
async with _engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tablas creadas/verificadas")
```

Since `Base.metadata.create_all()` automatically creates all tables defined in models.py, new models will be included without manual updates.

Key requirements:
- Use SQLAlchemy 2.0 async pattern (async with engine.begin())
- Tables should be created automatically by Base.metadata.create_all()
- Add logging for table creation mentioning new tables
- Idempotent (can run multiple times without error)
- Follow existing patterns in the file
  </action>
  <verify>
# Verify engine.py creates all tables automatically
python -c "
import asyncio
from bot.database.engine import init_db, engine
from bot.database.models import Base, ContentPackage, UserInterest, UserRoleChangeLog

async def test_engine():
    # Initialize database (this should create all tables)
    await init_db()

    print('✅ Database initialized successfully')

    # Verify tables exist by checking metadata
    tables = Base.metadata.tables.keys()
    assert 'content_packages' in tables, 'Missing content_packages table'
    assert 'user_interests' in tables, 'Missing user_interests table'
    assert 'user_role_change_log' in tables, 'Missing user_role_change_log table'

    print('✅ All new tables exist in metadata after init_db()')

asyncio.run(test_engine())
"
  </verify>
  <done>
Database tables ContentPackage, UserInterest, and UserRoleChangeLog are automatically created when init_db() is called
  </done>
</task>

</tasks>

<verification>
# Overall Phase 5-2B Verification

## 1. Model Structure Verification
```bash
# Test all models are properly defined
python -c "
from bot.database.models import ContentPackage, UserInterest, UserRoleChangeLog
from bot.database.enums import ContentCategory, PackageType, RoleChangeReason, UserRole
from bot.database.engine import get_session
import asyncio

async def verify_models():
    async with get_session() as session:
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
sqlite3 bot.db "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='user_role_change_log'"
```

## 3. Unique Constraint Verification
```bash
# Verify UserInterest has unique constraint
python -c "
from bot.database.models import UserInterest
import inspect

# Check table_args for unique constraint
table_args = UserInterest.__table_args__
has_unique = False
if isinstance(table_args, tuple):
    for arg in table_args:
        if hasattr(arg, 'unique') and arg.unique:
            has_unique = True
            break
elif hasattr(table_args, 'unique') and table_args.unique:
    has_unique = True

assert has_unique, 'UserInterest must have unique constraint on (user_id, package_id)'
print('✅ UserInterest has unique constraint for deduplication')
"
```
</verification>

<success_criteria>
1. UserInterest model has unique constraint on (user_id, package_id) for deduplication
2. UserInterest has composite index: (user_id, package_id, is_attended)
3. UserRoleChangeLog model has audit fields: previous_role, new_role, changed_by, reason, change_source, metadata
4. UserRoleChangeLog has indexes for user history and admin audit queries
5. All models use mapped_column() (SQLAlchemy 2.0 style)
6. All models have relationships defined correctly
7. Database tables can be created without errors using Base.metadata.create_all()
8. Engine properly creates all tables including new ones
</success_criteria>

<output>
After completion, create `.planning/phases/05-role-detection-database/05-02B-SUMMARY.md` with:

1. Frontmatter with phase, plan, subsystem, dependencies, tech-stack, key-files, key-decisions, patterns-established, duration, completed date
2. Summary of database models created (UserInterest, UserRoleChangeLog)
3. Schema details (indexes, constraints, relationships)
4. Any deviations from plan or discovered edge cases
5. Migration notes (how tables were created)
</output>
