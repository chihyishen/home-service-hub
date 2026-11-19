# Gateway route matrix

Unknown routes and methods are denied by default. Backend actuator and API documentation paths are never routed by the gateway.

| Client path | Methods | Upstream behavior |
| --- | --- | --- |
| `/api/items/**` | GET, HEAD | Inventory, path preserved |
| `/api/items/**` | POST, PUT, PATCH, DELETE | Inventory, path preserved |
| `/api/shopping-list/**` | GET, HEAD | Inventory, path preserved |
| `/api/shopping-list/**` | POST, PUT, PATCH, DELETE | Inventory, path preserved |
| `/api/accounting/**` | GET, HEAD | Accounting, path unchanged |
| `/api/accounting/**` | POST, PUT, PATCH, DELETE | Accounting, path unchanged |
| `/api/portfolio/**` | GET, HEAD | Portfolio, path preserved |
| `/api/portfolio/**` | POST, PUT, PATCH | Portfolio, path preserved |
| `/api/portfolio/**` | DELETE | Portfolio, path preserved |
| `/images/inventory-items/**` | GET, HEAD | Inventory, `/images` stripped |
| `/actuator/health/liveness` | GET | Gateway local endpoint |
| `/actuator/health/readiness` | GET | Gateway local endpoint |

The current Angular proxy contract is captured by `scripts/smoke/gateway-route-fixtures.json`. It includes method and rewrite examples used when comparing the gateway against the previous proxy.
