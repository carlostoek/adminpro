# Guía de Integración - Sistema de Menús

## Overview

Esta guía proporciona instrucciones paso a paso para extender el sistema de menús del bot con nuevas opciones. Aprenderá a crear message providers, agregar botones de teclado, manejar callbacks y mantener la voz de Lucien en toda la interfaz.

**Lo que aprenderá:**

- Cómo crear un Message Provider siguiendo el patrón BaseMessageProvider
- Cómo registrar servicios en ServiceContainer
- Cómo crear handlers con routers de Aiogram
- Cómo manejar callbacks y datos de teclado
- Cómo mantener la voz de Lucien consistentemente
- Errores comunes y cómo evitarlos

**Prerrequisitos:**

- Familiaridad con Python async/await
- Conocimiento básico de Aiogram 3.x
- Comprensión de SQLAlchemy (para servicios de datos)
- Lectura previa de `docs/guia-estilo.md` (voz de Lucien)

---

## Quick Start Checklist

Resumen rápido de los pasos (tiempo estimado: 30-45 minutos):

- [ ] **Paso 1** (5 min): Definir qué hará su opción de menú
- [ ] **Paso 2** (10 min): Crear Message Provider con voz de Lucien
- [ ] **Paso 3** (5 min): Registrar en ServiceContainer
- [ ] **Paso 4** (10 min): Crear Handler con callbacks
- [ ] **Paso 5** (5 min): Conectar al menú principal y probar

---

## Paso 1: Definir Su Opción de Menú

Antes de escribir código, responda estas preguntas:

### ¿Qué debe hacer?

- ¿Mostrará una lista de elementos?
- ¿Creará o editará datos?
- ¿Ejecutará una acción específica?

**Ejemplos:**

- "Gestionar paquetes de contenido" → Lista, vista detalle, crear, editar
- "Ver estadísticas de usuarios" → Vista de datos con filtros
- "Enviar broadcast" → Flujo de creación de mensaje

### ¿Qué rol(es) pueden accederlo?

- **Solo administradores**: Use `UserRole.ADMIN` check
- **Usuarios VIP**: Verifique suscripción activa
- **Todos los usuarios**: Sin verificación de rol

### ¿Qué datos necesita?

- ¿Necesita consulta a base de datos? → Cree un Service
- ¿Solo mostrar mensajes? → Solo Message Provider
- ¿Requiere entrada del usuario? → FSM states

---

## Paso 2: Crear Message Provider

### Ubicación del Archivo

Cree el archivo en: `bot/services/message/`

Convención de nombres:

- Menús de admin: `admin_{feature}.py`
- Menús de usuario: `user_{feature}.py`
- Compartidos: `common_{feature}.py`

### Estructura Básica

