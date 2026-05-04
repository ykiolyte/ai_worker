## 1. Domain And Persistence

- [x] 1.1 Add tests for `ConversationMessage` creation and allowed statuses/directions.
- [x] 1.2 Add the `ConversationMessage` domain entity.
- [x] 1.3 Add repository methods to add and list conversation messages by product.

## 2. Gmail And Worker Behavior

- [x] 2.1 Add worker tests for successful email contact persisting a sent conversation message.
- [x] 2.2 Add worker tests for failed email contact persisting a failed conversation message with redacted errors.
- [x] 2.3 Update supplier-contact worker to create outbound conversation messages.
- [x] 2.4 Document Gmail SMTP env configuration and keep existing SMTP connector compatible.

## 3. API

- [x] 3.1 Add API tests for product detail including conversation messages.
- [x] 3.2 Serialize conversation messages in `GET /api/products/{product_id}`.
- [x] 3.3 Keep `POST /api/products/{product_id}/contact-supplier` as the async task creation boundary.

## 4. WebUI

- [x] 4.1 Add/update frontend contract tests for "Начать общение" and message timeline.
- [x] 4.2 Update frontend types for conversation messages.
- [x] 4.3 Update product details button copy and timeline rendering.

## 5. Verification

- [x] 5.1 Run backend unit tests.
- [x] 5.2 Run frontend build.
- [x] 5.3 Run OpenSpec validation for this change.
- [x] 5.4 Smoke-test local API/WebUI path for starting communication.
