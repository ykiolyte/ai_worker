## Design

### Search Requests

The search list remains the operational entry point, but it now starts with summary cards. Metrics are computed from already loaded search requests, so no new API endpoint is required. Active rows show a stage label derived from status and product count.

### Catalog

Catalog filtering is local to the loaded product list. To support contact and channel filters without opening each product detail, the product-card API includes lightweight supplier contacts. Demo products are identified by the existing `attributes.demo` marker or the `demo.local` source domain.

### Product Details

The detail page is split into a left product-information panel and a right conversation panel. Supplier messages are rendered as inbound/outbound chat bubbles. Approval-needed replies keep the existing backend flag and expose clear continuation actions.

### Message Preferences

Language and style controls use segmented buttons for faster demo interaction. The preview mirrors the backend message template closely enough to help the user understand what will be sent; the backend remains the source of truth for the final sent text.

### Errors

Each page shows a short user-facing error and hides raw technical details in a `<details>` block.
