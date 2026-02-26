# Requirements: DianaBot v3.0 Narrativa

**Defined:** 2026-02-26
**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## v3.0 Requirements

### Narrative Core (NARR)

- [ ] **NARR-01**: Admin can create a story with metadata (title, description, is_premium)
- [ ] **NARR-02**: Admin can create story nodes with content (text, media_file_ids)
- [ ] **NARR-03**: Admin can define choices for a node (text, target_node_id, optional cost)
- [ ] **NARR-04**: User can start an available story from the story list
- [ ] **NARR-05**: User sees current node content with inline button choices
- [ ] **NARR-06**: User choice transitions to next node and saves progress
- [ ] **NARR-07**: User can resume a story from where they left off
- [ ] **NARR-08**: User has escape hatch button to exit story at any time
- [ ] **NARR-09**: System tracks user story progress (current_node, decisions_made, status)
- [ ] **NARR-10**: System handles story completion (end nodes) and records ending reached

### Admin Story Editor (ADMIN)

- [ ] **ADMIN-01**: Admin can list all stories with status (draft/published/archived)
- [ ] **ADMIN-02**: Admin can edit story metadata (title, description, premium flag)
- [ ] **ADMIN-03**: Admin can publish/unpublish stories (only published visible to users)
- [ ] **ADMIN-04**: Admin can delete draft stories (soft delete with is_active)
- [ ] **ADMIN-05**: Admin can create nodes via FSM wizard with content input
- [ ] **ADMIN-06**: Admin can edit node content and media attachments
- [ ] **ADMIN-07**: Admin can delete nodes (with cascade handling for choices)
- [ ] **ADMIN-08**: Admin can create choices linking nodes with optional besitos cost
- [ ] **ADMIN-09**: Admin can edit choice text and target node
- [ ] **ADMIN-10**: Admin can delete choices
- [ ] **ADMIN-11**: System validates stories (detect cycles, orphaned nodes, dead ends)
- [ ] **ADMIN-12**: Admin can view story statistics (total nodes, completion count)

### Economy Integration (ECON)

- [ ] **ECON-01**: Choices can have besitos cost (deducted on selection)
- [ ] **ECON-02**: Users with insufficient besitos see locked choices with cost displayed
- [ ] **ECON-03**: Story completion can trigger reward (besitos, items, VIP extension)
- [ ] **ECON-04**: Story nodes can unlock rewards when reached
- [ ] **ECON-05**: Choices can have conditions (level, streak, total earned) via extended condition system
- [ ] **ECON-06**: Conditions are evaluated using existing cascading condition system (AND/OR groups)
- [ ] **ECON-07**: Economy operations are atomic (no double-charging on rapid clicks)
- [ ] **ECON-08**: Reward notifications are batched (not spam per node)

### Tiered Access (TIER)

- [ ] **TIER-01**: Stories can be marked as Free (levels 1-3) or Premium (levels 4-6)
- [ ] **TIER-02**: Free users see only Free stories in their list
- [ ] **TIER-03**: VIP users see both Free and Premium stories
- [ ] **TIER-04**: Free users attempting Premium story see upsell message with VIP info
- [ ] **TIER-05**: Individual nodes can have tier restrictions (early levels Free, later Premium)

### Shop Integration (SHOP)

- [ ] **SHOP-01**: Shop products can unlock specific story levels/nodes as purchase bonus
- [ ] **SHOP-02**: Story completion can grant shop products as reward
- [ ] **SHOP-03**: Story nodes can require ownership of specific shop product to access
- [ ] **SHOP-04**: Product ownership is checked via existing UserContentAccess model
- [ ] **SHOP-05**: Shop integration uses existing condition system (extend with PRODUCT_OWNED condition)

### User Experience (UX)

