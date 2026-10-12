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

## AI triage
- [x] No unit test reaches the real LLM (autouse refusal in test_event_inbox)
- [x] AI never adds events / changes name, date, tz (only marks, impact, direction)
- [x] Owner mark before AI wins; any owner edit of a 🤖 item wins after
- [x] LLM failure recorded, run continues, items retried; doctor finding
- [x] CLAUDE.md + RUNBOOK updated with the behaviour change
- [x] Full suite green (1012 passed, 13 skipped)
- [x] Live triage on the real inbox (Stage 9)
