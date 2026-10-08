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