```python
# bot/services/message/admin_myfeature.py
"""
Admin MyFeature Messages Provider - MyFeature management messages.

Provides messages for MyFeature management UI with Lucien's voice.
All messages maintain Lucien's sophisticated mayordomo voice from docs/guia-estilo.md.
"""
from typing import Tuple, Optional, Any
from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard


class AdminMyFeatureMessages(BaseMessageProvider):
    """
    Admin MyFeature messages provider.

    Voice Characteristics (from docs/guia-estilo.md):
    - Admin = "custodio" (custodian) or "guardián" (guardian)
    - Uses "usted", never "tú"
    - Emoji 🎩 for Lucien
    - Collaborative tone with admin

    Stateless Design:
    - No session or bot stored as instance variables
    - All context passed as method parameters
    - Returns (text, keyboard) tuples for complete UI

    Examples:
        >>> provider = AdminMyFeatureMessages()
        >>> text, kb = provider.main_menu()
        >>> '🎩' in text and 'custodio' in text.lower()
        True
    """

    def __init__(self):
        super().__init__()
        # No self.session or self.bot - causes memory leaks!

    def main_menu(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate main menu for MyFeature management.

        Returns:
            Tuple of (text, keyboard) for main menu

        Voice Rationale:
            "Mi estimado custodio" maintains elegant address to admin.
            "Permite mí guiarle" offers collaborative assistance.
            70% formal tone, 30% slightly warmer.

        Examples:
            >>> provider = AdminMyFeatureMessages()
            >>> text, kb = provider.main_menu()
            >>> 'myfeature' in text.lower() or 'gestión' in text.lower()
            True
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Ah, el custodio de los dominios de Diana...</i>"

        body = (
            f"<b>📋 Gestión de MyFeature</b>\n\n"
            f"<i>Permítame guiarle a través de las opciones disponibles "
            f"para administrar este aspecto del reino.</i>\n\n"
            f"<i>Seleccione la acción que desea realizar.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._main_menu_keyboard()
        return text, keyboard

    def list_empty(self) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate message for empty list.

        Returns:
            Tuple of (text, keyboard) when no items exist

        Voice Rationale:
            "Los registros están vacíos" uses imagery of empty records.
            Encourages creation with "primer elemento".
        """
        header = "🎩 <b>Lucien:</b>\n\n<i>Parece que no hay elementos registrados...</i>"

        body = (
            f"<b>📋 Lista Vacía</b>\n\n"
            f"<i>No se encontraron elementos en el reino.</i>\n\n"
            f"<i>Le sugiero comenzar creando el primer elemento, "
            f"custodio. El reino agradecerá su contribución.</i>"
        )

        text = self._compose(header, body)
        keyboard = self._main_menu_keyboard()
        return text, keyboard

    def item_detail(self, item: Any) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Generate detail view for a single item.

        Args:
            item: The item object to display

        Returns:
            Tuple of (text, keyboard) with item details and action buttons
        """
        # Assuming item has id, name, description attributes
        header = "🎩 <b>Lucien:</b>\n\n<i>Los detalles del elemento seleccionado...</i>"

        body = (
            f"<b>📦 Detalles del Elemento</b>\n\n"
            f"<b>📝 Nombre:</b> {item.name}\n"
            f"<b>🆔 ID:</b> {item.id}\n"
        )

        if hasattr(item, 'description') and item.description:
            body += f"\n<b>📄 Descripción:</b>\n<i>{item.description}</i>\n"

        text = self._compose(header, body)
        keyboard = self._item_detail_keyboard(item.id)
        return text, keyboard

    # ===== PRIVATE KEYBOARD FACTORY METHODS =====

    def _main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """
        Generate keyboard for main menu.

        Returns:
            InlineKeyboardMarkup with main menu options
        """
        return create_inline_keyboard([
            [{"text": "📋 Ver Elementos", "callback_data": "admin:myfeature:list"}],
            [{"text": "➕ Crear Elemento", "callback_data": "admin:myfeature:create:start"}],
            [{"text": "🔙 Volver al Menú Principal", "callback_data": "admin:main"}],
        ])

    def _item_detail_keyboard(self, item_id: int) -> InlineKeyboardMarkup:
        """
        Generate keyboard for item detail view.

        Args:
            item_id: ID of the item

        Returns:
            InlineKeyboardMarkup with action buttons
        """
        return create_inline_keyboard([
            [
                {"text": "✏️ Editar", "callback_data": f"admin:myfeature:edit:{item_id}"},
                {"text": "🚫 Desactivar", "callback_data": f"admin:myfeature:deactivate:{item_id}"}
            ],
            [{"text": "🔙 Volver", "callback_data": "admin:myfeature:list"}],
        ])
```

### Generación de Keyboards

Usar `InlineKeyboardBuilder` de aiogram o la utilidad `create_inline_keyboard`:

```python
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def _list_keyboard(self, items: list, page: int = 1) -> InlineKeyboardMarkup:
    """Genera teclado para lista con paginación."""
    builder = InlineKeyboardBuilder()

    # Botones de acción por elemento
    for item in items:
        builder.button(
            text=f"📦 {item['name']}",
            callback_data=f"admin:myfeature:view:{item['id']}"
        )

    # Botones de navegación
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"admin:myfeature:page:{page-1}")
        )
    nav_buttons.append(
        InlineKeyboardButton(text="➡️", callback_data=f"admin:myfeature:page:{page+1}")
    )
    builder.row(*nav_buttons)

    # Botones de acción
    builder.row(
        InlineKeyboardButton(text="🔙 Volver", callback_data="admin:myfeature:back"),
        InlineKeyboardButton(text="❌ Salir", callback_data="admin:menu:exit"),
    )

    return builder.as_markup()
```

### Voice Integration Guidelines

Al escribir mensajes, siga estos principios de `docs/guia-estilo.md`:

1. **Siempre hable de "usted"**, nunca tutee
2. **Use lenguaje refinado pero natural**
3. **Emoji 🎩 para Lucien** siempre presente
4. **Referencias a Diana** cuando sea apropiado
5. **Nunca use jerga técnica directa**
6. **Emplee pausas dramáticas con "..."**

**Ejemplos de transformación:**

