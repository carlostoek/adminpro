# Pitfalls Research: Adding Narrative Systems to Existing Applications

**Domain:** Interactive Fiction / Branching Story System for Telegram Bot
**Researched:** 2026-02-26
**Confidence:** HIGH (based on existing codebase analysis + ecosystem research)

## Executive Summary

Adding a branching narrative system (v3 Narrativa) to an existing Telegram bot with 42k lines, 19 services, and 409+ tests introduces unique integration risks. The existing system has mature gamification (besitos economy), VIP/Free tier access, FSM-based flows (VIP entry ritual), and a sophisticated reward condition system. The narrative system must integrate without destabilizing these foundations.

**Key Risk:** State management conflicts between story progression and existing FSM flows, database query explosion from graph-structured narrative data, economy-narrative race conditions, and admin UX complexity for story authoring.

---

## Critical Pitfalls

### Pitfall 1: State Machine Hell (User Stuck in Story)

**What goes wrong:**
Users become trapped in narrative FSM states with no escape path. The bot stops responding to normal commands (/start, /menu) because the user is "in a story." Users must complete the narrative or wait for state timeout, creating frustration and support burden.

**Why it happens:**
- Aiogram FSM states are exclusive - a user can only be in one state at a time
- Story handlers intercept ALL messages while in narrative mode
- No "emergency exit" pattern implemented
- State timeouts not configured (RedisStorage defaults to no TTL)

**How to avoid:**
1. **Implement a universal escape hatch**: Every story node must offer "Salir de la historia" button that clears FSM state and returns to main menu
2. **Use state hierarchy**: Track story state separately from UI state using a composite pattern:
   ```python
   # Instead of: user in "story_node_5" state
   # Use: user in "in_story" state + story_progress stored in data
   ```
3. **Set aggressive TTLs**: Configure RedisStorage with `state_ttl=1800` (30 min) to auto-recover stuck users
4. **Command override**: Ensure /start and /menu commands work from ANY state using `State("*")` or explicit state checks

**Warning signs:**
- Support tickets: "El bot no me responde"
- Users sending multiple /start commands in succession
- High bounce rate on first story node

**Phase to address:** Phase 1 (Core Story Engine) - MUST be in foundation

---

### Pitfall 2: Progress Loss on Bot Restart

**What goes wrong:**
Users lose their story progress when the bot restarts (deployment, crash, or maintenance). With default MemoryStorage, ALL FSM states are lost. Even with Redis, story progress stored only in FSM data (not database) evaporates.

**Why it happens:**
- Default aiogram setup uses MemoryStorage
- Story progress tracked only in FSM context, not persisted to database
- No separation between "session state" (ephemeral) and "story progress" (persistent)

**How to avoid:**
1. **Dual-track persistence**:
   - FSM state: ephemeral UI state (current menu, input waiting)
   - Database: persistent story progress (current_node_id, choices_made, flags)
2. **Auto-save pattern**: After every choice, persist to database BEFORE sending next node
3. **Recovery on startup**: Handler checks database story state on entry, resumes from last node
4. **Use RedisStorage**: Mandatory for production; configure with appropriate TTL

**Warning signs:**
- Users report "me hizo empezar de nuevo"
- Story completion rates drop after deployments
- Inconsistent story state across devices (if user switches phones)

**Phase to address:** Phase 1 (Core Story Engine) - Database schema must support this

---

### Pitfall 3: N+1 Query Explosion in Story Traversal

**What goes wrong:**
Story navigation becomes unbearably slow as complexity grows. Loading a story node with 3 choices triggers 5+ database queries (node + 3 choice texts + conditions + rewards). At 100 concurrent users, database connection pool exhausts.

**Why it happens:**
- Naive ORM usage: `node.choices` triggers lazy loading of each relationship
- No prefetching of related nodes
- Condition checking queries database for each choice
- Reward evaluation queries economy tables per choice

**How to avoid:**
1. **Eager loading pattern**:
   ```python
   result = await session.execute(
       select(StoryNode)
       .options(
           selectinload(StoryNode.choices),
           selectinload(StoryNode.conditions),
           selectinload(StoryNode.rewards)
       )
       .where(StoryNode.id == node_id)
   )
   ```
2. **Story cache**: Cache complete story graph in memory (stories are small, reads are frequent)
3. **Denormalized choice preview**: Store choice text inline with node, not separate query
4. **Batch condition evaluation**: Pre-load all user progress data in one query, evaluate conditions in Python

**Warning signs:**
- Story navigation latency > 2 seconds
- Database connection pool warnings in logs
- CPU spikes during story peak usage

**Phase to address:** Phase 1 (Core Story Engine) - Query patterns established early

