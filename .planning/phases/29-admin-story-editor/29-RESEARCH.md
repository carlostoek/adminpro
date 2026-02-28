# Phase 29: Admin Story Editor - Research

**Researched:** 2026-02-28
**Domain:** Telegram Bot Admin Interface - Story Content Management
**Confidence:** HIGH (existing codebase patterns, standard aiogram practices)

---

## Summary

This phase delivers the complete admin interface for creating, editing, validating, and publishing branching stories. The implementation builds on Phase 27's core narrative engine (StoryEditorService) and Phase 28's user-facing experience. The admin editor must integrate with the existing cascading condition system (from rewards) and support inline reward creation within the node wizard.

**Primary recommendation:** Implement as a new handler module `bot/handlers/admin/story_management.py` with dedicated FSM states in `bot/states/admin.py`, following the established wizard patterns from reward_management.py and content_set_management.py.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Editor Workflow:**
- **Entry:** Botón "Crear historia" en el menú de administración
- **Post-creation:** Wizard automático de nodos comienza inmediatamente
- **Node creation flow:**
  1. Contenido del nodo (texto/media)
  2. Configuración de condiciones de acceso (si aplica)
  3. Configuración de recompensas (si aplica)
  4. Declarar nodo final O crear elecciones obligatoriamente
- **After node completion:** Continuar al siguiente nodo automáticamente o mostrar opción de volver al panel

**Condition Configuration (Critical Integration):**
- **Timing:** Configuración de condiciones integrada en el wizard ANTES/DURANTE la creación del nodo
- **Scope:** Integración completa con sistema de condiciones existente (cascading conditions)
- **Condition types supported:** Tier, Level, Streaks, Besitos, Objects
- **UI:** Bot pregunta "¿Este nodo tiene condiciones de acceso?" → si sí, muestra sistema de condiciones existente

**Reward Configuration (Inline Creation):**
- **Timing:** Mismo wizard de nodo, sin salir del flujo
- **Existing rewards:** Bot muestra lista de recompensas disponibles para seleccionar
- **New rewards:** Opción "Crear nueva recompensa" inicia wizard inline de creación de recompensa
- **Return flow:** Al finalizar creación de recompensa, regresar automáticamente al punto del wizard de nodo
- **Trigger:** Recompensas se otorgan al llegar al nodo (entrada), no al salir

**Story Structure Visualization:**
- **Story list:** Título + cantidad de nodos + progreso de validación (ej: "✅ Jugable", "⚠️ Revisar")
- **Node list:** Lista lineal ordenada por creación cronológica
- **Connections:** No se muestran en la lista general; entras al nodo para ver sus elecciones
- **Global view:** Modo "Preview como usuario" permite probar la historia como la vería un usuario

**Validation Timing & Behavior:**
- **When:** Validación ejecuta al guardar cada nodo/elección
- **Critical errors (bloquean guardar):** Ciclos infinitos, nodos huérfanos, nodos sin elecciones no finales
- **Publishing:** No se permite publicar historias con warnings; debe estar "limpio" para publicar

**Content Input (Media):**
- **Methods:** Adjuntar archivo directamente O reenviar mensaje existente de Telegram
- **Quantity:** Un solo archivo por nodo (foto O video, no ambos)
- **Text placement:** Texto del nodo va como caption del media
- **Allowed types:** Fotos (JPG, PNG) y Videos (MP4)

**Blocked Access Experience:**
- **Message style:** Comunicación por Lucien (🎩) con tono elegante de mayordomo
- **Content:** Explica qué requisitos faltan de forma específica
- **Upsell:** Incluye opciones de upsell relevantes (ej: "Hazte VIP", "Compra en la tienda")

### Claude's Discretion
- Exacto formato de mensajes de validación (emojis, estructura)
- Cómo se visualiza el "progreso de validación" en la lista de historias
- Implementación técnica del wizard inline de recompensas (cómo se suspende/resume el flujo padre)
- Cómo se detectan ciclos en tiempo real (algoritmo específico)
- Diseño de los mensajes de Lucien para acceso bloqueado
- Orden específico de preguntas dentro del wizard de nodo