```python
# ❌ MAL (técnico, sin voz)
"Error: Database connection failed. Please try again."

# ✅ BIEN (voz de Lucien)
"🎩 <b>Lucien:</b>\n\n<i>Hmm... algo inesperado ha ocurrido "
"con los archivos del reino. Permítame consultar con Diana "
"sobre este inconveniente.</i>"
```

---

## Paso 3: Registrar en ServiceContainer

Si su menú necesita acceso a datos (no solo mostrar mensajes), cree un Service y regístrelo.

### Crear el Service (si necesario)

```python
# bot/services/myfeature.py
"""
MyFeature Service - Business logic for MyFeature management.

Provides CRUD operations and business logic for MyFeature entities.
"""
import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import MyFeatureModel

logger = logging.getLogger(__name__)


class MyFeatureService:
    """
    Service for managing MyFeature entities.

    This service encapsulates all business logic related to MyFeature,
    including CRUD operations and validations.

    Stateless Design:
        - Receives session via constructor (not stored)
        - All methods are async
        - Returns model instances or raises exceptions

    Examples:
        >>> service = MyFeatureService(session)
        >>> items = await service.get_all()
        >>> len(items) >= 0
        True
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize service with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def get_all(self, active_only: bool = True) -> List[MyFeatureModel]:
        """
        Get all MyFeature items.

        Args:
            active_only: If True, only return active items

        Returns:
            List of MyFeatureModel instances
        """
        query = select(MyFeatureModel)

        if active_only:
            query = query.where(MyFeatureModel.is_active == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, item_id: int) -> Optional[MyFeatureModel]:
        """
        Get MyFeature item by ID.

        Args:
            item_id: ID of the item

        Returns:
            MyFeatureModel instance or None
        """
        query = select(MyFeatureModel).where(MyFeatureModel.id == item_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> MyFeatureModel:
        """
        Create new MyFeature item.

        Args:
            **kwargs: Field values for the new item

        Returns:
            Created MyFeatureModel instance
        """
        item = MyFeatureModel(**kwargs)
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)

        logger.info(f"Created MyFeature item: {item.id}")
        return item

    async def update(self, item_id: int, **kwargs) -> Optional[MyFeatureModel]:
        """
        Update MyFeature item.

        Args:
            item_id: ID of the item to update
            **kwargs: Field values to update

        Returns:
            Updated MyFeatureModel instance or None
        """
        item = await self.get_by_id(item_id)
        if not item:
            return None

        for key, value in kwargs.items():
            if hasattr(item, key):
                setattr(item, key, value)

        await self.session.commit()
        await self.session.refresh(item)

        logger.info(f"Updated MyFeature item: {item_id}")
        return item
```

### Registrar en ServiceContainer

Edite `bot/services/container.py`:

```python
# bot/services/container.py (agregar estas líneas)

class ServiceContainer:
    """... documentación existente ..."""

    # ... propiedades existentes ...

    @property
    def myfeature(self) -> "MyFeatureService":
        """
        Lazy-loaded MyFeature service.

        Returns:
            MyFeatureService instance

        Examples:
            >>> container = ServiceContainer(session, bot)
            >>> items = await container.myfeature.get_all()
            >>> isinstance(items, list)
            True
        """
        from bot.services.myfeature import MyFeatureService

        if "_myfeature" not in self._services:
            self._services["_myfeature"] = MyFeatureService(self._session)

        return self._services["_myfeature"]
```

### Actualizar Exports

Edite `bot/services/__init__.py`:

```python
# bot/services/__init__.py (agregar import)

from bot.services.myfeature import MyFeatureService

__all__ = [
    # ... exports existentes ...
    "MyFeatureService",
]
```

---

## Paso 4: Crear Handler

### Ubicación del Archivo

Cree el archivo en: `bot/handlers/admin/` (o `user/`, `vip/`, `free/`)

### Estructura Básica del Handler

