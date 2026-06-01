## ADDED Requirements

### Requirement: Provide Search Provider Abstraction

The system SHALL discover product candidates through explicit provider abstractions rather than hardcoding one website into business logic.

#### Scenario: Provider router runs configured providers

- GIVEN provider order is configured
- WHEN a product search task runs
- THEN the provider router SHALL call providers in configured order
- AND provider results SHALL be returned as candidate/provenance data, not trusted persisted products

#### Scenario: Provider partially fails

- GIVEN one provider fails and another provider is configured
- WHEN product search runs
- THEN the system SHALL attempt the next configured provider
- AND task output SHALL include provider failure information without leaking secrets

### Requirement: Public-Only Made-in-China-like Provider

The Made-in-China-like provider SHALL use only public pages visible in a normal browser/search flow.

#### Scenario: Provider extracts public fields

- GIVEN a public product/search page is accessible without login, private API, or anti-bot bypass
- WHEN the provider extracts candidates
- THEN it MAY extract title, URL, image URL, price text, MOQ text, supplier name, public supplier badges, source domain, and public contact hints when visible
- AND it SHALL store provenance for extracted fields where possible

#### Scenario: Provider encounters protected or private content

- GIVEN a target requires login, unauthorized cookies, CAPTCHA/WAF bypass, signed request replay, or private/undocumented endpoints
- WHEN the provider evaluates the target
- THEN it SHALL skip that target or fail safely
- AND it SHALL NOT attempt bypass or unauthorized access

### Requirement: Preserve Provenance

The system SHALL preserve discovery provenance for product candidates.

#### Scenario: Candidate is normalized

- GIVEN a provider returns a product candidate
- WHEN the normalizer converts it to product payload
- THEN raw provenance SHALL be preserved in `raw_agent_payload`
- AND trusted fields SHALL only be populated after validation