### Deferred Ideas (OUT OF SCOPE)
- **Vista de grafo/gráfica:** Representación visual de la estructura (tipo mapa mental) — pertenece a fase futura de "Editor Avanzado"
- **Exportación de estructura:** Generar imagen o texto del grafo para documentación externa — fase de analytics
- **Colaboración multi-admin:** Edición concurrente por múltiples administradores — fase de administración de equipo
- **Versionado de historias:** Guardar versiones, rollback a versiones anteriores — fase de editor avanzado
- **Analytics en tiempo real:** Ver cuántos usuarios han llegado a cada nodo mientras editas — fase de analytics
</user_constraints>

---

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiogram | 3.4.1 | Telegram Bot Framework | Async handlers, FSM, inline keyboards |
| SQLAlchemy | 2.0.25 | ORM for story persistence | Existing pattern in all services |
| aiosqlite | 0.19.0 | Async SQLite driver | Current database stack |

### No New Dependencies Required
All functionality uses existing stack:
- **Media handling:** `message.photo[-1].file_id` or `message.video.file_id` (used in content_set_management.py)
- **Keyboard generation:** `InlineKeyboardMarkup` (pattern in keyboards.py)
- **FSM states:** `aiogram.fsm.state.State/StatesGroup` (used in admin.py states)
- **Voice messages:** LucienVoiceService (established pattern for admin interfaces)
- **Condition system:** Reuse RewardCondition pattern from reward_management.py

---

## Architecture Patterns

### Recommended Handler Structure
```
bot/handlers/admin/story_management.py    # Main story editor handlers
bot/states/admin.py                        # Add StoryEditorStates
bot/utils/keyboards.py                     # Add story management keyboards
```

### Pattern 1: Handler Architecture (from reward_management.py)

**Router Setup:**
```python
story_router = Router(name="story_management")
story_router.message.middleware(DatabaseMiddleware())
story_router.callback_query.middleware(DatabaseMiddleware())
```

**Handler Signature Pattern:**
```python
@story_router.callback_query(F.data == "admin:stories")
async def callback_stories_menu(
    callback: CallbackQuery,
    session: AsyncSession
) -> None:
    """Handler with session injection via middleware."""
    container = ServiceContainer(session, callback.bot)
    # Use container.story_editor for admin operations
```

**Source:** `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/admin/reward_management.py` lines 36-46

### Pattern 2: FSM State Design for Story Editor Wizard

**State Requirements:**
```python
class StoryEditorStates(StatesGroup):
    """
    Estados para el editor de historias (admin).

    Flujo de creación de historia:
    1. waiting_for_title: Título de la historia
    2. waiting_for_description: Descripción opcional
    3. waiting_for_premium: Flag is_premium (sí/no)
    → Crear historia → Iniciar wizard de nodos automáticamente

    Flujo de creación de nodo:
    4. waiting_for_content: Contenido del nodo (texto/media)
    5. waiting_for_conditions: Configurar condiciones (sí/no → sistema existente)
    6. waiting_for_rewards: Configurar recompensas (sí/no → seleccionar/crear)
    7. waiting_for_final_decision: ¿Es nodo final? (sí/no → crear elecciones)

    Flujo de creación de elecciones:
    8. waiting_for_choice_text: Texto de la elección
    9. waiting_for_target_node: Nodo destino (existente o crear nuevo)
    10. waiting_for_cost_besitos: Costo en besitos (opcional)
    """
    # Story creation
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_premium = State()

    # Node creation
    waiting_for_content = State()
    waiting_for_node_type = State()  # START, STORY, CHOICE, ENDING
    waiting_for_conditions = State()
    waiting_for_rewards = State()
    waiting_for_final_decision = State()

    # Choice creation
    waiting_for_choice_text = State()
    waiting_for_target_node = State()
    waiting_for_cost_besitos = State()

    # Inline reward creation (checkpoint/resume pattern)
    creating_inline_reward = State()  # Special state for nested reward wizard
```

**State Transitions:**
```
admin:story:create → waiting_for_title
waiting_for_title → waiting_for_description
waiting_for_description → waiting_for_premium
waiting_for_premium → Create Story → waiting_for_content (auto-start node wizard)

waiting_for_content → waiting_for_conditions
waiting_for_conditions → waiting_for_rewards (or skip)
waiting_for_rewards → waiting_for_final_decision (or inline reward creation)
waiting_for_final_decision → [END] or waiting_for_choice_text

waiting_for_choice_text → waiting_for_target_node
waiting_for_target_node → waiting_for_cost_besitos
waiting_for_cost_besitos → Save choice → waiting_for_final_decision (ask: another choice?)
```