```python
# bot/handlers/admin/myfeature.py
"""
MyFeature Handlers - Admin interface for managing MyFeature.

Handlers for listing, viewing, creating, and editing MyFeature items.
"""
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserRole
from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer
from bot.states.admin import MyFeatureStates  # Si usa FSM

logger = logging.getLogger(__name__)

# Router para handlers de MyFeature
myfeature_router = Router(name="admin_myfeature")

# Aplicar middleware
myfeature_router.callback_query.middleware(DatabaseMiddleware())
myfeature_router.message.middleware(DatabaseMiddleware())


# ===== MENU NAVIGATION =====

@myfeature_router.callback_query(F.data == "admin:myfeature")
async def callback_myfeature_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Show MyFeature management submenu.

    Args:
        callback: Callback query
        session: Database session (injected by middleware)
    """
    logger.debug(f"MyFeature: Usuario {callback.from_user.id} abrió menú")

    container = ServiceContainer(session, callback.bot)

    # Import message provider
    from bot.services.message.admin_myfeature import AdminMyFeatureMessages
    messages = AdminMyFeatureMessages()

    # Get message from provider
    text, keyboard = messages.main_menu()

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje de menú: {e}")

    await callback.answer()


# ===== LIST ITEMS =====

@myfeature_router.callback_query(F.data == "admin:myfeature:list")
async def callback_myfeature_list(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Show list of MyFeature items.

    Args:
        callback: Callback query
        session: Database session
    """
    logger.debug(f"MyFeature: Usuario {callback.from_user.id} listando elementos")

    container = ServiceContainer(session, callback.bot)
    from bot.services.message.admin_myfeature import AdminMyFeatureMessages
    messages = AdminMyFeatureMessages()

    # Get items using service
    items = await container.myfeature.get_all()

    # Check if empty
    if not items:
        text, keyboard = messages.list_empty()
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editando mensaje lista vacía: {e}")

        await callback.answer()
        return

    # Format list (simple version - use Paginator for production)
    header = "🎩 <b>Lucien:</b>\n\n<i>Los elementos del reino, custodio...</i>"

    body = "<b>📋 Elementos Disponibles</b>\n\n"

    for item in items:
        body += f"<b>🆔 {item.id}:</b> {item.name}\n"
        if hasattr(item, 'description') and item.description:
            desc = item.description[:50] + "..." if len(item.description) > 50 else item.description
            body += f"<i>{desc}</i>\n"
        body += "\n"

    text = f"{header}\n\n{body}"

    # Create keyboard
    from bot.utils.keyboards import create_inline_keyboard
    keyboard = create_inline_keyboard([
        [{"text": "🔙 Volver", "callback_data": "admin:myfeature"}],
    ])

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje lista: {e}")

    await callback.answer()


# ===== ITEM DETAIL VIEW =====

@myfeature_router.callback_query(F.data.startswith("admin:myfeature:view:"))
async def callback_myfeature_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Show MyFeature item details.

    Args:
        callback: Callback query
        session: Database session
    """
    # Extract item_id from callback
    try:
        item_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"Callback data inválido: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    logger.debug(f"MyFeature: Usuario {callback.from_user.id} viendo elemento {item_id}")

    container = ServiceContainer(session, callback.bot)
    from bot.services.message.admin_myfeature import AdminMyFeatureMessages
    messages = AdminMyFeatureMessages()

    # Get item
    item = await container.myfeature.get_by_id(item_id)
    if not item:
        await callback.answer("❌ Elemento no encontrado", show_alert=True)
        return

    # Get detail view
    text, keyboard = messages.item_detail(item)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje detalle: {e}")

    await callback.answer()
```

### Patrones de Callback Data

Use un formato consistente para los datos de callback:

```
Formato: {scope}:{feature}:{action}:{id}

Ejemplos:
- admin:myfeature:list → Listar elementos
- admin:myfeature:view:123 → Ver elemento 123
- admin:myfeature:edit:123 → Editar elemento 123
- admin:myfeature:delete:123 → Eliminar elemento 123
- admin:myfeature:create:start → Iniciar creación
```

**Parsing:**

```python
parts = callback.data.split(":")
# parts[0] = "admin" (scope)
# parts[1] = "myfeature" (feature)
# parts[2] = "view" (action)
# parts[3] = "123" (id)

try:
    item_id = int(parts[3]) if len(parts) > 3 else None
except (ValueError, IndexError):
    await callback.answer("❌ Formato inválido", show_alert=True)
    return
```

### Aplicación de Middlewares

Los middlewares se aplican al router, no a cada handler:

```python
myfeature_router.callback_query.middleware(DatabaseMiddleware())
myfeature_router.message.middleware(DatabaseMiddleware())

# Después del middleware, los handlers reciben la sesión:
@myfeature_router.callback_query(F.data == "admin:myfeature:list")
async def callback_list(callback: CallbackQuery, session: AsyncSession):
    # session está inyectada automáticamente por DatabaseMiddleware
    container = ServiceContainer(session, callback.bot)
    ...
```

---

## Paso 5: Conectar al Sistema

