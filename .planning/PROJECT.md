# LucienVoiceService - Sistema Centralizado de Mensajes

## What This Is

Un servicio centralizado que gestiona todos los mensajes del bot con la voz caracteristica de Lucien (mayordomo sofisticado de Diana). El servicio provee templates organizados por flujo de navegacion, soporta dinamismo completo (variables, condicionales, listas dinamicas, variaciones aleatorias), y retorna mensajes formateados en HTML junto con sus keyboards inline correspondientes.

El bot ahora incluye un sistema completo de gamificación con economía virtual "besitos", reacciones con botones inline, tienda de contenido, recompensas configurables, y panel de administración.

## Current State

**v2.1 SHIPPED** (2026-02-21)

Deployment readiness improvements with optional broadcast reactions/content protection and complete data migration infrastructure:
- Extended broadcast FSM with `configuring_options` state for per-message configuration
- Admins can toggle reaction buttons ON/OFF per broadcast message
- Admins can toggle content protection (no download) ON/OFF per message
- Default values ensure backward compatibility (reactions ON, protection OFF)
- Alembic data migration seeds default economy configuration
- User gamification profile backfill for all existing users
- Python seeder module (BaseSeeder + reward/shop seeders)
- Default rewards: Primeros Pasos, Ahorrador Principiante, Racha de 7 Dias
- Default shop products: Pack de Bienvenida, Pack VIP Especial
- Idempotent migration design (safe to run multiple times)
- Safety-first downgrade (preserves user data)

**v2.0 SHIPPED** (2026-02-17)

Complete virtual economy system with "besitos" currency, inline reactions, daily rewards with streaks, content shop, configurable rewards, and admin configuration panel:
- WalletService with atomic transactions and audit trail
- Inline reaction system with rate limiting and daily caps
- Daily rewards with streak tracking and UTC midnight background jobs
- Shop system with product catalog and VIP discounts
- Configurable rewards with cascading condition creation
- Admin configuration panel with economy settings and user profile viewer
- 197+ tests covering all gamification features
- 43/43 v2.0 requirements satisfied (100%)

**v1.2 SHIPPED** (2026-01-30)

Production-ready deployment infrastructure with PostgreSQL migration support, comprehensive test coverage, health monitoring, and performance profiling:
- PostgreSQL and SQLite dual-dialect support with automatic dialect detection
- Alembic migration system with auto-migration on startup
- FastAPI health check endpoint with database connectivity verification
- Railway deployment configuration (Railway.toml, Dockerfile)
- 212 system tests covering all critical flows
- CLI test runner and Telegram /run_tests command
- Performance profiling with pyinstrument (/profile command)
- 37/37 v1.2 requirements satisfied (100%)

**v1.1 SHIPPED** (2026-01-28)

Sistema de menús contextuales según rol (Admin/VIP/Free) completamente integrado:
- RoleDetectionService con detección automática de rol (Admin > VIP > Free)
- ContentService con operaciones CRUD para paquetes de contenido
- InterestService con deduplicación de 5 minutos y notificaciones admin
- Flujo de ingreso al canal Free con teclado de redes sociales
- Flujo de entrada VIP ritualizado en 3 etapas
- 57/57 requerimientos v1.1 satisfechos (100%)

**v1.0 SHIPPED** (2026-01-24)

Centralized message service maintaining Lucien's voice:
- 7 message providers delivering consistent voice across all interactions
- Stateless architecture with lazy loading via ServiceContainer
- Session-aware variation selection preventing repetition
- Voice validation pre-commit hook
- 140/140 tests passing

## Core Value

Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## Requirements

### Validated

Infraestructura existente que funciona y ha sido preservada:

**v2.1 Deployment Readiness (Shipped 2026-02-21):**
- ✓ BROADCAST-01 through BROADCAST-04: Optional reactions and content protection per message
- ✓ MIGRATION-01 through MIGRATION-05: Idempotent data migration with default rewards and shop products

**v2.0 Gamification (Shipped 2026-02-17):**
- ✓ ECON-01 through ECON-08: Virtual economy with besitos, wallet, transaction history, levels
- ✓ REACT-01 through REACT-07: Inline reaction buttons with rate limiting and daily caps
- ✓ STREAK-01 through STREAK-07: Daily rewards with streaks and UTC midnight jobs
- ✓ SHOP-01 through SHOP-08: Product catalog with purchases and VIP discounts
- ✓ REWARD-01 through REWARD-06: Configurable rewards with cascading conditions
- ✓ ADMIN-01 through ADMIN-08: Admin configuration panel with economy metrics

