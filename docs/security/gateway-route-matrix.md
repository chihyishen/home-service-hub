# Gateway route and authorization matrix

Unknown routes and methods are denied by default. Backend actuator and API documentation paths are never routed by the gateway.

| Client path | Methods | Upstream behavior | Required authority |
| --- | --- | --- | --- |
| `/api/items/**` | GET, HEAD | Inventory, path preserved | `inventory.read` |
| `/api/items/**` | POST, PUT, PATCH, DELETE | Inventory, path preserved | `inventory.write` |
| `/api/shopping-list/**` | GET, HEAD | Inventory, path preserved | `inventory.read` |
| `/api/shopping-list/**` | POST, PUT, PATCH, DELETE | Inventory, path preserved | `inventory.write` |
| `/api/accounting/**` | GET, HEAD | Accounting, `/api/accounting` stripped | `accounting.read` |
| `/api/accounting/**` | POST, PUT, PATCH, DELETE | Accounting, `/api/accounting` stripped | `accounting.write` |
| `/api/portfolio/**` | GET, HEAD | Portfolio, path preserved | `portfolio.read` |
| `/api/portfolio/**` | POST, PUT, PATCH | Portfolio, path preserved | `portfolio.write` |
| `/api/portfolio/**` | DELETE | Portfolio, path preserved | `household-admin` and `portfolio.write` |
| `/minio/inventory-items/**` | GET, HEAD | MinIO, `/minio` stripped | Public compatibility route |
| `/otlp/v1/traces` | POST | Collector, `/otlp` stripped | Public compatibility route |
| `/actuator/health/liveness` | GET | Gateway local endpoint | Operator loopback only |
| `/actuator/health/readiness` | GET | Gateway local endpoint | Operator loopback only |

The current Angular proxy contract is captured by `scripts/smoke/gateway-route-fixtures.json`. It includes method and rewrite examples used when comparing the gateway against the previous proxy.
