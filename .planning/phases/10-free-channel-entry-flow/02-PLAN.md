---
wave: 1
depends_on: [PLAN-01]
files_modified:
  - bot/services/message/user_flows.py
autonomous: true
estimated_minutes: 8
---

# Plan 02: UserFlowMessages - Lucien Voice + Social Media Keyboard

## Goal
Update UserFlowMessages with Lucien's voice, social media keyboard generation, and approval message.

## Context
Current Free entry flow uses generic messages. This plan adapts them to Lucien's voice (following `docs/guia-estilo.md`) and adds social media buttons with inline keyboard generation.

## Tasks

### T1: Update free_request_success() with Lucien Voice + Social Keyboard
**File:** `bot/services/message/user_flows.py`

**New Signature:**
```python
def free_request_success(
    self,
    wait_time_minutes: int,
    social_links: dict[str, str] = None
) -> tuple[str, InlineKeyboardMarkup]:
```

**Changes:**
1. **Header:** Change to Lucien format
2. **Body:** Remove specific wait time mention (per Phase 10 Context)
3. **Social Media CTA:** Prominent first position
4. **Keyboard:** Generate social media buttons
5. **Return type:** Change from str to tuple[str, InlineKeyboardMarkup]

**New Implementation:**
```python
def free_request_success(
    self,
    wait_time_minutes: int,
    social_links: dict[str, str] = None
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Free request success message with Lucien's voice and social media buttons.

    Args:
        wait_time_minutes: Wait time configured (NOT shown to user per Phase 10 spec)
        social_links: Dict of social media links {'instagram': '@handle', ...}

    Returns:
        Tuple of (text, keyboard) with social media buttons

    Voice Rationale:
        - Lucien header format: "🎩 <b>Lucien:</b>"
        - No specific wait time mentioned (creates mystery, reduces anxiety)
        - Social media CTA first (prominent position)
        - "Los Kinkys" channel name (not "Free channel" or "jardín")
        - References to Diana ("Diana se complace...")
        - Reassurance about automatic processing

    Examples:
        >>> flows = UserFlowMessages()
        >>> text, kb = flows.free_request_success(5, {'instagram': '@diana'})
        >>> '🎩 <b>Lucien:</b>' in text
        True
        >>> 'Los Kinkys' in text
        True
        >>> kb is not None
        True
    """
    # Header - Lucien voice
    header = "🎩 <b>Lucien:</b>"

    # Body - Welcoming arrival, no specific wait time
    body = self._compose(
        "<i>Ah, un nuevo visitante busca acceso a Los Kinkys...</i>",
        "",
        "<i>Su solicitud ha sido registrada. Diana aprecia su interés en "
        "nuestro espacio, y le aseguro que la espera valdrá la pena.</i>",
        "",
        "<i>Mientras tanto, le invito a seguir a Diana en las redes sociales. "
        "Es una excelente manera de conocer mejor el contenido que le espera...</i>"
    )

    # Footer - Reassurance
    footer = self._compose(
        "💡 <i>No necesita esperar mirando este chat. Le notificaré cuando su acceso esté listo.</i>",
        "",
        "<i>Disfrute de las redes de Diana mientras tanto. 👇</i>"
    )

    text = self._compose(header, body, footer)

    # Generate social media keyboard
    keyboard = self._social_media_keyboard(social_links or {})

    return text, keyboard
```

**Voice Rationale:**
- "Ah, un nuevo visitante..." - welcoming observation
- No "5 minutos" mentioned (per Phase 10 decision)
- "Los Kinkys" - exact channel name
- Social media buttons prominent (generated below message)
- "Le notificaré" - Lucien's service commitment

**Acceptance:**
- [ ] Header uses "🎩 <b>Lucien:</b>" format
- [ ] No specific wait time mentioned in message
- [ ] "Los Kinkys" channel name used
- [ ] Returns tuple[str, InlineKeyboardMarkup]
- [ ] Calls _social_media_keyboard() helper

---

### T2: Add _social_media_keyboard() Helper Method
**File:** `bot/services/message/user_flows.py`

