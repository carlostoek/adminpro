# Feature Research: Message Service for Conversational Bots

**Domain:** Centralized Message/Voice Service for Telegram Bots
**Researched:** 2026-01-23
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features essential for any message service. Missing these = unusable or inconsistent messaging.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Variable Interpolation** | Every bot needs dynamic content (names, dates, numbers) | LOW | Use `{variable_name}` syntax. Already partially implemented in formatters. Critical for personalization. |
| **HTML Formatting Support** | Telegram supports HTML; users expect rich text (bold, italic, links) | LOW | Already used throughout codebase. Must escape user input to prevent injection. |
| **Centralized Message Storage** | Hardcoded strings scattered in handlers = maintenance nightmare | MEDIUM | All messages in one location. Enables voice consistency audits and batch updates. |
| **Error Message Standards** | Consistent error UX across all flows (VIP, Free, Admin) | LOW | Standardized format with emoji, title, reason, next steps. Prevents confusion. |
| **Success/Confirmation Standards** | User needs confirmation that actions succeeded | LOW | Standard pattern for all successful operations. Includes next action guidance. |
| **Message Categories** | Logical grouping (admin, user, vip, free, errors, system) | LOW | File/class structure. Makes maintenance scalable. Prevents "message soup". |
| **Keyboard Integration** | Messages often need action buttons (inline keyboards) | MEDIUM | Message service must pair text with keyboards. Already using `create_inline_keyboard()`. |
| **Type Safety** | Runtime errors from typos in message keys | LOW | Enum/constants for message keys. IDE autocomplete + compile-time checking. |

### Differentiators (Competitive Advantage)

Features that make the service excellent and maintain sophisticated voice consistency.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Voice Consistency Engine** | Lucien's sophisticated voice maintained across ALL messages | HIGH | Core value. Random variations + tone rules. Prevents robotic repetition while maintaining personality. |
| **Contextual Message Adaptation** | Same message adjusts based on user role/state (Admin vs VIP vs Free) | MEDIUM | Dynamic content selection. "Your VIP access" vs "VIP access" vs "member access". Sophisticated personalization. |
| **Random Variations** | Multiple phrasings for same message; bot feels alive | MEDIUM | Critical for voice freshness. "Certainly!" vs "Of course!" vs "Absolutely!". Prevents repetition fatigue. |
| **Conditional Content Blocks** | Show/hide sections based on runtime conditions | MEDIUM | Example: Show "Days remaining" only if VIP active. Eliminates N duplicate messages. |
| **Dynamic List Rendering** | Format lists (tokens, subscribers, history) consistently | MEDIUM | Table-stakes data + sophisticated formatting. Bullet styles, numbering, separators matching voice. |
| **Message Composition** | Build complex messages from reusable components | MEDIUM | Header + body + footer templates. DRY principle for messages. Enables voice consistency at component level. |
| **Tone Directives** | Explicit tone markers (formal, friendly, urgent, celebratory) | MEDIUM | Ensures appropriate voice for context. Urgent errors vs friendly greetings vs formal admin notices. |
| **Voice Validation Tools** | Dev tools to audit messages for voice consistency | LOW | Regex patterns for voice anti-patterns. Pre-commit hooks. Prevents voice drift during rapid development. |
| **Message Versioning** | Track message changes for A/B testing or rollback | LOW | Git-based or DB-based. Enables testing "Does variation A convert better?" |
| **Preview Mode** | Test message rendering with sample data before deploy | LOW | Critical for QA. See exactly what users will see with real variable values. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems in message services.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Database-Stored Messages** | "Easy to update without deploy!" | Schema changes require migrations; no version control; hard to review changes; performance overhead; SQL injection risks in templates | **Use code-based messages with hot-reload in dev.** Version control + code review + no DB overhead. For user-customizable messages only (admin custom greetings), use separate DB table with clear scope. |
| **Fully Dynamic Templates (eval/exec)** | "Ultimate flexibility!" | Security nightmare; allows arbitrary code execution; impossible to audit; breaks type safety; performance issues | **Use safe templating with explicit variable injection.** Jinja2/similar with sandboxing if complexity needed. Never eval user input. |
| **Per-User Message Customization** | "Let users customize bot language!" | Voice consistency impossible; maintenance explosion; storage bloat; testing nightmare (N × M combinations) | **Offer voice presets if needed** (formal/casual), but keep core personality constant. Or i18n (see below). |
| **Real-Time Translation (per-message)** | "Support all languages instantly!" | Breaks voice consistency; translation APIs expensive/slow; loses personality nuance; Telegram has character limits | **Build i18n properly** (separate translation files per language with human review) or **start English-only** and expand deliberately. Don't auto-translate Lucien's voice. |
| **Markdown Everywhere** | "Markdown is universal!" | Telegram has non-standard Markdown (MarkdownV2); HTML more reliable; escaping issues; confusing for mixed content | **Use HTML exclusively.** Telegram HTML is stable, well-documented, easier to escape. Already in use throughout codebase. |
| **Message Analytics in Service** | "Track which messages users read!" | Mixing concerns; service becomes bloated; Telegram doesn't report read receipts reliably; privacy concerns | **Use separate analytics service** if needed. Message service focuses on content, not tracking. Bot framework may handle metrics. |
| **Inline Message Editing** | "Change message after sending!" | Breaks message history; confuses users if content changes; not all message types editable; state management complex | **Send new messages instead.** Clearer UX. Only edit for progress updates (loading states) with explicit design. |

