# Remove Keycloak + nginx single entry (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop all Keycloak/OIDC/JWT auth from home-service-hub and serve the app through one nginx container at `http://<ip>/hub/`, over plain HTTP.

**Architecture:** A new repo `~/projects/infra` owns an unprivileged nginx container, the only thing on the LAN. It serves a landing page at `/`, the Angular build at `/hub/`, and proxies `/api/*`, `/images/inventory-items/*` and `/otlp/*` to the gateway on the Mac (`host.docker.internal:8088`, which binds `127.0.0.1`). The gateway, the backends and the frontend lose every auth layer.

**Tech Stack:** Spring Boot 4 / Spring Cloud Gateway (webmvc), FastAPI + shared-python-lib, Angular 21, nginx (`nginxinc/nginx-unprivileged`, alpine), Docker Compose on OrbStack, pm2.

**Spec:** `docs/superpowers/specs/2026-11-19-remove-keycloak-design.md`

## Global Constraints

- No login of any kind, including Basic auth and static tokens.
- Gateway and backends keep binding `127.0.0.1`. Nothing new binds `0.0.0.0` except nginx.
- nginx proxies only `/api/items`, `/api/shopping-list`, `/api/accounting`, `/api/portfolio`, `/images/inventory-items`, `/otlp`. Every other path except `/` and `/hub/` returns 404.
- `client_max_body_size 15m`; `server_tokens off`; 4xx bodies pass through untouched; only 500/502/503/504 get a generic page.
- Mount `frontend/dist` (the parent folder), never `browser/`, because `ng build` recreates its output folder.
- Pin the nginx image by digest, the same way the existing compose files do.
- Do not touch `~/.hermes`, the Loki/Grafana/Tempo/OTel services, or Postgres.
- Python tests run via `uv run --with-requirements requirements.txt --with-requirements requirements-dev.txt -m pytest`. Lint with `uvx ruff check services scripts`.

## Review Focus

1. Refreshing a deep link such as `/hub/portfolio/dividends` must return the app, not a 404. Test in Task 6.
2. A photo upload of roughly 12MB must not be rejected by nginx with 413. Test in Task 6.
3. Backend validation errors (4xx JSON) must still reach the UI toast. nginx must not swap them for an HTML page. Test in Task 6.
4. Stored photo URLs (`/images/inventory-items/<uuid>.jpg`) live at the root, not under `/hub/`, and must load. Test in Task 6.
5. Every request now shares one rate-limit bucket, keyed on the nginx source address. A normal dashboard burst must not hit 429. Test in Task 6.

---

### Task 1: Spike: can a container reach the gateway on host loopback? (controller, before anything else)

- [ ] Run: `docker run --rm curlimages/curl -s -o /dev/null -w '%{http_code}\n' http://host.docker.internal:8088/actuator/health/liveness`
  Expected: `200`. If it isn't, **stop and report to the user**. Do not rebind the gateway to the LAN.

### Task 2: Gateway: remove Spring Security entirely

Route matching already rejects unknown paths with 404, and actuator only exposes `health`. Spring Security therefore adds nothing once JWT is gone, so it goes away completely. This deviates from the spec's "whitelist SecurityConfig" and reaches the same outcome with less code.

**Files:**
- Delete: `services/gateway-service/src/main/java/com/homeservicehub/gateway/security/` (whole package)
- Delete: `services/gateway-service/src/test/java/com/homeservicehub/gateway/security/` (whole package)
- Modify: `services/gateway-service/build.gradle.kts`. Drop `spring-boot-starter-oauth2-resource-server` and `spring-security-test`.
- Modify: `services/gateway-service/src/main/resources/application.yml`. Drop the `security.oidc` block.
- Modify: `services/gateway-service/src/main/java/com/homeservicehub/gateway/ratelimit/RateLimitFilter.java`.
  - `trustedIdentity` returns `"source:" + request.getRemoteAddr()`.
  - Remove the JWT imports and branch, and the `principal_type` branch in the log line.
