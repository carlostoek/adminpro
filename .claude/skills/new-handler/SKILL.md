---
name: new-handler
description: Scaffold new aiogram handler following ONDA 1 patterns with FSM and voice. Use this skill when the user asks to create a new handler, add a handler function, or scaffold bot command handlers. Generates boilerplate with proper imports, ServiceContainer DI, FSM states, and voice-appropriate message templates (Lucien 🎩 for admin, Diana 🫦 for user).
---

# new-handler

Scaffold new aiogram handlers following ONDA 1 architecture patterns.

## When to use

- User asks to "create a handler" or "add a handler"
- User wants to "scaffold" a new bot command
- User mentions implementing a new feature that needs handlers
- User needs boilerplate for Telegram bot handlers

## Arguments

- `type`: Handler category - `admin`, `user`, `vip`, or `free`
- `name`: Base name for the handler function (e.g., `manage_content`)
- `command`: Bot command name if applicable (e.g., `/manage_content`)
- `needs_fsm`: Whether handler needs FSM states - `true` or `false`
- `needs_callback`: Whether handler handles callback queries - `true` or `false`

## Output structure

### Admin Handler (Lucien voice 🎩)

```python
"""
Admin handlers for <feature_name>.

Voice: Lucien 🎩 (formal, mayordomo, third person)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.services.container import ServiceContainer
from bot.states.admin import <StateClass>
from bot.utils.keyboards import create_admin_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("<command>"))
async def <name>_handler(message: Message, state: FSMContext):
    """
    Handle /<command> for admin <feature>.

    Voice: Lucien 🎩 - Formal, mayordomo, third person (su/usted/le)
    """
    container: ServiceContainer = state.context['container']

    # TODO: Implement handler logic

    await message.answer(
        "🎩 <b>Lucien</b>:\n\n"
        "<i>Su solicitud ha sido recibida.</i>",
        parse_mode="HTML",
        reply_markup=create_admin_keyboard()
    )
    logger.info(f"Admin {message.from_user.id} accessed <feature>")
```

### User Handler (Diana voice 🫦)

```python
"""
User handlers for <feature_name>.

Voice: Diana 🫦 (direct, íntima, second person)
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.services.container import ServiceContainer
from bot.states.user import <StateClass>
from bot.utils.keyboards import create_user_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("<command>"))
async def <name>_handler(message: Message, state: FSMContext):
    """
    Handle /<command> for user <feature>.

    Voice: Diana 🫦 - Direct, íntima, second person (tú/eres/estás)
    """
    container: ServiceContainer = state.context['container']

    # TODO: Implement handler logic

    await message.answer(
        "🫦 Ya estás dentro. Aquí empieza el juego.",
        parse_mode="HTML",
        reply_markup=create_user_keyboard()
    )
    logger.info(f"User {message.from_user.id} accessed <feature>")
```

## Voice Guidelines

### Lucien (🎩) - Admin handlers
- **Tone**: Formal, mayordomo, elegant
- **Person**: Third person / usted ("su solicitud", "le informo", "usted puede")
- **Emoji**: 🎩 at start
- **HTML**: Use `<i>` for emphasis, `<b>` for titles
- **Examples**: "Su token ha sido generado.", "Permítame mostrarle..."

### Diana (🫦) - User handlers
- **Tone**: Direct, íntima, empoderadora
- **Person**: Second person tú ("tú eres", "estás aquí", "tu acceso")
- **Emoji**: 🫦 at start
- **HTML**: Minimal, conversational
- **Examples**: "Ya no estás afuera.", "Eres Kinky.", "Aquí empieza el juego."

## Error Handling Pattern

Always include try-except with proper logging:

```python
@router.message(Command("<command>"))
async def <name>_handler(message: Message, state: FSMContext):
    container: ServiceContainer = state.context['container']

    try:
        # Handler logic
        pass
    except Exception as e:
        logger.error(f"Error in <name>_handler: {e}", exc_info=True)
        await message.answer(
            "🎩 <b>Atención</b> - Ha ocurrido una perturbación...",
            parse_mode="HTML"
        )
```

## Usage

```
/new-handler type=admin name=manage_content command=manage_content needs_fsm=true
/new-handler type=user name=view_profile command=profile needs_fsm=false
```

Or answer the prompts to specify handler details.
