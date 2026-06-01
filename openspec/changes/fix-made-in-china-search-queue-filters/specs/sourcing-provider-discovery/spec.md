## MODIFIED Requirements

### Requirement: Made-in-China-like Public Extraction

The system SHALL extract visible supplier, product, and filter information from public provider content without using private or protected mechanisms.

#### Scenario: Public filter panel is normalized

- GIVEN public provider HTML contains visible sections for original attributes, common filters, and grouped product attributes
- WHEN the provider parses the public content
- THEN selected original attributes SHALL be added to normalized intent or common filters
- AND common filters such as price range, customization, sample availability, and manufacturer preference SHALL be added to `common_filters`
- AND grouped attributes such as sensor type, resolution, and frame rate SHALL be added to `product_attributes`
- AND group summary text SHALL be preserved in sourcing guidance or product attribute metadata

#### Scenario: Public supplier information is preserved

- GIVEN public provider content contains supplier name, supplier badges, location, MOQ, price range, sample/customization flags, or verification/audit claims
- WHEN a candidate is normalized
- THEN the resulting product payload SHALL preserve those fields only when visible public evidence exists
- AND raw provenance SHALL identify source URL/domain and extraction method

#### Scenario: Protected content is rejected

- GIVEN provider content requires credentials, unauthorized cookies, CAPTCHA/WAF bypass, private APIs, signed requests, or hidden endpoints
- WHEN the provider detects that requirement
- THEN it SHALL fail safely or fall back to the next provider
- AND it SHALL NOT bypass the restriction
