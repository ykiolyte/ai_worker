## Overview

The implementation extends the existing optional `MadeInChinaSearchConnector` rather than adding a second runtime connector. Keyword queries keep using the existing search-result parser. Queries that include a direct Made-in-China product/showroom URL use a new detail-page parser and return a single normalized product candidate.

## Detail Parser

The parser reads public HTML only. It prefers stable page-level data before visual layout blocks:

- OpenGraph and `product:*` meta tags for title, canonical URL, image, price, currency, and availability.
- Product description meta text.
- `Basic Info.` table-like blocks for model, type, resolution, focal length, transport package, origin, HS code, and similar attributes.
- Supplier/contact sidebar links for supplier name, supplier URL, inquiry URL, and contact person.
- Product images from the primary OpenGraph image and detail-page image attributes.

The parser must avoid collecting recommendation cards as the main product. It therefore builds the main product from page metadata and product-detail sections, not from arbitrary product links in "also viewed" sections.

## URL Handling

The connector recognizes direct detail targets from:

- `site:https://...made-in-china.com/product/...`
- a raw `https://...made-in-china.com/product/...` URL in the query text
- compatible `wholesaler.made-in-china.com` URLs when they are provided as direct targets

The connector fetches only the detected target URL and applies the same HTTP failure and captcha/protection handling as search pages.

## Normalization

Output uses the existing product candidate schema consumed by the worker:

- `title`, `productUrl`, `supplierName`, `contacts`, `images`, optional `price`, optional `currency`, optional `description`, and `attributes`.
- Detail-page metadata is stored in `attributes` under non-breaking keys such as `sourcePlatform`, `detailSource`, `supplierUrl`, `inquiryUrl`, `contactPerson`, `availability`, and `basicInfo`.
- `contacts` remains empty unless a supported email or Telegram contact is actually present. Inquiry links are metadata, not supported supplier contacts.
- The worker treats Made-in-China inquiry-only products as persistable contactless candidates when they include `sourcePlatform=made-in-china` plus supplier URL, inquiry URL, or Made-in-China product URL. Other contactless products continue to follow the existing global contactless setting.
- The worker queries Made-in-China before the browser/AI discovery path. If Made-in-China returns any candidates, the worker skips browser discovery so a slow browser or AI path does not block Made-in-China search results. Browser discovery remains the fallback when Made-in-China is disabled, fails, or returns no products.

## Catalog Presentation

The catalog separates visible results into an "Oстальные источники" column and a "Made-in-China" column. Made-in-China cards surface the fields that matter for supplier screening: price text, MOQ, supplier location, business type, inquiry URL, supplier name, and source link when present.

## Boundaries

No authentication, protected page access, captcha bypass, checkout, ordering, payment, or supplier message sending is added. If Made-in-China serves a protection page, the connector reports the structured error and returns no partial product.

## Verification

Tests cover deterministic HTML snippets for detail parsing and direct URL fetch behavior. A separate local smoke check parses the user-provided saved HTML in `made_in_china/` without committing or modifying that artifact.
