# Phase 28: User Story Experience - Research

**Researched:** 2026-02-26
**Domain:** Telegram Bot UI/UX - Interactive Narrative Reading Experience
**Confidence:** HIGH (existing codebase patterns, standard aiogram practices)

---

## Summary

This phase delivers the complete user-facing story reading experience. Building on Phase 27's core narrative engine (models + services), we now implement the UI layer: handlers for story discovery, reading flow, choice selection, progress tracking, and escape hatches. The implementation follows established patterns from existing handlers (streak.py, shop.py) and integrates with the ServiceContainer for dependency injection.

**Primary recommendation:** Implement as a new handler module `bot/handlers/user/story.py` with dedicated FSM states in `bot/states/user.py`, following the Lucien/Diana voice architecture and existing keyboard patterns.

---

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiogram | 3.4.1 | Telegram Bot Framework | Async handlers, FSM, inline keyboards |
| SQLAlchemy | 2.0.25 | ORM for progress persistence | Existing pattern in all services |
| aiosqlite | 0.19.0 | Async SQLite driver | Current database stack |

### No New Dependencies Required
All functionality uses existing stack:
- **Media handling:** `bot.send_photo/video/media_group` (used in shop.py)
- **Keyboard generation:** `InlineKeyboardMarkup` (pattern in keyboards.py)
- **FSM states:** `aiogram.fsm.state.State/StatesGroup` (used in user.py states)
- **Voice messages:** LucienVoiceService + Diana manual messages (established pattern)

---

## Architecture Patterns

### Recommended Handler Structure
```
bot/handlers/user/story.py       # Main story reading handlers
bot/states/user.py               # Add StoryReadingStates
bot/utils/keyboards.py           # Add story_choice_keyboard()
```

### Pattern 1: Handler Architecture (from streak.py, shop.py)

**Router Setup:**
```python
story_router = Router(name="story")
story_router.message.middleware(DatabaseMiddleware())
story_router.callback_query.middleware(DatabaseMiddleware())
```

**Handler Signature Pattern:**
```python
@story_router.message(Command("stories"))
async def cmd_stories(
    message: Message,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """Handler with container injection via middleware."""
    user_id = message.from_user.id
    # Use container.narrative for story operations
```

**Source:** `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/user/streak.py` lines 26-31, 191-210

### Pattern 2: FSM State Design for Story Flow

**State Requirements:**
```python
class StoryReadingStates(StatesGroup):
    """
    Estados para lectura de historias.

    Flujo:
    1. browsing_stories: Usuario viendo lista de historias disponibles
    2. reading_node: Usuario leyendo un nodo con opciones visibles
    3. story_completed: Historia terminada, mostrando resumen
    4. confirm_restart: Confirmación para reiniciar historia completada
    """
    browsing_stories = State()      # NARR-04: Story list
    reading_node = State()          # NARR-05, NARR-06: Reading + choices
    story_completed = State()       # NARR-10: End reached
    confirm_restart = State()       # UX-03: Restart confirmation
```

**State Transitions:**
```
/start_story → browsing_stories (if multiple stories)
             → reading_node (if starting immediately)

reading_node → reading_node (after choice, next node)
             → story_completed (if ending node)
             → browsing_stories (if escape hatch)

story_completed → confirm_restart (if user wants replay)
                → browsing_stories (if done)

confirm_restart → reading_node (restart confirmed)
                → browsing_stories (cancelled)
```

### Pattern 3: Keyboard Generation for Story Choices

**Callback Data Format (from keyboards.py pattern):**
```python
# Format: "story:{action}:{story_id}:{choice_id}"
# Examples:
# - "story:start:123"           # Start story 123
# - "story:choice:123:456"      # Make choice 456 in story 123
# - "story:exit:123"            # Exit story 123
# - "story:restart:123"         # Restart story 123
# - "story:confirm_restart:123" # Confirm restart
```

