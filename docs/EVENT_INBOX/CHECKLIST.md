# Event inbox — pre-flight checklist

- [x] `pytest` from worktree root fully green (report counts)
- [x] No test touches real `tracking/` (conftest guard covers inbox + ledger)
- [x] No network in unit tests (fetch injected); integration test marked
- [x] Inbox refresh preserves owner marks/edits (round-trip test)
- [x] Promote output has every field existing events have + `inbox_id`
- [x] Pipeline step cannot fail the run; `[event-inbox]` line printed
- [x] Doctor reads only; check skipped with reason on old runs
- [x] CLAUDE.md + RUNBOOK updated in the CLI commit
- [x] DECISIONS.md records date/tz rule + fuzzy rule + doctor classification
