# Progress
## 2026-10-08
- Planned; delegated Stages 1-3 to a sub-agent in a worktree.
- Sub-agent (worktree): fast-forwarded to 609d161. Baseline 900 passed /
  12 skipped (needs `data/pricedb` symlinked into the worktree — git-ignored).
- One live read-only fetch of 000739: 26 rows; 2026-10-08 row is
  PRETAX_BONUS_RMB 1.39, BONUS_IT_RATIO null, 实施分配 — parsing confirmed.
- No tracking/ fingerprint guard exists in any conftest (memory note is stale);
  tests/test_corporate_actions.py carries its own module-scoped guard.
- Stages 1+2 done: scripts/corporate_actions.py + position_manager dividend
  term; 29 new tests; full suite 929 passed / 12 skipped.
- Stage 3 done: `run_daily.apply_corporate_actions` is phase-3 step 0a
  (before enforce_hard_sells; refreshes the phase-1 positions copy after a
  送转). Result in the phase-3 log (`log.json` → `corporate_actions`) and
  Gate 3 (dividend = note; fetch failure / crash / 送转 = soft warn). The
  write moved to `position_manager.save_corporate_actions` (only writer rule).
- TRACKER_SCHEMA.md updated; site cross-check note no longer claims the book
  ignores dividends. No command changes → RUNBOOK/CLAUDE.md untouched.
- Doctor has no cash/equity reconciliation check; nothing to keep in sync.
- Dry run on a COPY of live tracking/ (2026-10-08), 3 extra read-only
  fetches approved by coordinator (000739 reused from the first fetch):
  - 000739 普洛药业 ex 2026-10-08 10派1.39: gross 236.30, tax 47.26 (20%),
    net 189.04
  - 603259 药明康德 ex 2026-09-04 10派5.1 (missed, back-credit): gross
    153.00, tax 15.30 (10%, held 07-31→09-04 > 1 month), net 137.70
  - 601872 (ex 2026-07-10) and 603127 (ex 2026-06-30): before entry, none
  - cash +326.74, realizedPnl +326.74, re-run applied 0, live tracking/
    hash unchanged.
- Full suite: 937 passed / 12 skipped.
- Merged to master by coordinator (conflict: build_site.py JS had moved to
  scripts/site_assets/app.js — kept master, carried the one text edit over).
  941 passed / 12 skipped with the restored root live-book guard (e9d7958).
- Live book NOT touched tonight: the next pipeline slot back-credits both
  events (FUTURE.md check due 2026-10-09).
