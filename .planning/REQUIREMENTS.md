# Requirements: LucienVoiceService v2.0 Gamification

**Defined:** 2026-02-08
**Core Value:** Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## v2.0 Requirements

Requirements for gamification milestone. Each maps to roadmap phases.

### Economy Foundation (ECON)

- [ ] **ECON-01**: User can view their "besitos" balance in menu
- [ ] **ECON-02**: User can view transaction history (earned/spent)
- [ ] **ECON-03**: System prevents negative balance (validation before spend)
- [ ] **ECON-04**: All transactions are atomic (no race conditions)
- [ ] **ECON-05**: Transaction audit trail is maintained
- [ ] **ECON-06**: Admin can adjust user's besitos balance (manual credit/debit)
- [ ] **ECON-07**: Level displayed based on total lifetime besitos earned
- [ ] **ECON-08**: Level progression formula is configurable by admin

### Reaction System (REACT)

- [ ] **REACT-01**: Channel messages display inline reaction buttons (❤️, 🔥, 💋, 😈)
- [ ] **REACT-02**: User can react to content via inline buttons
- [ ] **REACT-03**: System deduplicates reactions (one per user per content per emoji)
- [ ] **REACT-04**: Rate limiting prevents reaction spam (30s cooldown)
- [ ] **REACT-05**: User earns besitos for valid reactions (configurable amount)
- [ ] **REACT-06**: Daily reaction limit per user (configurable)
- [ ] **REACT-07**: Only accessible content can be reacted to (VIP for VIP content)

### Daily Rewards & Streaks (STREAK)

- [ ] **STREAK-01**: User can claim daily gift once per 24h period
- [ ] **STREAK-02**: User earns besitos for daily gift (base + streak bonus)
- [ ] **STREAK-03**: Streak increases with consecutive daily claims
- [ ] **STREAK-04**: Streak resets to 0 if missed (no grace period for v2.0)
- [ ] **STREAK-05**: Streak displayed in user menu
- [ ] **STREAK-06**: Reaction streak tracked separately (consecutive days with reactions)
- [ ] **STREAK-07**: Background job handles streak expiration at UTC midnight

### Shop System (SHOP)

- [x] **SHOP-01**: User can browse shop catalog with besitos prices
- [x] **SHOP-02**: Content packages available for besitos purchase
- [x] **SHOP-03**: VIP membership extension available for besitos purchase
- [x] **SHOP-04**: Purchase validates sufficient balance before transaction
- [x] **SHOP-05**: Purchase is atomic (deduct + deliver)
- [x] **SHOP-06**: User receives purchased content automatically
- [x] **SHOP-07**: Purchase history maintained
- [x] **SHOP-08**: VIP users see discounted prices (if configured)

### Rewards System (REWARD)

- [ ] **REWARD-01**: User can view available rewards and their conditions
- [ ] **REWARD-02**: System automatically checks reward eligibility
- [ ] **REWARD-03**: User receives reward automatically when conditions met
- [ ] **REWARD-04**: Reward conditions support: streak length, total points, level, besitos spent
- [ ] **REWARD-05**: Multiple conditions can be combined (AND logic)
- [ ] **REWARD-06**: Reward has maximum cap (e.g., max 100 besitos per reward)

### Admin Configuration (ADMIN)

- [ ] **ADMIN-01**: Admin can configure besitos values (per reaction, daily gift, streak bonus)
- [ ] **ADMIN-02**: Admin can configure daily limits (reactions, gifts)
- [ ] **ADMIN-03**: Admin can create shop products with besitos price
- [ ] **ADMIN-04**: Admin can enable/disable shop products
- [ ] **ADMIN-05**: Admin can create rewards with cascading condition creation
- [ ] **ADMIN-06**: Admin can create conditions inline from reward creation flow
- [ ] **ADMIN-07**: Admin can view economy metrics (total besitos in circulation, active users)
- [ ] **ADMIN-08**: Admin can view user's gamification profile (balance, streak, history)

