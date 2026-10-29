# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Service Hub is a polyglot microservices platform for personal life management. It consists of three backend services, a frontend dashboard, and a shared infrastructure layer (Docker Compose).

## Architecture

```
services/
  inventory-api/       # Java 21 / Spring Boot 4.0 — Gradle project (item-service)
  gateway-service/     # Java 21 / Spring Cloud Gateway
  accounting-service/  # Python 3.13 / FastAPI — financial transaction tracking
  stock-portfolio-service/  # Python 3.13 / FastAPI — Taiwan stock portfolio
frontend/              # Angular 21 + PrimeNG (utility CSS layer in styles.scss; Bootstrap removed)
infra/                 # Docker Compose configs for observability stack
```

Request path: browser → `frontend/proxy.conf.js` (plain forward, no rewrite) → `gateway-service`
(Spring Cloud Gateway, :8088) → the target service. The gateway routes by prefix:
- `/api/items`, `/api/shopping-list` → inventory-api
- `/api/accounting` → accounting-service
- `/api/portfolio` → stock-portfolio-service

Every service declares its own full `/api/<domain>` prefix and the gateway strips nothing, so the
path the browser calls is the path the service serves. Keep it that way when adding endpoints.

All services connect to a shared PostgreSQL instance (separate databases per service). Observability is via OpenTelemetry → OTel Collector → Tempo/Loki/Grafana.

## Common Commands

### Infrastructure
```bash
cp .env.example .env          # first-time setup
docker compose up -d           # start Postgres and the always-on logs/traces stack
```

### Inventory API (Java/Spring Boot)
```bash
cd services/inventory-api
./gradlew :item-service:bootRun          # run the service
./gradlew :item-service:test             # run tests (uses H2 in-memory DB)
./gradlew :item-service:test --tests "com.inventory.item.SomeTest"  # single test
```

### Accounting Service (Python/FastAPI)
```bash
cd services/accounting-service
uvicorn app.main:app --port 8000         # run the service
pytest                                    # run all tests
pytest tests/unit/                        # unit tests only
pytest tests/integration/                 # integration tests only
pytest tests/unit/test_foo.py::test_name  # single test
```

### Stock Portfolio Service (Python/FastAPI)
```bash
cd services/stock-portfolio-service
uvicorn app.main:app --port 8001
pytest
pytest tests/unit/
pytest tests/integration/
```

### Frontend (Angular)
```bash
cd frontend
npm install
npm start        # dev server (runs set-env.js then ng serve)
npm test         # tests via Vitest
npm run build    # production build
```

### All Services (PM2)
```bash
npx pm2 start ecosystem.config.js   # start all services at once
```

## Key Conventions

- **Environment**: Python database settings load the root `.env` without overriding process environment variables, so process environment takes precedence. The Gradle build auto-loads root `.env` into Java `bootRun` and test tasks. The frontend's `proxy.conf.js` and `set-env.js` also read from root `.env`.
- **Python service structure**: Both Python services follow identical layout — `app/{main,database,tracing,models/,routers/,schemas/,services/}`.
- **Java structure**: Standard Spring layered architecture under `com.inventory.item` — controller → service → repository, with DTOs via MapStruct, Lombok for boilerplate.
- **Testing**: Java tests use H2 in-memory DB. Python tests are split into `unit/` and `integration/` directories.
- **Observability**: Each service has `tracing.py` or Spring auto-config for OpenTelemetry. Traces flow through the OTel Collector (ports 4317/4318).
