## Decisions

- Treat language selection as an output contract, not only a prompt hint.
- Keep duplicate supplier candidates outside the persisted primary `products`
  collection; expose them from task output as a separate API field.
- Keep contract drafts non-binding and generated only from known facts when the
  model is unavailable or returns an error.

## Approach

- Add lightweight language checks for `ru`, `en`, and `zh` outputs before
  accepting model/corrected supplier messages.
- Localize fallback initial and follow-up supplier messages.
- Catch model/provider exceptions in contract generation and return a validated
  fallback draft with a clear missing-fields list.
- Serialize duplicate supplier skipped entries from `agent_tasks.output_payload`
  into `/api/search-requests/{id}/products`.
- Add a catalog filter/category for duplicates.

## Non-Goals

- Replacing the model provider.
- Persisting duplicate candidates as normal product cards.
- Making contract drafts legally binding or adding order/payment commitments.
