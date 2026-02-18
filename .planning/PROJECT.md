# LucienVoiceService - Sistema Centralizado de Mensajes

## What This Is

Un servicio centralizado que gestiona todos los mensajes del bot con la voz caracteristica de Lucien (mayordomo sofisticado de Diana). El servicio provee templates organizados por flujo de navegacion, soporta dinamismo completo (variables, condicionales, listas dinamicas, variaciones aleatorias), y retorna mensajes formateados en HTML junto con sus keyboards inline correspondientes. Diseado para reemplazar todos los mensajes hardcodeados dispersos en los handlers actuales.

## Current Milestone: v2.0 Gamificación

**Goal:** Sistema completo de gamificación con moneda "besitos", sistema de reacciones con botones inline, tienda de contenido, logros con configuración en cascada, y mecánicas de engagement (regalo diario, rachas, niveles).

**Target features:**

### Sistema de Reacciones (ReactionService)
- Botones inline con emojis (❤️, 🔥, 💋, 😈) en mensajes de canales
- Tracking de reacciones por usuario (quien reaccionó a qué)
- Otorgamiento de besitos por reacciones
- Límite diario configurable

### Economía de Besitos
- Moneda "besitos" como único medio en tienda
- Compra de paquetes de besitos con dinero real (fuera del bot)
- Otorgamiento por: reacciones, regalo diario, rachas
- Sistema de niveles basado en puntos totales acumulados
- Rachas: diaria de reacciones, diaria de regalo — se reinician si se rompen

### Tienda (ShopService)
- Catálogo de productos comprables con besitos
- ContentPackages disponibles solo con besitos
- Beneficios VIP (extensión de membresía, etc.)
- Flujo de compra con confirmación

### Sistema de Recompensas (RewardService)
- Recompensas desbloqueables con condiciones
- Condiciones configurables: rachas, puntos mínimos, nivel, besitos gastados
- Configuración en cascada: crear condiciones inline desde el flujo de recompensa
- UI unificada: todo en una pantalla, sin fragmentación

### Configuración Admin
- Panel para configurar valores de economía (besitos por reacción, límite diario, etc.)
- Gestión de recompensas con creación de condiciones inline
- Gestión de productos en tienda
- Monitoreo de métricas de gamificación

---

## Current State

**v1.2 SHIPPED** (2026-01-30)

Production-ready deployment infrastructure with PostgreSQL migration support, comprehensive test coverage, health monitoring, and performance profiling:
- PostgreSQL and SQLite dual-dialect support with automatic dialect detection
- Alembic migration system with auto-migration on startup
- FastAPI health check endpoint with database connectivity verification
- Railway deployment configuration (Railway.toml, Dockerfile)
- 212 system tests covering all critical flows
- CLI test runner and Telegram /run_tests command
- Performance profiling with pyinstrument (/profile command)
- N+1 query detection and eager loading optimization
- 37/37 v1.2 requirements satisfied (100%)

**v1.1 SHIPPED** (2026-01-28)

Sistema de menús contextuales según rol (Admin/VIP/Free) completamente integrado:
- RoleDetectionService con detección automática de rol (Admin > VIP > Free)
- 3 nuevos modelos de base de datos (ContentPackage, UserInterest, UserRoleChangeLog)
- ContentService con operaciones CRUD para paquetes de contenido
- InterestService con deduplicación de 5 minutos y notificaciones admin
- UserManagementService con validación de permisos y logging de auditoría
- Flujo de ingreso al canal Free con teclado de redes sociales
- Flujo de entrada VIP ritualizado en 3 etapas
- Vista detallada de paquetes con UX mejorada
- Documentación exhaustiva: MENU_SYSTEM.md (1,353 líneas), INTEGRATION_GUIDE.md (1,393 líneas), EXAMPLES.md (3,031 líneas)
- 1,070+ docstrings en servicios y handlers
- 57/57 requerimientos v1.1 satisfechos (100%)

**v1.0 SHIPPED** (2026-01-24)

The centralized message service is production-ready with:
- 7 message providers delivering Lucien's voice across all bot interactions
- Stateless architecture with lazy loading via ServiceContainer
- Session-aware variation selection preventing repetition
- Voice validation pre-commit hook for consistency enforcement
- Message preview CLI tool for development workflow
- ~330 lines of hardcoded strings eliminated
- 140/140 tests passing

## Core Value

Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## Requirements

### Validated

Infraestructura existente que funciona y ha sido preservada:

- ✓ Bot de Telegram funcional con aiogram 3.4.1 — v1.0
- ✓ Sistema VIP/Free completo (tokens, canjes, solicitudes, background tasks) — v1.0
- ✓ Service Container con DI y lazy loading — v1.0
- ✓ 6 servicios de negocio (Subscription, Channel, Config, Pricing, Stats, User) — v1.0
- ✓ Middlewares (Database session injection, AdminAuth) — v1.0
- ✓ FSM States para flujos multi-paso (admin y user) — v1.0
- ✓ Handlers organizados por rol (admin/, user/) — v1.0
- ✓ Utilities (Formatters, Keyboards, Validators, Pagination) — v1.0
- ✓ SQLAlchemy Async ORM con SQLite/PostgreSQL — v1.0
- ✓ Background tasks con APScheduler — v1.0
- ✓ Suite de tests E2E — v1.0
- ✓ Sistema de menús contextuales (Admin/VIP/Free) — v1.1
- ✓ ContentPackage management — v1.1
- ✓ Deployment infrastructure (Railway, health checks, migrations) — v1.2

### Active

**v2.0 Gamification Requirements:**

