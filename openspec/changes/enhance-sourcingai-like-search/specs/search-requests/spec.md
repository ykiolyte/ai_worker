## MODIFIED Requirements

### Requirement: Create Search Request

The system SHALL allow a user to create a product search request using free-text input and optional SourcingAI-like advanced fields.

#### Scenario: User creates a valid basic search request

- GIVEN the user is on the search request creation page
- WHEN the user submits a query text from 3 to 1000 characters and a `maxResults` value from 1 to 50
- THEN the system SHALL create a search request
- AND the search request status SHALL be `queued`
- AND the system SHALL create a corresponding durable agent task of type `product_search`
- AND the API response SHALL return without waiting for agent search completion

#### Scenario: User creates a search request with advanced sourcing fields

- GIVEN the user is on the SourcingAI-like search page
- WHEN the user submits `queryText`, `maxResults`, `targetMarket`, `quantity`, `budget`, `certifications`, and `supplierPreference`
- THEN the system SHALL persist the advanced fields with the search request or its task input
- AND the product search worker SHALL use those fields when building normalized intent
- AND existing clients that send only `queryText` and `maxResults` SHALL continue to work

#### Scenario: User submits invalid search fields

- GIVEN the user is on the search request creation page
- WHEN the user submits an empty query, a query shorter than 3 characters, a query longer than 1000 characters, or `maxResults` outside 1..50
- THEN the system SHALL reject the request
- AND the system SHALL display or return a validation error

### Requirement: Persist Normalized Search Context

The system SHALL persist normalized intent and sourcing context generated during product search.

#### Scenario: Worker completes search normalization

- GIVEN a product search task is running
- WHEN the worker produces normalized intent, missing fields, clarifying questions, common filters, product attribute facets, sourcing guidance, and supplier count
- THEN the system SHALL persist those fields on the search request
- AND `GET /api/search-requests/{id}` SHALL return those fields
- AND the fields SHALL default to empty JSON-compatible values before processing completes

#### Scenario: Search output lacks optional sourcing context

- GIVEN a provider or legacy connector returns only product records
- WHEN the worker validates and saves the search output
- THEN the system SHALL keep normalized intent and guidance fields as empty defaults
- AND the search SHALL NOT fail only because optional sourcing context is absent

### Requirement: Track Search Request Status

The system SHALL persist and expose the processing status of each search request through durable state shared by API and worker.

#### Scenario: External worker starts processing

- GIVEN a search request has status `queued`
- AND its corresponding agent task was created by the API
- WHEN a separate worker process reads the queued task from durable state
- THEN the system SHALL update the search request and agent task status to `running`
- AND the API SHALL be able to read the updated status

#### Scenario: External worker completes processing

- GIVEN a search request has status `running`
- WHEN the worker successfully saves valid search results and sourcing metadata
- THEN the system SHALL update the request status to `completed`
- AND the system SHALL set `completed_at`
- AND the API SHALL expose the completed status and product count

#### Scenario: Worker fails critically

- GIVEN a search request has status `running`
- WHEN the worker encounters a critical provider, validation, repository, or connector failure that prevents saving any valid result
- THEN the system SHALL update the request status to `failed`
- AND the system SHALL persist a user-readable error message

