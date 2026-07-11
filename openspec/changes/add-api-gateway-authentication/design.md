## Context

Home Service Hub currently uses the Angular development proxy as its browser-facing router. Inventory, Accounting, and Stock Portfolio have separate host ports and do not share an identity, authorization, or rate-limit boundary. Recent hardening changed backend and infrastructure listeners to loopback by default, but the frontend remains LAN/VPN reachable and forwards requests without authenticating them.

The system spans Spring Boot, FastAPI, Angular, Docker Compose, and PM2. The design must work for interactive household users and non-interactive AI agents, preserve end-to-end trace context, avoid leaking tokens into observability data, and remain operable on one household server without introducing a distributed-platform burden.

## Goals / Non-Goals

**Goals:**

- Provide one supported API origin and stable path namespace for all clients.
- Add standards-based login and short-lived access tokens without implementing identity cryptography locally.
- Enforce least privilege independently at the gateway and every backend.
- Keep upstream services inaccessible from LAN/VPN clients.
- Support both Angular users and scoped AI-agent clients.
- Add useful abuse controls and security-safe operational signals.
- Provide a staged migration and rollback path that does not require a flag-day deployment.

**Non-Goals:**

- Public Internet exposure, multi-tenant signup, social identity providers, or account self-registration.
- Replacing service-specific business validation with gateway rules.
- Building a custom identity provider, OAuth implementation, or WebAuthn server.
- Kubernetes, service discovery, multi-region availability, or distributed rate limiting in the first deployment.
- Fine-grained row-level ownership for household data; authorization initially protects service capabilities and administrative operations.
- Completing the separate private-image/presigned-URL roadmap item.

## Decisions

### D1: Use a dedicated Spring Cloud Gateway Server MVC service

Create `services/gateway-service` on Java 21 and Spring Boot 4, using the compatible Spring Cloud 2025.1.x release-train BOM. The gateway owns external API routing and cross-cutting HTTP policy; it contains no business logic and no database access.

Server MVC is preferred over a custom proxy because routing, OAuth2 integration, filters, actuator health, and rate limiting are maintained framework capabilities. It is preferred over the reactive variant because expected household traffic does not require a reactive runtime and MVC aligns with the repository's existing Java operational model. Caddy remains an optional future outer TLS proxy, not the application authorization boundary.

### D2: Make the gateway the only supported API entry point

The gateway will preserve these client-visible prefixes:

| External path | Upstream | Upstream path behavior |
| --- | --- | --- |
| `/api/items/**` | Inventory | Preserve path |
| `/api/shopping-list/**` | Inventory | Preserve path |
| `/api/accounting/**` | Accounting | Strip `/api/accounting` as the current proxy does |
| `/api/portfolio/**` | Stock Portfolio | Preserve path |
| `/minio/inventory-items/**` | MinIO | Temporary GET/HEAD-only compatibility route; strip `/minio` |
| `/otlp/**` | OTel Collector HTTP | Browser telemetry compatibility route with strict method, body-size, and rate limits |

In Compose, only the frontend and gateway are published to the host; application upstreams use private service DNS. In PM2/local mode, upstreams remain on `127.0.0.1`. The Angular development server proxies API paths only to the gateway and is not a security boundary.

The gateway removes untrusted forwarding headers and emits its own `Forwarded`/`X-Forwarded-*` values. Requests receive a bounded body size, header size, and timeout. Route misses return a generic `404`; upstream failures return a generic `502/503` without internal hostnames.

### D3: Use Keycloak as the identity provider

Keycloak owns credentials, login UI, sessions, signing keys, client registration, and role/scope claims. (WebAuthn/passkeys were dropped post-implementation — see tasks 2.5 — in favor of password + long remember-me sessions.) Realm configuration is exported as reviewable bootstrap configuration with secrets injected separately. Self-registration is disabled and the initial administrator is bootstrapped from secrets that must be rotated after first use.

The Angular application is a public OpenID Connect client using Authorization Code flow with S256 PKCE, exact redirect URIs, and exact web origins. Access and refresh tokens remain in memory and are never written to localStorage, sessionStorage, URLs, logs, or telemetry. Reload may require a Keycloak session check or a fresh redirect.

AI agents use separate confidential clients and Client Credentials grants. Each agent receives its own client, secret, and narrow scopes; agents never reuse a household user's password or browser token. Client secrets are stored only in local secret configuration and are independently revocable.

### D4: Validate authorization at both gateway and services

The gateway validates issuer, signature, expiry, intended audience, and route-level scopes before forwarding. It relays the original bearer token downstream. Each backend independently performs the same cryptographic validation and enforces its own endpoint-level roles/scopes, so direct or accidentally exposed upstream access does not bypass authorization.

Initial authorities are:

- `household-user`: normal interactive access to Inventory, Accounting, and Portfolio read/write operations.
- `household-admin`: user-management-adjacent and destructive maintenance operations in addition to normal access.
- Service scopes such as `inventory.read`, `inventory.write`, `accounting.read`, `accounting.write`, `portfolio.read`, and `portfolio.write` for agents and explicit route policies.

