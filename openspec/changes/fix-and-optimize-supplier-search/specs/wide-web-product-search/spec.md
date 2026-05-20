## MODIFIED Requirements

### Requirement: Bounded Optimized Supplier Search

Internet supplier search SHALL minimize browser page visits while preserving the existing browser extraction fallback.

#### Scenario: search stops after enough valid products

- GIVEN ranked web-search candidates exceed requested `maxResults`
- WHEN browser extraction returns enough valid product payloads
- THEN the connector SHALL stop visiting additional candidate pages
- AND it SHALL report the number of candidates visited

#### Scenario: contact enrichment is bounded

- GIVEN a product page has no contact data
- WHEN contact enrichment is disabled or the enrichment budget is exhausted
- THEN the connector SHALL return the product without slow unbounded contact-page probing
- AND existing contact enrichment behavior SHALL remain available through configuration
