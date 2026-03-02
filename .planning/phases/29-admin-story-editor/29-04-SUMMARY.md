# Plan 29-04: Story Testing and Preview

## Summary

Complete admin story editor with validation display, preview mode, and menu integration.

## Metrics

| Metric | Value |
|--------|-------|
| Duration | ~5 minutes (verification) |
| Tasks | 4/4 |
| Files Modified | 3 |

## Deliverables

### Task 1: Validation Status Display ✅

**Helper Function:** `format_validation_status()` in story_management.py:42
- Returns emoji + text status: "✅ Jugable", "⚠️ Revisar", "❌ Bloqueado"
- Shows error count if any
- Displays unreachable nodes as warnings

**Integration Points:**
- Story list shows validation badges (line 182, 255)
- Story details shows validation status (line 1067)
- Publish blocked if validation fails (line 273-277)

### Task 2: Preview Mode ✅

**Handlers Implemented:**
1. `callback_story_preview()` (line 774) - Start preview mode
   - Uses NarrativeService to simulate user experience
   - Shows Diana's voice (🫦) for content
   - Displays node with choices as users see it

2. `callback_preview_choice()` (line 856) - Handle choice in preview
   - Processes choices and shows next node
   - Continues until ending or exit

3. `callback_preview_exit()` (line 944) - Exit preview mode
   - Clears preview state
   - Returns to story details

**Preview State Management:**
- Stores `preview_story_id`, `preview_current_node_id`
- Uses `StoryEditorStates.preview_mode` FSM state
- Preview progress is transient (not saved to DB)

### Task 3: Admin Menu Integration ✅

**Menu Integration:**
- "📖 Crear Historia" button in `menu.py:47`
- callback_data: "admin:stories"
- Routes to `callback_stories_menu()` handler

**Also referenced in:**
- `admin_main.py:238` - Alternative menu location

### Task 4: Keyboard Utilities ✅

**All keyboard functions implemented in `keyboards.py`:**

1. `get_story_management_keyboard()` (line 538)
   - Buttons: "Crear Historia", "Listar Historias", "Volver"

2. `get_story_list_keyboard_admin()` (line 557)
   - Paginated story list with status badges
   - "Crear Nueva" button at bottom

3. `get_story_detail_keyboard()` (line 622)
   - Buttons: Editar, Publicar/Despublicar, Preview, Ver Nodos, Eliminar
   - Publish button disabled if not valid

4. `get_node_list_keyboard()` (line 663)
   - Node list with type emoji and preview
   - "Agregar Nodo" button

5. `get_node_edit_keyboard()` (line 710)
   - Buttons: Editar Contenido, Condiciones, Recompensas, Ver Elecciones, Eliminar

6. `get_choice_list_keyboard()` (line 734)
   - Choice list with target node info
   - "Agregar Elección" button

## Files Modified

- `bot/handlers/admin/story_management.py` - Validation helpers, preview handlers
- `bot/handlers/admin/menu.py` - Admin menu integration
- `bot/utils/keyboards.py` - Keyboard utilities for story editor

## Verification Status

All ADMIN-01 through ADMIN-12 requirements satisfied:
- ✅ ADMIN-01: Create stories with metadata
- ✅ ADMIN-02: Edit story metadata
- ✅ ADMIN-03: Delete (soft) stories
- ✅ ADMIN-04: Publish/unpublish stories
- ✅ ADMIN-05: Create nodes with content
- ✅ ADMIN-06: Configure node conditions
- ✅ ADMIN-07: Attach rewards to nodes
- ✅ ADMIN-08: Create choices linking nodes
- ✅ ADMIN-09: Validation before publish
- ✅ ADMIN-10: Preview stories
- ✅ ADMIN-11: View story statistics
- ✅ ADMIN-12: List all stories with status

## Notes

This plan was verified rather than implemented from scratch, as the components
were already in place from previous development. All functionality is working
and integrated.
