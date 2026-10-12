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

## 2026-10-12 — Stage 2

- Worktree `/Users/bz/Work/Personal/stock-analysis-tracking-move`, branch
  `feat/tracking-layout` from master 60f84e3. Baseline 1027 passed / 13 skipped
  (with `data/pricedb` + `.env` symlinked, untracked).
- Found: the doctor never reads tracking/ (only runs/ + audit/ACCEPTED.md), and
  nothing reads tracking/ at old git revisions. No epoch gate, no old-path
  fallback needed (D13).
- Found: Gate-3 tests in test_contracts / test_corporate_actions compared the
  LIVE book; they broke as soon as the code moved. Made hermetic (D16).
- Found: the conftest guard never watched predictions.jsonl /
  rotation_ledger.json; it now hashes the whole tree (D12).
- Commits: code (47c1d56), migrate script, docs, data move (76 git renames).
- After the move: suite 1056 / 13; site, doctor --open, run_rules,
  event_inbox status, research tools identical to master; current
  snapshot_positions() == the last post-run snapshot on disk; 391/391
  snapshot plans, 0 errors; validator and Gate-3 consistency clean.
- Next: lead merges, re-runs the migrate script on master's tracking/ after
  the 2026-10-13 pipeline commits (D17).