### Pattern 3: Inline Reward Creation (Checkpoint/Resume Pattern)

**Problem:** Need to suspend node wizard, create reward, then resume at exact same point.

**Solution - FSM Checkpoint Pattern:**
```python
@story_router.callback_query(F.data == "node:reward:create_inline")
async def callback_create_inline_reward(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Suspend node wizard and start inline reward creation."""
    # 1. Save current wizard state as checkpoint
    current_data = await state.get_data()
    await state.update_data(
        checkpoint_state="waiting_for_rewards",
        checkpoint_data=current_data,
        node_creation_context={
            "story_id": current_data.get("story_id"),
            "node_content": current_data.get("node_content"),
            "node_media": current_data.get("node_media"),
            # ... all partial node data
        }
    )

    # 2. Switch to reward creation state
    await state.set_state(RewardCreateState.waiting_for_name)
    await state.update_data(
        return_to="story_editor",
        return_callback="node:reward:created"
    )

    # 3. Show reward creation UI (reuse existing reward handlers)
    await show_reward_name_prompt(callback.message)
```

**Resume Pattern:**
```python
@story_router.callback_query(F.data == "node:reward:created")
async def callback_inline_reward_created(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Resume node wizard after reward creation."""
    data = await state.get_data()

    # 1. Get the newly created reward ID
    created_reward_id = data.get("created_reward_id")

    # 2. Restore checkpoint
    checkpoint_data = data.get("checkpoint_data", {})
    await state.update_data(**checkpoint_data)
    await state.update_data(selected_reward_id=created_reward_id)

    # 3. Return to original state
    await state.set_state(StoryEditorStates.waiting_for_rewards)

    # 4. Continue wizard
    await show_reward_selection(callback.message, state)
```

### Pattern 4: Condition Integration (Reuse RewardCondition System)

**Node conditions use same cascading logic as RewardConditions:**
```python
# In models.py - NodeCondition table (NEW - needs migration)
class NodeCondition(Base):
    """Condiciones de acceso para nodos de historia."""
    __tablename__ = "node_conditions"

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey("story_nodes.id", ondelete="CASCADE"))
    condition_type = Column(Enum(RewardConditionType))  # Reuse existing enum
    condition_value = Column(Integer, nullable=True)
    condition_group = Column(Integer, default=0)  # 0=AND, 1+=OR
```

**UI Reuse:**
```python
# Reuse same condition selection UI from reward_management.py
async def show_condition_type_selection(
    message: Message,
    state: FSMContext,
    target_type: str = "node"  # "node" or "reward"
) -> None:
    """Show condition type selection - reused for both nodes and rewards."""
    text = (
        f"🎩 <b>Configurar Condiciones de {'Nodo' if target_type == 'node' else 'Recompensa'}</b>\n\n"
        f"<b>Tipo de Condición</b>\n\n"
        f"Seleccione el tipo de condición:"
    )

    keyboard = create_inline_keyboard([
        [{"text": "📊 Nivel requerido", "callback_data": f"cond_type:LEVEL_REACHED:{target_type}"}],
        [{"text": "⭐ Tier VIP", "callback_data": f"cond_type:TIER_REQUIRED:{target_type}"}],
        [{"text": "📅 Racha de días", "callback_data": f"cond_type:STREAK_LENGTH:{target_type}"}],
        [{"text": "💰 Besitos totales", "callback_data": f"cond_type:TOTAL_POINTS:{target_type}"}],
        [{"text": "🛒 Objeto comprado", "callback_data": f"cond_type:PRODUCT_OWNED:{target_type}"}],
        [{"text": "✅ Finalizar condiciones", "callback_data": "cond:done"}],
    ])
```

### Pattern 5: Validation Integration

**StoryEditorService.validate_story() already exists:**
```python
# From story_editor.py lines 231-321
async def validate_story(self, story_id: int) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Valida la integridad de una historia antes de publicar.

    Returns:
        Tuple[bool, List[str], Dict]: (is_valid, errors, info)
    """
    # Check 1: Exactamente un nodo START
    # Check 2: Al menos un nodo ENDING
    # Check 3: Todos los nodos (excepto ENDING) tienen al menos una elección activa
    # Check 4: Verificar que todas las elecciones apuntan a nodos existentes
    # Check 5: Nodos no alcanzables desde START (warning, not error)
```

