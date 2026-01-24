# Pitfalls Research: Message Templating Service

**Domain:** Telegram Bot Message Service Refactoring
**Researched:** 2026-01-23
**Confidence:** HIGH

## Executive Summary

Refactoring 10+ handlers to use a centralized message service (LucienVoiceService) introduces critical risks around voice consistency, test brittleness, and template bloat. This research identifies pitfalls from real-world bot refactoring projects and message service implementations.

**Key Risk:** Message services start simple but become "message junk drawers" where every handler dumps strings without organization, leading to inconsistent voice, duplicated templates, and handlers that still contain presentation logic.

---

## Critical Pitfalls

### Pitfall 1: Hardcoded Presentation Logic Leaking into Handlers

**What goes wrong:**
Handlers continue to contain formatting logic, emoji selection, and conditional message assembly even after introducing a message service. Example:
```python
# BAD: Handler still contains presentation logic
if is_vip:
    emoji = "🟢"
    text = f"{emoji} Usuario VIP activo\n"
    text += f"Días restantes: {days}\n"
else:
    emoji = "⚪"
    text = f"{emoji} Usuario normal\n"
```

The message service becomes a simple string store instead of encapsulating voice and presentation rules.

**Why it happens:**
- Developers refactor incrementally, moving strings first but keeping formatting logic
- "Just this one dynamic part" exceptions multiply across handlers
- No clear boundary between business logic and presentation
- Existing formatters (like `bot/utils/formatters.py`) remain unused

**How to avoid:**
1. **Context-based templating:** Message service receives context objects, not assembled strings
2. **Encapsulate variation logic:** Voice service decides emoji/tone based on context, not handler
3. **Single formatting responsibility:** All HTML tags, emojis, and formatting in service layer only

```python
# GOOD: Handler passes context, service handles presentation
await message_service.send_user_status(
    context={"user_id": user_id, "is_vip": is_vip, "days_remaining": days},
    channel=message.chat.id
)
```

**Warning signs:**
- Handlers still use f-strings for messages
- Multiple `if/else` blocks in handlers for message assembly
- Emoji constants defined in handlers
- formatters.py functions called from handlers instead of service

**Phase to address:** Phase 1 (Service Foundation)

**Impact if ignored:** CRITICAL - Voice consistency impossible, refactor becomes cosmetic

---

### Pitfall 2: Template Explosion Without Hierarchy

**What goes wrong:**
Message service grows 100+ template methods without organization:
```python
# 6 months later...
class MessageService:
    def vip_welcome(self) -> str: ...
    def vip_welcome_returning(self) -> str: ...
    def vip_welcome_expired_recently(self) -> str: ...
    def vip_welcome_first_time(self) -> str: ...
    def vip_welcome_extended(self) -> str: ...
    # ... 95 more methods
```

Every edge case gets a new template method. No composition, no hierarchy, just a flat namespace of similar templates.

**Why it happens:**
- Easiest solution is "add another method"
- No template composition patterns established upfront
- Fear of breaking existing messages by refactoring
- WhatsApp's 2026 policy shift away from general-purpose bots encourages structured, business-specific templates (see [respond.io](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban)), but without proper architecture this leads to copy-paste

**How to avoid:**
1. **Template composition:** Base templates + variation layers
2. **Context-driven selection:** One method with variant logic inside
3. **Template inheritance:** YAML/JSON template files with parent/child relationships
4. **Limit by persona/context:** Group by actor (admin/vip/free) and action, not by edge cases

```python
# GOOD: Compositional approach
def user_welcome(self, context: WelcomeContext) -> str:
    base = self._base_welcome(context.user_name)

    if context.returning_vip:
        variation = self._vip_returning_variant(context.days_remaining)
    elif context.new_vip:
        variation = self._vip_first_time_variant()
    else:
        variation = self._standard_user_variant()

    return self._compose(base, variation, context.footer)
```

**Warning signs:**
- More than 30 public methods in message service
- Method names with 3+ qualifiers (`vip_token_generation_with_plan_error_retry`)
- Copy-pasted template strings with minor variations
- Developers unsure where to add new messages

**Phase to address:** Phase 2 (Template Organization)

