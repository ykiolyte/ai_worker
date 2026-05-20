## Overview

Supplier deduplication belongs in the backend worker because connector output is untrusted and may contain repeated product pages from the same supplier domain. The worker already validates products; after validation it should derive a stable supplier key and skip duplicates before persistence.

Supplier communication is already implemented by `process_supplier_contact`; the fix is to lock the behavior with automated coverage and address any regression found by the test.

## Supplier Key

The supplier key is derived in this order:

1. normalized product/source domain;
2. normalized contact email domain or Telegram handle;
3. normalized supplier name.

Demo cards keep their own unique key so demo presentation support is not removed.

## Selection

When several candidates have the same supplier key, keep the first valid candidate from the ranked connector output and report later candidates as skipped duplicates. This preserves the optimized search ranking while preventing repeated supplier cards.

## Verification

- Unit/worker test for duplicate supplier domains.
- API test for auto-processed supplier contact reaching `sent` and persisting an outbound conversation.
- Full `pytest`, frontend build, and OpenSpec strict validation.
