---
phase: 05-role-detection-database
plan: 04B
type: execute
wave: 6
depends_on: [05-04A]
files_modified:
  - bot/handlers/vip/menu.py
  - bot/handlers/free/menu.py
  - bot/handlers/__init__.py
autonomous: true

must_haves:
  truths:
    - "Usuarios VIP ven menú VIP con opciones de contenido exclusivo"
    - "Usuarios Free ven menú Free con opciones básicas y upgrade"
    - "Todos los handlers de menú son exportables desde módulo bot.handlers"
  artifacts:
    - path: "bot/handlers/vip/menu.py"
      provides: "VIP menu handlers with content access"
      contains: "async def show_vip_menu"
      min_lines: 50
    - path: "bot/handlers/free/menu.py"
      provides: "Free menu handlers with basic options"
      contains: "async def show_free_menu"
      min_lines: 50
    - path: "bot/handlers/__init__.py"
      provides: "Export of all menu handlers and MenuRouter"
      contains: "from bot.handlers.menu_router import MenuRouter"
      min_lines: 10 (new or modified)
  key_links:
    - from: "bot/handlers/vip/menu.py"
      to: "bot/services/content.py"
      via: "ContentService access for VIP content"
      pattern: "container\.content"
    - from: "bot/handlers/free/menu.py"
      to: "bot/services/subscription.py"
      via: "SubscriptionService access for Free queue info"
      pattern: "container\.subscription"
    - from: "bot/handlers/__init__.py"
      to: "bot/handlers/menu_router.py"
      via: "MenuRouter export"
      pattern: "from bot\.handlers\.menu_router import MenuRouter"
---

<objective>
Create VIP and Free menu handlers and export all menu components from bot.handlers module.

Purpose: Complete role-based menu system with personalized experiences for VIP and Free users - MENU-02 requirement
Output: Working VIP and Free menu handlers with proper exports
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
@.planning/phases/05-role-detection-database/05-04A-SUMMARY.md (MenuRouter and admin menu handler)

# Existing patterns to follow
@bot/handlers/admin/menu.py (admin menu handler pattern from 05-04A)
@bot/handlers/user/start.py (existing user handlers pattern)
@bot/utils/keyboards.py (keyboard factory)

# DatabaseMiddleware + ServiceContainer Integration
The menu handlers assume:
1. DatabaseMiddleware injects session into data["session"]
2. ServiceContainer is created with session and bot, then injected into data["container"]
3. RoleDetectionMiddleware injects user_role into data["user_role"]
4. Handlers access services via container.property (lazy loading)
</context>

<tasks>

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
# Overall Phase 5-4B Verification

## 1. Handler Structure Test
```bash
# Test all handlers have correct structure
python -c "
from bot.handlers.vip.menu import show_vip_menu
from bot.handlers.free.menu import show_free_menu
import inspect

# Verify all handlers are async
import asyncio
assert asyncio.iscoroutinefunction(show_vip_menu), 'show_vip_menu must be async'
assert asyncio.iscoroutinefunction(show_free_menu), 'show_free_menu must be async'

# Verify all have required parameters
for handler in [show_vip_menu, show_free_menu]:
    sig = inspect.signature(handler)
    params = list(sig.parameters.keys())
    assert 'message' in params, f'{handler.__name__} missing message parameter'
    assert 'data' in params, f'{handler.__name__} missing data parameter'

print('✅ VIP and Free menu handlers have correct structure')
"
```

## 2. Export Verification
```bash
# Test all exports work
python -c "
from bot.handlers import MenuRouter, show_admin_menu, show_vip_menu, show_free_menu

# Verify all are importable
assert MenuRouter is not None
assert show_admin_menu is not None
assert show_vip_menu is not None
assert show_free_menu is not None

print('✅ All menu components are exportable from bot.handlers')
"
```

## 3. Menu Content Verification
```bash
# Verify menu handlers follow patterns
python -c "
import inspect

# Check that handlers access container from data
vip_source = inspect.getsource(show_vip_menu)
free_source = inspect.getsource(show_free_menu)

assert 'container = data.get' in vip_source, 'VIP handler should access container from data'
assert 'container = data.get' in free_source, 'Free handler should access container from data'

print('✅ Menu handlers follow pattern of accessing container from data')
"
```
</verification>

<success_criteria>
1. VIP users see VIP menu with content access and subscription management
2. Free users see Free menu with free content and upgrade options
3. All handlers are async and follow existing codebase patterns
4. Handlers access container from data for service calls
5. Menu options are grouped logically with appropriate emojis
6. Welcome messages include user info and role-specific status
7. VIP menu shows subscription expiration info
8. Free menu shows queue status if user is in queue
9. All handlers are exportable from bot.handlers module
10. MenuRouter is also exportable from bot.handlers module
</success_criteria>

<output>
After completion, create `.planning/phases/05-role-detection-database/05-04B-SUMMARY.md` with:

1. Frontmatter with phase, plan, subsystem, dependencies, tech-stack, key-files, key-decisions, patterns-established, duration, completed date
2. Summary of VIP and Free menu handlers implementation
3. Export configuration for all menu components
4. Any deviations from plan or discovered edge cases
</output>
