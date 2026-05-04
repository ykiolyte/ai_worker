# Test Protocol Coverage Matrix

This matrix keeps `test_protocol.md` visible during implementation. Update the
status and automated-test references as work lands.

Status values:

- `Planned`: covered by OpenSpec but not implemented.
- `Automated`: automated test exists.
- `Manual`: requires manual or external verification.
- `Passed`: verified in the target environment.
- `Deferred`: intentionally postponed with reason.

| Case | Focus | OpenSpec Capability | Primary Tasks | Status |
| --- | --- | --- | --- | --- |
| TC-E2E-001 | Create search request through WebUI | search-requests, webui, persistence | 3, 4, 8 | Automated |
| TC-E2E-002 | Worker processes search request asynchronously | search-requests, agent-orchestration | 4, 6, 10 | Automated |
| TC-E2E-003 | Persist discovered product | product-catalog, persistence | 2, 3, 6 | Automated |
| TC-E2E-004 | Persist supplier contact | product-catalog, persistence | 2, 3, 6 | Automated |
| TC-E2E-005 | Display product catalog | product-catalog, webui | 4, 8 | Automated |
| TC-E2E-006 | Display product details | product-catalog, webui | 4, 8 | Automated |
| TC-E2E-007 | Request supplier contact through WebUI | supplier-contact, webui, persistence | 4, 7, 8 | Automated |
| TC-E2E-008 | Send email through real connector | supplier-contact, agent-orchestration, test-protocol | 7, 9 | Manual |
| TC-E2E-009 | Send Telegram through real connector | supplier-contact, agent-orchestration, test-protocol | 7, 9 | Manual |
| TC-E2E-010 | Browser MCP / agent search error | agent-orchestration, search-requests | 6, 10 | Automated |
| TC-E2E-011 | Invalid product card is skipped | product-catalog, agent-orchestration | 3, 6 | Automated |
| TC-E2E-012 | Product without price is saved | product-catalog, webui | 2, 6, 8 | Automated |
| TC-E2E-013 | Empty query validation | search-requests, webui | 3, 4, 8 | Automated |
| TC-E2E-014 | Short query validation | search-requests, webui | 3, 4, 8 | Automated |
| TC-E2E-015 | Overlong query validation | search-requests, webui | 3, 4, 8 | Automated |
| TC-E2E-016 | Prevent duplicate active contact attempt | supplier-contact, webui | 3, 4, 7, 8 | Automated |
| TC-E2E-017 | Product without contacts cannot be contacted | supplier-contact, webui | 3, 4, 8 | Automated |
| TC-E2E-018 | Email connector error is saved | supplier-contact, agent-orchestration | 7, 10 | Automated |
| TC-E2E-019 | Telegram connector error is saved | supplier-contact, agent-orchestration | 7, 10 | Automated |
| TC-E2E-020 | GET search requests API | search-requests | 4 | Automated |
| TC-E2E-021 | GET search request detail API | search-requests | 4 | Automated |
| TC-E2E-022 | GET request products API | product-catalog | 4 | Automated |
| TC-E2E-023 | GET product detail API | product-catalog | 4 | Automated |
| TC-E2E-024 | POST contact supplier API | supplier-contact | 4 | Automated |
| TC-E2E-025 | SearchRequest status transitions | search-requests, persistence | 3, 6 | Automated |
| TC-E2E-026 | AgentTask status transitions | agent-orchestration, persistence | 3, 6, 7 | Automated |
| TC-E2E-027 | ContactAttempt status transitions | supplier-contact, persistence | 3, 7 | Automated |
| TC-E2E-028 | UI loading states | webui | 8 | Automated |
| TC-E2E-029 | UI empty states | webui | 8 | Automated |
| TC-E2E-030 | UI error states | webui | 8 | Automated |
| TC-E2E-031 | Safe supplier message | supplier-contact | 5, 7 | Automated |
| TC-E2E-032 | Product search logs | agent-orchestration | 6, 10 | Automated |
| TC-E2E-033 | Supplier contact logs | agent-orchestration | 7, 10 | Automated |
| TC-E2E-034 | Search request creation latency | search-requests | 4, 11 | Automated |
| TC-E2E-035 | 1000 search requests list performance | search-requests, webui | 4, 8, 11 | Planned |
| TC-E2E-036 | Product catalog pagination | product-catalog, webui | 4, 8, 11 | Automated |
| TC-E2E-037 | WebUI refresh preserves persisted status | webui, persistence | 8, 11 | Planned |
| TC-E2E-038 | Worker restart during queued search | agent-orchestration, persistence | 6, 10, 11 | Planned |
| TC-E2E-039 | Worker restart during supplier contact | supplier-contact, agent-orchestration | 7, 10, 11 | Planned |
| TC-E2E-040 | No autonomous purchase | webui, supplier-contact | 5, 8 | Automated |
| TC-E2E-041 | No CRM functionality | webui | 8 | Automated |
| TC-E2E-042 | No mass messaging | webui, supplier-contact | 8 | Automated |
| TC-E2E-ACCEPTANCE-001 | Full happy path | all capabilities | 9, 11, 13 | Planned |
