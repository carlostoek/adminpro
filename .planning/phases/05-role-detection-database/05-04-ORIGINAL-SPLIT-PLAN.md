---
phase: 05-role-detection-database
plan: 04
type: execute
wave: 4
depends_on: [05-01, 05-02, 05-03]
files_modified:
  - bot/handlers/menu_router.py
  - bot/handlers/__init__.py
  - bot/handlers/admin/menu.py
  - bot/handlers/vip/menu.py
  - bot/handlers/free/menu.py
autonomous: true

must_haves:
  truths:
    - "Sistema enruta automáticamente a menú correcto basado en rol detectado"
    - "Usuarios VIP ven menú VIP con opciones de contenido exclusivo"
    - "Usuarios Free ven menú Free con opciones básicas y upgrade"
    - "Admins ven menú Admin con herramientas de gestión"
    - "Router central maneja redirección basada en user_role inyectado"
  artifacts:
    - path: "bot/handlers/menu_router.py"
      provides: "MenuRouter class with role-based routing logic"
      exports: ["MenuRouter"]
      min_lines: 80
    - path: "bot/handlers/admin/menu.py"
      provides: "Admin menu handlers with admin-only options"
      contains: "async def admin_menu_handler"
      min_lines: 50
    - path: "bot/handlers/vip/menu.py"
      provides: "VIP menu handlers with content access"
      contains: "async def vip_menu_handler"
      min_lines: 50
    - path: "bot/handlers/free/menu.py"
      provides: "Free menu handlers with basic options"
      contains: "async def free_menu_handler"
      min_lines: 50
  key_links:
    - from: "bot/handlers/menu_router.py"
      to: "bot/middlewares/role_detection.py"
      via: "data['user_role'] access for routing decision"
      pattern: "data\[['\"]user_role['\"]\]"
    - from: "bot/handlers/admin/menu.py"
      to: "bot/services/container.py"
      via: "ServiceContainer access for admin features"
      pattern: "container\.(subscription|channel|config)"
    - from: "bot/handlers/vip/menu.py"
      to: "bot/services/content.py"
      via: "ContentService access for VIP content"
      pattern: "container\.content"
---

<objective>
Create role-based menu routing system that automatically directs users to appropriate menu based on detected role (Admin, VIP, Free) - MENU-02 requirement.

Purpose: Provide personalized user experience with role-appropriate options and features
Output: Working menu router with three role-specific menu handlers
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
@.planning/phases/05-role-detection-database/05-01-SUMMARY.md (RoleDetectionService, RoleDetectionMiddleware)
@.planning/phases/05-role-detection-database/05-02-SUMMARY.md (Database models)
@.planning/phases/05-role-detection-database/05-03-SUMMARY.md (ContentService)

# Existing patterns to follow
@bot/handlers/admin/main.py (existing admin handlers pattern)
@bot/handlers/user/start.py (existing user handlers pattern)
@bot/utils/keyboards.py (keyboard factory)
</context>

<tasks>

<task type="auto">
  <name>Create MenuRouter for role-based routing</name>
  <files>bot/handlers/menu_router.py</files>
  <action>
Create bot/handlers/menu_router.py with MenuRouter class:

