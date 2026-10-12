# Event inbox — TODO

- [x] Stage 1: event_inbox.py core + tests
- [x] Stage 2: promote + ledger + CLI; CLAUDE.md + RUNBOOK
- [x] Stage 3: run_daily wiring + input/event_inbox.json
- [x] Stage 4: doctor check + test
- [x] Stage 5: real refresh, tick midterm, promote, data commit
- [x] Add inbox + ledger to root conftest LIVE_STATE guard

## AI triage (owner 2026-10-12)
- [x] Stage 6: event_triage.py + agents/EVENT_TRIAGE.md + triage/override in event_inbox; CLAUDE.md + RUNBOOK
- [x] Stage 7: report 〔AI选入〕 marker (event_calendar passes decided_by)
- [ ] Stage 8: doctor triage-failure finding; status AI stats; WEEKLY_AUDIT step
- [ ] Stage 9: live triage of the 22 undecided items; data commit

## Follow-ups for the owner (not done here)
- [x] Triage the first inbox — now done by the AI (Stage 9).
- [ ] events.json `美国9月CPI公布（日期待BLS确认）` says 2026-10-13; wallstreetcn
      lists 美国9月CPI 2026-10-14 20:30 Beijing (impact 10-15). The fuzzy
      dedupe matched them (±1 day) so no inbox item was raised — fix the date by hand.
- [x] Raise MIN_IMPORTANCE to 4 (owner 2026-10-12: 91 items at >=3, mostly noise).