---

### Pitfall 4: Circular Reference Death Trap

**What goes wrong:**
Admins create story loops (Node A -> B -> C -> A) either intentionally (retry paths) or accidentally. The story engine enters infinite loops, consuming memory and CPU. Users get spammed with the same messages.

**Why it happens:**
- No validation on story graph structure during admin creation
- Story editor allows arbitrary connections
- No cycle detection in the graph validation
- Visit tracking not implemented

**How to avoid:**
1. **DAG validation on save**: When admin saves story, run cycle detection (DFS with visited set)
2. **Max visit counter**: Each node tracks visit count; hard limit (e.g., 3 visits) before forcing exit
3. **Loop detection in engine**: Track node history in session; detect repeated pattern and break
4. **Admin warning**: Visual indicator in editor when creating backward links

**Warning signs:**
- Users receiving duplicate messages
- Memory usage climbing for specific users
- "La historia se repite" user reports

**Phase to address:** Phase 2 (Admin Story Editor) - Validation layer

---

### Pitfall 5: Economy-Narrative Race Conditions

**What goes wrong:**
Story choices that cost besitos create race conditions. User has 100 besitos, two parallel story sessions (rare but possible with quick clicks) both deduct 80 besitos. Result: -60 balance or duplicate purchases.

**Why it happens:**
- Check-then-act pattern: read balance -> check sufficient -> deduct -> save
- No database-level locking on wallet operations
- Story engine and wallet service use separate transactions

**How to avoid:**
1. **Atomic wallet operations** (already implemented in WalletService):
   ```python
   # Use UPDATE with WHERE clause for optimistic locking
   UPDATE user_gamification_profiles
   SET balance = balance - {cost}
   WHERE user_id = {user_id} AND balance >= {cost}
   ```
2. **Story choice as transaction**: Wrap choice selection + reward/cost in single database transaction
3. **Idempotency keys**: Each choice button includes unique idempotency token; duplicate clicks ignored
4. **Pre-validation**: Check conditions BEFORE showing choice button (not after click)

**Warning signs:**
- Negative balance reports in economy stats
- Duplicate reward claims from same user
- "Me cobro dos veces" support tickets

**Phase to address:** Phase 1 (Core Story Engine) - Integration with existing WalletService

---

### Pitfall 6: The Overwhelming Story Editor

**What goes wrong:**
Admin story editor becomes unusable as stories grow. 50+ nodes with branching create spaghetti visualization. Admins lose track of story structure, create dead ends, and accidentally break existing paths when adding new content.

**Why it happens:**
- Linear list view of nodes (table with parent_id)
- No visual graph representation
- No story organization (chapters, scenes)
- No validation of story completeness (orphaned nodes, unreachable branches)

**How to avoid:**
1. **Hierarchical organization**: Stories -> Chapters -> Scenes -> Nodes
2. **Visual graph editor**: Mini-map showing node connections (even if text-based)
3. **Validation suite**: On save, check for:
   - Orphaned nodes (no incoming edges)
   - Dead ends (no choices, not marked as ending)
   - Unreachable branches
4. **Story templates**: Pre-defined patterns (linear, diamond, hub-and-spoke) admins can start from
5. **Test playthrough**: Admin can walk through story before publishing

**Warning signs:**
- Admins avoid using story features
- Stories have simple linear structure despite branching capability
- Frequent "arregla la historia X" requests

**Phase to address:** Phase 2 (Admin Story Editor) - UX critical

---

### Pitfall 7: Tier Access Logic Sprawl

**What goes wrong:**
VIP/Free tier checks scattered across story engine, handlers, and templates. Adding a new tier (Premium) requires changes in 15+ files. Inconsistent access rules lead to Free users seeing VIP content and vice versa.

**Why it happens:**
- Tier checks inline in story loading code
- No centralized access control for narrative content
- Story nodes store tier as string, not referencing canonical tier system

**How to avoid:**
1. **Centralized access service**: `StoryAccessService` that encapsulates all tier logic
2. **Use existing role system**: Leverage `UserRole` enum already in codebase
3. **Condition composition**: Tier access is just another condition type in the condition system
4. **Single source of truth**: Story nodes reference `ContentTier` enum (already exists in models)

**Warning signs:**
- Free users reporting VIP story content
- Inconsistent "Necesitas VIP" messages
- Code search for "VIP" returns 100+ results across story code

**Phase to address:** Phase 1 (Core Story Engine) - Design integration point

---

### Pitfall 8: Reward Notification Spam

**What goes wrong:**
Story completion triggers 5 separate reward notifications (level up, achievement, besitos, streak bonus, new content unlock). User receives flood of messages, misses important info, and perceives bot as spammy.