**New Method:**
```python
def _social_media_keyboard(
    self,
    social_links: dict[str, str]
) -> InlineKeyboardMarkup:
    """
    Generate inline keyboard with social media buttons.

    Args:
        social_links: Dict with keys 'instagram', 'tiktok', 'x'
                      Values are handles (e.g., '@diana') or full URLs

    Returns:
        InlineKeyboardMarkup with social media buttons (clickable URLs)

    Voice Rationale:
        - Fixed order: Instagram → TikTok → X (priority)
        - Emoji + handle format: "📸 @diana_insta"
        - Links embedded in button URLs (clickable)
        - Omits None/unconfigured platforms gracefully

    Examples:
        >>> flows = UserFlowMessages()
        >>> kb = flows._social_media_keyboard({'instagram': '@diana'})
        >>> len(kb.inline_keyboard) == 1
        True
        >>> 'instagram.com' in kb.inline_keyboard[0][0].url
        True
    """
    if not social_links:
        return InlineKeyboardMarkup(inline_keyboard=[])

    # Platform order: Instagram → TikTok → X
    platform_order = ['instagram', 'tiktok', 'x']

    # Button configuration: emoji + URL template
    platform_config = {
        'instagram': {'emoji': '📸', 'url_template': 'https://instagram.com/{}'},
        'tiktok': {'emoji': '🎵', 'url_template': 'https://tiktok.com/@{}'},
        'x': {'emoji': '𝕏', 'url_template': 'https://x.com/{}'}
    }

    buttons = []

    for platform in platform_order:
        if platform not in social_links:
            continue  # Skip unconfigured platforms

        handle = social_links[platform].strip()
        if not handle:
            continue  # Skip empty handles

        # Get platform config
        config = platform_config.get(platform)
        if not config:
            continue

        # Extract handle (remove @ prefix and existing URLs)
        if handle.startswith('@'):
            handle = handle[1:]
        elif 'instagram.com/' in handle:
            handle = handle.split('instagram.com/')[-1].split('/')[0]
        elif 'tiktok.com/@' in handle:
            handle = handle.split('tiktok.com/@')[-1].split('/')[0]
        elif 'x.com/' in handle or 'twitter.com/' in handle:
            # Extract from x.com/username or twitter.com/username
            parts = handle.split('/')
            for i, part in enumerate(parts):
                if part in ['x.com', 'twitter.com']:
                    if i + 1 < len(parts):
                        handle = parts[i + 1].split('?')[0]
                        break

        # Build URL
        url = config['url_template'].format(handle)

        # Button text: emoji + @handle
        button_text = f"{config['emoji']} @{handle}"

        buttons.append([{
            'text': button_text,
            'url': url
        }])

    # Use create_inline_keyboard utility
    from bot.utils.keyboards import create_inline_keyboard
    return create_inline_keyboard(buttons)
```

**Voice Rationale:**
- Fixed order respects Phase 10 decision (IG → TikTok → X)
- Handles both "@username" and "https://instagram.com/username" formats
- Emoji mapping: 📸 Instagram, 🎵 TikTok, 𝕏 X
- URL extraction robust for various input formats

**Acceptance:**
- [ ] Method returns InlineKeyboardMarkup
- [ ] Buttons in fixed order: Instagram → TikTok → X
- [ ] Button text format: "📸 @diana_handle"
- [ ] Buttons clickable (url field set correctly)
- [ ] Skips unconfigured platforms (no empty buttons)
- [ ] Handles various input formats (@handle, full URLs)

---

### T3: Update free_request_duplicate() with Lucien Voice
**File:** `bot/services/message/user_flows.py`

**Changes:**
1. Change header to Lucien format
2. Adapt voice to Lucien (keep time display logic)

**New Implementation:**
```python
def free_request_duplicate(
    self,
    time_elapsed_minutes: int,
    time_remaining_minutes: int
) -> str:
    """
    Message when user requests Free access again (duplicate).

    Shows progress (elapsed/remaining) with Lucien's voice.

    Args:
        time_elapsed_minutes: Minutes since original request
        time_remaining_minutes: Minutes until approval

    Returns:
        HTML-formatted reminder message (text-only, no keyboard)

    Voice Rationale:
        - "Ya tiene una solicitud en proceso" - polite reminder
        - Time display helps reduce anxiety (progress indicator)
        - "Le notificaré" - Lucien's service commitment
        - Same tone as success message but with reminder context

    Examples:
        >>> flows = UserFlowMessages()
        >>> msg = flows.free_request_duplicate(10, 20)
        >>> '🎩 <b>Lucien:</b>' in msg
        True
        >>> '10 minutos' in msg and '20 minutos' in msg
        True
    """
    header = "🎩 <b>Lucien:</b>"

    body = self._compose(
        "<i>Ah, veo que su paciencia está siendo puesta a prueba...</i>",
        "",
        "<i>Su solicitud de acceso a Los Kinkys ya está en proceso. "
        f"⏱️ Tiempo transcurrido: {time_elapsed_minutes} minutos</i>",
        f"<i>⌛ Tiempo restante: {time_remaining_minutes} minutos</i>",
        "",
        "<i>Le notificaré cuando su acceso esté listo. Mientras tanto, "
        "puede cerrar este chat sin preocupación.</i>"
    )

    return self._compose(header, body)
```

**Voice Rationale:**
- "Ah, veo que su paciencia está siendo puesta a prueba..." - empathetic observation
- Time display keeps logic but uses Lucien's tone
- "Le notificaré" - reassurance

**Acceptance:**
- [ ] Header uses "🎩 <b>Lucien:</b>" format
- [ ] Shows elapsed and remaining time
- [ ] Mentions "Los Kinkys" channel name
- [ ] Returns str (no keyboard for duplicate)

