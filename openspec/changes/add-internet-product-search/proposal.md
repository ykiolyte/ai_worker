## Why

The MVP currently searches only a configured supplier site or a `site:` target.
Users need product discovery across the public web so they can enter a normal
product query and receive real product candidates without first knowing a
supplier domain.

## What Changes

- Add an internet product-search mode behind the existing browser connector
  boundary.
- Add a configurable search-engine provider that uses a real browser MCP session
  to open search result pages and collect candidate URLs.
- Add public-internet browsing safeguards: explicit opt-in, public HTTP(S) URL
  checks, private/internal host blocking, and existing allowlist support for
  controlled E2E sites.
- Extend generic product extraction for real product pages using JSON-LD,
  OpenGraph/meta tags, visible headings, prices, images, supplier names, and
  public contact hints.
- Allow product search to persist useful product cards without supplier contacts
  when configured, while keeping supplier-contact actions disabled for those
  products.
- Document how to switch between controlled supplier-site mode and public
  internet mode.

## Capabilities

### New Capabilities

- `internet-product-search`: Discover and extract product candidates from
  public web search results through the browser MCP connector.

### Modified Capabilities

- `agent-orchestration`: Product search tasks may use internet search before
  browser extraction and may persist validated products with no contacts when
  configured.
- `product-catalog`: Product cards without supplier contacts can be shown in the
  catalog and product detail pages, with contact actions remaining disabled.

## Impact

- Backend connector settings, browser research flow, extraction scripts, URL
  safety checks, and worker validation behavior.
- Environment files and Docker Compose variables for internet mode.
- Unit/contract tests for search-result parsing, public URL security,
  contactless product persistence, and configuration.
- Documentation for enabling real internet product search and its limitations.
