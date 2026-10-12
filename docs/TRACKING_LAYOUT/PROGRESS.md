# Tracking layout — progress

## 2026-10-12 — Stage 1

- Worktree `/Users/bz/Work/Personal/stock-analysis-restore-fix`, branch
  `fix/restore-snapshot` from master 5e19ea6. Baseline 977 passed / 13 skipped
  (needs the `data/pricedb` symlink for `test_backtest`).
- Found: snapshots are written by `snapshot_positions` — `pre_run` to
  `input/positions_snapshot.json` (start of phase 1) and `post_run` to
  `output/positions_snapshot.json` (end of the run), plus
  `output/hypotheses_snapshot.json` + `output/LEARNINGS.md` via
  `snapshot_aux_state`. 391 snapshot files on disk (2026-03-05 → 2026-10-12);
  all have full `active_positions` records (with `history`), non-empty
  `positions_json` and `portfolio_config`. 2026-03 ones also carry
  `learnings_md` (ignored).
- Found: `closed_positions` is a summary keyed by code; live book has 65
  closed files (42 undated, 23 dated), 60 with `exitSlot`.
- Wrote 12 red tests (7 failed on master), then the fix; added 2 more
  (aux restore kept, contradiction abort). 14 pass.
- Dry-planned every real snapshot against the live book, read-only: 0 errors;
  e.g. the 2026-10-08 noon snapshot would delete only `000739_2026-10-09.json`
  and keep 64 closed files.
- Full suite: 991 passed, 13 skipped.
- Next: stage 2 after `feat/event-triage` merges.
