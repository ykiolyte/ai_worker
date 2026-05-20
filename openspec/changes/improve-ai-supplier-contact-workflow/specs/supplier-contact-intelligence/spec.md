## ADDED Requirements

### Requirement: Preferred Supplier Contact

The system SHALL choose and expose the best available supplier contact when
starting supplier communication.

#### Scenario: Product has multiple contacts

- **GIVEN** a product has multiple supplier contacts
- **WHEN** the user starts supplier communication without selecting a contact
- **THEN** the system SHALL choose the highest-quality contact based on channel,
  sales-oriented address, supplier-domain match, primary flag, and confidence
  metadata
- **AND** product detail responses SHALL indicate the preferred contact and its
  quality score

### Requirement: AI Supplier Reply Analysis

The system SHALL analyze inbound supplier replies and persist structured
commercial terms on the product.

#### Scenario: Supplier replies with commercial terms

- **GIVEN** an inbound supplier message is recorded manually or synced from
  Gmail
- **WHEN** model runtime is available
- **THEN** the system SHALL extract summary, price, currency, MOQ, lead time,
  availability, payment terms, delivery terms, risk flags, next step, and
  communication score
- **AND** the extracted values SHALL be saved on product attributes

### Requirement: Communication-Aware Supplier Rating

The system SHALL include contact and communication quality in supplier
comparison.

#### Scenario: Product detail includes supplier comparison

- **GIVEN** a product has contacts and conversation history
- **WHEN** product comparison is serialized
- **THEN** metrics SHALL include contact quality score and communication score
- **AND** the overall rating SHALL account for those metrics

### Requirement: Product Supplier Excel Export

The system SHALL let the user download product and supplier information as an
Excel-compatible file.

#### Scenario: User saves supplier information

- **GIVEN** the user opens a product detail page
- **WHEN** the user clicks the save Excel action
- **THEN** the browser SHALL download an Excel-compatible file
- **AND** the file SHALL include product data, supplier contacts, rating metrics,
  AI-extracted supplier terms, next step, and conversation messages
