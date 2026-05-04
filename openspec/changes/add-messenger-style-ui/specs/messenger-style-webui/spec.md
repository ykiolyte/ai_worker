## ADDED Requirements

### Requirement: WebUI Must Use A Two-Column Messenger Shell

The WebUI MUST render a persistent left sidebar with real search requests and a right work area for the selected workflow.

#### Scenario: User opens any main route

- GIVEN search requests exist
- WHEN the WebUI renders
- THEN the sidebar SHALL list real search requests
- AND the active search request SHALL be visually highlighted when applicable

### Requirement: Product Cards Must Render As Message Attachments

Catalog products MUST be presented as rounded message attachment cards with supplier/contact preview information and accessible actions.

#### Scenario: User opens a catalog

- GIVEN products have been loaded from the API
- WHEN the catalog renders
- THEN each product SHALL appear as a bubble or attachment-style card
- AND actions SHALL remain keyboard accessible

### Requirement: Supplier History Must Render As Chat Messages

Supplier communication history MUST render inbound and outbound messages as visually distinct chat bubbles.

#### Scenario: User opens product details

- GIVEN conversation messages exist
- WHEN the product detail page renders
- THEN inbound and outbound messages SHALL use distinct bubble styles
- AND system/approval statuses SHALL be shown as non-chat system messages

### Requirement: WebUI Must Support Light And Dark Themes

The WebUI MUST define light and dark visual tokens and expose a UI control for switching between them.

#### Scenario: User changes theme

- GIVEN the WebUI is open
- WHEN the user toggles the theme
- THEN the shell SHALL switch to the alternate theme without changing API data

### Requirement: WebUI Must Provide Accessible Interaction States

The WebUI MUST preserve labels, visible focus states, disabled states, and non-disruptive micro-interactions.

#### Scenario: User navigates by keyboard

- GIVEN interactive controls are visible
- WHEN the user tabs through the page
- THEN focused controls SHALL have a visible focus indicator