- Check: `RateLimitFilter` is still registered as a servlet filter now that `SecurityConfig.addFilterAfter` is gone. Find its `@Bean` in `ratelimit/`. A `Filter` bean is auto-registered by Boot; confirm it.
- Test: `services/gateway-service/src/test/java/com/homeservicehub/gateway/ratelimit/RateLimitFilterTest.java`, plus a new `services/gateway-service/src/test/java/com/homeservicehub/gateway/GatewayExposureTest.java`

- [ ] **Step 1: Write the failing tests.**
  - `GatewayExposureTest`: `@SpringBootTest(webEnvironment = RANDOM_PORT)` with `TestRestTemplate`.
    - `unknownPathIs404`: `GET /nope` gives 404.
    - `actuatorEnvNotExposed`: `GET /actuator/env` gives 404.
    - `livenessIsUp`: `GET /actuator/health/liveness` gives 200.
    - `apiRequestWithoutTokenIsNotRejected`: `GET /api/accounting/transactions` with no `Authorization` header gives a status that is neither 401 nor 403. The upstream may be down in tests, so 5xx/502 is acceptable.
  - `RateLimitFilterTest`: `trustedIdentity(request with remoteAddr 10.0.0.5)` equals `"source:10.0.0.5"`.
- [ ] **Step 2:** `cd services/inventory-api && ./gradlew -p ../gateway-service test`. Expected: the new tests fail (401 on the API test, compile error on `trustedIdentity`).
- [ ] **Step 3:** Make the deletions and edits above.
- [ ] **Step 4:** Run the same command. Expected: BUILD SUCCESSFUL. Also check that `git grep -n -i -E 'oauth2|jwt|oidc' services/gateway-service` is empty.
- [ ] **Step 5: Commit:** `refactor(gateway): drop JWT auth and Spring Security`

### Task 3: inventory-api: remove Spring Security

**Files:**
- Delete: `services/inventory-api/item-service/src/main/java/com/inventory/item/config/ResourceServerSecurityConfig.java` and `.../config/AuditModeSecurityConfig.java`
- Delete: `services/inventory-api/item-service/src/test/java/com/inventory/item/config/ResourceServerSecurityConfigTest.java`
- Modify: `services/inventory-api/item-service/build.gradle.kts`. Drop `spring-boot-starter-security`, `spring-boot-starter-oauth2-resource-server` and `spring-security-test`.
- Modify: `services/inventory-api/item-service/src/main/resources/application.yml`. Drop the `security.oauth2` block (lines 5-10).
- Modify: `services/inventory-api/item-service/src/main/java/com/inventory/item/config/WebConfig.java:12`. The `ALLOWED_ORIGINS` default becomes `http://localhost:4200,http://localhost,http://192.168.0.100`.
- Test: one new test in the existing controller test class for items. Put it in a new `src/test/java/com/inventory/item/controller/NoAuthTest.java` if no MockMvc class fits.

- [ ] **Step 1: Write the failing test** `postWithoutTokenSucceedsEvenWithEnforcementFlag`.
  - Use `@SpringBootTest` + `@AutoConfigureMockMvc`, with `@TestPropertySource(properties = "AUTH_ENFORCEMENT_ENABLED=true")`.
  - `GET /api/items` with no `Authorization` gives 200.
- [ ] **Step 2:** `cd services/inventory-api && ./gradlew :item-service:test --tests '*NoAuthTest'`. Expected: FAIL with 401.
- [ ] **Step 3:** Make the deletions and edits above.
- [ ] **Step 4:** Run `./gradlew :item-service:test` (full suite). Expected: BUILD SUCCESSFUL. Also check that `git grep -n -i -E 'oauth2|jwt|security' services/inventory-api/item-service/src/main` returns nothing auth-related.
- [ ] **Step 5: Commit:** `refactor(inventory): drop JWT resource server`

### Task 4: Python services: remove shared auth

