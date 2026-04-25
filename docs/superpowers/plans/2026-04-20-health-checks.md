# Health Checks + Docker Compose Healthcheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/health` liveness endpoints to all three backend services and wire `healthcheck` blocks into `docker-compose.yml` so orchestration can gate startup order on readiness instead of plain `depends_on`.

**Architecture:** Each service returns a minimal JSON payload (status + optional DB probe) with HTTP 200 when healthy, non-200 when degraded. Docker compose adds `healthcheck` for Postgres and each service, then `depends_on.condition: service_healthy` so dependents wait for Postgres (and services wait for themselves to be up) before traffic.

**Tech Stack:** FastAPI (Python), Spring Boot Actuator (Java), Docker Compose.

---

## File Structure

- Create: `services/accounting-service/app/routers/health.py` — FastAPI router exposing `/health` and `/health/ready`
- Create: `services/stock-portfolio-service/app/routers/health.py` — same pattern
- Modify: `services/accounting-service/app/main.py` — register health router
- Modify: `services/stock-portfolio-service/app/main.py` — register health router
- Modify: `services/inventory-api/item-service/build.gradle.kts` — add `spring-boot-starter-actuator`
- Modify: `services/inventory-api/item-service/src/main/resources/application.yml` — expose `/actuator/health` with DB probe
- Modify: `docker-compose.yml` — add healthcheck blocks; switch `depends_on` to `condition: service_healthy`
- Create: `services/accounting-service/tests/unit/test_health.py`
- Create: `services/stock-portfolio-service/tests/unit/test_health.py`

---

### Task 1: Add health router to accounting-service

**Files:**
- Create: `services/accounting-service/app/routers/health.py`
- Create: `services/accounting-service/tests/unit/test_health.py`
- Modify: `services/accounting-service/app/main.py`

- [ ] **Step 1: Write failing test**

Create `services/accounting-service/tests/unit/test_health.py`:

```python
from fastapi.testclient import TestClient


def test_liveness_returns_200(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_200_when_db_reachable(client: TestClient):
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
```

Note: existing `tests/conftest.py` already provides a `client` fixture. Inspect it first (`cat services/accounting-service/tests/conftest.py`) to confirm the fixture name and adjust if different.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd services/accounting-service
pytest tests/unit/test_health.py -v
```

Expected: FAIL with 404 (route not yet registered).

- [ ] **Step 3: Create health router**

Create `services/accounting-service/app/routers/health.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness():
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception as exc:
        return {"status": "degraded", "database": f"error: {exc.__class__.__name__}"}
```

- [ ] **Step 4: Register router in main.py**

Edit `services/accounting-service/app/main.py`. Find the block:

```python
from .routers import transactions, cards, recurring, categories, payment_methods
```

Change to:

```python
from .routers import transactions, cards, recurring, categories, payment_methods, health
```

Then after the other `app.include_router(...)` lines, add:

```python
app.include_router(health.router)
```

- [ ] **Step 5: Run test — verify pass**

```bash
pytest tests/unit/test_health.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add services/accounting-service/app/routers/health.py \
        services/accounting-service/app/main.py \
        services/accounting-service/tests/unit/test_health.py
git commit -m "feat(accounting): add /health and /health/ready endpoints"
```

---

### Task 2: Add health router to stock-portfolio-service

**Files:**
- Create: `services/stock-portfolio-service/app/routers/health.py`
- Create: `services/stock-portfolio-service/tests/unit/test_health.py`
- Modify: `services/stock-portfolio-service/app/main.py`

- [ ] **Step 1: Write failing test**

Create `services/stock-portfolio-service/tests/unit/test_health.py` with the same content as Task 1 Step 1 test file. Same reasoning.

- [ ] **Step 2: Verify failure**

```bash
cd services/stock-portfolio-service
pytest tests/unit/test_health.py -v
```

Expected: FAIL (404).

- [ ] **Step 3: Create health router**

Create `services/stock-portfolio-service/app/routers/health.py` with **identical** content to Task 1 Step 3. (Do not import from accounting-service — these are separate services.)

- [ ] **Step 4: Register router in main.py**

Edit `services/stock-portfolio-service/app/main.py`. Find:

```python
from .routers import portfolio
```

Change to:

```python
from .routers import portfolio, health
```

Then after `app.include_router(portfolio.router)` add:

```python
app.include_router(health.router)
```

- [ ] **Step 5: Verify pass**

```bash
pytest tests/unit/test_health.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add services/stock-portfolio-service/app/routers/health.py \
        services/stock-portfolio-service/app/main.py \
        services/stock-portfolio-service/tests/unit/test_health.py
