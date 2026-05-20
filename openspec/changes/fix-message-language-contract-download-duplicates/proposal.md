## Why

Three regressions are visible in the supplier workflow:

- Supplier messages may be sent in English even when the user selected Russian.
- Contract draft generation can fail with upstream `HTTP Error 404: Not Found`,
  leaving no downloadable draft.
- Duplicate supplier candidates are skipped, but users cannot review them
  separately from the primary search results.

## What Changes

- Enforce selected supplier message language for initial and follow-up messages,
  with localized safe fallbacks.
- Make contract draft generation resilient to model/provider failures by
  producing a safe non-binding draft from existing product/conversation data.
- Expose duplicate supplier candidates as a separate search-result category in
  the API and catalog UI while keeping primary results deduplicated.

## Impact

- User-selected language is respected for outbound supplier messages.
- Contract drafts can be downloaded even when the model provider fails.
- Duplicate suppliers remain visible for audit/review without polluting the main
  supplier list.