**Files:**
- Delete: `services/shared-python-lib/shared_lib/auth.py` and `services/shared-python-lib/tests/test_auth.py`
- Modify: `services/shared-python-lib/shared_lib/app_factory.py`. Remove the `install_resource_server` import, the `auth_service` parameter and the `if auth_service:` block.
- Modify: `services/accounting-service/app/main.py:21` and `services/stock-portfolio-service/app/main.py:72`. Remove the `auth_service=` argument.
- Modify: `services/shared-python-lib/pyproject.toml:14`. Remove `PyJWT[crypto]`.
- Modify: `services/shared-python-lib/shared_lib/config.py:28`. The `allowed_origins` default becomes `"http://localhost:4200,http://localhost,http://192.168.0.100"`.
- Test: `services/shared-python-lib/tests/test_app_factory.py`

- [ ] **Step 1: Write the failing test** `test_requests_need_no_token_even_with_enforcement_env(monkeypatch)`.
  - Set `AUTH_ENFORCEMENT_ENABLED=true`.
  - Call `create_app(...)` with one router exposing `GET /api/accounting/ping`.
  - Use `TestClient` with no headers. Assert the response is 200.
  - Also assert `"auth_service" not in inspect.signature(create_app).parameters`.
- [ ] **Step 2:** Run it from `services/shared-python-lib` using the uv command (Global Constraints). Expected: FAIL.
- [ ] **Step 3:** Make the edits above.
- [ ] **Step 4:** Run the full pytest in `shared-python-lib`, `accounting-service` and `stock-portfolio-service` (each with its own requirements files), then run `uvx ruff check services scripts`. Expected: all pass. Also check that `git grep -n -i -E 'jwt|auth_service|AUTH_ENFORCEMENT' services` is empty.
- [ ] **Step 5: Commit:** `refactor(python): drop JWT resource server`

### Task 5: Frontend: no keycloak, build for `/hub/`, dev server local-only

**Files:**
- Delete: `frontend/src/app/auth/` and `frontend/src/app/interceptors/auth.interceptor.ts`
- Modify: `frontend/src/app/app.config.ts`. Remove the `authInterceptor`, `AuthService` and `provideAppInitializer` lines. The interceptor list becomes `[errorLoggingInterceptor]`, and the `inject`/`provideAppInitializer` imports go too.
- Modify: `frontend/src/app/app.routes.ts`. Remove the `authGuard` import and `canActivate`.
- Modify: `frontend/package.json`.
  - Run `npm uninstall keycloak-js` so the lockfile updates too.
  - `"start": "npm run config && ng serve"`, with no `--host`.
- Modify: `frontend/set-env.js`. Drop the `oidcUrl`/`oidcRealm`/`oidcClientId` lines and the whole `ALLOWED_HOSTS`/angular.json rewrite block.
- Modify: `frontend/angular.json`.
  - Under `build.configurations.production`, add `"baseHref": "/hub/"`.
  - Under `serve.options`, remove `host`, `allowedHosts`, `ssl`, `sslCert` and `sslKey`. Keep `proxyConfig`.
- Modify: `frontend/public/manifest.json`. `"scope": "./"` and `"start_url": "./"`.

- [ ] **Step 1:** `cd frontend && npx ng test --watch=false`. Record the baseline: 42 tests pass.
- [ ] **Step 2:** Make the edits above.
- [ ] **Step 3:** `npx ng test --watch=false`. Expected: all pass. Fix any spec that imported the deleted files.
- [ ] **Step 4:** Run `npm run build`, then `grep -o '<base href="[^"]*"' dist/inventory-ui/browser/index.html`.
  - Expected: `<base href="/hub/"`.
  - Then `grep -c keycloak -r dist/inventory-ui/browser` should print `0`. Also check that `git grep -n -i -E 'keycloak|oidc' frontend -- ':!package-lock.json'` is empty.
- [ ] **Step 5: Commit:** `refactor(frontend): drop keycloak-js and serve under /hub/`

### Task 6: `~/projects/infra`: nginx entry; hub compose, pm2, CI and env cleanup

