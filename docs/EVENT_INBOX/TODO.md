# Event inbox — TODO

- [x] Stage 1: event_inbox.py core + tests
- [x] Stage 2: promote + ledger + CLI; CLAUDE.md + RUNBOOK
- [x] Stage 3: run_daily wiring + input/event_inbox.json
- [x] Stage 4: doctor check + test
- [x] Stage 5: real refresh, tick midterm, promote, data commit
- [x] Add inbox + ledger to root conftest LIVE_STATE guard

## Follow-ups for the owner (not done here)
- [ ] Triage the first inbox: 91 undecided items, 48 inside the 7-day window.
- [ ] events.json `美国9月CPI公布（日期待BLS确认）` says 2026-10-13; wallstreetcn
      lists 美国9月CPI 2026-10-14 20:30 Beijing (impact 10-15). The fuzzy
      dedupe matched them (±1 day) so no inbox item was raised — fix the date by hand.
- [ ] Consider raising MIN_IMPORTANCE to 4 or filtering regions if triage is too heavy.