```python
"""
Menu Router - Enruta automáticamente a menú basado en rol detectado.

Responsabilidades:
- Detectar rol del usuario desde data["user_role"] (inyectado por RoleDetectionMiddleware)
- Redirigir a handler apropiado (admin, vip, free)
- Manejar casos edge (rol no detectado, fallback a free)
- Logging de routing decisions

Pattern: Router central que delega a handlers específicos por rol
"""
import logging
from typing import Dict, Any

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message

from bot.database.enums import UserRole

logger = logging.getLogger(__name__)


class MenuRouter:
    """
    Router central para menús basados en rol.

    Uso:
        menu_router = MenuRouter()
        menu_router.register_routes(dp)

    Flujo:
        1. Usuario ejecuta /menu
        2. RoleDetectionMiddleware inyecta user_role en data
        3. MenuRouter detecta rol y redirige a handler apropiado
        4. Handler muestra menú específico para ese rol
    """

    def __init__(self):
        """Inicializa el router."""
        self.router = Router()
        self._setup_routes()
        logger.debug("✅ MenuRouter inicializado")

    def _setup_routes(self):
        """Configura las rutas del router."""
        # /menu command - main entry point
        self.router.message.register(self._route_to_menu, Command("menu"))

    async def _route_to_menu(self, message: Message, **kwargs):
        """
        Handler principal que enruta a menú basado en rol.

        Args:
            message: Mensaje de Telegram
            **kwargs: Data del handler (incluye user_role inyectado por middleware)

        Flujo:
            1. Obtener user_role de kwargs["data"] (inyectado por RoleDetectionMiddleware)
            2. Redirigir a handler apropiado según rol
            3. Fallback a menú Free si rol no detectado
        """
        data = kwargs.get("data", {})
        user_role = data.get("user_role")

        if user_role is None:
            logger.warning(f"⚠️ No se detectó rol para user {message.from_user.id}, usando FREE por defecto")
            user_role = UserRole.FREE

        # Routing basado en rol
        if user_role == UserRole.ADMIN:
            await self._show_admin_menu(message, data)
        elif user_role == UserRole.VIP:
            await self._show_vip_menu(message, data)
        else:  # FREE o cualquier otro
            await self._show_free_menu(message, data)

    async def _show_admin_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú de administrador.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        from bot.handlers.admin.menu import show_admin_menu
        await show_admin_menu(message, data)

    async def _show_vip_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú VIP.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        from bot.handlers.vip.menu import show_vip_menu
        await show_vip_menu(message, data)

    async def _show_free_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú Free.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        from bot.handlers.free.menu import show_free_menu
        await show_free_menu(message, data)

    def register_routes(self, dispatcher):
        """
        Registra las rutas en el dispatcher.

        Args:
            dispatcher: Dispatcher de Aiogram
        """
        dispatcher.include_router(self.router)
        logger.info("✅ MenuRouter registrado en dispatcher")
```

Key requirements:
- Follow existing router patterns in codebase
- Use data["user_role"] injected by RoleDetectionMiddleware
- Implement fallback to FREE menu if role not detected
- Add comprehensive logging for routing decisions
- Delegate to role-specific handlers (to be created in other tasks)
- Type hints for all parameters
- Google Style docstrings
  </action>
  <verify>
# Check MenuRouter structure
python -c "
from bot.handlers.menu_router import MenuRouter
import inspect

# Verify class exists
assert MenuRouter is not None

# Verify methods exist
methods = ['_route_to_menu', '_show_admin_menu', '_show_vip_menu', '_show_free_menu', 'register_routes']
for m in methods:
    assert hasattr(MenuRouter, m), f'Missing method: {m}'

# Verify router attribute exists
router = MenuRouter()
assert hasattr(router, 'router'), 'Missing router attribute'
assert router.router is not None

print('✅ MenuRouter structure verified')
"
  </verify>
  <done>
MenuRouter exists with role-based routing logic and delegation to role-specific handlers
  </done>
</task>

<task type="auto">
  <name>Create admin menu handler</name>
  <files>bot/handlers/admin/menu.py</files>
  <action>
Create bot/handlers/admin/menu.py with admin menu handler:

```python
"""
Admin Menu Handler - Menú específico para administradores.

Opciones:
- Gestión de usuarios VIP (listar, agregar, eliminar)
- Gestión de contenido (crear, editar paquetes)
- Configuración del bot
- Estadísticas y reportes
"""
import logging
from typing import Dict, Any

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import UserRole

logger = logging.getLogger(__name__)


async def show_admin_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú de administrador.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Crear teclado inline con opciones de admin
    keyboard = InlineKeyboardBuilder()

    # Sección VIP Management
    keyboard.button(text="👑 Gestión VIP", callback_data="admin:vip_management")
    keyboard.button(text="📊 Listar VIPs", callback_data="admin:list_vips")
    keyboard.button(text="🔑 Generar Token VIP", callback_data="admin:generate_vip_token")

    # Sección Content Management
    keyboard.button(text="📦 Gestión Contenido", callback_data="admin:content_management")
    keyboard.button(text="➕ Crear Paquete", callback_data="admin:create_package")
    keyboard.button(text="📋 Listar Paquetes", callback_data="admin:list_packages")

    # Sección Configuración
    keyboard.button(text="⚙️ Configuración", callback_data="admin:config")
    keyboard.button(text="📈 Estadísticas", callback_data="admin:stats")

    # Sección Free Queue
    keyboard.button(text="🆓 Cola Free", callback_data="admin:free_queue")
    keyboard.button(text="✅ Procesar Free", callback_data="admin:process_free")

    # Ajustar layout (3 columnas)
    keyboard.adjust(3, 3, 2, 2)

    # Mensaje de bienvenida
    welcome_text = (
        f"👑 *Menú de Administrador*\n\n"
        f"Hola, {user.first_name}!\n"
        f"ID: `{user.id}`\n"
        f"Rol: {UserRole.ADMIN.value.upper()}\n\n"
        f"*Opciones disponibles:*\n"
        f"• Gestión de usuarios VIP\n"
        f"• Gestión de contenido\n"
        f"• Configuración del bot\n"
        f"• Estadísticas y reportes\n\n"
        f"Selecciona una opción:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    logger.info(f"👑 Menú admin mostrado a {user.id} (@{user.username or 'sin username'})")
```

Key requirements:
- Follow existing admin handler patterns (bot/handlers/admin/main.py)
- Use InlineKeyboardBuilder for interactive menu
- Group options logically (VIP, Content, Config, Free)
- Use emojis for visual clarity
- Include user info in welcome message
- Access container from data for future service calls
- Add comprehensive logging
- Type hints for all parameters
- Google Style docstrings
  </action>
  <verify>
# Check admin menu handler
python -c "
from bot.handlers.admin.menu import show_admin_menu
import inspect

# Verify function exists
assert show_admin_menu is not None

# Verify it's async
import asyncio
assert asyncio.iscoroutinefunction(show_admin_menu), 'show_admin_menu must be async'

# Verify signature
sig = inspect.signature(show_admin_menu)
params = list(sig.parameters.keys())
assert 'message' in params, 'Missing message parameter'
assert 'data' in params, 'Missing data parameter'

print('✅ Admin menu handler verified')
"
  </verify>
  <done>
Admin menu handler exists with VIP/content/config options following existing patterns
  </done>
</task>

<task type="auto">
  <name>Create VIP menu handler</name>
  <files>bot/handlers/vip/menu.py</files>
  <action>
Create bot/handlers/vip/menu.py with VIP menu handler:

```python
"""
VIP Menu Handler - Menú específico para usuarios VIP.

Opciones:
- Acceso a contenido VIP
- Gestión de suscripción
- Historial de contenido
- Invitar amigos (referral)
"""
import logging
from typing import Dict, Any

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import UserRole, ContentCategory

logger = logging.getLogger(__name__)


async def show_vip_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú VIP.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Obtener información de suscripción VIP
    vip_info = ""
    if container:
        try:
            subscriber = await container.subscription.get_vip_subscriber(user.id)
            if subscriber:
                from datetime import datetime
                expires_str = subscriber.expires_at.strftime("%d/%m/%Y %H:%M") if subscriber.expires_at else "No expira"
                vip_info = f"📅 *Expira:* {expires_str}\n"
        except Exception as e:
            logger.error(f"Error obteniendo info VIP para {user.id}: {e}")

    # Crear teclado inline con opciones VIP
    keyboard = InlineKeyboardBuilder()

    # Sección Contenido VIP
    keyboard.button(text="⭐ Contenido VIP", callback_data="vip:content_vip")
    keyboard.button(text="💎 VIP Premium", callback_data="vip:content_premium")
    keyboard.button(text="📚 Biblioteca", callback_data="vip:library")

    # Sección Suscripción
    keyboard.button(text="📅 Mi Suscripción", callback_data="vip:subscription")
    keyboard.button(text="🔄 Extender VIP", callback_data="vip:extend")
    keyboard.button(text="👥 Invitar Amigos", callback_data="vip:invite")

    # Sección Intereses
    keyboard.button(text="❤️ Mis Intereses", callback_data="vip:interests")
    keyboard.button(text="🔔 Notificaciones", callback_data="vip:notifications")

    # Ajustar layout (3 columnas)
    keyboard.adjust(3, 3, 2)

    # Mensaje de bienvenida
    welcome_text = (
        f"⭐ *Menú VIP*\n\n"
        f"Hola, {user.first_name}!\n"
        f"ID: `{user.id}`\n"
        f"Rol: {UserRole.VIP.value.upper()}\n\n"
        f"{vip_info}"
        f"*Opciones disponibles:*\n"
        f"• Acceso a contenido VIP exclusivo\n"
        f"• Gestión de tu suscripción\n"
        f"• Invitar amigos y ganar beneficios\n"
        f"• Biblioteca de contenido descargado\n\n"
        f"Selecciona una opción:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    logger.info(f"⭐ Menú VIP mostrado a {user.id} (@{user.username or 'sin username'})")
```

Key requirements:
- Follow existing user handler patterns (bot/handlers/user/start.py)
- Show VIP subscription info (expiration date)
- Group options logically (Content, Subscription, Interests)
- Use emojis for visual clarity
- Include subscription status in welcome message
- Access container from data for service calls
- Add comprehensive logging
- Type hints for all parameters
- Google Style docstrings
  </action>
  <verify>
# Check VIP menu handler
python -c "
from bot.handlers.vip.menu import show_vip_menu
import inspect

# Verify function exists
assert show_vip_menu is not None

# Verify it's async
import asyncio
assert asyncio.iscoroutinefunction(show_vip_menu), 'show_vip_menu must be async'

# Verify signature
sig = inspect.signature(show_vip_menu)
params = list(sig.parameters.keys())
assert 'message' in params, 'Missing message parameter'
assert 'data' in params, 'Missing data parameter'

print('✅ VIP menu handler verified')
"
  </verify>
  <done>
VIP menu handler exists with content access and subscription management options
  </done>
</task>

<task type="auto">
  <name>Create Free menu handler</name>
  <files>bot/handlers/free/menu.py</files>
  <action>
Create bot/handlers/free/menu.py with Free menu handler:

```python
"""
Free Menu Handler - Menú específico para usuarios Free.

Opciones:
- Contenido gratuito disponible
- Solicitar acceso a cola Free
- Información sobre beneficios VIP
- Contacto y soporte
"""
import logging
from typing import Dict, Any

from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.keyboards import create_inline_keyboard
from bot.database.enums import UserRole, ContentCategory

logger = logging.getLogger(__name__)


async def show_free_menu(message: Message, data: Dict[str, Any]):
    """
    Muestra el menú Free.

    Args:
        message: Mensaje de Telegram
        data: Data del handler (incluye container, session, etc.)
    """
    user = message.from_user
    container = data.get("container")

    # Obtener información de cola Free
    queue_info = ""
    if container:
        try:
            free_request = await container.subscription.get_free_request(user.id)
            if free_request:
                from datetime import datetime
                created_str = free_request.created_at.strftime("%d/%m/%Y %H:%M")
                queue_info = f"📋 *En cola desde:* {created_str}\n"
        except Exception as e:
            logger.error(f"Error obteniendo info Free para {user.id}: {e}")

    # Crear teclado inline con opciones Free
    keyboard = InlineKeyboardBuilder()

    # Sección Contenido Gratuito
    keyboard.button(text="🆓 Contenido Free", callback_data="free:content_free")
    keyboard.button(text="📚 Tutoriales", callback_data="free:tutorials")
    keyboard.button(text="🎁 Muestras VIP", callback_data="free:vip_samples")

    # Sección Upgrade
    keyboard.button(text="⭐ Convertirse en VIP", callback_data="free:become_vip")
    keyboard.button(text="💎 Ver Beneficios VIP", callback_data="free:vip_benefits")
    keyboard.button(text="🔑 Canjear Token", callback_data="free:redeem_token")

    # Sección Cola Free
    keyboard.button(text="📋 Solicitar Acceso Free", callback_data="free:request_access")
    keyboard.button(text="⏳ Estado de Cola", callback_data="free:queue_status")

    # Sección Ayuda
    keyboard.button(text="❓ Ayuda", callback_data="free:help")
    keyboard.button(text="📞 Contacto", callback_data="free:contact")

    # Ajustar layout (3 columnas)
    keyboard.adjust(3, 3, 2, 2)

    # Mensaje de bienvenida
    welcome_text = (
        f"🆓 *Menú Free*\n\n"
        f"Hola, {user.first_name}!\n"
        f"ID: `{user.id}`\n"
        f"Rol: {UserRole.FREE.value.upper()}\n\n"
        f"{queue_info}"
        f"*Opciones disponibles:*\n"
        f"• Contenido gratuito disponible\n"
        f"• Solicitar acceso a cola Free\n"
        f"• Información sobre beneficios VIP\n"
        f"• Tutoriales y muestras\n\n"
        f"Selecciona una opción:"
    )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard.as_markup()
    )

    logger.info(f"🆓 Menú Free mostrado a {user.id} (@{user.username or 'sin username'})")
```

Key requirements:
- Follow existing user handler patterns (bot/handlers/user/start.py)
- Show Free queue status if user is in queue
- Group options logically (Free Content, Upgrade, Queue, Help)
- Use emojis for visual clarity
- Include queue status in welcome message
- Access container from data for service calls
- Add comprehensive logging
- Type hints for all parameters
- Google Style docstrings
  </action>
  <verify>
# Check Free menu handler
python -c "
from bot.handlers.free.menu import show_free_menu
import inspect

# Verify function exists
assert show_free_menu is not None

# Verify it's async
import asyncio
assert asyncio.iscoroutinefunction(show_free_menu), 'show_free_menu must be async'

# Verify signature
sig = inspect.signature(show_free_menu)
params = list(sig.parameters.keys())
assert 'message' in params, 'Missing message parameter'
assert 'data' in params, 'Missing data parameter'

print('✅ Free menu handler verified')
"
  </verify>
  <done>
Free menu handler exists with free content, upgrade options, and queue management
  </done>
</task>

<task type="auto">
  <name>Export handlers from __init__.py</name>
  <files>bot/handlers/__init__.py</files>
  <action>
Modify bot/handlers/__init__.py to export menu handlers:

Check if __init__.py exists and has existing exports. Add:

```python
# Menu Router
from bot.handlers.menu_router import MenuRouter

# Menu Handlers
from bot.handlers.admin.menu import show_admin_menu
from bot.handlers.vip.menu import show_vip_menu
from bot.handlers.free.menu import show_free_menu
```

If __all__ exists in the file, add these to the list:
- "MenuRouter"
- "show_admin_menu"
- "show_vip_menu"
- "show_free_menu"

If __init__.py doesn't exist or is minimal, ensure the imports are present for:
```python
from bot.handlers import MenuRouter, show_admin_menu, show_vip_menu, show_free_menu
```