Depends on Tasks 1 and 5 (needs `frontend/dist/inventory-ui/browser`).

**Files (new repo `~/projects/infra`, `git init`):**
- Create: `docker-compose.yml`.
  - Service `nginx`, container `home-nginx`.
  - Image `nginxinc/nginx-unprivileged:<1.x>-alpine@sha256:<digest>`. Pull it, then read the digest with `docker inspect --format '{{index .RepoDigests 0}}'`.
  - `ports: ["80:8080"]`, `read_only: true`, `tmpfs: [/tmp]`.
  - Volumes, all `:ro`:
    - `./nginx/conf.d:/etc/nginx/conf.d`
    - `./nginx/html:/srv/landing`
    - `../home-service-hub/frontend/dist:/srv/hub-dist`
  - `extra_hosts: ["host.docker.internal:host-gateway"]` only if Task 1 needed it.
  - `restart: unless-stopped`.
- Create: `nginx/conf.d/00-server.conf`. A single `server { listen 8080; }` containing:
  - `server_tokens off`, `client_max_body_size 15m` and `add_header X-Content-Type-Options nosniff always`.
  - `location = / { root /srv/landing; try_files /index.html =404; }`
  - `include /etc/nginx/conf.d/services/*.conf;`
  - `location / { return 404; }`
  - `proxy_intercept_errors on; error_page 500 502 503 504 /50x.html;`, with `location = /50x.html { root /srv/landing; internal; }`
- Create: `nginx/conf.d/services/hub.conf`. Keep it outside the top-level include glob so `server` is not included twice; adjust the include pattern if the image's default config globs `conf.d/*.conf`.
  - `location /hub/ { alias /srv/hub-dist/inventory-ui/browser/; try_files $uri $uri/ /hub/index.html; }`
  - One `location` per proxied prefix (Global Constraints). Each has `proxy_pass http://host.docker.internal:8088;`, `proxy_set_header X-Forwarded-For $remote_addr;` and `proxy_set_header X-Forwarded-Proto $scheme;`.
- Create: `nginx/html/index.html` (a list of service links; for now only `/hub/` "Home Service Hub") and `nginx/html/50x.html` (one generic sentence, no details).
- Create: `README.md`. Three lines: what it is, `docker compose up -d`, and "add a service = add a file under `nginx/conf.d/services/`".

**Files (home-service-hub):**
- Modify: `docker-compose.yml`. Remove the `keycloak-postgres` and `keycloak` services, and the `keycloak_postgres_data` volume declaration.
- Delete: tracked files under `infra/keycloak/` (realm JSON, `themes/`) and `scripts/smoke/validate-keycloak-realm.sh`.
- Modify: `ecosystem.config.js`. Remove the `frontend` app and all `AUTH_ENFORCEMENT_ENABLED` env lines (drop the now-empty `env` blocks).
- Modify: `.github/workflows/service-tests.yml`. Remove `AUTH_ENFORCEMENT_ENABLED` (line 86) and `OIDC_ISSUER_URI` (line 145).
- Modify: `.env.example`.
  - Delete `ALLOWED_HOSTS` and section 8's 15 identity keys (`OIDC_*`, `GATEWAY_JWKS_URI`, `KEYCLOAK_*`, `IDENTITY_BIND_HOST`).
  - `ALLOWED_ORIGINS=http://localhost:4200,http://localhost,http://192.168.0.100`.

- [ ] **Step 1:** `cd ~/projects/infra && docker compose config -q`. Expected: no output, exit 0.
- [ ] **Step 2:** `docker compose up -d`, then run the acceptance curls against `http://127.0.0.1`. Each must hold:
  - `curl -s -o /dev/null -w '%{http_code}' /` → `200`, and the body contains `/hub/`.
  - `/hub/` and `/hub/portfolio/dividends` → `200`, and both bodies contain `<base href="/hub/">`.
  - `/nope` → `404`. `curl -sI /hub/` has no nginx version in `Server`.
  - `/api/accounting/transactions` → `200` JSON.
  - An existing photo: `curl -sI` on one `image_url` value from `inventory` DB `items` → `200`.
  - A POST with an invalid body to an accounting endpoint gives a 4xx whose body is the backend's JSON, not HTML.
  - A ~12MB upload: `head -c 12000000 /dev/urandom > /tmp/x.jpg`, then multipart POST to the inventory image endpoint. The status must not be `413`.
  - A burst: 40 parallel `GET /api/accounting/transactions` contain no `429`.