**Real-time Validation in Handlers:**
```python
async def validate_node_before_save(
    container: ServiceContainer,
    story_id: int,
    node_data: Dict
) -> Tuple[bool, List[str]]:
    """Validate node before saving - blocks save on critical errors."""
    errors = []

    # Check: Non-ending nodes must have choices or be marked as final
    if not node_data.get("is_final") and not node_data.get("choices"):
        errors.append("Los nodos no finales deben tener al menos una elección")

    # Check: Content text or media required
    if not node_data.get("content_text") and not node_data.get("media_file_ids"):
        errors.append("El nodo debe tener contenido (texto o media)")

    # Check: Cycle detection (if editing existing node)
    if node_data.get("node_id"):
        has_cycle = await check_for_cycles(
            container,
            story_id,
            node_data["node_id"],
            node_data.get("choices", [])
        )
        if has_cycle:
            errors.append("Esta configuración crearía un ciclo infinito")

    return len(errors) == 0, errors
```

### Pattern 6: Media Input Handling

**From content_set_management.py pattern:**
```python
@story_router.message(StoryEditorStates.waiting_for_content, F.photo)
async def process_node_photo(
    message: Message,
    state: FSMContext
) -> None:
    """Process photo for node content."""
    # Get largest photo size (best quality)
    photo = message.photo[-1]
    file_id = photo.file_id

    # Get caption if provided
    caption = message.caption

    # Store in state
    await state.update_data(
        media_file_ids=[file_id],
        content_text=caption,
        media_type="photo"
    )

    # Continue to next step
    await ask_conditions_question(message, state)


@story_router.message(StoryEditorStates.waiting_for_content, F.video)
async def process_node_video(
    message: Message,
    state: FSMContext
) -> None:
    """Process video for node content."""
    file_id = message.video.file_id
    caption = message.caption

    await state.update_data(
        media_file_ids=[file_id],
        content_text=caption,
        media_type="video"
    )

    await ask_conditions_question(message, state)
```

### Pattern 7: Lucien Voice for Admin Interface

**All admin messages use Lucien (🎩):**
```python
def get_story_editor_header() -> str:
    """Header for story editor messages."""
    return "🎩 <b>Editor de Historias</b>"

def get_node_wizard_prompt(step: str, data: Dict) -> str:
    """Generate wizard prompt with Lucien's voice."""
    headers = {
        "content": "🎩 <b>Nuevo Nodo</b>\n\n<i>¿Qué contenido desea mostrar?</i>\n\nEnvíe el texto o adjunte una foto/video.",
        "conditions": "🎩 <b>Condiciones de Acceso</b>\n\n<i>¿Este nodo requiere condiciones especiales?</i>",
        "rewards": "🎩 <b>Recompensas</b>\n\n<i>¿Desea otorgar una recompensa al llegar a este nodo?</i>",
        "final": "🎩 <b>Tipo de Nodo</b>\n\n<i>¿Es este un nodo final de la historia?</i>",
    }
    return headers.get(step, "🎩 <b>Editor de Historias</b>")
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Condition evaluation | Custom condition parser | Reuse RewardCondition logic | Already handles AND/OR groups, all condition types |
| Media storage | File download/upload | Telegram file_ids | Efficient, cached, no storage costs |
| Story validation | Custom graph traversal | StoryEditorService.validate_story() | Already implements cycle detection, orphan detection |
| FSM state management | Global variables | aiogram FSMContext | Built-in, Redis-ready, per-user isolation |
| Keyboard layout | Manual button math | keyboards.py create_inline_keyboard() | Consistent UX, tested patterns |
| Voice consistency | Hardcoded strings | LucienVoiceService | Single source of truth for admin voice |

---

## Common Pitfalls

### Pitfall 1: Message Edit with Media Type Change
**What goes wrong:** Editing a message with media to text-only (or vice versa) fails.

**Why it happens:** Telegram API doesn't allow changing message type in edit.

**How to avoid:**
```python
# If current message has media and new content doesn't:
await callback.message.delete()
await callback.message.answer(text=new_text, reply_markup=new_keyboard)

