---
phase: 05-role-detection-database
plan: 02A
type: execute
wave: 2
depends_on: []
files_modified:
  - bot/database/enums.py
  - bot/database/models.py
autonomous: true

must_haves:
  truths:
    - "Sistema puede almacenar paquetes de contenido con categorías (FREE/VIP/PREMIUM)"
    - "Paquetes tienen precios con precisión decimal (para moneda)"
    - "Admin puede filtrar paquetes por categoría y estado activo rápidamente"
  artifacts:
    - path: "bot/database/enums.py"
      provides: "ContentCategory, PackageType, RoleChangeReason enums"
      exports: ["ContentCategory", "PackageType", "RoleChangeReason"]
      min_lines: 60
    - path: "bot/database/models.py"
      provides: "ContentPackage SQLAlchemy model"
      contains: "class ContentPackage"
      min_lines: 100 (new code)
  key_links:
    - from: "bot/database/models.py (ContentPackage)"
      to: "bot/database/enums.py"
      via: "ContentCategory and PackageType enums"
      pattern: "Enum\(ContentCategory\)"
    - from: "bot/database/models.py (ContentPackage)"
      to: "bot/database/models.py (UserInterest)"
      via: "SQLAlchemy relationship for future UserInterest model"
      pattern: "relationship\([\"']UserInterest[\"']"
---

<objective>
Create database enums (ContentCategory, PackageType, RoleChangeReason) and ContentPackage model with proper indexes, relationships, and constraints following existing SQLAlchemy 2.0 async patterns.

Purpose: Enable content package storage system - CONTENT-01 requirement
Output: Working database enums and ContentPackage model ready for table creation
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
</context>

<tasks>

<task type="auto">
  <name>Add content and role change enums to enums.py</name>
  <files>bot/database/enums.py</files>
  <action>
Modify bot/database/enums.py to add ContentCategory, PackageType, and RoleChangeReason enums:

**IMPORTANT:** UserRole enum already exists in the file (line 9). DO NOT recreate it. Only add the new enums after the existing UserRole class.

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

</tasks>

<verification>
# Overall Phase 5-2A Verification

## 1. Model Structure Verification
```bash
# Test ContentPackage model is properly defined
python -c "
from bot.database.models import ContentPackage
from bot.database.enums import ContentCategory, PackageType
from bot.database.engine import get_session
import asyncio

async def verify_model():
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

asyncio.run(verify_model())
"
```

## 2. Price Field Type Verification
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
3. All models use mapped_column() (SQLAlchemy 2.0 style)
4. Price field uses Numeric(10, 2) not Float (precision for currency)
5. ContentCategory, PackageType, and RoleChangeReason enums exist with display_name properties
</success_criteria>

<output>
After completion, create `.planning/phases/05-role-detection-database/05-02A-SUMMARY.md` with:

1. Frontmatter with phase, plan, subsystem, dependencies, tech-stack, key-files, key-decisions, patterns-established, duration, completed date
2. Summary of database enums and ContentPackage model created
3. Schema details (indexes, constraints, relationships)
4. Any deviations from plan or discovered edge cases
</output>
