---
wave: 1
depends_on: [PLAN-01, PLAN-02]
files_modified:
  - bot/handlers/user/free_flow.py
autonomous: true
estimated_minutes: 4
---

# Plan 03: Free Flow Handler - Social Media Keyboard Integration

## Goal
Update Free flow handler to use new UserFlowMessages with social media keyboard.

## Context
Plan 02 changed `free_request_success()` return type from `str` to `tuple[str, InlineKeyboardMarkup]`. This plan updates the handler to unpack the tuple and apply the keyboard.

## Tasks

### T1: Update callback_request_free() to Use Social Media Keyboard
**File:** `bot/handlers/user/free_flow.py`

**Changes:**
1. Import ConfigService (already available via container)
2. Fetch social media links
3. Unpack tuple from `free_request_success()`
4. Apply keyboard to message edit

**Updated Implementation:**
```python
@user_router.callback_query(F.data == "user:request_free")
async def callback_request_free(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Procesa solicitud de acceso al canal Free.

    Crea la solicitud y notifica al usuario con mensaje de Lucien
    y botones de redes sociales.

    Args:
        callback: Callback query
        session: Sesión de BD
    """
    user_id = callback.from_user.id
    logger.info(f"📺 Usuario {user_id} solicitando acceso Free")

    container = ServiceContainer(session, callback.bot)

    # Verificar que canal Free está configurado
    if not await container.channel.is_free_channel_configured():
        # Use provider for error message
        error_text = container.message.user.flows.free_request_error(
            error_type="channel_not_configured"
        )
        await callback.answer(
            error_text.replace("<b>", "").replace("</b>", "").replace("🎩 ", ""),
            show_alert=True
        )
        return

    # Verificar si ya tiene solicitud pendiente
    existing_request = await container.subscription.get_free_request(user_id)

    if existing_request:
        # Calcular tiempo restante (business logic stays in handler)
        from datetime import datetime, timezone

        wait_time_minutes = await container.config.get_wait_time()
        time_since_request = (datetime.now(timezone.utc) - existing_request.request_date).total_seconds() / 60
        time_elapsed_minutes = int(time_since_request)
        time_remaining_minutes = max(0, int(wait_time_minutes - time_since_request))

        # Use provider for duplicate message (text-only, no keyboard)
        duplicate_text = container.message.user.flows.free_request_duplicate(
            time_elapsed_minutes=time_elapsed_minutes,
            time_remaining_minutes=time_remaining_minutes
        )

        try:
            await callback.message.edit_text(
                duplicate_text,
                parse_mode="HTML"
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.error(f"Error editando mensaje: {e}")

        await callback.answer()
        return

    # Crear nueva solicitud
    request = await container.subscription.create_free_request(user_id)

    # Fetch social media links from config
    social_links = await container.config.get_social_media_links()

    # Use provider for success message with social media keyboard
    success_text, keyboard = container.message.user.flows.free_request_success(
        wait_time_minutes=await container.config.get_wait_time(),
        social_links=social_links
    )

    try:
        await callback.message.edit_text(
            success_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            logger.error(f"Error editando mensaje: {e}")

    await callback.answer("✅ Solicitud creada")

    logger.info(f"✅ Solicitud Free creada para user {user_id} con redes sociales")
```

**Voice Rationale:**
- Handler logic unchanged (still validates, checks duplicates, creates request)
- Only changes: fetch social_links, unpack tuple, apply keyboard
- Error message uses callback.answer() (no change needed)
- Duplicate message uses text-only format (no keyboard)

**Acceptance:**
- [ ] Fetches social_links via `container.config.get_social_media_links()`
- [ ] Unpacks tuple: `text, keyboard = container.message.user.flows.free_request_success(...)`
- [ ] Applies keyboard: `reply_markup=keyboard`
- [ ] Handles missing social_links gracefully (empty dict)
- [ ] All logging updated to mention social media

---

## Verification

### Pre-Commit Verification:
1. **Import check:** No new imports needed (ConfigService via container)
2. **Method call:** `free_request_success()` signature matches Plan 02
3. **Keyboard application:** `reply_markup` parameter used correctly

### Post-Commit Testing:
```python
# Test with social media configured
# Mock container.config.get_social_media_links() to return {'instagram': '@diana'}

# Test without social media
# Mock container.config.get_social_media_links() to return {}
# Should work with empty keyboard

# Test duplicate request
# Should still call free_request_duplicate() (text-only, no keyboard)
```

### Manual UAT:
1. **With social media:**
   - Click "Request Free Access"
   - See Lucien-voiced message
   - See 3 social media buttons (IG → TikTok → X)
   - Click button → opens Instagram/TikTok/X

2. **Without social media:**
   - Configure social fields as None in DB
   - Click "Request Free Access"
   - See Lucien-voiced message
   - No social media buttons (empty keyboard)

3. **Duplicate request:**
   - Request access twice
   - Second request shows duplicate message (no keyboard)
   - Shows elapsed/remaining time

---

## Integration Notes

**No Breaking Changes:**
- Handler logic unchanged (validation, duplicate check, request creation)
- Only message formatting changes

**Keyboard Behavior:**
- If social_links is empty dict, keyboard is empty (no buttons)
- Message still displays correctly with empty keyboard
- User can close chat and wait for approval message

**Error Handling:**
- Existing error handling for "message is not modified" preserved
- Social media fetch failures handled gracefully (empty dict)

---

## must_haves

1. ✅ Handler fetches social_links via `container.config.get_social_media_links()`
2. ✅ Handler unpacks tuple from `free_request_success(wait_time, social_links)`
3. ✅ Handler applies keyboard via `reply_markup=keyboard`
4. ✅ Duplicate request path unchanged (text-only, no keyboard)
5. ✅ Logging updated to mention "con redes sociales"
6. ✅ No new imports needed (uses container)