## Feature Dependencies

```
[Variable Interpolation]
    └──requires──> [Type Safety]
                      └──enhances──> [Preview Mode]

[Voice Consistency Engine]
    └──requires──> [Random Variations]
    └──requires──> [Tone Directives]
    └──enhanced-by──> [Voice Validation Tools]

[Contextual Message Adaptation]
    └──requires──> [Conditional Content Blocks]
    └──uses──> [Variable Interpolation]

[Dynamic List Rendering]
    └──requires──> [HTML Formatting Support]
    └──uses──> [Message Composition]

[Message Composition]
    └──requires──> [Centralized Message Storage]
    └──requires──> [Message Categories]
```

### Dependency Notes

- **Variable Interpolation requires Type Safety:** Without type-safe keys, you get runtime errors. Typos like `{user_nmae}` fail silently or crash.
- **Voice Consistency Engine requires Random Variations + Tone Directives:** Can't maintain sophisticated voice with single static strings. Need variation pool + context awareness.
- **Contextual Adaptation uses Conditional Blocks:** Same message, different content based on `if user.is_vip` or `if days_remaining < 7`.
- **Message Composition requires Centralized Storage:** Can't compose from components scattered across handlers. Need single source of truth.
- **Preview Mode enhanced by Type Safety:** Type-safe keys enable IDE autocomplete in preview tools. See available variables instantly.

## MVP Definition

### Launch With (v1) — Core Message Service

Minimum viable message service to replace hardcoded strings and establish voice consistency.

- [x] **Centralized Message Storage** — Single file/module for all messages. Enables voice audit.
- [x] **Message Categories** — Logical structure (admin/, user/, vip/, free/, errors/). Scalable organization.
- [x] **Variable Interpolation** — `{user_name}`, `{days_remaining}`, etc. Already using formatters.
- [x] **HTML Formatting** — Already throughout codebase. Must maintain.
- [x] **Type Safety (Basic)** — Constants/enum for message keys. Prevents typos.
- [x] **Random Variations** — At least 2-3 variations per key message. Voice freshness.
- [x] **Tone Directives** — Explicit markers for context (friendly, urgent, formal).
- [ ] **Error Message Standards** — Consistent format: emoji + title + reason + next step.
- [ ] **Success Message Standards** — Consistent format with confirmation + next action.

**Rationale:** These features establish the foundation. Voice consistency starts here. Every message goes through service, not scattered across handlers.

### Add After Validation (v1.x) — Advanced Voice Features

