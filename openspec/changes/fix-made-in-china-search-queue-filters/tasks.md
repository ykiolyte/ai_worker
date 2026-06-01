## 0. OpenSpec

- [x] 0.1 Create OpenSpec change for queued search and Made-in-China-like filters.
- [x] 0.2 Keep clean-room constraints explicit: public content only, no private APIs, no CAPTCHA/WAF bypass, no unauthorized cookies/sessions.
- [x] 0.3 Validate OpenSpec change before implementation and after edits.

## 1. Queue And Worker Lifecycle

- [x] 1.1 Add regression test proving local/API auto-processing does not leave a product search task indefinitely `queued`.
- [x] 1.2 Add regression test proving runtime/provider failure persists `failed` status and error on task/request.
- [x] 1.3 Fix app/worker runtime so product search progresses in configured local/demo mode and remains worker-process compatible in durable mode.
- [x] 1.4 Add stale queued task handling or clear diagnostics for tasks that cannot be processed.

## 2. Public Provider Filter Extraction

- [x] 2.1 Add fixture/test using the supplied public filter-panel HTML shape.
- [x] 2.2 Parse selected original attributes, price range filter, customization/sample/manufacturer filters, grouped attribute rows, and group summary.
- [x] 2.3 Persist extracted filters into `common_filters`, `product_attributes`, `sourcing_guidance`, and per-product attributes where applicable.
- [x] 2.4 Preserve supplier fields and provenance only when visible public evidence exists.

## 3. Backend API And Domain

- [x] 3.1 Ensure product card/detail serializers expose all filterable fields and attributes.
- [x] 3.2 Ensure SearchRequest serializers expose common filters and grouped product attributes.
- [x] 3.3 Keep output validation strict and backward compatible with existing product payloads.

## 4. Frontend Filters

- [x] 4.1 Add frontend contract tests for filter panel rendering from API facets.
- [x] 4.2 Add frontend catalog filter state for price, common filters, and grouped attribute chips.
- [x] 4.3 Filter product cards using persisted product fields/attributes.
- [x] 4.4 Add clear-filters and empty-filtered-state behavior.

## 5. Verification

- [x] 5.1 Run targeted backend tests for workers, provider extraction, API, and domain.
- [x] 5.2 Run frontend tests/build.
- [x] 5.3 Run full pytest suite where feasible.
- [x] 5.4 Run `openspec.cmd validate fix-made-in-china-search-queue-filters --strict --no-interactive`.