Human roles are mapped to service scopes in Keycloak. Backends authorize scopes rather than depending solely on a broad realm role. Public exceptions are an explicit allowlist limited to gateway liveness/readiness, OIDC login callbacks handled by Spring Security, constrained browser telemetry ingestion, and temporary public inventory image reads if required by current UI behavior. Backend actuator and API documentation endpoints are never public through the gateway.

### D5: Use local Bucket4j rate limits first

The first deployment runs one gateway instance and uses Bucket4j with an in-process Caffeine-backed store. Authenticated business traffic is keyed by token subject/client ID plus route class; unauthenticated traffic is keyed by trusted client IP plus route class. Login endpoints remain served by Keycloak and receive separate Keycloak/edge controls.

Limits are configuration, not hard-coded policy. Rejections return `429`, a stable JSON error code, and `Retry-After`. Rate-limit events record route ID, principal type, and a hashed/pseudonymous key but never raw access tokens, credentials, or full query strings. Redis is deferred until multiple gateway instances require shared counters.

### D6: Treat credentials and authorization metadata as sensitive telemetry

Gateway access logs and traces redact `Authorization`, `Cookie`, `Set-Cookie`, OAuth codes, tokens, client secrets, and configured sensitive query parameters. Token claims are not recorded wholesale. A stable internal principal category and optional pseudonymous subject hash may be used for security metrics; raw subject identifiers require an explicit trusted-debug switch.

W3C trace context continues across the gateway. Incoming trace headers are validated/bounded before propagation, and authentication failures still receive a server-generated trace ID for troubleshooting.

### D7: Fail closed for protected APIs

If Keycloak discovery/signing keys are unavailable and no valid cached key can verify a token, protected requests fail with `401/503` rather than bypassing authentication. Existing valid sessions may continue only within normal locally cached key and token validity. Readiness reports unhealthy when required identity configuration is invalid, while liveness remains independent so process supervisors do not create restart loops.

## Risks / Trade-offs

- [Gateway becomes a single point of failure] → Add explicit liveness/readiness, upstream timeouts, supervised restart, and a rollback path; household scale does not initially justify multiple instances.
- [Keycloak adds memory and operational complexity] → Pin a supported version, use declarative realm bootstrap, persistent backup, health checks, and documented admin recovery.
- [SPA-held bearer tokens are exposed to successful XSS] → Keep tokens in memory, enforce CSP and dependency hygiene, use short lifetimes, avoid unsafe HTML, and leave a future BFF migration possible if the threat model grows.
- [Gateway-only checks create a false trust boundary] → Require independent resource-server validation in all three backends and test direct unauthorized access.
- [Role/scope drift causes accidental over-permission] → Keep role-to-scope mapping in reviewed realm configuration and test a deny-by-default authorization matrix.
- [In-memory limits reset on restart and differ across instances] → Accept this for the single-instance phase; migrate the same policies to Redis before scaling horizontally.
- [Temporary public MinIO reads expose object URLs] → Restrict methods and prefix, preserve non-guessable object names, and replace the compatibility route when private presigned URLs are implemented.
- [Authentication rollout locks out existing clients] → Use an audit-only route inventory, staged enforcement flags, dedicated smoke-test clients, and a documented rollback window.

## Migration Plan

1. Add Keycloak and its database/realm bootstrap without changing existing request paths; create test users and agent clients from non-production secrets.
2. Add the gateway on a loopback-only test port and reproduce the current Angular proxy route contract. Verify path rewrites, uploads, images, telemetry, errors, timeouts, and trace propagation.
3. Add resource-server validation to each backend in an enforcement-disabled/audit mode where practical, then run authorization matrix tests with valid and invalid tokens.
4. Add Angular PKCE login and switch its proxy target to the gateway. Keep backend host ports loopback-only throughout.
5. Enable gateway enforcement, then backend enforcement, one service at a time. Verify browser and agent smoke tests after each cutover.
6. Remove direct backend publication from normal Compose and local runbooks. Retain an operator-only loopback diagnostic path.
7. Enable configured rate limits after observing normal traffic, then rotate all bootstrap and test credentials.

Rollback restores the prior frontend proxy routing while keeping upstreams loopback-only, disables backend enforcement through a time-bounded local emergency configuration, and stops the gateway/Keycloak additions. Database and realm state are retained for diagnosis. Rollback must never expose backend ports to `0.0.0.0`.

## Open Questions

- Confirm the initial household users and which person, if any, receives `household-admin`.
- Confirm whether every current inventory image may remain temporarily readable to authenticated-network users, or whether private presigned URLs must be pulled into this change.
- Choose concrete per-route rate-limit values after a short observation period; the specification defines behavior but not arbitrary production thresholds.
- Decide whether VPN-only HTTP is acceptable initially or whether Caddy-managed HTTPS is required in the first deployment.

