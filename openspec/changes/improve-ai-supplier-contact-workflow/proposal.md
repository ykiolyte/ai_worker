## Why

Supplier communication currently records messages and can auto-reply, but the
product card does not retain structured supplier terms, contact quality, or a
portable summary for review.

## What Changes

- Prefer the highest-quality supplier contact when starting communication.
- Analyze inbound supplier replies with AI and persist extracted commercial
  terms on the product attributes.
- Include communication quality in supplier comparison metrics and overall
  rating.
- Export product, supplier, contacts, extracted terms, and conversation evidence
  as an Excel-compatible file from the product detail page.

## Impact

- Backend API: product detail serialization, contact selection, Gmail/manual
  inbound processing, and product export endpoint.
- Worker: inbound Gmail sync enriches product attributes with supplier reply
  analysis.
- Frontend: product detail page exposes Excel download and displays new scoring
  metrics.
- Tests: API, Gmail worker, and frontend contract tests.
