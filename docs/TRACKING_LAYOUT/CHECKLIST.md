# Tracking layout — pre-flight checklist

## Stage 1
- [x] New tests red before the fix (7 of 12 failed), green after
- [x] Full suite green: 991 passed, 13 skipped (baseline 977 / 13)
- [x] No test touches the real `tracking/` (tmp dirs; root conftest guard passed)
- [x] Missing snapshot: exit 1, nothing changed (test)
- [x] Malformed snapshot: exit 1, nothing changed, run dirs kept (test)
- [x] Contradictory snapshot: exit 1, nothing changed (test)
- [x] Works with the 391 snapshots on disk (read-only dry plan, 0 errors)
- [x] `--reset-to` CLI unchanged
- [x] RUNBOOK updated
- [x] Not run against the live book (destructive; dry plan only)

## Stage 2
- [x] Doctor judges pre-move runs at the old paths — it reads runs/ only, so the
      layout never enters a judgement (D13); `doctor --open` output identical to master
- [x] conftest guard covers every new path (`tests/test_live_state_guard.py`)
- [x] Site builds; equity curve unchanged (HTML identical to master except the
      build timestamp and the footer path text: 144 equity points, 3 positions,
      65 closed trades)
- [x] Full suite green: 1056 passed, 13 skipped (baseline 1027 / 13)
- [x] Migrate script idempotent; refuses on old≠new and on unknown root files (tests)
- [x] Old snapshots restore: 391/391 plan with 0 errors on the migrated book;
      a real 2026-10-09 snapshot restores into book/ (test)
- [x] `run_rules --human`, `event_inbox status` identical to master
- [x] research tools (reentry_stats, win_rate, exit_ablation, entry_drift,
      candidate_alpha picks) identical to master
- [ ] A full `--run --no-commit` on a scratch copy — NOT done (lead: do not run
      the pipeline; it calls the LLM). First live slot after the merge is the
      end-to-end check.