### Registrar Router en main.py

Agregue su router al dispatcher principal:

```python
# main.py

from bot.handlers.admin.myfeature import myfeature_router

# Registrar router
dp.include_router(myfeature_router)

# IMPORTANTE: El orden de registro importa.
# Los routers más específicos deben registrarse antes
# de los routers generales.
```

### Agregar al Menú Principal

Edite el menú principal correspondiente (admin o usuario):

```python
# bot/services/message/admin_menu.py (ejemplo)

def _main_keyboard(self) -> InlineKeyboardMarkup:
    """Genera teclado del menú principal."""
    return create_inline_keyboard([
        # ... opciones existentes ...
        [{"text": "📋 MyFeature", "callback_data": "admin:myfeature"}],
        # ... más opciones ...
    ])
```

### Probar el Flujo

1. **Inicie el bot** y acceda al menú de administrador
2. **Verifique** que el botón aparece en el menú principal
3. **Click en el botón** → debe mostrar su menú
4. **Verifique cada acción**: listar, ver detalle, crear, editar
5. **Pruebe errores**: IDs inválidos, listas vacías, etc.

---

## Ejemplo Completo: De Principio a Fin

Este ejemplo muestra cómo agregar una opción completa "Gestionar Categorías" al menú de admin.

### 1. Message Provider

```python
# bot/services/message/admin_categories.py
from typing import Tuple
from aiogram.types import InlineKeyboardMarkup

from bot.services.message.base import BaseMessageProvider
from bot.utils.keyboards import create_inline_keyboard


class AdminCategoriesMessages(BaseMessageProvider):
    """Mensajes para gestión de categorías."""

    def main_menu(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Menú principal de categorías."""
        header = "🎩 <b>Lucien:</b>\n\n<i>Las categorías que organizan el reino...</i>"

        body = (
            f"<b>📁 Gestión de Categorías</b>\n\n"
            f"<i>Desde aquí puede administrar las clasificaciones "
            f"que dan orden al contenido del reino.</i>"
        )

        text = self._compose(header, body)
        keyboard = create_inline_keyboard([
            [{"text": "📋 Ver Categorías", "callback_data": "admin:categories:list"}],
            [{"text": "➕ Crear Categoría", "callback_data": "admin:categories:create:start"}],
            [{"text": "🔙 Volver", "callback_data": "admin:main"}],
        ])
        return text, keyboard

    def list_empty(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Mensaje de lista vacía."""
        header = "🎩 <b>Lucien:</b>\n\n<i>No hay categorías registradas...</i>"

        body = (
            f"<b>📋 Sin Categorías</b>\n\n"
            f"<i>El reino necesita organización. "
            f"Le sugiero crear la primera categoría, custodio.</i>"
        )

        text = self._compose(header, body)
        keyboard = create_inline_keyboard([
            [{"text": "🔙 Volver", "callback_data": "admin:categories"}],
        ])
        return text, keyboard
```

### 2. Service (si necesario)

```python
# bot/services/categories.py
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import Category

logger = logging.getLogger(__name__)


class CategoryService:
    """Servicio para gestión de categorías."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Category]:
        """Obtener todas las categorías."""
        result = await self.session.execute(select(Category))
        return list(result.scalars().all())

    async def get_by_id(self, category_id: int):
        """Obtener categoría por ID."""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()
```

### 3. ServiceContainer

```python
# bot/services/container.py (agregar propiedad)

@property
def categories(self) -> "CategoryService":
    from bot.services.categories import CategoryService

    if "_categories" not in self._services:
        self._services["_categories"] = CategoryService(self._session)

    return self._services["_categories"]
```

### 4. Handler

```python
# bot/handlers/admin/categories.py
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.middlewares import DatabaseMiddleware
from bot.services.container import ServiceContainer

logger = logging.getLogger(__name__)

categories_router = Router(name="admin_categories")
categories_router.callback_query.middleware(DatabaseMiddleware())


@categories_router.callback_query(F.data == "admin:categories")
async def callback_categories_menu(callback: CallbackQuery, session: AsyncSession):
    """Menú de categorías."""
    container = ServiceContainer(session, callback.bot)

    from bot.services.message.admin_categories import AdminCategoriesMessages
    messages = AdminCategoriesMessages()

    text, keyboard = messages.main_menu()

    try:
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error: {e}")

    await callback.answer()


@categories_router.callback_query(F.data == "admin:categories:list")
async def callback_categories_list(callback: CallbackQuery, session: AsyncSession):
    """Lista de categorías."""
    container = ServiceContainer(session, callback.bot)
    from bot.services.message.admin_categories import AdminCategoriesMessages
    messages = AdminCategoriesMessages()

    categories = await container.categories.get_all()

    if not categories:
        text, keyboard = messages.list_empty()
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    # Format list
    header = "🎩 <b>Lucien:</b>\n\n<i>Las categorías del reino...</i>"
    body = "<b>📁 Categorías</b>\n\n"

    for cat in categories:
        body += f"• <b>{cat.name}</b>\n"

    text = f"{header}\n\n{body}"

    from bot.utils.keyboards import create_inline_keyboard
    keyboard = create_inline_keyboard([
        [{"text": "🔙 Volver", "callback_data": "admin:categories"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
```