**Keyboard Layout (max 3 per row, max 10 total - UX-05):**
```python
def get_story_choice_keyboard(
    story_id: int,
    choices: List[StoryChoice],
    show_exit: bool = True
) -> InlineKeyboardMarkup:
    """
    Generate keyboard for story choices.

    Layout:
    - Choices arranged in rows of max 3 buttons
    - Exit button always at bottom (if show_exit=True)
    """
    buttons = []

    # Choice buttons (max 3 per row)
    choice_buttons = []
    for choice in choices:
        choice_buttons.append(InlineKeyboardButton(
            text=choice.choice_text[:50],  # Telegram limit
            callback_data=f"story:choice:{story_id}:{choice.id}"
        ))

    # Arrange in rows of 3
    for i in range(0, len(choice_buttons), 3):
        buttons.append(choice_buttons[i:i+3])

    # Exit button (escape hatch - NARR-08)
    if show_exit:
        buttons.append([InlineKeyboardButton(
            text="🚪 Salir de la historia",
            callback_data=f"story:exit:{story_id}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**Source:** `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/utils/keyboards.py` lines 72-77 (reaction keyboard row pattern)

### Pattern 4: Voice Architecture Application

**Diana's Voice (🫦) - Content Nodes:**
```python
def _get_diana_header() -> str:
    """Retorna encabezado de Diana para contenido narrativo."""
    return "🫦"

def _format_node_content(node: StoryNode, progress_text: str) -> str:
    """
    Formatea contenido de nodo con voz de Diana.

    Diana es directa, íntima, empoderadora.
    Segunda persona (tú/eres/estás).
    """
    return f"""🫦

{node.content_text}

{progress_text}"""
```

**Lucien's Voice (🎩) - System Messages:**
```python
def _get_lucien_header() -> str:
    """Retorna encabezado estándar de Lucien."""
    return "🎩 <b>Lucien:</b>"

def _get_story_list_header() -> str:
    """Mensaje de lista de historias con voz de Lucien."""
    return f"""{_get_lucien_header()}

<i>Le presento las historias disponibles...</i>

<i>Seleccione una para comenzar su viaje.</i>"""

def _get_upsell_message() -> str:
    """Mensaje de upsell para contenido Premium (TIER-04)."""
    return f"""{_get_lucien_header()}

<i>Esta historia es exclusiva de nuestro círculo Premium.</i>

💎 <b>Acceso restringido</b>

<i>Si desea acceder a este contenido, considere unirse a nuestra membresía VIP.</i>"""
```

**Source:** `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/user/streak.py` lines 37-40, 57-63 (Lucien voice pattern)

### Pattern 5: Progress Tracking and Display

**Progress Indicator (UX-01):**
```python
def format_progress_indicator(
    current_node: StoryNode,
    total_nodes: int
) -> str:
    """
    Formatea indicador de progreso.

    Example: "Escena 3 de 12"
    """
    # order_index is 0-based, display as 1-based
    current = current_node.order_index + 1
    return f"📖 Escena {current} de {total_nodes}"
```

**Completion Status Badges (UX-02):**
```python
def get_story_status_badge(progress: Optional[UserStoryProgress]) -> str:
    """
    Retorna badge de estado para lista de historias.

    Badges:
    - 📖 Nuevo (no progress)
    - 🔴 En progreso (ACTIVE)
    - ⏸️ Pausada (PAUSED)
    - ✅ Completada (COMPLETED)
    """
    if not progress:
        return "📖"
    return progress.status.emoji  # Using StoryProgressStatus.emoji property
```

### Pattern 6: Media Handling Approach

**Media Display (from shop.py deliver_purchased_content):**
```python
async def display_node_media(
    message: Message,
    node: StoryNode,
    caption: str
) -> None:
    """
    Muestra media asociada a un nodo.

    Supports:
    - Single photo: send_photo
    - Multiple photos: send_media_group
    - Video: send_video
    """
    if not node.media_file_ids:
        return

    file_ids = node.media_file_ids

    if len(file_ids) == 1:
        # Single media item
        await message.answer_photo(
            photo=file_ids[0],
            caption=caption,
            parse_mode="HTML"
        )
    else:
        # Multiple photos - send as media group
        media = []
        for i, file_id in enumerate(file_ids):
            media.append(InputMediaPhoto(
                media=file_id,
                caption=caption if i == 0 else None,
                parse_mode="HTML"
            ))
        await message.answer_media_group(media=media)
