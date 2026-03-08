# Phase 30: Economy & Shop Integration - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Full integration with existing gamification systems - choice costs, rewards, conditions, and shop connectivity. This phase delivers the connection between the narrative system and the existing economy (WalletService), rewards (RewardService), and shop (ShopService) infrastructure.

**In scope:**
- Choice costs (deducted on selection)
- Locked choice display when insufficient balance
- Story completion/node rewards (besitos, items, VIP extension)
- Cascading condition evaluation for choice access
- Shop product unlocking story nodes as purchase bonus
- Node access requiring specific product ownership

**Out of scope (deferred):**
- New reward types beyond existing ones
- Real money purchases (the infrastructure exists but this phase only integrates existing shop)

</domain>

<decisions>
## Implementation Decisions

### Choice Cost Display
- Locked choices always visible — users see all choices even if unaffordable
- Emoji indicator only: 🔒 shown in choice button for costly/locked choices
- Cost displayed in confirmation dialog, not upfront in button
- VIP discounts shown as "VIP: 40 (was 50)" format when applicable

### Insufficient Balance Behavior
- Lucien's voice (🎩) explains requirement elegantly:
  - "Para esta decisión necesita hacer una inversión de 50 besitos, ahora cuenta con X besitos. Le sugiero que vaya a reclamar su regalo del día, tal vez con eso pueda acceder."
- Choice remembered as "wishlist" — when user earns besitos, offer to complete the pending choice
- Recovery path: "Cómo ganar besitos" button to economy menu
- Same treatment for VIP and Free users (no special VIP forgiveness)

### Reward Delivery UX
- Batched summary: Single message listing all rewards from node
- Timing: Immediate per node (rewards given as soon as node is reached)
- Flow: Continue seamlessly (no pause, reward shown as message)
- VIP extensions: Display as "Días +X" format (e.g., "+3 días de membresía VIP añadidos")

### Condition Visibility
- Specific requirements shown: "Necesitas nivel 5"
- Elegant hints in Lucien's voice to encourage continued play
- Visual distinction with different icons:
  - 🚫 for level/condition-locked
  - 🔒 for costly choices (insufficient besitos)
  - ⭐ for special/premium content
- Multiple conditions: Show all requirements ("Necesitas: nivel 5 Y racha 7")

### Claude's Discretion
- Exact wording of elegant hints for locked content
- Economy menu content/layout for recovery path
- Batched reward message formatting and emoji selection
- Error handling for failed economy transactions (retry logic)

</decisions>

<specifics>
## Specific Ideas

**Lucien's voice for insufficient balance:**
> "🎩 Para esta decisión necesita hacer una inversión de 50 besitos, ahora cuenta con X besitos. Le sugiero que vaya a reclamar su regalo del día, tal vez con eso pueda acceder."

**Visual indicators by lock type:**
- 🚫 Level or streak requirement not met
- 🔒 Insufficient besitos for this choice
- ⭐ Premium/VIP content

**Reward summary format:**
- Batched single message
- Diana's or Lucien's voice depending on reward type
- Emojis for visual clarity

</specifics>

<deferred>
## Deferred Ideas

**Scope creep redirected:**
- Real money purchase flow ("comprar besitos") — this would be a new capability in a future phase
- Wishlist UI for remembering locked choices — could enhance deferred choice persistence
- Social rewards (share story completion for bonus) — social features phase

**None of the above — discussion stayed within phase scope.**

</deferred>

---

*Phase: 30-economy-shop-integration*
*Context gathered: 2026-03-08*