---

### T4: Add free_request_approved() Method
**File:** `bot/services/message/user_flows.py`

**New Method:**
```python
def free_request_approved(
    self,
    channel_name: str,
    channel_link: str
) -> tuple[str, InlineKeyboardMarkup]:
    """
    Approval message when wait time elapses.

    Sent as NEW message (not edit) with channel access button.

    Args:
        channel_name: Name of Free channel ("Los Kinkys")
        channel_link: Invite link or public URL (t.me/loskinkys)

    Returns:
        Tuple of (text, keyboard) with channel access button

    Voice Rationale:
        - Brief + action-oriented (user has waited enough)
        - "Su acceso está listo" - clear confirmation
        - "Diana se complace" - references creator
        - Single button: "🚀 Acceder al canal" (action-oriented)

    Examples:
        >>> flows = UserFlowMessages()
        >>> text, kb = flows.free_request_approved("Los Kinkys", "t.me/loskinkys")
        >>> '🚀' in text or 'Acceder' in text
        True
        >>> kb is not None and len(kb.inline_keyboard) > 0
        True
    """
    header = "🎩 <b>Lucien:</b>"

    body = self._compose(
        "<i>Su acceso está listo. Diana se complace de su compañía...</i>",
        "",
        f"<b>Bienvenido a {channel_name}</b> 🎉",
        "",
        "<i>El enlace de invitación se encuentra a continuación. "
        "Recuerde que tiene 24 horas para usarlo.</i>"
    )

    text = self._compose(header, body)

    # Channel access button
    keyboard = create_inline_keyboard([
        [{"text": "🚀 Acceder al canal", "url": channel_link}]
    ])

    return text, keyboard
```

**Voice Rationale:**
- Brief message (user has waited long enough)
- "Diana se complace" - references creator
- "🚀 Acceder al canal" - action-oriented button
- Mention 24-hour limit (practical info)

**Acceptance:**
- [ ] Returns tuple[str, InlineKeyboardMarkup]
- [ ] Single button: "🚀 Acceder al canal" with URL
- [ ] Brief, action-oriented message
- [ ] References Diana appropriately

---

## Verification

### Pre-Commit Verification:
1. **Import test:** `from bot.services.message.user_flows import UserFlowMessages` - no errors
2. **Method signatures:** Check return types (str vs tuple)
3. **Keyboard generation:** Test with empty/partial social_links

### Post-Commit Testing:
```python
# Test success message with social media
flows = UserFlowMessages()
social_links = {
    'instagram': '@diana_official',
    'tiktok': '@diana_tiktok',
    'x': '@diana_x'
}
text, kb = flows.free_request_success(5, social_links)

assert '🎩 <b>Lucien:</b>' in text
assert 'Los Kinkys' in text
assert '5 minutos' not in text  # No specific wait time
assert len(kb.inline_keyboard) == 3  # 3 social buttons

# Test keyboard URLs
insta_button = kb.inline_keyboard[0][0]
assert '@diana_official' in insta_button.text
assert 'instagram.com' in insta_button.url

# Test approval message
text, kb = flows.free_request_approved("Los Kinkys", "https://t.me/loskinkys")
assert 'Acceder al canal' in kb.inline_keyboard[0][0].text
assert 't.me/loskinkys' in kb.inline_keyboard[0][0].url
```

---

## Integration Notes

**Breaking Changes:**
- `free_request_success()` return type: str → tuple[str, InlineKeyboardMarkup]
- Handler in `bot/handlers/user/free_flow.py` must be updated (Plan 03)

**Import Addition:**
```python
from bot.utils.keyboards import create_inline_keyboard
```

**Social Media Input Formats:**
The keyboard generator handles various input formats:
- "@diana" → extracts "diana", builds https://instagram.com/diana
- "https://instagram.com/diana" → extracts "diana", builds https://instagram.com/diana
- "https://tiktok.com/@diana_tiktok" → extracts "diana_tiktok", builds https://tiktok.com/@diana_tiktok

---

## must_haves

1. ✅ free_request_success() returns tuple[str, InlineKeyboardMarkup]
2. ✅ free_request_success() uses Lucien voice ("🎩 <b>Lucien:</b>")
3. ✅ free_request_success() does NOT mention specific wait time (e.g., "5 minutos")
4. ✅ free_request_success() calls _social_media_keyboard() with social_links
5. ✅ _social_media_keyboard() generates buttons in fixed order: IG → TikTok → X
6. ✅ _social_media_keyboard() button format: "📸 @diana_handle" with clickable URL
7. ✅ _social_media_keyboard() skips unconfigured platforms (no empty buttons)
8. ✅ free_request_duplicate() updated with Lucien voice
9. ✅ free_request_approved() returns tuple[str, InlineKeyboardMarkup] with channel button
10. ✅ All docstrings include Voice Rationale section
