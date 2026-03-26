# Phase 15: Health Check & Railway Preparation

**Status:** ✅ COMPLETE
**Plans:** 5 (including 1 gap closure)
**Duration:** ~35 minutes
**Dependencies:** Phase 14 (Database Migration Foundation)

---

## Overview

Phase 15 implements health monitoring infrastructure and prepares the bot for Railway deployment. This phase adds a FastAPI health check endpoint, configures concurrent execution of bot and health API, creates Railway deployment configuration, implements environment variable validation with webhook/polling mode switching, and fixes graceful shutdown issues.

## Goals

1. **Health Monitoring (HEALTH-01 to HEALTH-05)**
   - HTTP `/health` endpoint for Railway monitoring
   - Bot and database connectivity verification
   - 200 OK when healthy, 503 Service Unavailable when degraded
   - Separate FastAPI server on port 8000
   - Concurrent execution with bot

2. **Railway Preparation (RAIL-01 to RAIL-05)**
   - Railway.toml with health check configuration
   - Production Dockerfile with multi-stage build
   - Environment variable validation and documentation
   - Webhook/polling mode switching via WEBHOOK_MODE
   - Deployment documentation in README

3. **Graceful Shutdown (Gap Closure)**
   - Bot responds to Ctrl+C within 10 seconds
   - Health API stops cleanly on shutdown
   - Port reuse with SO_REUSEADDR for rapid restarts
   - Retry logic for port binding conflicts

---

## Plans

### Plan 15-01: FastAPI Health Check Endpoint ✅
**Wave:** 1 | **Duration:** ~10 min

Create a FastAPI application with `/health` endpoint that monitors bot token validity and database connectivity.

**Deliverables:**
- `bot/health/check.py` - Health check utilities
- `bot/health/endpoints.py` - FastAPI app with /health endpoint
- `requirements.txt` - FastAPI and uvicorn dependencies

---

### Plan 15-02: Concurrent Bot and Health API Execution ✅
**Wave:** 2 | **Duration:** ~10 min

Implement concurrent execution of aiogram bot and FastAPI health API using asyncio tasks.

**Deliverables:**
- `bot/health/runner.py` - Health API server runner with uvicorn
- `main.py` - Start/stop health server in callbacks

---

### Plan 15-03: Railway.toml and Dockerfile Configuration ✅
**Wave:** 3 | **Duration:** ~15 min

Create Railway deployment configuration files.

**Deliverables:**
- `Railway.toml` - Railway deployment configuration
- `Dockerfile` - Multi-stage production Docker image
- `.dockerignore` - Build optimization exclusions

---

### Plan 15-04: Environment Variable Validation ✅
**Wave:** 4 | **Duration:** ~10 min

Implement environment variable validation and webhook/polling mode switching.

**Deliverables:**
- `config.py` - Enhanced validation, WEBHOOK_MODE support
- `main.py` - Mode detection and startup logic

---

### Plan 15-05: Graceful Shutdown Fix (Gap Closure) ✅
**Wave:** 1 | **Duration:** ~9 min

Fix bot not responding to Ctrl+C and health API port conflicts.

**Problem:** Bot hung for 150 seconds on Ctrl+C due to AiohttpSession(120) + polling timeout(30)

**Solution:**
- Reduced timeouts from 150s to 10s (AiohttpSession and polling)
- Added SO_REUSEADDR for port reuse on rapid restarts
- Implemented retry logic (3 attempts) for port binding
- Enhanced shutdown logging

**Deliverables:**
- `main.py` - Reduced timeouts, better logging
- `bot/health/runner.py` - Retry logic, SO_REUSEADDR, graceful error handling

---

## Requirements Mapping

| Requirement | Plans |
|-------------|-------|
| HEALTH-01: Endpoint HTTP /health retorna estado del bot | 15-01, 15-02 |
| HEALTH-02: Health check verifica conexión a base de datos | 15-01 |
| HEALTH-03: Health check retorna 200 OK / 503 según estado | 15-01 |
| HEALTH-04: Health check en puerto separado (FastAPI + uvicorn) | 15-01, 15-02 |
| HEALTH-05: Bot y API de salud corren concurrentemente | 15-02 |
| RAIL-01: Railway.toml configurado con health check | 15-03 |
| RAIL-02: Dockerfile creado para despliegue en Railway | 15-03 |
| RAIL-03: Variables de entorno requeridas documentadas | 15-03, 15-04 |
| RAIL-04: Validación de variables de entorno al inicio | 15-04 |
| RAIL-05: Bot puede cambiar entre polling y webhook vía ENV | 15-04 |

---

## Execution Order

```
Wave 1: 15-01 (FastAPI Health Check Endpoint)
    ↓
Wave 2: 15-02 (Concurrent Execution)
    ↓
Wave 3: 15-03 (Railway Configuration)
    ↓
Wave 4: 15-04 (ENV Validation & Mode Switching)
    ↓
Gap Closure: 15-05 (Graceful Shutdown Fix)
```

---

## Key Technical Decisions

1. **Health Check Architecture**
   - Separate FastAPI server instead of aiogram endpoint
   - Runs concurrently in same event loop (not separate process)
   - Independent monitoring even if bot fails

2. **Railway Configuration**
   - Multi-stage Docker build for smaller image size
   - Non-root user for security
   - Health check path: `/health` on port 8000

3. **Graceful Shutdown**
   - 10-second timeout balance (fast shutdown + reliable networks)
   - SO_REUSEADDR for rapid restarts (handles TIME_WAIT)
   - Retry logic for transient port conflicts
   - Graceful degradation (bot works without health API)

4. **Webhook/Polling Mode**
   - WEBHOOK_MODE="polling" (default) for local development
   - WEBHOOK_MODE="webhook" for Railway production

---

## Artifacts Created

**Health Module:**
- `bot/health/__init__.py` - Module exports
- `bot/health/check.py` - Health check utilities (157 lines)
- `bot/health/endpoints.py` - FastAPI endpoints (102 lines)
- `bot/health/runner.py` - Server runner with retry logic (179 lines)

**Deployment Files:**
- `Railway.toml` - Railway configuration (20 lines)
- `Dockerfile` - Multi-stage build (55 lines)
- `.dockerignore` - Build exclusions (65 lines)

**Integration:**
- `requirements.txt` - FastAPI + uvicorn
- `config.py` - HEALTH_PORT, HEALTH_HOST, WEBHOOK_MODE
- `main.py` - Health API lifecycle management

---

## Success Metrics

- ✅ Health check endpoint returns 200 OK when healthy
- ✅ Health check returns 503 when degraded
- ✅ Bot and health API run concurrently
- ✅ Ctrl+C stops bot within 10 seconds (was 150s)
- ✅ No orphaned processes after shutdown
- ✅ Rapid restart works without port conflicts
- ✅ Railway.toml and Dockerfile production-ready
- ✅ Environment variables validated on startup

---

## Phase 15 Complete ✅

**Verified:** 2026-01-29
**Status:** 6/6 must-haves verified
**Score:** PASSED

All requirements satisfied. Ready for Phase 16: Testing Infrastructure.

---

## Next Steps

**Phase 16: Testing Infrastructure**
- pytest-asyncio configuration
- Test fixtures (test_db, mock_bot, container)
- In-memory database for test isolation

`/gsd:discuss-phase 16` - Gather context and clarify approach
