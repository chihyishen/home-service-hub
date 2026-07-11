## Why

The frontend and AI agents can currently reach individual backend services without a shared authentication or policy boundary. Establishing a single gateway and Keycloak-backed identity layer now preserves the recent loopback-only hardening while providing a safe path for LAN/VPN access, user login, agent credentials, authorization, and abuse controls.

## What Changes

- Add a Spring Cloud Gateway Server MVC service as the only browser- and agent-facing API entry point.
- Route stable public API prefixes to Inventory, Accounting, and Stock Portfolio while keeping those services bound to loopback or a private container network.
- Add Keycloak as the OpenID Connect identity provider for interactive users and non-interactive agents.
- Add Angular Authorization Code with PKCE login, logout, session restoration, and authenticated route handling.
- Require and independently validate access tokens at the gateway and each backend service, with explicit public-route exceptions.
- Define roles/scopes for household users, administrators, and AI agents, including least-privilege authorization per service.
- Add per-principal and pre-authentication rate limits with consistent `429` responses.
- Preserve trace propagation while preventing credentials, tokens, cookies, and sensitive authorization data from entering logs or telemetry.
- **BREAKING**: Backend business APIs will no longer be supported as directly accessible browser/LAN entry points; clients must use the gateway and authenticated API paths.

## Capabilities

### New Capabilities

- `api-gateway-routing`: Single-entry routing, path ownership, trusted forwarding, health behavior, and private upstream access.
- `user-and-agent-authentication`: Keycloak-backed interactive PKCE login and non-interactive agent authentication lifecycle.
- `api-authorization`: Token validation and least-privilege role/scope enforcement at both gateway and backend services.
- `api-rate-limiting`: Principal- and source-aware request limiting with predictable rejection behavior and observability.

### Modified Capabilities

None.

## Impact

- Adds a new Java gateway service and Spring Cloud 2025.1.x dependency management compatible with Spring Boot 4.0.x.
- Adds Keycloak configuration, realm bootstrap data, secrets, and persistent storage to local deployment configuration.
- Changes Angular startup, routing, HTTP interception, and session UX.
- Adds OAuth2 resource-server configuration and authorization tests to Inventory, Accounting, and Stock Portfolio services.
- Changes frontend and agent API base URLs to gateway-owned paths and removes direct LAN publication of backend API ports.
- Adds operational requirements for issuer discovery, signing-key rotation, bootstrap administration, health checks, rate-limit state, and security-safe telemetry.