**Why it happens:**
- Each system (wallet, reward, streak) sends separate notification
- No coordination between reward triggers
- Story completion triggers multiple reward checks simultaneously

**How to avoid:**
1. **Batch reward notifications**: Collect all rewards from story completion, send single consolidated message
2. **Notification queue**: Story engine adds to queue; single sender processes batch
3. **Priority filtering**: Only show "significant" rewards (>50 besitos, new tier, rare achievement)
4. **Digest mode**: Option to receive reward summary at end of session vs. real-time

**Warning signs:**
- Users disabling bot notifications
- "Me llegaron muchos mensajes" reports
- Low engagement with reward messages

**Phase to address:** Phase 3 (Story-Economy Integration) - Notification architecture

---

### Pitfall 9: Implicit Story State Dependencies

**What goes wrong:**
Story nodes reference flags/variables set by other nodes, creating invisible dependencies. When admin modifies one node, seemingly unrelated story paths break. Debugging requires tracing entire story graph.

**Why it happens:**
- No explicit declaration of node inputs/outputs
- Flags created ad-hoc during story writing
- No validation that referenced flags exist

**How to avoid:**
1. **Explicit variable schema**: Each story declares required variables upfront
2. **Static analysis**: Editor validates all flag references on save
3. **Default values**: All flags have defaults; missing flag doesn't crash story
4. **Dependency graph**: Visualize which nodes set/consume which flags

**Warning signs:**
- "Esa opcion no aparecia antes" user reports
- Story behavior changes without code deployment
- Admins confused why stories behave differently than expected

**Phase to address:** Phase 2 (Admin Story Editor) - Variable management system

---

### Pitfall 10: Message Length Limits in Story Nodes

**What goes wrong:**
Story nodes with long text hit Telegram's 4096 character limit for text messages. Bot crashes or truncates story mid-sentence. Admins unaware of limit until users report broken stories.

**Why it happens:**
- Telegram API limit: 4096 chars for text messages, 1024 for callback button text
- No validation in story editor
- Story text includes formatting (HTML tags) that count toward limit

**How to avoid:**
1. **Editor validation**: Real-time character counter with warning at 3500, hard stop at 4000
2. **Auto-splitting**: Story engine automatically paginates long nodes with "Continuar..." button
3. **Template preview**: Admin sees exact message preview before publishing
4. **Graceful degradation**: If limit exceeded, split at paragraph boundary

**Warning signs:**
- `MessageIsTooLong` exceptions in logs
- Stories cutting off mid-word
- Admins asking "por que no se envia todo el texto"

**Phase to address:** Phase 2 (Admin Story Editor) - Content validation

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store story progress only in FSM | Simpler code, no DB migration | Progress lost on restart | NEVER in production |
| Inline tier checks in handlers | Faster to write first story | Inconsistent access control, sprawl | MVP only, refactor by Phase 2 |
| Simple parent_id tree structure | Easy to understand | Can't handle converging branches, cycles | Linear stories only |
| Text-based choice matching | No choice ID schema | Breaks when text edited | NEVER - use stable IDs |
| Synchronous story loading | Simpler async code | Blocks bot for all users during load | NEVER - use async throughout |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| WalletService | Calling spend_besitos without checking return value | Always check `(success, msg, tx)` tuple; handle insufficient balance gracefully |
| RewardService | Checking rewards AFTER story completion | Check conditions at story milestones, batch notify at end |
| Existing FSM states | Story state colliding with VIP entry flow | Use separate state groups; story state doesn't block VIP flow |
| Reaction system | Story choices look like content reactions | Different callback_data prefix (`story:` vs `react:`); separate handlers |
| Content packages | Story unlocks not integrated with package system | Use existing `UserContentAccess` model for story unlocks |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full story graph per user | Memory usage grows with users | Cache story graph globally, user only stores node pointer | 100+ concurrent users |
| Recursive story traversal | Stack overflow on deep stories | Iterative traversal with explicit stack; max depth limit | 100+ node depth |
| Synchronous condition evaluation | Bot freezes during complex checks | Async condition evaluation; timeout on external checks | Complex multi-condition nodes |
| Storing choice history as JSON array | Querying progress becomes O(n) | Separate table for choice history with proper indexing | Users with 1000+ choices |
| Real-time story analytics | Every choice triggers analytics write | Buffer analytics, flush async; use background task | High-frequency story usage |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Story node IDs exposed in callbacks | Users can skip ahead by crafting callback_data | Use opaque tokens or validate node reachable from current position |
| Admin bypasses not logged | Can't audit admin story testing | Log all admin story access with `is_test=true` flag |
| Story content not sanitized | XSS via story text | Sanitize HTML in story editor; whitelist allowed tags |
| Choice conditions client-side | Users can send "valid" choice that should be locked | Always re-validate conditions server-side on choice receipt |
| Story flag injection | Malicious flag names collide with system | Namespace story flags (`story_{id}_{flag}`) |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No "save and continue later" | Users must complete story in one sitting | Auto-save progress; "Continuar historia" button in menu |
| Story interrupts VIP entry flow | Users confused between story and onboarding | Don't offer stories during VIP entry ritual (stages 1-3) |
| Choices not visible without scroll | Users miss options | Max 3 choices visible; use pagination for more |
| No progress indicator | Users don't know story length | Progress bar: "Escena 3 de 12" |
| Story text too dense | Users don't read | Max 2 paragraphs per node; use pacing (delay between messages) |
| Inconsistent tone | Breaks immersion | Story content uses Diana voice (intimate), system messages use Lucien |

