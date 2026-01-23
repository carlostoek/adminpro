# LucienVoiceService - Sistema Centralizado de Mensajes

## What This Is

Un servicio centralizado que gestiona todos los mensajes del bot con la voz característica de Lucien (mayordomo sofisticado de Diana). El servicio provee templates organizados por flujo de navegación, soporta dinamismo completo (variables, condicionales, listas dinámicas, variaciones aleatorias), y retorna mensajes formateados en HTML junto con sus keyboards inline correspondientes. Diseñado para reemplazar todos los mensajes hardcodeados dispersos en los handlers actuales.

## Core Value

Consistencia absoluta en la voz de Lucien: cada mensaje del bot debe sonar elegante, misterioso y natural viniendo del mayordomo, sin importar qué handler o flujo lo invoque.

## Requirements

### Validated

Infraestructura existente que funciona y debe ser preservada:

- ✓ Bot de Telegram funcional con aiogram 3.4.1 — existing
- ✓ Sistema VIP/Free completo (tokens, canjes, solicitudes, background tasks) — existing
- ✓ Service Container con DI y lazy loading — existing
- ✓ 6 servicios de negocio (Subscription, Channel, Config, Pricing, Stats, User) — existing
- ✓ Middlewares (Database session injection, AdminAuth) — existing
- ✓ FSM States para flujos multi-paso (admin y user) — existing
- ✓ Handlers organizados por rol (admin/, user/) — existing
- ✓ Utilities (Formatters, Keyboards, Validators, Pagination) — existing
- ✓ SQLAlchemy Async ORM con SQLite — existing
- ✓ Background tasks con APScheduler — existing
- ✓ Suite de tests E2E — existing

### Active

Nuevo sistema de mensajería centralizado:

- [ ] **VOICE-01**: Servicio LucienVoiceService como clase centralizada de generación de mensajes
- [ ] **VOICE-02**: Templates organizados por flujo de navegación (main_menu, vip, free, profile, admin)
- [ ] **VOICE-03**: Soporte para variables simples (nombres, números, fechas, estados)
- [ ] **VOICE-04**: Soporte para condicionales (mensajes diferentes según rol VIP/Free/Admin)
- [ ] **VOICE-05**: Soporte para listas dinámicas (inventarios, historial, leaderboards)
- [ ] **VOICE-06**: Sistema de variaciones aleatorias con pool de opciones
- [ ] **VOICE-07**: Variaciones basadas en contexto (hora del día, frecuencia de uso)
- [ ] **VOICE-08**: Sistema de ponderación (variantes comunes vs raras)
- [ ] **VOICE-09**: Keyboards inline integrados con cada mensaje
- [ ] **VOICE-10**: Formateo HTML consistente para Telegram
- [ ] **VOICE-11**: Métodos para todos los flujos principales (greetings, transactions, errors)
- [ ] **VOICE-12**: Métodos para flujos VIP (tokens, canjes, expiración)
- [ ] **VOICE-13**: Métodos para flujos Free (solicitudes, cola, aprobación)
- [ ] **VOICE-14**: Métodos para flujos admin (configuración, dashboard, gestión)
- [ ] **VOICE-15**: Refactor de todos los handlers en bot/handlers/admin/ para usar el servicio
- [ ] **VOICE-16**: Refactor de todos los handlers en bot/handlers/user/ para usar el servicio
- [ ] **VOICE-17**: Migrar keyboards de bot/utils/keyboards.py al nuevo servicio
- [ ] **VOICE-18**: Tests unitarios para cada tipo de mensaje
- [ ] **VOICE-19**: Tests de integración con handlers refactorizados
- [ ] **VOICE-20**: Documentación de la API del servicio (métodos disponibles, parámetros)

### Out of Scope

Características explícitamente excluidas de esta iteración:

- **Internacionalización (i18n)** — Solo español por ahora; estructura puede prepararse pero sin implementación
- **Sistema de gamificación** — Servicio debe ser extensible pero no incluir mensajes de misiones/logros aún
- **Sistema de narrativa** — Servicio debe ser extensible pero no incluir contenido narrativo aún
- **Persistencia de variaciones** — No rastrear qué variante se mostró a cada usuario (puede agregarse después)
- **A/B testing** — No métricas de efectividad de diferentes variantes
- **Voice profiles alternos** — Solo voz de Lucien, sin variaciones de personalidad

## Context

### Codebase Existente

El bot ya tiene una arquitectura sólida en producción:

- **Patrón arquitectónico**: Layered Service-Oriented con DI
- **Handler layer**: Entry points para Telegram (admin/, user/)
- **Service layer**: Lógica de negocio (6 servicios)
- **Middleware layer**: Session injection y auth
- **Data access layer**: SQLAlchemy Async ORM
- **State management**: aiogram FSM para flujos multi-paso
- **Background tasks**: APScheduler para mantenimiento autónomo

### Problema Actual

Los mensajes están dispersos y hardcodeados en ~15 handlers diferentes:
- Inconsistencia en tono y estilo (algunos elegantes, otros técnicos)
- Duplicación de textos similares
- Difícil mantener la voz de Lucien consistentemente
- Keyboards definidos separadamente de los mensajes
- Cambiar un saludo requiere buscar en múltiples archivos

### Guía de Estilo Existente

Existe `docs/guia-estilo.md` con 410 líneas que definen:
- Personalidad de Lucien (mayordomo sofisticado, observador, misterioso)
- Patrones de diálogo (inicios, transiciones, referencias a Diana, despedidas)
- Terminología característica ("visitante", "círculo exclusivo", "moneda especial")
- Estructura visual con emojis (🎩 para Lucien, 🌸 para Diana, etc.)
- Clase base LucienVoice con métodos de ejemplo

### Migración

El refactor debe ser completo pero seguro:
- Todos los handlers deben migrar al nuevo servicio
- Los tests existentes deben seguir pasando
- La funcionalidad actual no debe cambiar (mismas respuestas, mismo flujo)
- Solo cambia dónde está definido el contenido

## Constraints

- **Tech stack**: Python 3.12.12, aiogram 3.4.1, SQLAlchemy 2.0.25 — No introducir nuevas dependencias pesadas
- **Platform**: Optimizado para Termux (ambiente lightweight) — Evitar generadores de templates complejos (ej: no Jinja2)
- **Compatibilidad**: Debe integrarse con ServiceContainer existente — Seguir patrón de lazy loading
- **Testing**: Todos los tests E2E actuales deben seguir pasando — No romper funcionalidad existente
- **Performance**: Sin overhead significativo — Mensajes deben generarse en <10ms
- **Memoria**: Sin cachés grandes en memoria — Sistema debe ser liviano como los servicios existentes
- **Deployment**: Sin cambios en main.py más allá de importar el nuevo servicio — Mínima invasión

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Sistema híbrido: métodos estáticos + string templates | Pool de variaciones necesita flexibilidad; métodos estáticos mantienen simplicidad y performance; evita overhead de Jinja2 en Termux | — Pending |
| Organización por flujo de navegación | Alineado con estructura mental del usuario (main_menu, vip, free) vs técnico (greetings, errors); facilita encontrar mensajes relacionados | — Pending |
| Keyboards integrados con mensajes | Cada mensaje conoce sus acciones asociadas; previene desincronización entre texto y botones; API más limpia para handlers | — Pending |
| Refactor completo vs gradual | Mejor consistencia total; evita mantener dos sistemas en paralelo; proyecto pequeño permite refactor completo sin riesgo alto | — Pending |
| Variaciones aleatorias con ponderación | Algunas frases más "Lucien" que otras; ponderación permite controlar frecuencia; seed opcional para testing determinístico | — Pending |
| Sin i18n por ahora | Español es único idioma necesario; i18n agregaría complejidad sin beneficio inmediato; estructura extensible permite agregarlo después | — Pending |

---
*Last updated: 2026-01-23 after initialization*
