## ADDED Requirements

### Requirement: Protected APIs deny by default
Every business API route SHALL require a valid access token unless the route is present in a reviewed public allowlist.

#### Scenario: Missing token
- **WHEN** a client calls a protected API without an access token
- **THEN** the gateway SHALL return `401` and SHALL NOT forward the request upstream

#### Scenario: Unlisted route
- **WHEN** a new API route has no explicit authorization policy
- **THEN** access SHALL be denied until a policy is defined

### Requirement: Tokens receive complete validation
The gateway and each backend service SHALL independently validate token signature, trusted issuer, expiry/not-before constraints, intended audience, and required scopes or roles.

#### Scenario: Valid authorized token
- **WHEN** a token passes all validation checks and includes authority required by the endpoint
- **THEN** the request SHALL be eligible for normal business processing

#### Scenario: Wrong audience
- **WHEN** a correctly signed token targets a different audience
- **THEN** the gateway and directly tested backend SHALL reject it

#### Scenario: Expired or invalidly signed token
- **WHEN** a token is expired, not yet valid, malformed, or signed by an untrusted key
- **THEN** the request SHALL be rejected without business processing

### Requirement: Backends preserve defense in depth
Inventory, Accounting, and Stock Portfolio SHALL enforce authorization locally even when the request is received from the gateway network.

#### Scenario: Direct internal request lacks token
- **WHEN** an internal client reaches a backend protected endpoint without a valid token
- **THEN** the backend SHALL reject the request

#### Scenario: Gateway forwards under-scoped token
- **WHEN** the gateway forwards a valid token that lacks the backend endpoint's required scope
- **THEN** the backend SHALL return `403`

### Requirement: Human and agent authorities are least privilege
The system SHALL define normal household-user and household-admin roles and service-specific read/write scopes, and SHALL authorize agent clients through scopes rather than a blanket administrator role.

#### Scenario: Read-only agent attempts mutation
- **WHEN** an agent token containing `inventory.read` but not `inventory.write` calls an Inventory mutation endpoint
- **THEN** the request SHALL be rejected with `403`

#### Scenario: Normal user attempts administrative operation
- **WHEN** a household-user token without household-admin authority calls an administrative endpoint
- **THEN** the request SHALL be rejected with `403`

### Requirement: Public exceptions are minimal and explicit
Only gateway health endpoints, framework-managed OIDC callbacks, constrained browser telemetry, and explicitly approved temporary image reads SHALL be accessible without a bearer token; backend actuator and API documentation endpoints SHALL remain unavailable through public routing.

#### Scenario: Public allowlisted request
- **WHEN** a client calls an allowlisted route using its allowed method and constraints
- **THEN** the gateway SHALL process that route without requiring a bearer token

#### Scenario: API documentation discovery
- **WHEN** a client attempts to reach backend Swagger, OpenAPI, or detailed actuator paths through the gateway
- **THEN** the gateway SHALL return `404` or `403` without forwarding the request

### Requirement: Authorization failures are safe and traceable
Authentication and authorization failures SHALL use a stable JSON error shape, SHALL distinguish `401` from `403`, and SHALL include a correlation identifier without exposing token contents or internal policy details.

#### Scenario: Insufficient scope
- **WHEN** an authenticated principal lacks required authority
- **THEN** the system SHALL return `403` with a stable error code and correlation identifier and SHALL NOT reveal the missing internal policy expression

### Requirement: Identity dependency failure is fail-closed
Protected APIs SHALL NOT bypass token validation when issuer discovery or signing-key refresh fails.

#### Scenario: Keycloak unavailable with unverifiable token
- **WHEN** Keycloak is unavailable and the presented token cannot be verified using valid cached key material
- **THEN** the protected request SHALL fail without reaching business processing

