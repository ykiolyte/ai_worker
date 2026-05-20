## ADDED Requirements

### Requirement: Product search can use Made-in-China discovery

Product search orchestration SHALL be able to include Made-in-China discovery as an optional source while preserving the existing asynchronous task lifecycle.

#### Scenario: Made-in-China discovery contributes candidates
- **GIVEN** a product search task is queued
- **AND** Made-in-China discovery is enabled
- **WHEN** the worker processes the task
- **THEN** the worker SHALL call the Made-in-China discovery connector through the runtime connector abstraction
- **AND** valid Made-in-China candidates SHALL be validated before persistence like other agent or connector output

#### Scenario: Made-in-China discovery is disabled
- **GIVEN** Made-in-China discovery is disabled
- **WHEN** the worker processes a product search task
- **THEN** product search SHALL continue using the existing discovery and extraction path
- **AND** the HTTP API SHALL NOT block while Made-in-China discovery is skipped
