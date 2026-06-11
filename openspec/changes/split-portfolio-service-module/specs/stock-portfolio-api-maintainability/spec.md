# Delta: stock-portfolio-api-maintainability

## ADDED Requirements

### Requirement: Portfolio service logic is organized into cohesive modules behind a stable facade

The portfolio service SHALL organize its domain logic into single-concern modules under `app/services/portfolio/`, and `app/services/portfolio_service.py` SHALL remain a facade that re-exports the public API so existing importers do not change.

#### Scenario: External importers are unaffected by the split
- **WHEN** routers or sibling services import `portfolio_service` and access its functions as attributes
- **THEN** every previously available public function (and the private helpers exercised by tests) SHALL resolve through the facade with identical signatures and behavior

#### Scenario: Cross-module monkeypatching through the facade keeps working
- **WHEN** a test patches a facade attribute consumed by another module via dynamic `portfolio_service.<name>` lookup (e.g. scheduler, snapshot, networth-backfill tests)
- **THEN** the patched attribute SHALL take effect without the test changing its patch target

#### Scenario: Submodules stay cohesive and bounded
- **WHEN** maintainers inspect `app/services/portfolio/`
- **THEN** each module SHALL cover one concern (corporate-action adjustment, cashflow/XIRR, holdings, summary, day-trade validation, history backfill, CRUD, shared helpers) and the facade SHALL contain no business logic of its own

#### Scenario: No import cycles between facade and submodules
- **WHEN** the package is imported
- **THEN** submodules SHALL NOT import the facade; only code outside the package SHALL go through `portfolio_service`
