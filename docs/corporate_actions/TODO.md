# TODO
- [x] Stage 1 — event source (`corporate_actions.fetch_events` / `parse_events`)
- [x] Stage 2 — apply to the book (`apply_due`, `position_manager.dividend_cash`)
- [x] Stage 3 — wired into phase3_apply (step 0a) + Gate 3 + TRACKER_SCHEMA
- [x] dry run against a COPY of tracking/ (2026-10-08) — see PROGRESS.md
- [ ] review + merge the worktree branch (coordinator)
- [ ] live book: nothing to run by hand — the next pipeline slot's phase 3
      applies the two due events (000739, 603259). Verify after that run:
      `tracking/000739.json` + `603259.json` carry `corporateActions`,
      `positions.json` portfolio.dividendCash == 326.74.
- [ ] (owner) 送股 par-value tax not modelled — decide if it matters