**v1.x Infrastructure:**
- ✓ Bot de Telegram funcional con aiogram 3.4.1 — v1.0
- ✓ Sistema VIP/Free completo (tokens, canjes, solicitudes, background tasks) — v1.0
- ✓ Service Container con DI y lazy loading — v1.0
- ✓ Middlewares (Database session injection, AdminAuth) — v1.0
- ✓ FSM States para flujos multi-paso — v1.0
- ✓ Sistema de menús contextuales (Admin/VIP/Free) — v1.1
- ✓ Deployment infrastructure (Railway, health checks, migrations) — v1.2

### Active

**Next Milestone (v2.2):**

Potential areas for enhancement:
- Analytics dashboard for economy health (faucet vs sink rates)
- Enhanced reward types (badges, cosmetic items)
- Streak recovery mechanic (one-time forgiveness)
- VIP besitos multiplier (2x earnings for VIP)
- Limited-time shop items (seasonal/flash sales)
- Complex achievement system with events
- User-facing reward notifications and progress tracking

### Out of Scope

Características explícitamente excluidas:

- **Compra de besitos dentro del bot** — El dinero real se maneja fuera
- **Subastas o mercado P2P** — No intercambio entre usuarios
- **Leaderboards públicos** — Sin tablas de clasificación visibles (privacidad)
- **Misiones complejas multi-paso** — Solo reacciones y regalo diario
- **Intercambio de besitos entre usuarios** — No transferencias P2P
- **Múltiples monedas** — Solo "besitos", sin sistema dual

## Context

### Codebase State (v2.1)

- **Total lines of code:** ~42,000 Python (bot/ directory)
- **Services:** 19 (14 base + 5 gamification: Wallet, Reaction, Streak, Shop, Reward)
- **Database models:** 10+ gamification models added
- **Tests:** 409+ total (212 base + 197+ gamification)
- **Message providers:** 13
- **Deployment:** Railway-ready with health checks and data migration
- **Migration:** Idempotent Alembic migration with Python seeders

### Architecture

- **Patrón arquitectónico**: Layered Service-Oriented con DI
- **Handler layer**: Organizado por rol (admin/, user/)
- **Service layer**: ServiceContainer con lazy loading, 19 servicios
- **Data access**: SQLAlchemy Async ORM (SQLite/PostgreSQL)
- **State management**: aiogram FSM para flujos multi-paso
- **Background tasks**: APScheduler para tareas programadas
- **Message service**: LucienVoiceService con voz consistente

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Botones inline para reacciones | Telegram no expone reacciones nativas en canales | ✓ Implementado con éxito - UserReaction model trackea reacciones |
| Tienda solo con besitos | Separar economía virtual de dinero real | ✓ ShopService con besitos_price, sin integración de pagos |
| Configuración en cascada | Evitar fragmentación que complica UX admin | ✓ Reward creation FSM con inline condition creation |
| Rachas se reinician | Mecánica simple, fácil de entender | ✓ StreakService con reset en missed day |
| Niveles por puntos totales | Progresión clara y medible | ✓ calculate_level() basado en total_earned |
| Atomic transaction pattern | UPDATE SET col = col + delta para thread-safety | ✓ WalletService usa operaciones atómicas |
| FSM para economy config | Consistente con admin handlers existentes | ✓ EconomyConfigState con 4 estados |
| Broadcast options configuration step | Give admins control over reactions/protection per message | ✓ Implemented (25-01) - configuring_options state with toggle UI |
| Default reactions ON, protection OFF | Backward compatibility with existing behavior | ✓ Implemented (25-01) - sensible defaults |
| Idempotent data migration pattern | Use INSERT OR IGNORE for safe re-runs in production | ✓ Implemented (26-01) - Migration safely re-runnable |
| Preserve user data on downgrade | Downgrade only resets config, keeps user profiles/rewards | ✓ Implemented (26-01) - Safety-first downgrade |
| Python seeders for relational data | ORM relationships too complex for raw SQL | ✓ Implemented (26-02/26-03) - BaseSeeder + reward/shop seeders |

---

*Last updated: 2026-02-21 after v2.1 milestone completion*
