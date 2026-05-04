## ADDED Requirements

### Requirement: Search Dashboard Must Summarize Demo State

The WebUI MUST show summary metrics above search requests for active searches, found products, replies awaiting attention, and received replies.

#### Scenario: User opens search requests

- GIVEN search requests have been loaded
- WHEN the page renders
- THEN it SHALL show dashboard metrics before the request table
- AND active searches SHALL show progress with a human-readable stage label

### Requirement: Catalog Must Support Demo-Friendly Filtering

The product catalog MUST allow filtering by contact availability, demo products, and contact channel.

#### Scenario: User filters catalog cards

- GIVEN product cards include supplier contact summaries
- WHEN the user selects a catalog filter
- THEN the catalog SHALL show only cards matching that filter
- AND demo cards SHALL be visually marked as demo cards

### Requirement: Product Detail Must Present Supplier Dialogue As Chat

The product detail page MUST separate product information from supplier conversation controls and render messages as inbound/outbound chat entries.

#### Scenario: Supplier asks for clarification

- GIVEN a conversation message requires user approval
- WHEN the product detail page renders
- THEN the message SHALL show an attention panel
- AND the user SHALL be able to continue the conversation from that panel

### Requirement: Message Preferences Must Be Previewable

The product detail page MUST let the user choose supplier-message language and style with segmented controls and preview the outgoing message before sending.

#### Scenario: User changes message preferences

- GIVEN a product detail page is open
- WHEN the user changes language or style
- THEN the preview SHALL update to reflect the selected preference
