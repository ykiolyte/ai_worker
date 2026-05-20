## 1. Regression Tests

- [x] 1.1 Add a failing worker test proving queued initial supplier-contact tasks are sent by a worker tick.
- [x] 1.2 Add a failing worker-entry test proving the standalone worker loop processes at least one queued supplier-contact task instead of idling.

## 2. Worker Fix

- [x] 2.1 Replace the idle worker entry point with a processing loop that uses the existing runtime and task processors.
- [x] 2.2 Keep connector failures persisted and redacted for UI/API visibility.

## 3. Verification

- [x] 3.1 Run targeted supplier contact, API, connector, and worker tests.
- [x] 3.2 Run full backend test suite.
- [x] 3.3 Run frontend build.
- [x] 3.4 Validate OpenSpec change strictly.
