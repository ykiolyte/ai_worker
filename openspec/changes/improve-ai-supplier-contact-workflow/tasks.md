## 1. Contact Quality

- [x] 1.1 Score contacts by channel, address quality, supplier-domain match,
  primary flag, and metadata confidence.
- [x] 1.2 Use the best contact by default when the user does not select a
  specific supplier contact.
- [x] 1.3 Serialize preferred contact and quality score to product detail API.

## 2. Supplier Reply Analysis

- [x] 2.1 Add AI supplier reply analysis for price, currency, MOQ, lead time,
  availability, payment, delivery, risk flags, next step, and communication
  score.
- [x] 2.2 Persist analysis on product attributes for manual inbound replies.
- [x] 2.3 Persist analysis on product attributes for Gmail inbound sync replies.

## 3. Rating

- [x] 3.1 Include contact quality score in supplier comparison metrics.
- [x] 3.2 Include communication score in supplier comparison metrics and overall
  supplier rating.

## 4. Excel Export

- [x] 4.1 Add API endpoint for product/supplier Excel-compatible export.
- [x] 4.2 Add WebUI button to download product/supplier information.
- [x] 4.3 Include contacts, rating metrics, AI-extracted supplier terms, and
  conversation messages in export.

## 5. Verification

- [x] 5.1 Add API/worker/frontend contract tests.
- [x] 5.2 Run full Python test suite.
- [x] 5.3 Run frontend build.
- [x] 5.4 Validate OpenSpec change.