- [ ] **UX-01**: User sees progress indicator ("Escena 3 de 12") during story
- [ ] **UX-02**: User sees story list with completion status (not started, in progress, completed)
- [ ] **UX-03**: User can restart a completed story (with confirmation)
- [ ] **UX-04**: Story content uses Diana's voice (🫦), system messages use Lucien's (🎩)
- [ ] **UX-05**: Choices are presented as inline keyboard buttons (max 3 per row, max 10 total)
- [ ] **UX-06**: Media content (photos/videos) displays correctly in sequence with text

## v3.1+ Requirements (Future)

### Advanced Narrative

- **ADV-01**: Consequences system (choices affect other stories)
- **ADV-02**: Hidden paths unlockable via specific decision sequences
- **ADV-03**: Story variables (track custom state across nodes)
- **ADV-04**: Timed choices (limited time to decide)

### Analytics

- **ANAL-01**: Track choice popularity (which paths users take)
- **ANAL-02**: Track story completion rates and drop-off points
- **ANAL-03**: Track average time to complete stories

### Social

- **SOC-01**: Users can share story recommendations
- **SOC-02**: Community choices (periodic votes affect canon story)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Sentiment analysis | Out of scope per v3 simplification |
| NLP/intent recognition | Natural language choices not supported |
| Procedural generation | All content is admin-authored |
| User-generated stories | Admin-only story creation for v3 |
| Real-time multiplayer | No collaborative story experience |
| Visual tree editor | Telegram-based admin UI only |
| Complex puzzles | Focus on choices, not puzzles |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| NARR-01 | Phase 27 | Pending |
| NARR-02 | Phase 27 | Pending |
| NARR-03 | Phase 27 | Pending |
| NARR-04 | Phase 28 | Pending |
| NARR-05 | Phase 28 | Pending |
| NARR-06 | Phase 28 | Pending |
| NARR-07 | Phase 28 | Pending |
| NARR-08 | Phase 28 | Pending |
| NARR-09 | Phase 27 | Pending |
| NARR-10 | Phase 28 | Pending |
| ADMIN-01 | Phase 29 | Pending |
| ADMIN-02 | Phase 29 | Pending |
| ADMIN-03 | Phase 29 | Pending |
| ADMIN-04 | Phase 29 | Pending |
| ADMIN-05 | Phase 29 | Pending |
| ADMIN-06 | Phase 29 | Pending |
| ADMIN-07 | Phase 29 | Pending |
| ADMIN-08 | Phase 29 | Pending |
| ADMIN-09 | Phase 29 | Pending |
| ADMIN-10 | Phase 29 | Pending |
| ADMIN-11 | Phase 29 | Pending |
| ADMIN-12 | Phase 30 | Pending |
| ECON-01 | Phase 30 | Pending |
| ECON-02 | Phase 30 | Pending |
| ECON-03 | Phase 30 | Pending |
| ECON-04 | Phase 30 | Pending |
| ECON-05 | Phase 30 | Pending |
| ECON-06 | Phase 30 | Pending |
| ECON-07 | Phase 30 | Pending |
| ECON-08 | Phase 30 | Pending |
| TIER-01 | Phase 27 | Pending |
| TIER-02 | Phase 28 | Pending |
| TIER-03 | Phase 28 | Pending |
| TIER-04 | Phase 28 | Pending |
| TIER-05 | Phase 29 | Pending |
| SHOP-01 | Phase 30 | Pending |
| SHOP-02 | Phase 30 | Pending |
| SHOP-03 | Phase 30 | Pending |
| SHOP-04 | Phase 30 | Pending |
| SHOP-05 | Phase 30 | Pending |
| UX-01 | Phase 28 | Pending |
| UX-02 | Phase 28 | Pending |
| UX-03 | Phase 28 | Pending |
| UX-04 | Phase 28 | Pending |
| UX-05 | Phase 28 | Pending |
| UX-06 | Phase 28 | Pending |

**Coverage:**
- v3.0 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0 ✓

---

*Requirements defined: 2026-02-26*
*Last updated: 2026-02-26 after initial definition*