git commit -m "feat(stock): add /health and /health/ready endpoints"
```

---

### Task 3: Enable Spring Boot Actuator on inventory-api

**Files:**
- Modify: `services/inventory-api/item-service/build.gradle.kts`
- Modify: `services/inventory-api/item-service/src/main/resources/application.yml`

- [ ] **Step 1: Add actuator dependency**

Edit `services/inventory-api/item-service/build.gradle.kts`. Find the `// 4.2 Validation` block (line 32-33). **After** that block, add:

```kotlin
    // 4.3 Actuator (health + metrics)
    implementation("org.springframework.boot:spring-boot-starter-actuator")
```

- [ ] **Step 2: Configure actuator in application.yml**

Edit `services/inventory-api/item-service/src/main/resources/application.yml`. **Append** to the file (after the `minio:` block):

```yaml

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: when-authorized
      probes:
        enabled: true
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
    db:
      enabled: true
```

- [ ] **Step 3: Build and start service locally to verify**

```bash
cd services/inventory-api
./gradlew :item-service:build -x test
./gradlew :item-service:bootRun &
sleep 15
curl -sf http://localhost:${INVENTORY_ITEM_SERVICE_PORT}/actuator/health | tee /dev/stderr | grep -q '"status":"UP"'
```

Expected: grep exits 0 (status UP). Stop the service: `kill %1`.

If the port env var isn't expanded in your shell, source `.env` first: `set -a && source .env && set +a`.

- [ ] **Step 4: Commit**

```bash
git add services/inventory-api/item-service/build.gradle.kts \
        services/inventory-api/item-service/src/main/resources/application.yml
git commit -m "feat(inventory): enable Spring Boot Actuator health endpoints"
```

---

### Task 4: Add healthcheck blocks to docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add Postgres healthcheck**

Edit `docker-compose.yml`. In the `postgres:` service block (lines 3-15), **add** after the `networks:` line:

```yaml
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 10
```

- [ ] **Step 2: Add inventory-item-service healthcheck + gated depends_on**

In the `inventory-item-service:` block (lines 28-41). Replace:

```yaml
    depends_on:
      - postgres
    networks:
      - inventory-net
```

with:

```yaml
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - inventory-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```

Note: the container may not have `curl` pre-installed depending on base image. If the healthcheck fails with "curl: not found" when you run `docker compose ps`, change the test to use `wget`:

```yaml
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8080/actuator/health"]
```

If neither is available, change the Dockerfile at `services/inventory-api/Dockerfile` to install curl, or use the Spring Boot image's built-in `/actuator/health` via `HEALTHCHECK` in the Dockerfile instead.

- [ ] **Step 3: Add accounting-service healthcheck + gated depends_on**

In the `accounting-service:` block (lines 43-55), apply the same pattern:

```yaml
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - inventory-net
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
```

- [ ] **Step 4: Add stock-portfolio-service healthcheck + gated depends_on**

In the `stock-portfolio-service:` block (lines 57-69), same pattern but change the port in the test to `8001`:

```yaml
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - inventory-net
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8001/health').status==200 else 1)"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
```

- [ ] **Step 5: Validate compose file**

```bash
docker compose config > /dev/null
```

Expected: no errors.

- [ ] **Step 6: Bring up infrastructure + apps and verify health**

```bash
docker compose --profile apps up -d
sleep 60
docker compose ps
```

Expected: all services show `healthy` status. If any are `unhealthy`, `docker compose logs <service>` and diagnose.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml
git commit -m "chore(infra): add healthcheck blocks for postgres + backend services"
```

---

## Self-Review Checklist

- [ ] Accounting + stock tests cover both `/health` (no DB) and `/health/ready` (with DB probe)
- [ ] Every `depends_on` for a service that uses Postgres gates on `condition: service_healthy`
- [ ] No hardcoded passwords or secrets introduced
- [ ] Java actuator only exposes `health,info,metrics` (not `env`, `beans`, etc. — security)
- [ ] All 4 commits are self-contained and pass tests individually

## Out of Scope (do not do in this plan)

- Metrics scraping dashboards
- Auth on actuator endpoints (fine for internal network for now)
- RabbitMQ / MinIO healthchecks (not currently consumed by services)
