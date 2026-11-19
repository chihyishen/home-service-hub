## ADDED Requirements

### Requirement: Gateway applies configurable route-class limits
The gateway SHALL apply configurable token-bucket limits to protected business APIs and separately constrained public compatibility routes.

#### Scenario: Request is within limit
- **WHEN** a request's resolved rate-limit bucket has available capacity
- **THEN** the request SHALL continue through authentication, authorization, and routing

#### Scenario: Request exceeds limit
- **WHEN** a request's resolved bucket has no available capacity
- **THEN** the gateway SHALL return `429` without forwarding the request upstream

### Requirement: Authenticated limits use principal identity
Authenticated request buckets SHALL be keyed by stable token subject or client ID plus route class, without using or storing the raw bearer token as a key.

#### Scenario: Two agents use different clients
- **WHEN** two authenticated agents call the same route class
- **THEN** each agent SHALL consume a separate rate-limit bucket

#### Scenario: One principal changes source address
- **WHEN** an authenticated principal calls through a different network address
- **THEN** its principal-based request count SHALL continue to apply

### Requirement: Unauthenticated limits use trusted network identity
Requests that are validly allowed before authentication SHALL be keyed by the gateway-derived client address plus route class, and client-supplied forwarding headers SHALL NOT influence the key unless received from an explicitly trusted proxy.

#### Scenario: Client spoofs forwarded IP
- **WHEN** an untrusted client changes `X-Forwarded-For`
- **THEN** the request SHALL remain in the bucket derived from the accepted connection address

### Requirement: Rate-limit rejection is predictable
A rate-limited response SHALL use status `429`, a stable JSON error code, a correlation identifier, and a meaningful `Retry-After` value.

#### Scenario: Client is rate limited
- **WHEN** the gateway rejects a request because its bucket is exhausted
- **THEN** the response SHALL tell the client when retry is permitted without exposing bucket internals or other principals' activity

### Requirement: Rate-limit telemetry protects identity
The system SHALL emit rate-limit metrics and structured events by route and principal category without logging raw tokens, client secrets, full query strings, or unnecessary direct identifiers.

#### Scenario: Limit event is recorded
- **WHEN** a request is rejected by a rate limit
- **THEN** operators SHALL be able to identify the route, result, correlation identifier, and pseudonymous bucket category without recovering the credential from telemetry

### Requirement: Single-instance limits have an explicit scaling boundary
The initial in-process rate-limit store SHALL be used only while a single active gateway instance handles traffic; multiple active instances SHALL require a shared counter store before being considered enforcement-equivalent.

#### Scenario: Deployment scales gateway horizontally
- **WHEN** operators configure more than one active gateway instance
- **THEN** deployment validation SHALL require a shared supported rate-limit store or explicitly report rate-limit enforcement as degraded