### 5. Registro en main.py

```python
# main.py

from bot.handlers.admin.categories import categories_router

dp.include_router(categories_router)
```

### 6. Agregar al Menú Principal

```python
# bot/services/message/admin_menu.py

def _main_keyboard(self):
    return create_inline_keyboard([
        # ... opciones existentes ...
        [{"text": "📁 Categorías", "callback_data": "admin:categories"}],
        # ... más opciones ...
    ])
```

---

## Common Pitfalls

### Pitfall 1: FSM State Leaks

**Problema:** Olvidar limpiar el estado FSM después de completar un flujo.

**Síntomas:** Usuarios quedan "atascados" en estados anteriores, comportamientos inesperados.

**Solución:**

```python
# ❌ MAL - Olvidó limpiar estado
@router.callback_query(F.data == "admin:myfeature:create:confirm")
async def confirm_create(callback: CallbackQuery, state: FSMContext):
    # Crear elemento
    await container.myfeature.create(**data)
    # ⚠️ Olvidó limpiar estado!

# ✅ BIEN - Siempre limpiar estado
@router.callback_query(F.data == "admin:myfeature:create:confirm")
async def confirm_create(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    # Crear elemento
    await container.myfeature.create(**data)

    # CRÍTICO: Limpiar estado FSM
    await state.clear()

    # Mostrar mensaje de éxito
    text, keyboard = messages.create_success()
    await callback.message.edit_text(text=text, reply_markup=keyboard)
```

**Regla:** Cada handler que marca el **final** de un flujo FSM debe llamar `await state.clear()`.

---

### Pitfall 2: Missing callback.answer()

**Problema:** Olvidar llamar `await callback.answer()` en handlers de callback.

**Síntomas:** Botón queda "cargando" indefinidamente, callbacks lentos.

**Solución:**

```python
# ❌ MAL - Falta callback.answer()
@router.callback_query(F.data == "admin:myfeature:list")
async def callback_list(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(text="Hola")
    # ⚠️ Falta answer()

# ✅ BIEN - Siempre answer()
@router.callback_query(F.data == "admin:myfeature:list")
async def callback_list(callback: CallbackQuery, session: AsyncSession):
    await callback.message.edit_text(text="Hola")
    await callback.answer()  # Siempre!
```

**Nota:** Puede pasar texto a `answer()` para notificaciones:

```python
await callback.answer("✅ Cargado", show_alert=False)
```

---

### Pitfall 3: Non-Async Operations

**Problema:** Usar operaciones síncronas en handlers async.

**Síntomas:** Bot bloqueado, timeouts, mala experiencia de usuario.

**Solución:**

```python
# ❌ MAL - Operación síncrona en DB
@router.callback_query(F.data == "admin:myfeature:list")
async def callback_list(callback: CallbackQuery, session: AsyncSession):
    # ⚠️ session.execute() es async, pero list() es sync
    result = session.execute(select(MyFeature))  # Falta await!
    items = list(result.scalars().all())

# ✅ BIEN - Todo async
@router.callback_query(F.data == "admin:myfeature:list")
async def callback_list(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(select(MyFeature))  # Await!
    items = list(result.scalars().all())
```

**Regla:** Siempre use `await` para operaciones de BD y API.

---

### Pitfall 4: Forgotten Imports

**Problema:** Importar message providers dentro del handler (no afuera).

**Síntomas:** Imports circulares, errores de importación.

**Solución:**

