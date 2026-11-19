## ADDED Requirements

### Requirement: Keycloak owns identity lifecycle
The system SHALL use Keycloak as the OpenID Connect provider for credentials, login sessions, signing keys, clients, and identity claims, and SHALL NOT implement a separate password or token issuer in application services.

#### Scenario: User authenticates
- **WHEN** an enabled household user completes a configured Keycloak authentication flow
- **THEN** Keycloak SHALL issue standards-based tokens for the registered Home Service Hub client

#### Scenario: Disabled user attempts authentication
- **WHEN** a disabled household user attempts to authenticate
- **THEN** no application token SHALL be issued

### Requirement: Browser login uses Authorization Code with PKCE
The Angular application SHALL be registered as a public client using Authorization Code flow with S256 PKCE, exact redirect URIs, and exact allowed web origins.

#### Scenario: Successful browser login
- **WHEN** an unauthenticated user initiates login and successfully authenticates with Keycloak
- **THEN** the browser SHALL return to an approved application URI and the Angular application SHALL obtain an access token through the PKCE code exchange

#### Scenario: Unapproved redirect URI
- **WHEN** an authorization request specifies an unregistered redirect URI
- **THEN** Keycloak SHALL reject the request

### Requirement: Browser tokens remain ephemeral
The Angular application SHALL keep access and refresh tokens in memory and MUST NOT persist them in localStorage, sessionStorage, URLs, application logs, or telemetry.

#### Scenario: Browser reloads
- **WHEN** the application page reloads and in-memory tokens are lost
- **THEN** the application SHALL restore authentication through the Keycloak session flow or require login without reading a persisted bearer token

### Requirement: Logout terminates application access
The application SHALL clear local authentication state and invoke the Keycloak logout flow using an approved post-logout redirect.

#### Scenario: User logs out
- **WHEN** an authenticated user selects logout
- **THEN** subsequent protected API calls from that application session SHALL NOT carry the prior token and SHALL require authentication

### Requirement: Agents use separate confidential clients
Each non-interactive AI agent SHALL authenticate with its own confidential Keycloak client using Client Credentials and SHALL receive only its assigned service scopes.

#### Scenario: Agent obtains token
- **WHEN** an enabled agent presents valid client credentials
- **THEN** Keycloak SHALL issue a short-lived access token containing only the client's assigned scopes and audience

#### Scenario: Agent secret is revoked
- **WHEN** an agent client secret is rotated or the client is disabled
- **THEN** the old credentials SHALL NOT obtain new access tokens without affecting other agents

### Requirement: Bootstrap identity configuration is reproducible and secret-safe
Realm, client, role, scope, and mapping configuration SHALL be maintained as reviewable bootstrap configuration, while administrator passwords, client secrets, and private key material SHALL be supplied outside version control.

#### Scenario: Fresh local deployment
- **WHEN** an operator starts a fresh authorized deployment with required secrets
- **THEN** the deployment SHALL create or import the expected realm structure without committing secret values to the repository

