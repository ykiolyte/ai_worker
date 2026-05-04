## Design

### Shell

`App` owns the application frame. It loads real search requests for the left sidebar and highlights the active request based on the current route. The main route still renders the existing pages, preserving current API behavior.

### Visual Language

The UI uses neutral messenger-like patterns: a left conversation list, right work panel, rounded message bubbles, attachment-style product cards, subtle dividers, and compact action buttons. It does not use protected logos, names, or official assets from any external messenger product.

### Themes

Theme colors are CSS custom properties. Light and dark theme values are selected by a local UI toggle. The toggle changes only presentation state.

### Accessibility

Controls keep visible text where possible. Buttons that could be ambiguous include `aria-label`. Inputs keep labels. Focus rings are visible. Disabled states use opacity and text hints already present in the UI.

### Motion

Hover, card entry, status spinner, and state transitions are subtle CSS-only transitions. Heavy animation and motion that changes business behavior are avoided.