```python
# ❌ MAL - Import dentro del handler
@router.callback_query(F.data == "admin:myfeature")
async def callback_menu(callback: CallbackQuery, session: AsyncSession):
    from bot.services.message.admin_myfeature import AdminMyFeatureMessages  # ⚠️
    messages = AdminMyFeatureMessages()

# ✅ BIEN - Import al principio del archivo
from bot.services.message.admin_myfeature import AdminMyFeatureMessages

@router.callback_query(F.data == "admin:myfeature")
async def callback_menu(callback: CallbackQuery, session: AsyncSession):
    messages = AdminMyFeatureMessages()
```

**Excepción:** Imports dentro de handlers solo si hay import circular real (raro).

---

### Pitfall 5: Almacenar Session/Bot en Message Provider

**Problema:** Guardar session o bot como variable de instancia en Message Provider.

**Síntomas:** Memory leaks, sesiones vencidas, comportamiento impredecible.

**Solución:**

```python
# ❌ MAL - Almacena session
class AdminMyFeatureMessages(BaseMessageProvider):
    def __init__(self, session):
        super().__init__()
        self.session = session  # ⚠️ Memory leak!

# ✅ BIEN - Stateless
class AdminMyFeatureMessages(BaseMessageProvider):
    def __init__(self):
        super().__init__()
        # No self.session ni self.bot
```

**Regla:** Message Providers son **stateless**. Todo contexto se pasa como parámetro.

---

## Testing Strategies

### Unit Testing de Message Providers

```python
# tests/test_messages/test_admin_myfeature.py
import pytest
from bot.services.message.admin_myfeature import AdminMyFeatureMessages


class TestAdminMyFeatureMessages:
    """Tests para AdminMyFeatureMessages."""

    def test_main_menu_returns_tuple(self):
        """Verifica que main_menu devuelve tupla (text, keyboard)."""
        provider = AdminMyFeatureMessages()
        text, keyboard = provider.main_menu()

        assert isinstance(text, str)
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert "🎩" in text
        assert "custodio" in text.lower() or "gestión" in text.lower()

    def test_list_empty_has_lucien_voice(self):
        """Verifica que lista vacía use voz de Lucien."""
        provider = AdminMyFeatureMessages()
        text, keyboard = provider.list_empty()

        assert "vacío" in text.lower() or "vacio" in text.lower()
        assert "🎩" in text

    @pytest.fixture
    def mock_item(self):
        """Item de prueba."""
        class MockItem:
            id = 1
            name = "Test Item"
            description = "Test description"
        return MockItem()

    def test_item_detail_includes_id(self, mock_item):
        """Verifica que detalle incluya ID del item."""
        provider = AdminMyFeatureMessages()
        text, keyboard = provider.item_detail(mock_item)

        assert "1" in text  # ID del item
        assert "Test Item" in text
```

### Testing de Handlers con Mocks

```python
# tests/test_handlers/test_admin_myfeature.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from aiogram.types import CallbackQuery, Message, User, Chat

from bot.handlers.admin.myfeature import myfeature_router


class TestMyFeatureHandlers:
    """Tests para handlers de MyFeature."""

    @pytest.fixture
    def mock_callback(self):
        """Callback query mock."""
        callback = Mock(spec=CallbackQuery)
        callback.from_user = Mock(id=12345)
        callback.message = Mock()
        callback.answer = AsyncMock()
        return callback

    @pytest.fixture
    def mock_session(self):
        """Database session mock."""
        session = Mock()
        session.execute = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_callback_menu_sends_message(self, mock_callback, mock_session):
        """Verifica que callback_menu envíe mensaje."""
        # Import handler
        from bot.handlers.admin.myfeature import callback_myfeature_menu

        # Mock ServiceContainer
        with patch('bot.handlers.admin.myfeature.ServiceContainer') as mock_container_cls:
            mock_container = Mock()
            mock_messages = Mock()
            mock_messages.main_menu = Mock(return_value=("Test text", Mock()))
            mock_container.message.admin.myfeature = mock_messages
            mock_container_cls.return_value = mock_container

            # Call handler
            await callback_myfeature_menu(mock_callback, mock_session)

            # Verify
            mock_callback.message.edit_text.assert_called_once()
            mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_list_handles_empty(self, mock_callback, mock_session):
        """Verifica manejo de lista vacía."""
        from bot.handlers.admin.myfeature import callback_myfeature_list

        with patch('bot.handlers.admin.myfeature.ServiceContainer') as mock_container_cls:
            mock_container = Mock()
            mock_container.myfeature.get_all = AsyncMock(return_value=[])
            mock_messages = Mock()
            mock_messages.list_empty = Mock(return_value=("Empty", Mock()))
            mock_container.message.admin.myfeature = mock_messages
            mock_container_cls.return_value = mock_container

            await callback_myfeature_list(mock_callback, mock_session)

            # Verify list_empty was called
            mock_messages.list_empty.assert_called_once()
```

