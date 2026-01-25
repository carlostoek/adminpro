---
phase: 05-role-detection-database
plan: 04A
type: execute
wave: 5
depends_on: [05-01, 05-02A, 05-02B, 05-03]
files_modified:
  - bot/handlers/menu_router.py
  - bot/handlers/admin/menu.py
autonomous: true

must_haves:
  truths:
    - "Sistema enruta automáticamente a menú correcto basado en rol detectado"
    - "Admins ven menú Admin con herramientas de gestión"
    - "Router central maneja redirección basada en user_role inyectado"
  artifacts:
    - path: "bot/handlers/menu_router.py"
      provides: "MenuRouter class with role-based routing logic"
      exports: ["MenuRouter"]
      min_lines: 80
    - path: "bot/handlers/admin/menu.py"
      provides: "Admin menu handlers with admin-only options"
      contains: "async def show_admin_menu"
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
    - from: "bot/handlers/menu_router.py"
      to: "bot/handlers/admin/menu.py"
      via: "Delegation to admin menu handler with graceful fallback"
      pattern: "try:.*from bot\.handlers\.admin\.menu import show_admin_menu"
    - from: "bot/handlers/menu_router.py"
      to: "bot/handlers/vip/menu.py"
      via: "Delegation to VIP menu handler with graceful fallback"
      pattern: "try:.*from bot\.handlers\.vip\.menu import show_vip_menu"
    - from: "bot/handlers/menu_router.py"
      to: "bot/handlers/free/menu.py"
      via: "Delegation to Free menu handler with graceful fallback"
      pattern: "try:.*from bot\.handlers\.free\.menu import show_free_menu"
---

<objective>
Create MenuRouter for role-based routing and admin menu handler that automatically directs admin users to admin menu based on detected role.

Purpose: Provide personalized admin experience with admin-appropriate options and features - MENU-02 requirement
Output: Working menu router with admin menu handler
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
@.planning/phases/05-role-detection-database/05-02A-SUMMARY.md (Database enums)
@.planning/phases/05-role-detection-database/05-02B-SUMMARY.md (Database models)
@.planning/phases/05-role-detection-database/05-03-SUMMARY.md (ContentService)

# Existing patterns to follow
@bot/handlers/admin/main.py (existing admin handlers pattern)
@bot/handlers/user/start.py (existing user handlers pattern)
@bot/utils/keyboards.py (keyboard factory)

# DatabaseMiddleware + ServiceContainer Integration
The MenuRouter and handlers assume:
1. DatabaseMiddleware injects session into data["session"]
2. ServiceContainer is created with session and bot, then injected into data["container"]
3. RoleDetectionMiddleware injects user_role into data["user_role"]
4. Handlers access services via container.property (lazy loading)
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
        try:
            from bot.handlers.admin.menu import show_admin_menu
            await show_admin_menu(message, data)
        except ImportError:
            logger.warning("Admin menu handler not available, showing placeholder")
            await message.answer(
                "👑 *Menú de Administrador*\n\n"
                "Funcionalidad de menú admin en desarrollo.\n\n"
                "⚠️ Admin menu handler no disponible aún.",
                parse_mode="Markdown"
            )

    async def _show_vip_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú VIP.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        try:
            from bot.handlers.vip.menu import show_vip_menu
            await show_vip_menu(message, data)
        except ImportError:
            logger.warning("VIP menu handler not available, showing placeholder")
            await message.answer(
                "⭐ *Menú VIP*\n\n"
                "Funcionalidad de menú VIP en desarrollo.\n\n"
                "⚠️ VIP menu handler no disponible aún.",
                parse_mode="Markdown"
            )

    async def _show_free_menu(self, message: Message, data: Dict[str, Any]):
        """
        Muestra menú Free.

        Args:
            message: Mensaje de Telegram
            data: Data del handler (incluye container, session, etc.)
        """
        try:
            from bot.handlers.free.menu import show_free_menu
            await show_free_menu(message, data)
        except ImportError:
            logger.warning("Free menu handler not available, showing placeholder")
            await message.answer(
                "🆓 *Menú Free*\n\n"
                "Funcionalidad de menú Free en desarrollo.\n\n"
                "⚠️ Free menu handler no disponible aún.",
                parse_mode="Markdown"
            )

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
- Delegate to role-specific handlers with graceful fallback (try/except ImportError for vip/free handlers created in next plan)
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

</tasks>

<verification>
# Overall Phase 5-4A Verification

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
# Test admin handler has correct structure
python -c "
from bot.handlers.admin.menu import show_admin_menu
import inspect

# Verify handler is async
import asyncio
assert asyncio.iscoroutinefunction(show_admin_menu), 'show_admin_menu must be async'

# Verify has required parameters
sig = inspect.signature(show_admin_menu)
params = list(sig.parameters.keys())
assert 'message' in params, 'show_admin_menu missing message parameter'
assert 'data' in params, 'show_admin_menu missing data parameter'

print('✅ Admin menu handler has correct structure')
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
3. MenuRouter delegates to admin menu handler correctly
4. All handlers are async and follow existing codebase patterns
5. Handlers access container from data for service calls
6. Menu options are grouped logically with appropriate emojis
7. Welcome messages include user info and role-specific status
8. Comprehensive logging for menu display and routing decisions
</success_criteria>

<output>
After completion, create `.planning/phases/05-role-detection-database/05-04A-SUMMARY.md` with:

1. Frontmatter with phase, plan, subsystem, dependencies, tech-stack, key-files, key-decisions, patterns-established, duration, completed date
2. Summary of MenuRouter implementation and admin menu handler
3. Integration with RoleDetectionMiddleware for automatic routing
4. Any deviations from plan or discovered edge cases
</output>