---

## "Looks Done But Isn't" Checklist

- [ ] **Story persistence:** Progress saved to database, not just FSM - verify by restarting bot mid-story
- [ ] **State recovery:** User can resume story after /start - verify with fresh test user
- [ ] **Escape hatch:** Every node has working "Salir" option - verify from 3+ different nodes
- [ ] **Economy integration:** Choice costs actually deduct besitos - verify balance changes
- [ ] **Tier enforcement:** Free user can't access VIP story - verify with role downgrade test
- [ ] **Cycle protection:** Story with loop doesn't infinite loop - verify with intentional cycle
- [ ] **Message limits:** 4000+ char node handles gracefully - verify with edge case content
- [ ] **Concurrent safety:** Rapid double-click doesn't double-charge - verify with automated test
- [ ] **Admin validation:** Invalid story (orphan node) can't be published - verify in editor
- [ ] **Notification batching:** Story completion doesn't spam - verify reward notification count

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| User stuck in story | LOW | Clear FSM state via admin command; user resumes from last saved node |
| Progress lost | MEDIUM | Restore from backup if available; compensate user with besitos; apologize |
| Story has cycle | LOW | Admin edits story to break cycle; republish; no user impact if caught early |
| Economy exploit found | HIGH | Emergency bot shutdown; audit logs; fix exploit; rollback illegitimate transactions |
| Story editor corruption | MEDIUM | Restore story from JSON export; implement auto-export on save |
| Database query overload | LOW | Add missing indexes; implement caching; no data loss |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| State Machine Hell | Phase 1: Core Story Engine | Test: User can /start from any story node |
| Progress Loss | Phase 1: Core Story Engine | Test: Restart bot, verify story resumes |
| N+1 Query Explosion | Phase 1: Core Story Engine | Test: 100 concurrent story users, <100ms latency |
| Circular Reference | Phase 2: Admin Story Editor | Test: Attempt to save cyclic story, verify rejected |
| Economy Race Conditions | Phase 1: Core Story Engine | Test: Double-click choice, verify single charge |
| Overwhelming Editor | Phase 2: Admin Story Editor | UX testing with admin users |
| Tier Access Sprawl | Phase 1: Core Story Engine | Code review: tier checks centralized |
| Reward Notification Spam | Phase 3: Story-Economy Integration | Test: Complete story, verify single notification |
| Implicit Dependencies | Phase 2: Admin Story Editor | Test: Delete flag, verify validation error |
| Message Length Limits | Phase 2: Admin Story Editor | Test: Enter 5000 chars, verify validation |

---

## Sources

- [aiogram FSM Storage Documentation](https://docs.aiogram.dev/en/latest/dispatcher/finite_state_machine/storages.html) - Official storage options and Redis configuration
- [Save Game Architecture Best Practices](https://www.intelligent-artifice.com/2024/a-presentation-on-save-games/) - Persistent systems and state management patterns
- [Graph Data Modeling Best Practices](https://memgraph.com/docs/data-modeling/best-practices) - Node-edge relationship modeling
- [Gamification Pitfalls](https://www.commlabindia.com/blog/elearning-gamification-pitfalls-avoid) - Common gamification mistakes
- [The Dark Side of Gamification](https://www.growthengineering.co.uk/dark-side-of-gamification/) - Reward system failures
- [Open Design Challenges for Interactive Emergent Narrative](https://eis.ucsc.edu/papers/ryanEtAl_OpenDesignChallengesForInteractiveEmergentNarrative.pdf) - Narrative system complexity
- [Existing codebase analysis] - WalletService atomic operations, RewardService condition evaluation, FSM state patterns

---

*Pitfalls research for: Narrativa v3 - Branching Story System*
*Researched: 2026-02-26*
*Confidence: HIGH*
