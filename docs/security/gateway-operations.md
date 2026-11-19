# Gateway security operations

The supported topology is `LAN/VPN browser or agent -> nginx (~/projects/infra) -> gateway -> private backends`. There is no authentication layer (Keycloak/JWT removed 2026-11); the LAN/VPN boundary is the access control. Backend ports remain loopback-bound on the host.

Rate limits use a local Caffeine cache and Bucket4j token buckets. Counters reset whenever the gateway restarts. `GATEWAY_INSTANCE_COUNT` must remain `1`; startup fails when multiple instances are declared with `GATEWAY_RATE_STORE=local`. Configure a shared store before horizontal scaling.

## Local diagnostics

Operators may call a backend through `127.0.0.1` directly. Never change backend bindings to `0.0.0.0` for diagnosis. Logs retain correlation ID, route class and result but must not contain Authorization, cookies, raw claims, subjects or client addresses.
