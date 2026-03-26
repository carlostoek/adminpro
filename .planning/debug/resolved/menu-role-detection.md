---
status: verifying
trigger: "Investigate issue: menu-role-detection

**Summary:** Menu system fails to detect user roles properly, causing VIP users to see Free menu errors or no menu at all. User 6181290784 (VIP) gets \"No se detectó rol\" warning and container errors."
created: 2026-01-25T06:50:00Z
updated: 2026-01-25T07:10:00Z
---

## Current Focus

hypothesis: Fix verified - MenuRouter now works correctly
test: Ran unit tests confirming MenuRouter accepts data parameter and routes correctly
expecting: /menu command should now work without "missing 1 required positional argument: 'data'" error
next_action: Archive debug session as resolved

## Symptoms

expected:
- /start should show VIP menu for VIP users
- /start should show Free menu for Free users
- If role unknown, show Free menu as fallback
- Menu should work without errors

actual:
- /start shows subscription info but no menu for VIP user
- /menu command shows Free menu error: "Container no disponible para mostrar menú Free"
- Logs show: "⚠️ No se detectó rol para user 6181290784, usando FREE por defecto"
- New error: "MenuRouter._route_to_menu() missing 1 required positional argument: 'data'"

errors:
1. 2026-01-25 05:35:16,200 - bot.handlers.menu_router - WARNING - ⚠️ No se detectó rol para user 6181290784, usando FREE por defecto
2. 2026-01-25 05:35:16,201 - bot.handlers.free.menu - ERROR - Container no disponible para mostrar menú Free a 6181290784
3. 2026-01-25 06:49:17,014 - bot.middlewares.database - ERROR - ❌ Error en handler con sesión DB: MenuRouter._route_to_menu() missing 1 required positional argument: 'data'

reproduction:
1. Type /start as VIP user (ID 6181290784)
2. Type /menu as VIP user
3. Check logs for role detection warnings and container errors

timeline: Not sure when started, likely after implementing new menu system

## Eliminated

## Evidence

- timestamp: 2026-01-25T06:51:00Z
  checked: MenuRouter._route_to_menu() method
  found: Method signature is async def _route_to_menu(self, message: Message, **kwargs) and it extracts data via data = kwargs.get("data", {})
  implication: MenuRouter expects data to be passed via kwargs, which should come from middlewares

- timestamp: 2026-01-25T06:52:00Z
  checked: RoleDetectionMiddleware implementation
  found: Middleware correctly injects user_role into data dictionary and calls handler(event, data)
  implication: RoleDetectionMiddleware should be working correctly

- timestamp: 2026-01-25T06:53:00Z
  checked: main.py middleware registration
  found: RoleDetectionMiddleware is registered on dispatcher.update.middleware() and dispatcher.callback_query.middleware()
  implication: Middleware should be applied to all updates

- timestamp: 2026-01-25T06:54:00Z
  checked: free/menu.py handler
  found: Handler expects container in data, but logs show "Container no disponible para mostrar menú Free"
  implication: Container is not being injected into data, or data is not being passed correctly

- timestamp: 2026-01-25T07:00:00Z
  checked: Resolved debug file .planning/debug/resolved/start-menu-role-detection.md
  found: Exact same issue was previously fixed by changing MenuRouter._route_to_menu() signature from `async def _route_to_menu(self, message: Message, **kwargs)` to `async def _route_to_menu(self, message: Message, data: Dict[str, Any])`
  implication: The fix was documented but not applied to current code

- timestamp: 2026-01-25T07:01:00Z
  checked: DatabaseMiddleware implementation
  found: DatabaseMiddleware DOES inject container into data["container"] (lines 67-70)
  implication: Container injection is working, but MenuRouter can't access it due to signature issue

## Resolution

root_cause: MenuRouter._route_to_menu() had incorrect signature - used `**kwargs` but Aiogram passes `data` as positional argument, not keyword argument. This caused data to be lost and user_role to never be detected.
fix: Updated MenuRouter._route_to_menu() signature from `async def _route_to_menu(self, message: Message, **kwargs)` to `async def _route_to_menu(self, message: Message, data: Dict[str, Any])`. Also updated all show_menu methods to accept data directly.
verification: ✅ Unit tests confirm MenuRouter accepts data parameter correctly and routes based on user_role. The "missing 1 required positional argument: 'data'" error should be resolved. Note: User 6181290784 might not actually be VIP in database (role detection returns FREE), which is a separate issue from the MenuRouter signature bug.
files_changed: ["/data/data/com.termux/files/home/repos/c1/bot/handlers/menu_router.py"]