Reaction System (REACT):
- [ ] REACT-01: ReactionService para tracking de reacciones
- [ ] REACT-02: Botones inline con emojis (❤️, 🔥, 💋, 😈) en mensajes de canal
- [ ] REACT-03: Tracking de quién reaccionó a qué mensaje
- [ ] REACT-04: Límite diario de reacciones por usuario
- [ ] REACT-05: Otorgamiento de besitos por reacciones válidas

Economy System (ECON):
- [ ] ECON-01: Modelo UserGamificationProfile (besitos, nivel, puntos totales)
- [ ] ECON-02: WalletService para gestión de besitos
- [ ] ECON-03: Regalo diario con botón de reclamo
- [ ] ECON-04: Sistema de rachas (reacciones diarias, regalo diario)
- [ ] ECON-05: Niveles basados en puntos totales acumulados
- [ ] ECON-06: Reset de racha si se pierde (no hay penalización, solo reinicio)

Shop System (SHOP):
- [ ] SHOP-01: ShopService para gestión de productos
- [ ] SHOP-02: ContentPackages comprables solo con besitos
- [ ] SHOP-03: Beneficios VIP comprables (extensión de membresía)
- [ ] SHOP-04: Flujo de compra con confirmación y validación de saldo
- [ ] SHOP-05: Entrega automática tras compra exitosa

Reward System (REWARD):
- [ ] REWARD-01: RewardService para gestión de recompensas
- [ ] REWARD-02: Sistema de condiciones configurables (rachas, puntos, nivel, besitos)
- [ ] REWARD-03: Configuración en cascada: crear condiciones inline desde recompensa
- [ ] REWARD-04: UI unificada sin fragmentación (todo en una pantalla)
- [ ] REWARD-05: Verificación automática de elegibilidad de recompensas
- [ ] REWARD-06: Otorgamiento de recompensas desbloqueadas

Admin Configuration (ADMIN):
- [ ] ADMIN-01: Panel de configuración de economía (valores, límites, etc.)
- [ ] ADMIN-02: Gestión de recompensas con flujo de condiciones inline
- [ ] ADMIN-03: Gestión de productos en tienda
- [ ] ADMIN-04: Métricas de gamificación (usuarios activos, besitos circulantes, etc.)

### Out of Scope

Características explícitamente excluidas de v2.0:

- **Compra de besitos dentro del bot** — El dinero real se maneja fuera; solo se recargan besitos manualmente o por sistema externo
- **Subastas o mercado P2P** — No intercambio entre usuarios, solo tienda oficial
- **Leaderboards públicos** — Sin tablas de clasificación visibles (por privacidad)
- **Misiones complejas** — Solo reacciones y regalo diario, no misiones multi-paso
- **Items cosméticos de perfil** — Solo contenido y beneficios funcionales
- **Intercambio de besitos entre usuarios** — No transferencias P2P
- **Múltiples monedas** — Solo "besitos", sin sistema de gemas/premium dual

## Context

### Codebase State

El bot tiene una arquitectura sólida en producción:

- **Patrón arquitectónico**: Layered Service-Oriented con DI
- **Handler layer**: Organizado por rol (admin/, user/)
- **Service layer**: ServiceContainer con lazy loading, 14+ servicios existentes
- **Middleware layer**: Session injection y auth
- **Data access layer**: SQLAlchemy Async ORM (SQLite/PostgreSQL)
- **State management**: aiogram FSM para flujos multi-paso
- **Background tasks**: APScheduler para mantenimiento autónomo
- **Message service**: LucienVoiceService con session-aware variation selection

### Metrics (v1.2)

- Total lines of code: ~177,811 Python
- Bot directory: ~24,328 lines of Python
- Message providers: 13
- Services: 14
- Documentation: 5,777+ lines
- Test files: 13 (212 tests passing)
- Deployment: Railway-ready

### Gamification Architecture Notes

**Sistema de reacciones**: Como Telegram no expone quién reacciona en canales, implementaremos botones inline que sí podemos trackear. Cada mensaje publicado en canales tendrá botones de reacción.

**Configuración en cascada**: El flujo de creación de recompensas debe permitir:
1. Definir la recompensa (nombre, descripción, premio)
2. Agregar condiciones desde el mismo flujo
3. Si una condición no existe, crearla inline sin salir del flujo
4. El sistema configura todo en la BD automáticamente

**Economía**: Los valores específicos (besitos por reacción, costos en tienda) serán configurables por admin y se definirán durante el desarrollo basado en playtesting.

## Constraints

- **Tech stack**: Python 3.12.12, aiogram 3.4.1, SQLAlchemy 2.0.25 — Mantener consistencia
- **Platform**: Optimizado para Termux y Railway — Sin dependencias pesadas
- **Compatibilidad**: Integrar con ServiceContainer existente — Seguir patrón de lazy loading
- **Testing**: Mantener cobertura de tests — Todos los tests existentes deben seguir pasando
- **UX Admin**: Configuración en cascada obligatoria — No fragmentar la configuración en múltiples pantallas
- **Performance**: Mensajes generan en <10ms — Sistema de reacciones no debe ralentizar

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Botones inline para reacciones | Telegram no expone reacciones nativas en canales | — Pending |
| Tienda solo con besitos | Separar economía virtual de dinero real | — Pending |
| Configuración en cascada | Evitar fragmentación que complica UX admin | — Pending |
| Rachas se reinician | Mecánica simple, fácil de entender | — Pending |
| Niveles por puntos totales | Progresión clara y medible | — Pending |

---

*Last updated: 2026-02-08 after v2.0 milestone definition*