Key requirements:
- Follow existing export pattern in the file
- Add to __all__ if it exists
- Otherwise, import is sufficient
  </action>
  <verify>
# Verify imports work
python -c "
from bot.handlers import MenuRouter, show_admin_menu, show_vip_menu, show_free_menu

# Verify classes/functions are importable
assert MenuRouter is not None
assert show_admin_menu is not None
assert show_vip_menu is not None
assert show_free_menu is not None

print('✅ Menu handlers export verified')
"
  </verify>
  <done>
All menu handlers are exportable from bot.handlers module
  </done>
</task>

</tasks>

<verification>
# Overall Phase 5-4 Verification

## 1. Menu Router Integration Test
```bash
python -c "
import asyncio
from aiogram import Dispatcher, Bot
from aiogram.types import Message, User
from bot.handlers.menu_router import MenuRouter
from bot.database.enums import UserRole

async def test_menu_router():
    # Create mock objects
    mock_bot = Bot(token='test')
    dp = Dispatcher()

    # Create and register router
    menu_router = MenuRouter()
    menu_router.register_routes(dp)

    print('✅ MenuRouter can be registered with dispatcher')

    # Test routing logic (without actual execution)
    # This verifies the structure works

asyncio.run(test_menu_router())
"
```

## 2. Handler Structure Test
```bash
# Test all handlers have correct structure
python -c "
from bot.handlers.admin.menu import show_admin_menu
from bot.handlers.vip.menu import show_vip_menu
from bot.handlers.free.menu import show_free_menu
import inspect

# Verify all handlers are async
import asyncio
assert asyncio.iscoroutinefunction(show_admin_menu), 'show_admin_menu must be async'
assert asyncio.iscoroutinefunction(show_vip_menu), 'show_vip_menu must be async'
assert asyncio.iscoroutinefunction(show_free_menu), 'show_free_menu must be async'

# Verify all have required parameters
for handler in [show_admin_menu, show_vip_menu, show_free_menu]:
    sig = inspect.signature(handler)
    params = list(sig.parameters.keys())
    assert 'message' in params, f'{handler.__name__} missing message parameter'
    assert 'data' in params, f'{handler.__name__} missing data parameter'

print('✅ All menu handlers have correct structure')
"
```

## 3. Role-Based Routing Logic Test
```bash
# Test routing logic (simulated)
python -c "
from bot.handlers.menu_router import MenuRouter
from bot.database.enums import UserRole

# Create router instance
router = MenuRouter()

# Verify routing methods exist
assert hasattr(router, '_show_admin_menu'), 'Missing admin routing'
assert hasattr(router, '_show_vip_menu'), 'Missing VIP routing'
assert hasattr(router, '_show_free_menu'), 'Missing Free routing'

print('✅ Role-based routing methods exist')
"
```
</verification>

<success_criteria>
1. MenuRouter._route_to_menu() routes users based on data["user_role"]
2. Admin users see admin menu with VIP/content/config management options
3. VIP users see VIP menu with content access and subscription management
4. Free users see Free menu with free content and upgrade options
5. All handlers are async and follow existing codebase patterns
6. Handlers access container from data for service calls
7. Menu options are grouped logically with appropriate emojis
8. Welcome messages include user info and role-specific status
9. Comprehensive logging for menu display and routing decisions
10. All handlers are exportable from bot.handlers module
</success_criteria>

<output>
After completion, create `.planning/phases/05-role-detection-database/05-04-SUMMARY.md` with:

1. Frontmatter with phase, plan, subsystem, dependencies, tech-stack, key-files, key-decisions, patterns-established, duration, completed date
2. Summary of role-based menu routing implementation
3. Details of each menu handler (admin, vip, free)
4. Integration with RoleDetectionMiddleware for automatic routing
5. Any deviations from plan or discovered edge cases
</output>
