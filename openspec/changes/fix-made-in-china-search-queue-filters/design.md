## Context

The project now has durable SQL-backed state, but a user observed a real search remaining `queued` for more than 12 hours. That indicates a runtime boundary problem: API task creation is not enough unless either a worker is running or local/demo auto-processing is enabled and reliable.

The user also supplied public HTML from a Made-in-China AI search filter panel. The implementation must use this only as visible behavior guidance and test fixture shape. It must not use private APIs, reverse engineering, protected sessions, CAPTCHA bypass, or copied proprietary code/assets.

## Goals

- Prevent indefinite `queued` search state in supported runtime modes.
- Persist provider/search errors quickly when a search cannot run.
- Extract public visible filter/facet data into existing sourcing metadata.
- Persist supplier and product attributes sufficient for filtering and display.
- Add user-facing catalog filters that operate on API data only.

## Non-Goals

- No private Made-in-China endpoints or hidden API reconstruction.
- No CAPTCHA/WAF bypass, unauthorized cookies, signed request replay, or scraping protected content.
- No autonomous purchasing, order confirmation, payments, or commitments.
- No static pre-baked frontend results.

## Decisions

### Decision 1: Queue Safety Belongs To Runtime

The API should keep durable task creation, but local/demo launch modes must either auto-process product search tasks or clearly fail fast when no runtime can execute them. Worker polling remains the production-like boundary.

### Decision 2: Public HTML Filters Become Normalized Facets

Visible filter panel data is normalized into:

- `common_filters`: generic boolean/range filters like price, customization, sample, manufacturer-first.
- `product_attributes`: grouped attributes with title, summary, and values.
- per-product `attributes`: extracted item-level properties used by frontend filters.

### Decision 3: Filters Use Persisted Data

The frontend filters the catalog using product API responses and request-level facets. It must not parse provider HTML or hold static Made-in-China-specific data.

### Decision 4: Searches Are Bounded

Provider calls and background processing must use max results/timeouts and write task/request error states on critical failures. A queued task older than the configured stale threshold may be marked failed or retried by worker logic, but it must not be hidden from the user.

## Test Strategy

- Worker/API tests for auto-processing or fail-fast behavior so a created search does not remain queued forever in local/demo mode.
- Provider extraction tests using the supplied public HTML fixture shape for originals, common filters, grouped attributes, and group summary.
- Domain/worker tests proving extracted filters and supplier/product fields are persisted.
- Frontend contract tests proving catalog renders and applies filters from API data.
- Regression tests for clean-room constraints and bounded provider behavior.
