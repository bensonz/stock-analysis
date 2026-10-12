# Event inbox — pre-flight checklist

- [ ] `pytest` from worktree root fully green (report counts)
- [ ] No test touches real `tracking/` (conftest guard covers inbox + ledger)
- [ ] No network in unit tests (fetch injected); integration test marked
- [ ] Inbox refresh preserves owner marks/edits (round-trip test)
- [ ] Promote output has every field existing events have + `inbox_id`
- [ ] Pipeline step cannot fail the run; `[event-inbox]` line printed
- [ ] Doctor reads only; check skipped with reason on old runs
- [ ] CLAUDE.md + RUNBOOK updated in the CLI commit
- [ ] DECISIONS.md records date/tz rule + fuzzy rule + doctor classification