Features to add once core is working and voice is established.

- [ ] **Conditional Content Blocks** — `{if vip}Your exclusive content{/if}`. Eliminates duplicate messages.
- [ ] **Contextual Message Adaptation** — Same message key, different content based on user.role or state.
- [ ] **Dynamic List Rendering** — Format subscriber lists, token lists, history consistently.
- [ ] **Message Composition** — Build complex messages from reusable header/body/footer components.
- [ ] **Voice Validation Tools** — Pre-commit hooks to check for voice anti-patterns (e.g., "please wait" vs Lucien's style).
- [ ] **Preview Mode** — Dev tool to render messages with sample data before deploy.

**Trigger for adding:** When handlers start duplicating messages for different contexts (Admin vs User vs VIP versions). Or when voice inconsistencies emerge in code reviews.

### Future Consideration (v2+) — Scale & Localization

Features to defer until product-market fit is established and voice is proven.

- [ ] **i18n Support** — Multi-language with separate .ftl files per locale. Only if expanding beyond English.
- [ ] **Message Versioning** — Track changes for A/B testing. Only if conversion optimization needed.
- [ ] **Admin Message Customization** — Let admins customize specific messages (greetings, CTAs). Separate from core voice.
- [ ] **Voice Presets** — Offer formal/casual modes. Only if user feedback demands it.
- [ ] **Message Analytics Integration** — Track which CTAs convert. Requires separate analytics service.

**Why defer:** These add complexity without validating core value (voice consistency). Build after Lucien's voice is proven to drive engagement.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Impact on Voice |
|---------|------------|---------------------|----------|-----------------|
| Centralized Storage | HIGH | MEDIUM | **P1** | Critical - enables consistency |
| Variable Interpolation | HIGH | LOW | **P1** | High - personalization is voice |
| Random Variations | HIGH | MEDIUM | **P1** | Critical - prevents robotic feel |
| Tone Directives | MEDIUM | LOW | **P1** | Critical - context-aware voice |
| Type Safety | HIGH | LOW | **P1** | Medium - prevents errors |
| HTML Formatting | HIGH | LOW | **P1** | Medium - already implemented |
| Error Standards | HIGH | LOW | **P1** | High - user trust |
| Conditional Blocks | MEDIUM | MEDIUM | **P2** | High - reduces duplication |
| Contextual Adaptation | MEDIUM | MEDIUM | **P2** | High - sophisticated voice |
| Dynamic Lists | MEDIUM | MEDIUM | **P2** | Medium - consistency |
| Message Composition | MEDIUM | MEDIUM | **P2** | High - component-level voice |
| Voice Validation | LOW | LOW | **P2** | Critical - prevents drift |
| Preview Mode | LOW | LOW | **P2** | Low - QA tool |
| i18n Support | LOW | HIGH | **P3** | High risk - can break voice |
| Message Versioning | LOW | MEDIUM | **P3** | Low - analytics |
| Admin Customization | MEDIUM | HIGH | **P3** | High risk - voice fragmentation |

**Priority key:**
- **P1**: Must have for launch (MVP) — Establishes voice foundation
- **P2**: Should have, add when voice is validated — Sophisticated features
- **P3**: Nice to have, future consideration — Scale features

**Impact on Voice key:**
- **Critical**: Feature directly determines voice quality
- **High**: Feature significantly affects voice consistency
- **Medium**: Feature supports voice but not core
- **Low**: Feature unrelated to voice (dev tools, analytics)

## Competitor/Reference Analysis

Examined patterns from leading bot frameworks and message services:

| Feature | Microsoft Bot Framework | LivePerson | Zendesk | Our Approach (Lucien) |
|---------|------------------------|------------|---------|----------------------|
| **Variable Syntax** | `{$botContext.variable}` | `{variableName}` | `{{variable}}` | **`{variable_name}`** — Python f-string style, familiar to devs |
| **Formatting** | Markdown/HTML/Cards | Plain text + Rich | Markdown | **HTML exclusively** — Telegram-native, reliable |
| **Voice Management** | Language generation templates | Bot personality settings | Tone presets (3 options) | **Random variations + tone directives** — More sophisticated |
| **Localization** | SetLocaleMiddleware | Translation files (.ftl) | Multi-language UI | **Start English-only** — Validate voice first |
| **Variations** | Multiple LG templates | Conversation Builder slots | Limited (A/B test) | **Built-in variation system** — Core feature, not addon |
| **Conditional Content** | IF/ELSE in LG | Conditions in bot logic | Not supported | **Plan for v1.x** — High value, medium complexity |
| **Message Storage** | Code files (.lg) | JSON/Platform UI | Database + UI | **Python modules** — Version controlled, reviewable |

**Key Differentiator:** Most platforms treat message variations as optional/advanced. We make it **core** because voice consistency is the primary value proposition for Lucien.

## Architecture Pattern: Message Service Structure

Based on existing codebase structure (`bot/services/`, `bot/utils/formatters.py`):

```
bot/
├── services/
│   ├── message.py              # NEW: MessageService (core)
│   └── voice.py                # NEW: VoiceService (variations + tone)
├── messages/                   # NEW: Centralized message storage
│   ├── __init__.py            # Message keys (enums/constants)
│   ├── admin.py               # Admin messages
│   ├── user.py                # User messages (general)
│   ├── vip.py                 # VIP flow messages
│   ├── free.py                # Free flow messages
│   ├── errors.py              # Error messages (standardized)
│   ├── success.py             # Success confirmations
│   └── system.py              # System/background task messages
└── utils/
    ├── formatters.py          # EXISTING: format_datetime, format_currency, etc.
    └── keyboards.py           # EXISTING: Keyboard builders
```

**Service Integration:**
```python
# In handlers
container = ServiceContainer(session, bot)
message = await container.message.get(
    key="vip.token_activated",
    variables={
        "user_name": user.first_name,
        "plan_name": plan.name,
        "days_remaining": days,
    },
    user=user,  # For contextual adaptation
    tone="celebratory"
)
await bot.send_message(chat_id, message.text, reply_markup=message.keyboard)
```

## Voice Consistency: Technical Requirements

Based on research and project context (Lucien's sophisticated voice):

### Voice Characteristics (from research)
- **Consistent brand voice** builds trust and loyalty (Gorgias, 2026)
- **Tone should adapt dynamically** to user emotion/context (Lindy AI, 2026)
- **Inconsistent tone causes bad experiences** even if functional (Whoson, 2026)
- **Quarterly usability checks** needed to validate tone remains helpful (ProProfsChat, 2026)

### Implementation Requirements

1. **Variation Pool Per Message:**
   - Minimum 2-3 variations for key messages (greetings, confirmations)
   - Maximum 5-7 variations (diminishing returns, harder to maintain consistency)
   - All variations must pass "Lucien voice test" (sophisticated, never robotic)

2. **Tone Context Awareness:**
   - Error messages: Empathetic but clear, never dismissive
   - Success messages: Celebratory but not over-the-top
   - Admin messages: Professional but not cold
   - System messages: Informative but not bureaucratic

3. **Anti-Patterns to Detect:**
   - Generic fallbacks: "I don't understand" → "Hmm, I'm not quite sure what you mean. Could you rephrase?"
   - Robotic repetition: Same error 3 times → Vary phrasing
   - Jarring formality shifts: "Greetings!" then "thx bro" → Consistent register
   - Overly apologetic: "Sorry sorry sorry" → Confident, helpful tone

4. **Testing Voice Consistency:**
   - Read 10 random messages aloud — do they sound like same person?
   - User flow test — does voice stay consistent from /start through VIP activation?
   - Edge case test — errors, edge cases, timeouts still maintain voice?

## Message Length Best Practices (2026 Research)

From [Botpress Best Practices](https://botpress.com/blog/chatbot-best-practices):

- **60-90 characters per message on mobile** — Users don't read long blocks
- **Maximum 3 lines of text** on mobile screens — Prevents scroll fatigue
- **Intentional pacing** — Slight delays between messages feel more natural
- **Visual elements** — Use cards/buttons when platform supports (Telegram inline keyboards)

**Application to Lucien:**
- Break long messages into 2-3 shorter messages with delays
- Use inline keyboards to reduce text bulk (buttons instead of options lists)
- Format lists with emojis/bullets for scannability
- Key info (days remaining, price) as bold standalone lines

## Message Character Limits (Telegram-Specific)

- **Text messages:** 4096 characters max
- **Captions (photos/videos):** 1024 characters max
- **Button text:** ~64 characters recommended
- **Keyboard rows:** 8 buttons per row max, ~100 total buttons

**Implication:** Long messages (dashboards, lists) need pagination or chunking. Message service should handle splitting automatically if needed.

## Sources

**Bot Message Best Practices:**
- [Botpress: 24 Chatbot Best Practices 2026](https://botpress.com/blog/chatbot-best-practices)
- [Microsoft: Best practices for Bot Framework Composer](https://learn.microsoft.com/en-us/composer/concept-best-practices)
- [LivePerson: Conversation Builder — Messaging Bots](https://developers.liveperson.com/conversation-builder-bots-messaging-bots.html)
- [Zendesk: 25+ free chatbot templates 2026](https://www.zendesk.com/blog/chatbot-template/)

**Tone & Voice Management:**
- [Gorgias: How AI Agent Adapts to Your Brand Voice](https://www.gorgias.com/blog/brand-voice-examples)
- [Zendesk: Build a Bot Persona and Tone of Voice](https://support.zendesk.com/hc/en-us/articles/8357758777626-Build-a-Bot-Persona-and-Tone-of-Voice-Ultimate)
- [ProProfsChat: 10 Ways to Make Your Chatbot Sound Natural 2026](https://www.proprofschat.com/blog/make-your-chatbot-sound-natural/)
- [Whoson: The importance of chatbot tone of voice](https://www.whoson.com/chatbots-ai/the-importance-of-chatbot-tone-of-voice/)
- [Lindy AI: The Ultimate Guide to AI Voice Bots 2026](https://www.lindy.ai/blog/ai-voice-bots)

**Variable Interpolation & Formatting:**
- [Microsoft: Bot message format - Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/bot-v3/bots-message-format)
- [LivePerson: Conversation Builder — Variables](https://developers.liveperson.com/conversation-builder-variables-slots-variables.html)
- [Microsoft: Customize Bot Messages - Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/format-your-bot-messages)

**Telegram-Specific:**
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram: Styled text with message entities](https://core.telegram.org/api/entities)
- [GitHub: telegram-format](https://github.com/EdJoPaTo/telegram-format)

**Localization (i18n):**
- [grammY: Internationalization (i18n)](https://grammy.dev/plugins/i18n)
- [DEV: Chatbot Internationalization: i18n Implementation Guide](https://dev.to/chatboqai/chatbot-internationalization-i18n-implementation-guide-58h6)
- [Microsoft: Virtual Assistant Localization](https://microsoft.github.io/botframework-solutions/virtual-assistant/handbook/localization/)
- [SoluLab: How to Build a Multilingual Chatbot 2026](https://www.solulab.com/how-to-build-a-multilingual-chatbot/)

**Common Mistakes:**
- [AIM Multiple: 10+ Epic LLM/Chatbot Failures 2026](https://research.aimultiple.com/chatbot-fail/)
- [Chatbot.com: Chatbot Mistakes: Common Pitfalls](https://www.chatbot.com/blog/common-chatbot-mistakes/)
- [Chatbot.com: Your Ultimate Chatbot Best Practices Guide](https://www.chatbot.com/chatbot-best-practices/)

---

*Feature research for: Message Service (Subsequent Milestone)*
*Researched: 2026-01-23*
*Confidence: HIGH — Based on 2026 industry research + existing codebase analysis*