### End-to-End Testing

```python
# tests/e2e/test_myfeature_flow.py
import pytest
from aiogram.testing import MockBot, MockUpd
from aiogram.types import Update, CallbackQuery

from bot.main import dp


class TestMyFeatureE2E:
    """Tests end-to-end para flujo de MyFeature."""

    @pytest.mark.asyncio
    async def test_full_myfeature_flow(self):
        """Prueba flujo completo: menú → lista → detalle."""
        bot = MockBot()

        # 1. Simular callback "admin:myfeature"
        update = Update(
            update_id=1,
            callback_query=CallbackQuery(
                id="test1",
                from_user=User(id=123, is_bot=False, first_name="Test"),
                data="admin:myfeature",
                message=Mock(message_id=1)
            )
        )

        await dp.feed_update(bot, update)

        # Verificar que se envió mensaje
        assert bot.send_message.called or bot.edit_message_text.called

        # 2. Simular callback "admin:myfeature:list"
        update = Update(
            update_id=2,
            callback_query=CallbackQuery(
                id="test2",
                from_user=User(id=123, is_bot=False, first_name="Test"),
                data="admin:myfeature:list",
                message=Mock(message_id=1)
            )
        )

        await dp.feed_update(bot, update)

        # Verificar respuesta
        assert bot.answer_callback_query.called
```

---

## Best Practices

### 1. Voice Consistency

**Siempre** mantenga la voz de Lucien en todos los mensajes:

```python
# ✅ Voz consistente
text = self._compose(
    "🎩 <b>Lucien:</b>\n\n<i>Sus datos están listos, custodio...</i>",
    body
)

# ❌ Sin voz
text = "<b>Sus datos:</b>\n\nAquí están los datos."
```

### 2. Keyboard Organization

Organice botones lógicamente:

```python
# ✅ Buena organización
keyboard = create_inline_keyboard([
    # Botones principales
    [{"text": "📋 Ver", "callback_data": "..."}, {"text": "➕ Crear", "callback_data": "..."}],
    # Botones secundarios
    [{"text": "✏️ Editar", "callback_data": "..."}],
    # Navegación (siempre al final)
    [{"text": "🔙 Volver", "callback_data": "..."}, {"text": "❌ Salir", "callback_data": "..."}],
])
```

### 3. Error Handling

Siempre maneje errores en handlers:

```python
@router.callback_query(F.data.startswith("admin:myfeature:view:"))
async def callback_view(callback: CallbackQuery, session: AsyncSession):
    try:
        item_id = int(callback.data.split(":")[-1])
    except (ValueError, IndexError):
        logger.warning(f"Invalid callback data: {callback.data}")
        await callback.answer("❌ ID inválido", show_alert=True)
        return

    item = await container.myfeature.get_by_id(item_id)
    if not item:
        await callback.answer("❌ No encontrado", show_alert=True)
        return

    # ... rest of handler
```

### 4. Logging

Use logging apropiado:

```python
import logging

logger = logging.getLogger(__name__)

@router.callback_query(F.data == "admin:myfeature:list")
async def callback_list(callback: CallbackQuery, session: AsyncSession):
    logger.debug(f"MyFeature: User {callback.from_user.id} listing items")
    # ... handler code
    logger.info(f"MyFeature: Listed {len(items)} items for user {callback.from_user.id}")
```

### 5. Type Hints

Siempre use type hints:

```python
# ✅ Con type hints
async def callback_view(
    callback: CallbackQuery,
    session: AsyncSession
) -> None:
    ...

# ❌ Sin type hints
async def callback_view(callback, session):
    ...
```

---

## Summary

Esta guía cubre el proceso completo para agregar opciones de menú al sistema:

1. **Definir** qué hará la opción
2. **Crear Message Provider** con voz de Lucien
3. **Registrar Service** (si necesita datos)
4. **Crear Handler** con callbacks
5. **Conectar al sistema** y probar

**Recuerde:**

- Message Providers son **stateless**
- Siempre llame `await callback.answer()`
- Limpie estados FSM con `await state.clear()`
- Mantenga la voz de Lucien en todos los mensajes
- Use type hints y logging apropiados

Para más detalles sobre arquitectura, consulte `docs/ARCHITECTURE.md`.
Para más detalles sobre la voz de Lucien, consulte `docs/guia-estilo.md`.
