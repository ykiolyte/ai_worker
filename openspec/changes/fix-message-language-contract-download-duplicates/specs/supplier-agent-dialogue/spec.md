## MODIFIED Requirements

### Requirement: Agent Sends Follow-Up Replies

The system SHALL let the user request an AI-generated follow-up reply for an
existing supplier conversation.

#### Scenario: User-selected language is respected

- **GIVEN** the user selects Russian, English, or Chinese message language
- **WHEN** the system generates an initial supplier message or follow-up reply
- **THEN** the outbound message SHALL be written in the selected language
- **AND** if the model output uses a different language, the system SHALL reject
  that output and use a corrected or safe localized fallback
- **AND** the message SHALL still pass the MVP safety policy