- [ ] **Step 3:** In home-service-hub, run `docker compose config -q` and confirm `git grep -n -i -E 'keycloak|oidc|AUTH_ENFORCEMENT|ALLOWED_HOSTS' -- ':!docs' ':!openspec' ':!modify_history' ':!README.md' ':!ROADMAP.md'` is empty.
- [ ] **Step 4: Commit** both repos.
  - infra: `feat: nginx single LAN entry with /hub`
  - hub: `chore: remove keycloak from compose, pm2 and CI`

### Task 7: Docs and openspec (parallel with Task 6; disjoint files)

**Files:**
- Modify: `README.md`.
  - Architecture diagram: drop the identity subgraph, add nginx, and use the entry URL `http://<LAN-IP>/hub/`.
  - Update the startup steps (`npm run build` replaces `npm start` for the LAN; `~/projects/infra` `docker compose up -d`) and remove the Keycloak/identity paragraphs.
  - Add a note: re-add the iPhone home-screen icon from the new URL.
- Modify: `ROADMAP.md` (auth lines), `docs/security/gateway-operations.md`, `docs/security/gateway-route-matrix.md` (drop the "Required authority" column) and `CLAUDE.md` (request path: browser → nginx (`~/projects/infra`) → gateway; `proxy.conf.js` is local-dev only).
- Delete: `docs/security/keycloak-operations.md`
- Run: `openspec archive add-api-gateway-authentication --skip-specs -y`. Check `openspec archive --help` for the exact flags. Before archiving, add one line to its `proposal.md`: "Superseded 2026-11-19 by docs/superpowers/specs/2026-11-19-remove-keycloak-design.md; not implemented further."

- [ ] **Step 1:** Make the edits above.
- [ ] **Step 2:** `git grep -n -i keycloak -- README.md ROADMAP.md CLAUDE.md docs/security` returns only historical mentions ("removed 2026-11", if any).
- [ ] **Step 3: Commit:** `docs: remove keycloak, document nginx entry`

### Task 8: Cutover and acceptance (controller)

- [ ] Root `.env`: remove the same keys as `.env.example` in Task 6 and set `ALLOWED_ORIGINS` to the same value. Back up first to the scratchpad and delete the backup when done.
- [ ] Run, in order:
  - `pm2 delete frontend`
  - `pm2 restart item-service accounting-service stock-portfolio-service gateway-service`
  - `pm2 save`
  - `docker compose stop keycloak keycloak-postgres` and `docker compose rm -f keycloak keycloak-postgres`. If compose no longer knows them, use `docker rm -f` with the container names.
- [ ] Wait until item-service is really up (`lsof -iTCP:8080 -sTCP:LISTEN`). The Flyway V3 image-URL migration runs at this point.
- [ ] `lsof -iTCP -sTCP:LISTEN -nP`: on non-loopback interfaces there must be no 8180, 8443 or 4200, and `*:80` must belong to OrbStack.
- [ ] Ask the user to check on the iPhone: open `http://192.168.0.100/hub/` and use inventory (including a photo), accounting and portfolio without logging in; re-add the page to the home screen and confirm the icon is correct; then open `http://192.168.0.100/` and confirm the landing page.
- [ ] Confirm a browser trace from the session appears in Tempo through `/otlp`.
- [ ] Leave the `home-service-hub_keycloak_postgres_data` volume and the gitignored `infra/keycloak/certs` for the user to delete. Tell them the exact commands.
