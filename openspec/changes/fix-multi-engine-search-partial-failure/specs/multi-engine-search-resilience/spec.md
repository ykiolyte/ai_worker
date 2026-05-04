## ADDED Requirements

### Requirement: Multi-Engine Search Must Tolerate Individual Engine Failures

When multi-engine web search is enabled, failure of one configured engine MUST NOT fail the whole product search if another configured engine returns usable results.

#### Scenario: One engine is unavailable

- GIVEN multi-engine web search is configured with two engines
- AND the first engine fails with a connection error
- AND the second engine returns product-page results
- WHEN the system collects web search results
- THEN it SHALL return the unique results from the successful engine
- AND it SHALL NOT raise the failed engine error

#### Scenario: All engines fail

- GIVEN multi-engine web search is configured
- AND every configured engine fails
- WHEN the system collects web search results
- THEN it SHALL fail with a clear multi-engine search error
