## Why

Long-running searches can remain visible as `queued` for many hours when the API creates a durable task but no active worker processes it, or when the worker/runtime does not auto-process in the current launch mode. This makes the product unusable for the main search workflow.

Search results also need to expose supplier/product information and per-product filters comparable to the public Made-in-China AI search experience while staying clean-room and public-only. The provided HTML shows a visible filter panel pattern: selected original attributes, common filters such as price/customization/sample/manufacturer, and grouped product attributes such as sensor type, resolution, and frame rate.

## What Changes

- Make local/API-created product search tasks progress instead of staying `queued` when auto-processing is enabled or when the app runs in a demo/local mode without a separate worker.
- Ensure product search output from Made-in-China/public providers persists supplier names, supplier badges, MOQ, price range, verification/customization/sample flags, and product attribute facets where public evidence exists.
- Extract and normalize Made-in-China-like attribute/filter panels from public HTML into `common_filters`, `product_attributes`, and per-product attributes without copying proprietary code or using private APIs.
- Add frontend catalog filtering over persisted product fields and facets: price range, customization, sample availability, supplier/manufacturer preference, and attribute values.
- Keep searches bounded with timeouts/max results and persist failures with user-readable errors instead of leaving tasks indefinitely queued.

## Capabilities

### Modified Capabilities

- `agent-orchestration`: queued search tasks must not remain indefinitely queued in supported local/demo/API auto-processing modes.
- `sourcing-provider-discovery`: public provider extraction includes visible supplier and filter/facet data from public HTML.
- `product-catalog`: product cards/details expose supplier and attribute/filter data used by catalog filtering.
- `webui`: catalog screens provide interactive filters based on persisted product data.

## Impact

- Backend worker lifecycle and app startup/runtime processing behavior.
- Made-in-China/public extraction and normalization.
- Search request metadata and product attribute persistence.
- Frontend catalog filtering UI/state.
- Tests for queued lifecycle, public HTML filter extraction, product filtering, and no unbounded queued state.