**Impact if ignored:** HIGH - Maintenance nightmare, inconsistent voice, slow feature velocity

---

### Pitfall 3: Voice Inconsistency from Multiple Contributors

**What goes wrong:**
Lucien's personality degrades over time as different developers add messages:
- Admin panel: Formal, technical ("Configuration updated successfully")
- User flow: Casual, friendly ("¡Suscripción VIP Activada! 🎉")
- Error messages: Robotic ("Error code: INVALID_TOKEN")

No single source of truth for tone, pacing, emoji usage, or formality level.

**Why it happens:**
- Voice guide exists but isn't enforced by code
- Different developers interpret "Lucien's voice" differently
- Urgency leads to copy-paste from other handlers
- No review process for voice consistency
- Research shows "varying tone, pacing, and formality to match brand guidelines" is a known challenge requiring systematic approaches (see [Danish Lead Co.](https://danishleadco.io/blog?p=brand-voice-consistency-in-ai-b2b-outreach-2026-guide))

**How to avoid:**
1. **Voice rules as code:** Automated linting for emoji usage, sentence length, formality markers
2. **Message templates with voice annotations:** Each template tagged with intended tone/emotion
3. **Single voice author:** One person reviews all message PRs for voice consistency
4. **Examples in code:** Every template method includes voice rationale in docstring

```python
def token_generation_success(self, plan_name: str, deep_link: str) -> str:
    """
    VOICE: Celebratory but professional. User accomplished something valuable.
    TONE: Warm congratulations without being overly casual.
    EMOJI: Moderate (1-2 per section). 🎟️ for token, 🔗 for link.
    LENGTH: Medium. Include clear next steps.
    """
    return f"""🎟️ <b>Token VIP Generado</b>

<b>Plan:</b> {plan_name}
<b>Link:</b> <code>{deep_link}</code>

El link expira en 24 horas. Envíalo al usuario para activar su suscripción."""
```

**Warning signs:**
- Comments like "not sure what tone to use here"
- Same event type uses different emojis across messages
- Sentence length varies wildly (3 words vs 40 words)
- Users comment on "bot feels different today"
- Failed PRs with feedback "this doesn't sound like Lucien"

**Phase to address:** Phase 1 (Service Foundation) + Ongoing

**Impact if ignored:** CRITICAL - Brand identity erosion, user confusion

---

### Pitfall 4: Test Brittleness from String Matching

**What goes wrong:**
100+ tests break when you change "Token VIP" to "Token de Acceso VIP":

```python
# BRITTLE TEST
assert "Token VIP Generado" in message.text
assert "días" in message.text
assert "🎟️" in message.text
```

Every message change requires updating dozens of test assertions. Developers stop improving messages to avoid test churn.

**Why it happens:**
- Tests assert on final rendered strings instead of semantic meaning
- No test helpers for message validation
- Copy-paste test patterns from handler to handler
- Existing tests (see `tests/test_e2e_flows.py`) likely use string matching

**How to avoid:**
1. **Semantic assertions:** Test for message components, not exact strings
2. **Test message contracts:** Verify required information present, not specific wording
3. **Message test helpers:** Reusable validators for message structure
4. **Snapshot testing:** Accept message changes in bulk, review diffs

```python
# GOOD: Semantic test
result = parse_token_success_message(message.text)
assert result.has_token
assert result.has_deep_link
assert result.has_expiration
assert result.tone == "celebratory"

# ACCEPTABLE: Component test
assert_contains_token_format(message.text)  # Checks <code>...</code> pattern
assert_contains_deep_link(message.text)     # Checks https://t.me/...
assert_valid_html(message.text)             # Checks HTML structure
```

**Warning signs:**
- Tests with 10+ string assertions per message
- Test failure rate > 20% when messages change
- Developers avoid improving message wording
- Test maintenance takes longer than feature development
- Regex assertions in tests

**Phase to address:** Phase 3 (Testing Strategy)

**Impact if ignored:** HIGH - Slowed development, fear of refactoring

---

### Pitfall 5: Variation System Feels Random Instead of Natural

**What goes wrong:**
You implement message variation for personality:
```python
WELCOME_MESSAGES = [
    "¡Hola {name}! 👋",
    "¡Bienvenido {name}! 🎉",
    "¡Hola de nuevo {name}! 😊"
]
random.choice(WELCOME_MESSAGES)
```

Users report feeling "the bot is inconsistent" or "something seems off." The variation feels arbitrary, not natural.

**Why it happens:**
- True randomness doesn't match human communication patterns
- No context-aware variation (same message repeated within minutes)
- Variation applied equally to all message types (errors shouldn't vary much)
- No user memory of which variant they saw before

**How to avoid:**
1. **Context-driven variation:** Vary based on user state, time since last interaction
2. **Variation tiers:** High variation (greetings), medium (confirmations), low (errors)
3. **Stateful variation:** Remember recent variants, avoid repetition
4. **A/B test perception:** Measure if users notice/appreciate variation

```python
# GOOD: Context-aware variation
def user_welcome(self, context: WelcomeContext) -> str:
    if context.hours_since_last_visit < 1:
        # Just saw them, minimal variation
        return f"Hola de nuevo, {context.name}"
    elif context.hours_since_last_visit < 24:
        # Same day, moderate warmth
        return self._choose_variant(["¡Hola {name}!", "Bienvenido de vuelta, {name}"])
    else:
        # Been a while, warmer greeting
        return self._choose_variant([
            "¡Hola de nuevo {name}! 👋",
            "¡Bienvenido de vuelta {name}! 🎉"
        ])
```

**Warning signs:**
- Users report "bot feels inconsistent"
- Same greeting twice in a row for same user
- Error messages vary in formality (confusing)
- No analytics on which variants perform better
- Variation added "because it seems fun"

**Phase to address:** Phase 4 (Variation System) - DEFER if not needed for MVP

**Impact if ignored:** MEDIUM - User experience degradation, unprofessional feel

---

### Pitfall 6: Service Layer Becomes Stateful Without Proper Session Management

**What goes wrong:**
Message service accumulates state:
```python
class MessageService:
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session
        self._last_messages = {}  # DANGER
        self._user_preferences = {}  # DANGER
```

Database sessions leak, memory grows unbounded, concurrency bugs emerge when multiple handlers share service instance.

**Why it happens:**
- Need to track "recently sent messages" for deduplication
- Want to cache user preferences for formatting
- ServiceContainer (see `bot/services/container.py`) uses lazy loading but services aren't properly scoped
- Developers familiar with stateful OOP patterns

**How to avoid:**
1. **Stateless by default:** Service methods receive all context via parameters
2. **Session-scoped state only:** Use FSM context or database for cross-request state
3. **Explicit cache layer:** If caching needed, use separate cache service with TTL
4. **Request-scoped services:** Create new service instance per request if state needed

```python
# GOOD: Stateless service
class MessageService:
    def __init__(self):
        pass  # No session, no bot, no state

    def format_welcome(self, user_name: str, is_vip: bool, last_visit: datetime) -> str:
        # Pure function, all inputs via params
        ...
```

**Warning signs:**
- Service `__init__` accepts session/bot
- Instance variables updated in service methods
- Memory usage grows over time
- Concurrent handler calls cause race conditions
- ServiceContainer preload (see `container.py:preload_critical_services`) loads stateful services

**Phase to address:** Phase 1 (Service Foundation)

**Impact if ignored:** CRITICAL - Memory leaks, database session leaks, concurrency bugs

---

### Pitfall 7: Missing Localization Preparation (i18n)

**What goes wrong:**
All messages hardcoded in Spanish. Later requirement: "add English support." Entire refactor needs re-refactoring because localization wasn't considered.

**Why it happens:**
- Current project is Spanish-only, seems like premature optimization
- "We'll add it later if needed"
- i18n libraries feel heavy for simple message service
- Existing code shows no i18n structure (all messages in Spanish)

**How to avoid:**
1. **Keys not strings:** Even if single language, use message keys
2. **Interpolation patterns:** Separate static text from dynamic values
3. **String extraction ready:** Structure allows easy migration to gettext/Babel later
4. **Test with pseudo-locale:** Catch hardcoded strings early

```python
# GOOD: i18n-ready even if Spanish-only today
def token_success(self, context: TokenContext) -> str:
    return self.get_message(
        key="admin.token.success",
        plan_name=context.plan_name,
        deep_link=context.deep_link
    )

# messages_es.json
{
    "admin.token.success": "🎟️ <b>Token VIP Generado</b>\n\n<b>Plan:</b> {plan_name}\n..."
}
```

**Warning signs:**
- All strings in Python code (no separation)
- No message key constants
- Formatters directly return Spanish strings
- Comments like "TODO: i18n"

**Phase to address:** Phase 2 (Template Organization) - Design with i18n in mind, implement later

**Impact if ignored:** MEDIUM - Expensive refactor if internationalization needed

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| f-strings in handlers | Fast implementation | Voice inconsistency, impossible to refactor | Never (breaks core architecture) |
| Copy-paste similar templates | Avoids abstraction complexity | Template explosion (100+ methods) | Never (compounds quickly) |
| Random variation without context | Easy personality | Feels random/unprofessional | Only for low-stakes messages (daily tips) |
| String matching tests | Simple to write | Brittle, blocks message improvements | Only for critical exact-match (legal disclaimers) |
| Skip voice documentation | Faster coding | Voice drift, reviewer confusion | Never (voice is core value) |
| Stateful service for "just one cache" | Convenient | Memory leaks, concurrency bugs | Never (violates architecture) |
| Hardcode language (Spanish only) | No translation overhead | Expensive refactor if i18n needed | Acceptable if internationalization confirmed out-of-scope |

---

## Integration Gotchas

Common mistakes when connecting message service to existing bot components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| ServiceContainer | Add MessageService to container with session/bot in init | Make MessageService stateless, inject session/bot per-call |
| FSM Handlers | Store formatted messages in FSM context | Store raw data in FSM, format on display |
| Error Handling | Format error in service, log formatted string | Log structured data, format only for user display |
| Testing | Mock entire MessageService | Use real service with test message variants |
| Keyboards | Generate keyboard in message service | Separate keyboard utility, message service returns text only |
| Background Tasks | Use different message tone than handlers | Reuse same voice rules, mark system messages clearly |
| Database Models | Store rendered HTML in database | Store semantic data, render on retrieval |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Message template compilation on every call | High CPU, slow response time | Pre-compile templates at service init | >100 messages/sec |
| Loading all templates into memory | High memory usage, OOM crashes | Lazy-load templates, use generator patterns | >1000 templates |
| Complex variation logic blocking async loop | Handler timeout, queue backup | Pre-compute variations, cache results | >50 variation rules |
| HTML escaping on every character | Slow message formatting | Use Telegram's entity system instead of HTML where possible | >1000 char messages |
| Deep nested template inheritance | Slow rendering, hard to debug | Max 2-3 inheritance levels | >5 levels deep |
| Logging every formatted message at INFO | Log spam, disk I/O bottleneck | Log at DEBUG, sample INFO logs | >500 messages/sec |

**Note for this project:** Termux environment has memory constraints. Even "small scale" performance issues matter. Keep service lightweight.

---

## Security Mistakes

Domain-specific security issues for message templating.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Unsanitized user input in templates | XSS via Telegram HTML | Always use formatters.escape_html() for user content |
| Admin messages leaking user IDs | Privacy violation | Use format_user_id() which masks IDs or log audit separately |
| Error messages revealing system internals | Information disclosure | Generic error messages to users, detailed logs only |
| Deep links exposing tokens in URLs | Token theft if URL shared | Tokens should be short-lived (24h), single-use |
| Message templates with hardcoded secrets | Credentials in version control | Use environment variables, never in templates |
| Logging formatted messages with PII | PII in logs | Log message keys and context separately, not rendered output |

---

## UX Pitfalls

Common user experience mistakes in bot messaging.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Walls of text (>300 words) | TL;DR, users miss key info | Progressive disclosure: summary first, details on demand |
| Emoji overload (>5 per message) | Looks unprofessional, hard to read | 1-3 emojis maximum, purposeful placement |
| Inconsistent formatting (bold/code/italic) | Hard to scan, cognitive load | Consistent hierarchy: bold for headers, code for IDs/tokens |
| No clear call-to-action | Users unsure what to do next | Every message ends with action button or clear instruction |
| Error messages blame user | Frustration, abandonment | Frame errors as help: "Let's fix this together" |
| Success messages bury important info | Users miss invite links, expiration | **Bold** critical information, use line breaks for hierarchy |
| Mixing English/Spanish in UI | Confusion, feels unprofessional | Pick one language per user session, consistent terminology |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Message Service:** Has methods but they just return hardcoded strings (no voice rules)
- [ ] **Voice Consistency:** Voice guide document exists but not enforced in code review
- [ ] **Template Organization:** Templates grouped in code but no hierarchy (still flat namespace)
- [ ] **Test Strategy:** Tests pass but assert on exact strings (will break on wording changes)
- [ ] **Error Handling:** Error messages exist but reveal system internals to users
- [ ] **HTML Safety:** Using HTML parse mode but not escaping user input (XSS risk)
- [ ] **Variation System:** Messages vary but randomly (no context, feels artificial)
- [ ] **Performance:** Works in dev but no profiling for 100+ concurrent users
- [ ] **Localization:** All messages extracted but keys are generic (msg_001, msg_002)
- [ ] **Documentation:** Every method documented but no voice rationale or usage examples

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Voice inconsistency discovered | MEDIUM | 1. Audit all messages, categorize by tone<br>2. Define 3-5 voice archetypes<br>3. Rewrite outliers in batch<br>4. Add voice linting to CI |
| Template explosion (100+ methods) | HIGH | 1. Map message flow diagram<br>2. Identify composition opportunities<br>3. Refactor to base + variant pattern<br>4. Deprecate old methods gradually |
| Test brittleness blocking changes | LOW | 1. Create semantic test helpers<br>2. Rewrite tests in batches<br>3. Add snapshot testing<br>4. Update test guidelines |
| Service became stateful | CRITICAL | 1. Audit all state usage<br>2. Move state to FSM context or database<br>3. Make service stateless<br>4. Add lint rule preventing state |
| Missing i18n support | HIGH | 1. Extract all strings to keys<br>2. Create message catalog<br>3. Add locale parameter to all methods<br>4. Migrate handlers to use keys |
| Performance degraded | MEDIUM | 1. Profile message formatting<br>2. Pre-compile templates<br>3. Add caching layer<br>4. Optimize hot paths |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Hardcoded presentation logic in handlers | Phase 1: Service Foundation | Handler code review: zero f-strings, zero emoji constants |
| Template explosion | Phase 2: Template Organization | Template count < 30 public methods, composition pattern documented |
| Voice inconsistency | Phase 1 + Ongoing | Voice lint rules pass, PRs reviewed by voice champion |
| Test brittleness | Phase 3: Testing Strategy | Message wording change doesn't break >10% of tests |
| Random variation | Phase 4: Variation (Defer) | User testing: variation feels natural not random |
| Stateful service | Phase 1: Service Foundation | Service `__init__` accepts zero arguments, no instance vars |
| Missing i18n | Phase 2: Design (implement later) | All messages use keys, no hardcoded strings in service |

---

## Sources

- [GramIO Formatting](https://gramio.dev/formatting) - Telegram message formatting patterns
- [Telegram Bot API Inconsistencies](https://github.com/tdlib/telegram-bot-api/issues/515) - Known formatting issues
- [Brand Voice Consistency in AI 2026](https://danishleadco.io/blog?p=brand-voice-consistency-in-ai-b2b-outreach-2026-guide) - Voice consistency challenges
- [Chatbot Architecture Best Practices 2026](https://research.aimultiple.com/chatbot-architecture/) - Architecture patterns
- [Common Chatbot Mistakes](https://www.chatbot.com/blog/common-chatbot-mistakes/) - UX and implementation pitfalls
- [WhatsApp General-Purpose Chatbots Ban](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban) - Structured template requirements
- [Bot Service Architecture](https://moimhossain.com/2025/05/22/azure-bot-service-microsoft-teams-architecture-and-message-flow/) - Integration gotchas
- [Chatbot Best Practices 2026](https://botpress.com/blog/chatbot-best-practices) - 24 best practices including monitoring and security

---

*Pitfalls research for: Telegram Bot Message Service Refactoring*
*Researched: 2026-01-23*
*Confidence: HIGH (based on real-world patterns in codebase + web research + official documentation)*