# If both text-only:
await callback.message.edit_text(text=new_text, reply_markup=new_keyboard)
```

### Pitfall 2: Inline Reward Creation State Loss
**What goes wrong:** User cancels reward creation, loses all node wizard progress.

**Why it happens:** No checkpoint restoration on cancellation.

**How to avoid:**
```python
@story_router.callback_query(F.data == "reward:create:cancel")
async def callback_cancel_inline_reward(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Handle cancellation - restore checkpoint."""
    data = await state.get_data()

    # Restore checkpoint if exists
    checkpoint_data = data.get("checkpoint_data")
    if checkpoint_data:
        await state.update_data(**checkpoint_data)
        await state.set_state(StoryEditorStates.waiting_for_rewards)
        await show_reward_selection(callback.message, state)
    else:
        # No checkpoint - go back to stories list
        await state.clear()
        await callback_stories_menu(callback)
```

### Pitfall 3: Concurrent Node Editing
**What goes wrong:** Two admins editing same story simultaneously, overwriting each other's changes.

**Why it happens:** No optimistic locking on story edits.

**How to avoid:**
```python
# Store updated_at timestamp in state, verify before save
async def save_node_with_version_check(
    session: AsyncSession,
    node_id: int,
    expected_updated_at: datetime,
    new_data: Dict
) -> Tuple[bool, str]:
    """Save node only if version matches."""
    result = await session.execute(
        select(StoryNode).where(
            StoryNode.id == node_id,
            StoryNode.updated_at == expected_updated_at
        )
    )
    node = result.scalar_one_or_none()

    if not node:
        return False, "La historia fue modificada por otro administrador. Recargue e intente nuevamente."

    # Apply changes...
    await session.commit()
    return True, "Guardado exitosamente"
```

### Pitfall 4: Cycle Creation During Node Linking
**What goes wrong:** Admin creates a choice that points back to an ancestor node, creating infinite loop.

**Why it happens:** No cycle detection when creating choices.

**How to avoid:**
```python
async def would_create_cycle(
    session: AsyncSession,
    source_node_id: int,
    target_node_id: int
) -> bool:
    """Check if adding this choice would create a cycle."""
    # BFS from target - if we can reach source, it's a cycle
    visited = {target_node_id}
    to_visit = [target_node_id]

    while to_visit:
        current_id = to_visit.pop(0)

        # Get choices from current node
        result = await session.execute(
            select(StoryChoice.target_node_id).where(
                StoryChoice.source_node_id == current_id,
                StoryChoice.is_active == True
            )
        )
        next_nodes = result.scalars().all()

        for next_id in next_nodes:
            if next_id == source_node_id:
                return True  # Cycle detected
            if next_id not in visited:
                visited.add(next_id)
                to_visit.append(next_id)

    return False
```

---

## Code Examples

### Full Handler: Create Story Flow
```python
@story_router.callback_query(F.data == "admin:story:create:start")
async def callback_story_create_start(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """Start story creation flow."""
    await state.set_state(StoryEditorStates.waiting_for_title)

    text = (
        "🎩 <b>Crear Nueva Historia</b>\n\n"
        "<b>Paso 1/3:</b> Título\n\n"
        "Ingrese el título de la historia:\n"
        "<i>(Máximo 200 caracteres)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "❌ Cancelar", "callback_data": "admin:stories"}],
    ])

    await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@story_router.message(StoryEditorStates.waiting_for_title)
async def process_story_title(
    message: Message,
    state: FSMContext
) -> None:
    """Process story title input."""
    title = message.text.strip()

    if not title or len(title) > 200:
        await message.answer(
            "🎩 <b>Error:</b> El título debe tener entre 1 y 200 caracteres.\n\n"
            "Intente nuevamente:"
        )
        return

    await state.update_data(title=title)
    await state.set_state(StoryEditorStates.waiting_for_description)

    text = (
        f"🎩 <b>Crear Nueva Historia</b>\n\n"
        f"<b>Título:</b> {title}\n\n"
        f"<b>Paso 2/3:</b> Descripción\n\n"
        f"Ingrese la descripción:\n"
        f"<i>(Máximo 1000 caracteres, o envíe /skip)</i>"
    )

    keyboard = create_inline_keyboard([
        [{"text": "⏭️ Saltar", "callback_data": "story:create:skip_description"}],
        [{"text": "❌ Cancelar", "callback_data": "admin:stories"}],
    ])

    await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
```

### Full Handler: Node Creation with Validation
```python
@story_router.message(StoryEditorStates.waiting_for_content)
async def process_node_content(
    message: Message,
    state: FSMContext
) -> None:
    """Process node content (text or media)."""
    content_text = None
    media_file_ids = None
    media_type = None

    if message.photo:
        media_file_ids = [message.photo[-1].file_id]
        content_text = message.caption
        media_type = "photo"
    elif message.video:
        media_file_ids = [message.video.file_id]
        content_text = message.caption
        media_type = "video"
    elif message.text:
        content_text = message.text.strip()
        if len(content_text) > 4000:
            await message.answer(
                "🎩 <b>Error:</b> El texto excede 4000 caracteres.\n\n"
                "Intente nuevamente:"
            )
            return
    else:
        await message.answer(
            "🎩 <b>Error:</b> Envíe texto, foto o video.\n\n"
            "Intente nuevamente:"
        )
        return

    # Validate: at least text or media
    if not content_text and not media_file_ids:
        await message.answer(
            "🎩 <b>Error:</b> El nodo debe tener texto o media.\n\n"
            "Intente nuevamente:"
        )
        return

    # Store and continue
    await state.update_data(
        node_content_text=content_text,
        node_media_file_ids=media_file_ids,
        node_media_type=media_type
    )

    # Ask about conditions
    await ask_conditions_question(message, state)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 27: Core models only | Phase 29: Full admin editor | Now | Admins can create stories without DB access |
| Manual SQL for story creation | Wizard-based FSM flow | Now | Reduced errors, better UX |
| Separate condition systems | Unified cascading conditions | Phase 29 | Consistent logic, less code duplication |

---

## Open Questions

1. **Product ownership condition type**
   - What we know: CONTEXT mentions "Objetos de tienda (product ownership)" as condition type
   - What's unclear: PRODUCT_OWNED condition type doesn't exist in RewardConditionType enum yet
   - Recommendation: Add PRODUCT_OWNED to RewardConditionType enum, implement check in RewardService

2. **Node-level tier_required vs conditions**
   - What we know: StoryNode has tier_required field (1-6)
   - What's unclear: Should tier be a condition (flexible) or keep as field (simple)?
   - Recommendation: Keep tier_required as field for simple cases, add LEVEL_REACHED condition for complex cases

3. **Reward trigger timing**
   - What we know: CONTEXT says "Recompensas se otorgan al llegar al nodo (entrada)"
   - What's unclear: Need NodeReward junction table or use existing reward system?
   - Recommendation: Create NodeReward table linking StoryNode to Reward, check/award in NarrativeService.get_current_node()

---

## Sources

### Primary (HIGH confidence)
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/admin/reward_management.py` - Wizard patterns, condition UI
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/services/story_editor.py` - StoryEditorService API
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/database/models.py` - Story, StoryNode, StoryChoice models
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/states/admin.py` - FSM state patterns

### Secondary (MEDIUM confidence)
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/handlers/admin/content_set_management.py` - Media handling patterns
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/services/reward.py` - Condition evaluation logic
- `/data/data/com.termux/files/home/repos/adminpro-narrativa2/bot/database/enums.py` - RewardConditionType enum

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all dependencies already in project
- Architecture: HIGH - follows established wizard patterns
- Pitfalls: MEDIUM-HIGH - based on existing handler experience

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (30 days for stable stack)

---

## RESEARCH COMPLETE

**Phase:** 29 - Admin Story Editor
**Confidence:** HIGH

### Key Findings
1. **Zero new dependencies** - all functionality uses existing aiogram/SQLAlchemy stack
2. **StoryEditorService exists** - reuse validate_story(), create_story(), create_node(), create_choice()
3. **Wizard pattern established** - follow reward_management.py 8-step FSM flow
4. **Condition system reusable** - extend RewardConditionType for PRODUCT_OWNED, reuse cascading logic
5. **Inline reward creation needs checkpoint pattern** - save/restore FSM state for nested wizards
6. **Media handling ready** - reuse content_set_management.py photo/video handlers
7. **Lucien voice for all admin** - consistent with existing admin interfaces

### File Created
`.planning/phases/29-admin-story-editor/29-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All dependencies in project |
| Architecture | HIGH | Follows reward_management.py patterns |
| Pitfalls | MEDIUM-HIGH | Based on existing handler experience |

### Open Questions
1. PRODUCT_OWNED condition type needs to be added to enum
2. NodeReward junction table needed for node-reward linking
3. Tier as field vs condition needs decision

### Ready for Planning
Research complete. Planner can now create executable plans for:
- Handler implementation (story_management.py)
- FSM states addition (admin.py)
- NodeCondition model (if not exists)
- NodeReward model for reward linking
- Integration with existing condition system
