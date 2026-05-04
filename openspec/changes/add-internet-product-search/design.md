## Context

The current browser connector is intentionally bounded: it opens a configured
supplier site or a `site:<url>` target, extracts links, and visits candidate
product pages inside an allowlist. This is reliable for the controlled
acceptance contour, but it does not discover products across the public web.

The new behavior must keep the existing controlled-site flow intact while
adding an explicit public-internet mode. Public browsing creates security and
quality risks, so the implementation must opt in through configuration and keep
URL validation at the connector boundary.

## Goals / Non-Goals

**Goals:**

- Let users enter a normal product query and discover product candidates from a
  public web search result page.
- Keep browser automation behind `BrowserMcpConnector`.
- Preserve controlled supplier-site behavior for `site:` queries and E2E tests.
- Extract useful product cards from heterogeneous real pages using JSON-LD,
  metadata, visible text, prices, images, and contacts when available.
- Allow contactless product cards when configured, with the WebUI contact action
  disabled as already required.
- Block private/internal URL navigation unless explicitly allowlisted.

**Non-Goals:**

- No paid search API dependency in the first slice.
- No autonomous purchasing, checkout, login, captcha solving, or policy bypass.
- No guarantee that every arbitrary website can be scraped successfully.
- No broad crawling beyond the configured result/page limits.

## Decisions

### Decision 1: Configurable Internet Mode

Add `BROWSER_RESEARCH_MODE=site|internet`. In `site` mode the connector keeps
the current behavior. In `internet` mode a query without `site:` opens a search
engine URL and extracts result links before visiting product pages. Any query
that contains `site:<url>` continues to use bounded site mode.

Rationale: this preserves deterministic E2E while enabling real search for
local/product use.

### Decision 2: Configurable Product Search Page

Use a configurable `INTERNET_SEARCH_URL_TEMPLATE`. The local runnable demo uses
Adafruit's public product search because common general search engines may
return bot challenges to headless browsers. The connector only depends on
browser-visible links and does not add a new SDK or paid provider.

Rationale: this keeps setup light, provides a real no-key product-search path
for live checks, and leaves room to add Bing/Brave/SerpAPI or
Browserbase/Hyperbrowser later behind the same boundary.

### Decision 3: Public URL Safety Gate

Keep `BROWSER_ALLOWED_DOMAINS` for controlled domains. Add
`BROWSER_ALLOW_PUBLIC_INTERNET=true` to allow public HTTP(S) hosts. Block
localhost, private IP ranges, link-local, multicast, and internal-looking host
names unless they are explicitly allowlisted.

Rationale: public internet mode must not become an SSRF path to local services.

### Decision 4: Generic Product Extraction

Extend the browser extraction snippet to prefer JSON-LD `Product` data, then
fallback to headings, OpenGraph/meta tags, price-like visible text, images, and
contact hints. The result still goes through existing backend validation before
persistence.

Rationale: real product pages are inconsistent; structured data gives high
quality when available, and fallbacks keep the MVP useful.

### Decision 5: Contactless Product Cards Are Configurable

Wire the existing `ALLOW_PRODUCTS_WITHOUT_CONTACTS` flag into product-search
validation. When true, validated title+URL product cards may be stored without
contacts. Supplier contact attempts remain blocked by existing API/UI behavior
when no contacts exist.

Rationale: many real product pages do not expose email or Telegram contacts,
but they are still useful product candidates.

## Risks / Trade-offs

- Search engines may rate-limit or change markup -> keep provider configurable
  and result parsing broad.
- Some websites block browser automation -> persist user-readable failures and
  keep page limits low.
- Generic extraction may produce noisy cards -> strict validation and duplicate
  checks still apply.
- Public browsing can create SSRF risk -> public internet must be explicit and
  private/internal hosts are blocked.
- Contactless products reduce supplier-contact completeness -> WebUI already
  disables contact action when no supported contact exists.

## Migration Plan

- Default Docker/local controlled supplier flow remains available.
- Users can enable public search by setting internet-mode environment variables
  and recreating backend/worker containers.
- Rollback is setting `BROWSER_RESEARCH_MODE=site` and recreating backend/worker.

## Open Questions

- Which paid/managed search provider should be added later for production
  stability: Brave/Bing/SerpAPI/Tavily/Hyperbrowser?
- Whether to add source-domain scoring and vendor allow/deny lists after MVP
  internet search proves useful.
