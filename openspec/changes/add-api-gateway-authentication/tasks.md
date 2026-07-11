## 1. Dependency and Security Baseline

- [x] 1.1 Record the current frontend proxy route/method/path-rewrite matrix and add smoke fixtures for Inventory, Accounting, Portfolio, image, and OTLP paths before changing routing.
- [x] 1.2 Add Spring Cloud 2025.1.x dependency management compatible with the repository's Spring Boot 4.0.x version and pin the selected Keycloak container version.
- [x] 1.3 Add environment-variable templates for gateway, issuer/audience, Keycloak bootstrap, token lifetimes, and rate limits using placeholders only, and add secret files/exports to ignore rules.
- [x] 1.4 Document the initial route authorization matrix mapping every endpoint group and HTTP method to public, read, write, or admin authority, with deny-by-default treatment for unknown routes.

## 2. Keycloak Identity Provider

- [x] 2.1 Add Keycloak and its persistent database/user configuration to local Compose with loopback/private-network bindings and liveness/readiness health checks.
- [x] 2.2 Create reviewable realm bootstrap configuration with self-registration disabled, exact frontend redirect URIs/web origins, short token lifetimes, and no committed credentials.
- [x] 2.3 Define `household-user` and `household-admin` roles plus Inventory, Accounting, and Portfolio read/write client scopes and their role mappings.
- [x] 2.4 Configure the Angular public client for Authorization Code with S256 PKCE and configure at least one separately revocable confidential smoke-test agent client using Client Credentials.
- [x] 2.5 Configure WebAuthn/passkey as an available household-user authentication method and document first-user enrollment plus administrator recovery.
- [ ] 2.6 Add a repeatable identity smoke test covering discovery, user login, client-credentials token issuance, wrong redirect rejection, disabled client rejection, and scope/audience claims.

## 3. Gateway Service and Routing

- [x] 3.1 Scaffold `services/gateway-service` with Java 21, Spring Boot 4, Spring Cloud Gateway Server MVC, OAuth2 resource server, validation, actuator, tracing, and test support.
- [x] 3.2 Implement Inventory, Shopping List, Accounting, and Portfolio routes with exact current path-preservation/rewrite behavior and configuration-driven loopback/private-network upstream URIs.
- [x] 3.3 Implement constrained MinIO Inventory image GET/HEAD and browser OTLP compatibility routes with explicit method, content-type, body-size, and destination-prefix rules.
- [ ] 3.4 Add request/header size limits, upstream connection/response timeouts, generic route/upstream error mapping, and correlation IDs without internal-address disclosure.
- [ ] 3.5 Sanitize untrusted forwarding headers, create authoritative forwarding metadata, bound incoming trace headers, and propagate valid W3C trace context.
- [ ] 3.6 Configure operator-only liveness/readiness so invalid required identity/route configuration fails readiness without failing process liveness, and ensure detailed actuator/API-doc paths are not routed publicly.
- [ ] 3.7 Add gateway integration tests for every route/rewrite, unsupported methods, route misses, oversized bodies, spoofed forwarding headers, upstream timeout/failure, and liveness/readiness behavior.

## 4. Gateway Authentication and Authorization

- [x] 4.1 Configure JWT validation for trusted issuer, signature, expiry/not-before, and intended audience with fail-closed JWKS/discovery behavior.
- [x] 4.2 Implement the reviewed public allowlist and deny all other gateway routes when the token is missing or invalid.
- [x] 4.3 Enforce route/method service scopes and admin authority, relay the original bearer token to upstream services, and return stable `401`/`403` JSON errors with correlation IDs.
- [ ] 4.4 Add gateway authorization matrix tests using missing, malformed, expired, wrong-issuer, wrong-audience, under-scoped, user, admin, and agent tokens.
- [ ] 4.5 Add identity-outage tests proving unverifiable tokens fail closed while liveness remains healthy and readiness reflects unusable identity configuration.

## 5. Backend Defense in Depth

