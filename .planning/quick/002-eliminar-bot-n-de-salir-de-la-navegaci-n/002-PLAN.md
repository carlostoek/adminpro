---
phase: quick
plan: 002
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/utils/keyboards.py
  - bot/handlers/vip/callbacks.py
  - bot/handlers/free/callbacks.py
autonomous: true
user_setup: []

must_haves:
  truths:
    - "No 'Salir' button appears in any user menu (VIP or Free)"
    - "menu:exit callback handler is disabled (commented out)"
    - "Navigation only uses 'Volver' button for returning to previous menu"
    - "Main menus have no navigation buttons (only content buttons)"
  artifacts:
    - path: bot/utils/keyboards.py
      contains: "include_exit=False (default value changed)"
    - path: bot/handlers/vip/callbacks.py
      contains: "handle_menu_exit is commented out or removed"
    - path: bot/handlers/free/callbacks.py
      contains: "handle_menu_exit is commented out or removed"
  key_links:
    - from: "create_menu_navigation() default behavior"
      to: "include_exit=False"
      via: "Parameter default value change"
      pattern: "include_exit.*False"
    - from: "VIP/Free callback handlers"
      to: "Disabled menu:exit handler"
      via: "Comment out or remove handler"
      pattern: "#.*menu:exit.*commented"
---

<objective>
Eliminar botn de salir de la navegacin general del bot

Purpose: Remove the "Salir" (exit) button from all user navigation menus to simplify the user experience and reduce accidental menu closures. Users should only navigate backwards through the menu hierarchy, not close menus entirely.

Output: Navigation system without exit buttons, only back buttons for returning to previous menus. Main menus will have no navigation buttons (only content/action buttons).
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Navigation system uses:
- NavigationHelper class in bot/utils/keyboards.py (create_menu_navigation function)
- UserMenuMessages provider in bot/services/message/user_menu.py
- Callback handlers in bot/handlers/vip/callbacks.py and bot/handlers/free/callbacks.py
- Callback patterns: menu:back, menu:exit

Current behavior:
- Main menus (VIP/Free) use include_back=False, include_exit=True (default) = only "Salir" button
- Submenus use include_back=True, include_exit=True (default) = both "Volver" and "Salir" buttons
- menu:exit callback handlers delete the menu message

Target behavior:
- Main menus have NO navigation buttons (only content/action buttons)
- Submenus have ONLY "Volver" button (no "Salir")
- menu:exit callback handlers are disabled (commented out)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update create_menu_navigation default to include_exit=False</name>
  <files>bot/utils/keyboards.py</files>
  <action>
    In bot/utils/keyboards.py, modify the create_menu_navigation function:

    1. Change the default value of include_exit parameter from True to False:
       - Find: def create_menu_navigation(include_back: bool = True, include_exit: bool = True, ...
       - Change to: def create_menu_navigation(include_back: bool = True, include_exit: bool = False, ...

    2. Update the docstring to reflect the new default:
       - Find: "include_exit: Incluir botn 'Salir'"
       - Add/Update: "(default: False)" to the parameter description

    This change ensures that by default, NO exit buttons are created unless explicitly requested.
  </action>
  <verify>
    grep -n "include_exit.*False" /data/data/com.termux/files/home/repos/adminpro/bot/utils/keyboards.py
  </verify>
  <done>
    create_menu_navigation() defaults to include_exit=False, preventing "Salir" buttons from appearing unless explicitly requested
  </done>
</task>

<task type="auto">
  <name>Task 2: Disable menu:exit callback handlers in VIP and Free routers</name>
  <files>
    bot/handlers/vip/callbacks.py
    bot/handlers/free/callbacks.py
  </files>
  <action>
    For both bot/handlers/vip/callbacks.py and bot/handlers/free/callbacks.py:

    1. Find the handle_menu_exit function (handles "menu:exit" callback)
    2. Comment out the entire handler function AND its decorator:
       - Add "#" before @vip_callbacks_router.callback_query(lambda c: c.data == "menu:exit") (or @free_callbacks_router...)
       - Comment out the entire async def handle_menu_exit function body
    3. Add a comment explaining WHY it's disabled:
       "# DISABLED: Exit button removed from navigation (Quick Task 002)"

    Example format:
    ```python
    # DISABLED: Exit button removed from navigation (Quick Task 002)
    # @vip_callbacks_router.callback_query(lambda c: c.data == "menu:exit")
    # async def handle_menu_exit(callback: CallbackQuery):
    #     """Cierra el men (elimina mensaje)."""
    #     ...
    ```

    This prevents any existing "Salir" buttons from functioning if they somehow appear, and documents the architectural change.
  </action>
  <verify>
    grep -n "DISABLED.*Exit button" /data/data/com.termux/files/home/repos/adminpro/bot/handlers/vip/callbacks.py
    grep -n "DISABLED.*Exit button" /data/data/com.termux/files/home/repos/adminpro/bot/handlers/free/callbacks.py
  </verify>
  <done>
    menu:exit callback handlers are disabled and commented with explanation. Any stray exit buttons will not function.
  </done>
</task>

<task type="auto">
  <name>Task 3: Verify main menu keyboards have no navigation buttons</name>
  <files>bot/services/message/user_menu.py</files>
  <action>
    In bot/services/message/user_menu.py, verify the main menu keyboard factory methods:

    1. Check _vip_main_menu_keyboard() method:
       - Confirm it calls create_content_with_navigation with include_back=False
       - This ensures NO navigation buttons (no back, no exit)

    2. Check _free_main_menu_keyboard() method:
       - Confirm it calls create_content_with_navigation with include_back=False
       - This ensures NO navigation buttons (no back, no exit)

    3. If either method has include_back=True, change to include_back=False

    With the default include_exit=False from Task 1, main menus will have no navigation at all (content buttons only).
  </action>
  <verify>
    grep -A5 "_vip_main_menu_keyboard\|_free_main_menu_keyboard" /data/data/com.termux/files/home/repos/adminpro/bot/services/message/user_menu.py | grep "include_back"
  </verify>
  <done>
    Main menu keyboards (_vip_main_menu_keyboard and _free_main_menu_keyboard) correctly use include_back=False, resulting in no navigation buttons on main menus.
  </done>
</task>

</tasks>

<verification>
After completing all tasks:

1. Test VIP menu navigation:
   - Start bot as VIP user
   - Open main menu (should have NO navigation buttons)
   - Navigate to premium section (should have ONLY "Volver" button)
   - Click "Volver" to return to main menu

2. Test Free menu navigation:
   - Start bot as Free user
   - Open main menu (should have NO navigation buttons)
   - Navigate to content section (should have ONLY "Volver" button)
   - Click "Volver" to return to main menu

3. Verify no "Salir" buttons appear anywhere in user navigation
</verification>

<success_criteria>
- create_menu_navigation() defaults to include_exit=False
- VIP and Free menu:exit callback handlers are commented out
- Main menus display NO navigation buttons
- Submenus display ONLY "Volver" button (no "Salir")
- All user navigation works backwards through menu hierarchy
</success_criteria>

<output>
After completion, create `.planning/quick/002-eliminar-bot-n-de-salir-de-la-navegaci-n/002-SUMMARY.md`
</output>