## v2.1+ Requirements (Deferred)

Deferred to future releases. Tracked but not in current roadmap.

### Enhanced Gamification

- **STREAK-08**: Streak recovery mechanic (one-time forgiveness)
- **ECON-09**: VIP besitos multiplier (2x earnings for VIP)
- **SHOP-09**: Limited-time shop items (seasonal/flash sales)
- **REWARD-07**: Complex achievement system with events

### Social Features

- **SOCIAL-01**: Currency gifting between users
- **SOCIAL-02**: Leaderboard (opt-in privacy)
- **SOCIAL-03**: Public achievement showcase

### Analytics

- **ANALYTICS-01**: Economy health dashboard (faucet vs sink rates)
- **ANALYTICS-02**: Inflation tracking metrics
- **ANALYTICS-03**: User engagement funnel analysis

## Out of Scope

Explicitly excluded from v2.0. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real money → besitos conversion IN bot | Violates Telegram ToS; handle externally |
| Gambling/lottery mechanics | Regulatory issues in many jurisdictions |
| Currency cash-out (besitos → real money) | Money transmission laws apply |
| P2P trading/auctions | Abuse risk, economy destabilization |
| Leaderboards (public) | Privacy concerns for adult content context |
| Cosmetic profile items (badges, titles) | Scope creep; defer to v2.1+ |
| Quests/missions multi-paso | Complex event system; defer to v2.1+ |
| Multiple currencies | Keep simple: only "besitos" |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ECON-01 | Phase 19 | Pending |
| ECON-02 | Phase 19 | Pending |
| ECON-03 | Phase 19 | Pending |
| ECON-04 | Phase 19 | Pending |
| ECON-05 | Phase 19 | Pending |
| ECON-06 | Phase 19 | Pending |
| ECON-07 | Phase 19 | Pending |
| ECON-08 | Phase 19 | Pending |
| REACT-01 | Phase 20 | Pending |
| REACT-02 | Phase 20 | Pending |
| REACT-03 | Phase 20 | Pending |
| REACT-04 | Phase 20 | Pending |
| REACT-05 | Phase 20 | Pending |
| REACT-06 | Phase 20 | Pending |
| REACT-07 | Phase 20 | Pending |
| STREAK-01 | Phase 21 | Pending |
| STREAK-02 | Phase 21 | Pending |
| STREAK-03 | Phase 21 | Pending |
| STREAK-04 | Phase 21 | Pending |
| STREAK-05 | Phase 21 | Pending |
| STREAK-06 | Phase 21 | Pending |
| STREAK-07 | Phase 21 | Pending |
| SHOP-01 | Phase 22 | Complete |
| SHOP-02 | Phase 22 | Complete |
| SHOP-03 | Phase 22 | Complete |
| SHOP-04 | Phase 22 | Complete |
| SHOP-05 | Phase 22 | Complete |
| SHOP-06 | Phase 22 | Complete |
| SHOP-07 | Phase 22 | Complete |
| SHOP-08 | Phase 22 | Complete |
| REWARD-01 | Phase 23 | Pending |
| REWARD-02 | Phase 23 | Pending |
| REWARD-03 | Phase 23 | Pending |
| REWARD-04 | Phase 23 | Pending |
| REWARD-05 | Phase 23 | Pending |
| REWARD-06 | Phase 23 | Pending |
| ADMIN-01 | Phase 24 | Pending |
| ADMIN-02 | Phase 24 | Pending |
| ADMIN-03 | Phase 24 | Pending |
| ADMIN-04 | Phase 24 | Pending |
| ADMIN-05 | Phase 24 | Pending |
| ADMIN-06 | Phase 24 | Pending |
| ADMIN-07 | Phase 24 | Pending |
| ADMIN-08 | Phase 24 | Pending |

**Coverage:**
- v2.0 requirements: 43 total
- Mapped to phases: 43
- Unmapped: 0 ✓

---

*Requirements defined: 2026-02-08*
*Last updated: 2026-02-13 after Phase 22 completion*