```

**Source:** `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/user/shop.py` lines 1051-1121

### Pattern 7: Escape Hatch Implementation (NARR-08)

**Exit Button Pattern:**
```python
@story_router.callback_query(lambda c: c.data.startswith("story:exit:"))
async def handle_story_exit(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Handler para escape hatch - salir de historia.

    Actions:
    1. Abandon story via narrative service
    2. Clear FSM state
    3. Return to main menu
    """
    user_id = callback.from_user.id
    story_id = int(callback.data.split(":")[2])

    # Get progress and abandon
    progress = await container.narrative.get_story_progress(user_id, story_id)
    if progress:
        await container.narrative.abandon_story(user_id, progress)

    # Clear FSM state
    await state.clear()

    # Return to main menu (using existing menu handler)
    await callback.message.edit_text(
        text=_get_exit_message(),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("Has salido de la historia")
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress persistence | Custom JSON files | UserStoryProgress model + NarrativeService | ACID transactions, existing pattern |
| State management | Global variables | aiogram FSMContext | Built-in, Redis-ready |
| Keyboard layout | Manual button math | keyboards.py patterns | Consistent UX |
| Media sending | File download/upload | Telegram file_ids | Efficient, cached |
| Voice selection | If/else in handlers | Voice helper functions | Maintainability |

---

## Common Pitfalls

### Pitfall 1: Message Edit vs New Message
**What goes wrong:** Editing a message with media to text-only (or vice versa) fails.

**Why it happens:** Telegram API doesn't allow changing message type in edit.

**How to avoid:**
```python
# If current message has media and new node doesn't:
await callback.message.delete()
await callback.message.answer(text=new_text, reply_markup=new_keyboard)

# If both text-only:
await callback.message.edit_text(text=new_text, reply_markup=new_keyboard)
```

### Pitfall 2: FSM State Desync with Database
**What goes wrong:** User is in `reading_node` state but database shows no active progress.

**Why it happens:** Crash between state.set_state() and database commit.

**How to avoid:**
```python
# Always verify progress exists when entering handler
progress = await container.narrative.get_story_progress(user_id, story_id)
if not progress or progress.status != StoryProgressStatus.ACTIVE:
    await state.clear()
    await message.answer("Tu progreso no está disponible. Volviendo al menú...")
    return
```

### Pitfall 3: Callback Data Length Limit
**What goes wrong:** Callback data exceeds 64 bytes, causing "data too large" error.

**Why it happens:** Story IDs + choice IDs + prefixes can be long.

**How to avoid:**
```python
# Use compact format: "s:c:123:456" instead of "story:choice:123:456"
# Or store mapping in FSM state
```

### Pitfall 4: Race Conditions on Choice Selection
**What goes wrong:** User double-clicks, processes choice twice.

**Why it happens:** No debouncing on callback handlers.

**How to avoid:**
```python
# Set state to intermediate before processing
await state.set_state(StoryReadingStates.processing_choice)

# Process choice
success, msg, node, progress = await container.narrative.make_choice(...)

# Return to reading state
await state.set_state(StoryReadingStates.reading_node)
```

---

## Code Examples

### Full Handler: Start Story Reading
```python
@story_router.callback_query(lambda c: c.data.startswith("story:start:"))
async def handle_start_story(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Inicia o reanuda una historia.

    NARR-04: User can start available story
    NARR-07: Resume from where left off
    """
    user_id = callback.from_user.id
    story_id = int(callback.data.split(":")[2])

    # Check if already has progress
    existing = await container.narrative.get_story_progress(user_id, story_id)

    if existing and existing.status == StoryProgressStatus.COMPLETED:
        # UX-03: Ask for restart confirmation
        await state.set_state(StoryReadingStates.confirm_restart)
        text = _get_restart_confirmation_message()
        keyboard = get_restart_confirmation_keyboard(story_id)
        await callback.message.edit_text(text=text, reply_markup=keyboard)
        await callback.answer()
        return

    # Start or resume story
    success, msg, progress = await container.narrative.start_story(user_id, story_id)

    if not success:
        await callback.answer(f"Error: {msg}", show_alert=True)
        return

    # Get current node
    success, msg, node, choices = await container.narrative.get_current_node(progress)

    # Display node
    await state.set_state(StoryReadingStates.reading_node)
    await _display_node(callback.message, node, choices, progress, container)
    await callback.answer()
```

### Full Handler: Make Choice
```python
@story_router.callback_query(lambda c: c.data.startswith("story:choice:"))
async def handle_make_choice(
    callback: CallbackQuery,
    state: FSMContext,
    container: ServiceContainer
) -> None:
    """
    Procesa elección del usuario.

    NARR-06: Choice transitions to next node
    """
    user_id = callback.from_user.id
    parts = callback.data.split(":")
    story_id = int(parts[2])
    choice_id = int(parts[3])

    # Get progress
    progress = await container.narrative.get_story_progress(user_id, story_id)
    if not progress:
        await callback.answer("Progreso no encontrado", show_alert=True)
        return

    # Make choice
    success, msg, node, progress = await container.narrative.make_choice(
        user_id, progress, choice_id
    )

    if not success:
        await callback.answer(f"Error: {msg}", show_alert=True)
        return

    # Check if completed
    if progress.status == StoryProgressStatus.COMPLETED:
        await state.set_state(StoryReadingStates.story_completed)
        await _display_ending(callback.message, node, progress)
    else:
        # Get choices for new node
        success, msg, node, choices = await container.narrative.get_current_node(progress)
        await _display_node(callback.message, node, choices, progress, container)

    await callback.answer()
```

---

## Edge Cases and Error Handling

| Edge Case | Handling Strategy |
|-----------|-------------------|
| Story deleted while reading | Show error, return to menu, clear state |
| Node has no choices (not ending) | Log error, show "continue" button to next by order_index |
| Media file expired | Show text content with error note about media |
| User banned from bot during story | Handler catches exception, clears state |
| Concurrent sessions | FSM state per user prevents conflicts |
| Story made premium while reading | Allow completion, block restart for free users |

---

## Integration Points

### ServiceContainer Usage
```python
# Available services for story handlers:
container.narrative          # Story operations
container.role_detection     # Check VIP status for tier filtering
container.wallet            # Future: choice costs (Phase 30)
container.message           # Lucien voice messages
```

### Existing Handler Integration
```python
# Add to bot/handlers/user/__init__.py
from bot.handlers.user.story import story_router

# Register in main.py
user_router.include_router(story_router)
```

---

## State of the Art

All patterns are current as of aiogram 3.4.1 (project standard). No deprecated features identified.

---

## Open Questions

1. **Story discovery entry point:**
   - What: Command (/stories) or menu button or both?
   - Recommendation: Both - command for direct access, menu for discovery

2. **Completed story visibility:**
   - What: Show completed stories in list with replay option?
   - Recommendation: Yes, with ✅ badge and "Releer" option

3. **Progress persistence on exit:**
   - What: Save progress when user exits mid-story?
   - Recommendation: Yes, progress saved after each choice, exit just changes status to PAUSED

---

## Sources

### Primary (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/user/streak.py` - Handler patterns, Lucien voice
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/user/shop.py` - Complex flow handlers, media delivery
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/services/narrative.py` - NarrativeService API
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/utils/keyboards.py` - Keyboard patterns
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/states/user.py` - FSM state patterns

### Secondary (MEDIUM confidence)
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/database/models.py` - Story models (Story, StoryNode, StoryChoice, UserStoryProgress)
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/database/enums.py` - StoryStatus, NodeType, StoryProgressStatus
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/services/container.py` - Service injection pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all dependencies already in project
- Architecture: HIGH - follows established patterns
- Pitfalls: MEDIUM-HIGH - based on existing handler experience

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (30 days for stable stack)

---

## RESEARCH COMPLETE

**Phase:** 28 - User Story Experience
**Confidence:** HIGH

### Key Findings
1. **Zero new dependencies** - all functionality uses existing aiogram/SQLAlchemy stack
2. **Handler pattern established** - follow streak.py/shop.py patterns with ServiceContainer injection
3. **Voice architecture clear** - Diana (🫦) for content, Lucien (🎩) for system messages
4. **FSM states needed** - browsing, reading, completed, confirm_restart
5. **Keyboard constraints** - max 3 choices per row, max 10 total (UX-05)
6. **Media handling ready** - reuse shop.py deliver_purchased_content patterns
7. **Escape hatch required** - exit button on every node, calls abandon_story

### File Created
`.planning/phases/28-user-story-experience/28-RESEARCH.md`

### Ready for Planning
Research complete. Planner can now create executable plans for:
- Handler implementation (story.py)
- FSM states addition (user.py)
- Keyboard utilities (keyboards.py)
- Voice message helpers
- Integration with existing menu system
