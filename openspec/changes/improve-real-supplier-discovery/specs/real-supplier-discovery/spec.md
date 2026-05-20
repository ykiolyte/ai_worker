## ADDED Requirements

### Requirement: B2B Query Expansion

The system SHALL expand user search input into multiple B2B supplier discovery
queries.

#### Scenario: User searches for a product

- **GIVEN** the user enters a product search query
- **WHEN** AI internet search runs
- **THEN** the system SHALL search using supplier, manufacturer, distributor,
  wholesale, MOQ, stock, and contact-oriented variants when possible
- **AND** duplicate query strings SHALL be removed

### Requirement: Supplier Candidate Classification

The system SHALL classify and score search results before opening candidate
pages.

#### Scenario: Search results contain mixed page types

- **GIVEN** search results include product pages, supplier pages, marketplace
  pages, content pages, and login/cart pages
- **WHEN** candidates are selected
- **THEN** supplier/product candidates SHALL be preferred
- **AND** content, login, cart, and unrelated pages SHALL be de-prioritized

#### Scenario: Model selects fewer candidates than requested

- **GIVEN** the user requests more candidates than the model-selected list
  contains
- **WHEN** ranked search results include additional allowed supplier candidates
- **THEN** the system SHALL fill remaining candidate slots from the ranked
  results up to the requested limit

### Requirement: Supplier Contact Enrichment

The system SHALL attempt to enrich discovered products with supplier-domain
contact evidence.

#### Scenario: Product page has no contacts

- **GIVEN** a product page is extracted without contacts
- **WHEN** the supplier domain is public and allowed
- **THEN** the system SHALL try common contact/about/sales/distributor pages on
  that supplier domain
- **AND** valid discovered contacts SHALL be merged into the product payload

#### Scenario: Product page includes contact navigation links

- **GIVEN** a product page contains footer or navigation links for contact,
  sales, support, dealers, distributors, or about pages
- **WHEN** the product page has no extracted contacts
- **THEN** the system SHALL try those discovered links before guessed domain
  paths

#### Scenario: Contact details are embedded in page text

- **GIVEN** contact details appear as visible email text, mailto links,
  obfuscated "at/dot" text, Cloudflare-protected email spans, or Telegram links
- **WHEN** product/contact extraction runs
- **THEN** the system SHALL normalize and return supported contacts when valid

### Requirement: Discovery Metadata

The system SHALL retain supplier discovery evidence on product cards.

#### Scenario: Candidate is extracted

- **GIVEN** a product payload is created from a selected search candidate
- **WHEN** the product is returned to the worker
- **THEN** its attributes SHALL include supplier type, source confidence,
  contact confidence, discovery query, candidate reason, and candidate URL when
  available
