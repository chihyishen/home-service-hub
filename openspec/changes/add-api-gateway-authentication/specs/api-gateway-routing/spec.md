## ADDED Requirements

### Requirement: Single supported API entry point
The system SHALL expose business APIs to browser and agent clients only through the gateway, while Inventory, Accounting, and Stock Portfolio upstream listeners remain reachable only from loopback or the private application network.

#### Scenario: Client uses the gateway
- **WHEN** a client sends a request to a supported business API path through the gateway
- **THEN** the gateway SHALL route the request to the owning upstream service

#### Scenario: Client attempts direct LAN access
- **WHEN** a LAN or VPN client attempts to connect directly to an upstream service port
- **THEN** the upstream port SHALL NOT be published on the LAN or VPN interface

### Requirement: Stable route and rewrite contract
The gateway SHALL preserve the current client-visible API prefixes and SHALL apply an explicit, tested upstream path transformation for every route.

#### Scenario: Accounting prefix is routed
- **WHEN** a client requests `/api/accounting/transactions`
- **THEN** the gateway SHALL forward the request to the Accounting service as `/transactions`

#### Scenario: Portfolio prefix is preserved
- **WHEN** a client requests `/api/portfolio/summary`
- **THEN** the gateway SHALL forward the request to the Stock Portfolio service as `/api/portfolio/summary`

#### Scenario: Inventory route is preserved
- **WHEN** a client requests a path under `/api/items/**` or `/api/shopping-list/**`
- **THEN** the gateway SHALL forward the same path to the Inventory service

### Requirement: Explicit compatibility routes
The gateway SHALL define separate constrained policies for browser telemetry and temporary Inventory image delivery rather than treating them as unrestricted business API routes.

#### Scenario: Inventory image read
- **WHEN** a client sends `GET` or `HEAD` to `/minio/inventory-items/**`
- **THEN** the gateway SHALL forward the request only to the configured Inventory bucket path

#### Scenario: Inventory image mutation attempt
- **WHEN** a client sends a mutating method to `/minio/inventory-items/**`
- **THEN** the gateway SHALL reject the request without forwarding it to MinIO

#### Scenario: Browser telemetry submission
- **WHEN** the frontend submits telemetry to `/otlp/**` within configured method, content-type, and body-size limits
- **THEN** the gateway SHALL forward it to the configured OTel Collector endpoint

### Requirement: Trusted forwarding boundary
The gateway SHALL discard untrusted forwarding headers and SHALL generate authoritative forwarding metadata from the accepted connection.

#### Scenario: Client spoofs forwarded address
- **WHEN** an untrusted client supplies `Forwarded` or `X-Forwarded-*` headers
- **THEN** the upstream SHALL receive only forwarding values produced or explicitly trusted by the gateway

### Requirement: Bounded proxy behavior and safe errors
The gateway SHALL enforce configurable request-size, header-size, connection, and response time bounds and SHALL return errors that do not disclose internal hosts, ports, stack traces, or credentials.

#### Scenario: Oversized request
- **WHEN** a request exceeds the configured limit for its route class
- **THEN** the gateway SHALL reject it with the configured client error without forwarding the body upstream

#### Scenario: Upstream unavailable
- **WHEN** a routed upstream is unavailable or times out
- **THEN** the gateway SHALL return a generic `502` or `503` response containing a traceable error identifier but no upstream address

### Requirement: Operational health separation
The gateway SHALL expose operator-only liveness and readiness signals and SHALL NOT expose actuator details or API documentation through public routes.

#### Scenario: Process alive but dependency invalid
- **WHEN** the gateway process is alive but required route or identity configuration is invalid
- **THEN** liveness SHALL remain healthy and readiness SHALL report unhealthy

