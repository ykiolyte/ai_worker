## Why

Supplier replies currently may include quoted Gmail history, which pollutes the conversation. Follow-up agent replies can also fall back to the initial supplier-request template, making the agent look like a script instead of a context-aware employee.

## What Changes

- Clean quoted email history from inbound Gmail bodies before storing conversation messages.
- Keep only the supplier's new reply text when Gmail includes `On ... wrote:` or localized quote headers.
- Use a follow-up-specific safety policy that does not require repeating every initial sourcing question.
- Prevent conversation replies from falling back to the initial supplier outreach template.
- Ask the model for a contextual corrected reply when the first model output is unusable or outside MVP boundaries.
- Auto-send a contextual AI follow-up for every matched inbound Gmail supplier reply instead of waiting for manual approval.
- Include `docs/ooo.md` as authoritative company knowledge for supplier replies.

## Impact

- Gmail IMAP parsing and inbound sync behavior.
- Supplier reply generation and worker safety validation.
- Gmail sync default behavior and product-details sync mode.
- Tests for email cleaning, company knowledge from `docs/ooo.md`, and contextual AI replies.