- [x] 5.1 Add Spring Security OAuth2 resource-server validation to Inventory with explicit public health exceptions and method-level scope/admin policies from the authorization matrix.
- [x] 5.2 Add JWT issuer/audience/signature validation dependencies and reusable authorization helpers to the shared Python library without logging raw claims or tokens.
- [x] 5.3 Apply the shared Python resource-server validation and endpoint scope policies to Accounting with explicit health exceptions.
- [x] 5.4 Apply the shared Python resource-server validation and endpoint scope policies to Stock Portfolio with explicit health exceptions.
- [ ] 5.5 Add service-level tests proving each backend rejects direct missing/invalid tokens and under-scoped tokens even when requests originate from a trusted internal address.
- [ ] 5.6 Add cross-service authorization matrix tests proving household users, admins, read-only agents, and write-scoped agents receive the expected `2xx`, `401`, or `403` outcome.

## 6. Angular Login and Session UX

- [x] 6.1 Add the supported Keycloak JavaScript adapter and configuration loader without embedding client secrets or environment-specific issuer URLs in committed production bundles.
- [x] 6.2 Implement application initialization, login-required handling, S256 PKCE callback processing, in-memory token lifecycle, guarded routes, and a clear authentication-loading state.
- [x] 6.3 Add an HTTP interceptor that attaches a current access token only to same-origin protected API requests and safely refreshes or reauthenticates before token expiry.
- [x] 6.4 Implement logout through Keycloak with an exact approved post-logout redirect and clear all in-memory authenticated state.
- [x] 6.5 Replace the frontend's per-service proxy targets with a single gateway target while preserving client-visible URLs.
- [ ] 6.6 Add frontend tests proving protected navigation, login callback, token attachment boundaries, refresh failure, logout, and browser reload never persist bearer/refresh tokens in web storage or URLs.

## 7. Rate Limiting and Security-Safe Telemetry

- [x] 7.1 Add Bucket4j with an in-process Caffeine-backed store and configuration-driven route-class token buckets for the single-gateway deployment.
- [x] 7.2 Resolve authenticated buckets from subject/client ID plus route class and pre-auth/public buckets from gateway-derived client address plus route class, never from raw tokens or untrusted forwarding headers.
- [x] 7.3 Return stable `429` JSON errors with correlation ID and `Retry-After`, and add deterministic tests for burst, refill, bucket separation, restart-reset documentation, and spoofed-IP behavior.
- [ ] 7.4 Redact Authorization, cookies, OAuth codes/tokens, secrets, sensitive query values, and raw token claims from gateway logs/traces while retaining route, result, latency, and correlation diagnostics.
- [ ] 7.5 Add pseudonymous rate-limit/authentication metrics and structured events, and test captured logs/telemetry to prove credentials and direct identifiers are absent.
- [x] 7.6 Add a deployment guard or prominent health warning preventing multiple active gateway instances from being treated as enforcement-equivalent without a configured shared rate-limit store.

## 8. Deployment Cutover and Verification

- [x] 8.1 Add gateway startup to Compose and PM2/local workflows, publish only the gateway/frontend as appropriate, and keep all backend host bindings on loopback or private networks.
- [ ] 8.2 Run the gateway on a temporary loopback test port and verify route parity, uploads, image display, browser telemetry, trace continuity, and safe upstream failures before enforcing authentication.
- [ ] 8.3 Introduce and document a time-bounded audit/enforcement rollout sequence, then enable gateway and backend enforcement one service at a time with browser and agent smoke tests after each step.
- [x] 8.4 Remove direct backend API publication from normal LAN/VPN runbooks while retaining an operator-only loopback diagnostic procedure.
- [ ] 8.5 Verify from a separate LAN/VPN client that the frontend/gateway are reachable as intended, backend and infrastructure ports are not reachable, and direct backend requests fail authentication locally.
- [ ] 8.6 Rotate bootstrap administrator and smoke-test client credentials, confirm secret file permissions/backups, and document user disablement, agent revocation, signing-key rotation, and recovery procedures.
- [ ] 8.7 Execute the full Java, Python, Angular, Compose configuration, OpenSpec, and end-to-end security test suites and record the final supported access topology in README and ROADMAP.
- [ ] 8.8 Exercise and document rollback to the prior frontend proxy path without opening backend listeners to `0.0.0.0`, then restore the authenticated gateway deployment.
