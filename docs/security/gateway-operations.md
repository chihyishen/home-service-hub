# Gateway security operations

The supported topology is `LAN/VPN browser or agent -> frontend/gateway -> private backends`, with Keycloak reachable only through the trusted LAN/VPN identity listener. Backend ports remain loopback-bound on the host and private inside Compose.

Rate limits use a local Caffeine cache and Bucket4j token buckets. Counters reset whenever the gateway restarts. `GATEWAY_INSTANCE_COUNT` must remain `1`; startup fails when multiple instances are declared with `GATEWAY_RATE_STORE=local`. Configure a shared store before horizontal scaling.

## Staged enforcement

1. Start identity and gateway on loopback and validate discovery, audience and route fixtures.
2. Observe traffic for a bounded maintenance window and tune rate-limit environment values.
3. Enable Inventory enforcement and run browser plus agent smoke tests.
4. Enable Accounting, then Portfolio, repeating smoke tests after each service.
5. Remove backend ports from LAN/VPN runbooks; retain loopback-only diagnostics.

## Local diagnostics

Operators may call a backend through `127.0.0.1` with a valid scoped token. Never change backend bindings to `0.0.0.0` for diagnosis. Logs retain correlation ID, route class and result but must not contain Authorization, cookies, OAuth codes, raw claims, subjects or client addresses.

## Recovery and revocation

Disable an agent's dedicated client to revoke it, disable a user in Keycloak for user revocation, and follow Keycloak's active signing-key rotation procedure while retaining the previous verification key until issued access tokens expire. Bootstrap credentials and smoke-agent secrets must be rotated after initial validation and stored in permission-restricted secret files outside the repository.
