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
- [ ] Doctor judges pre-move runs at the old paths
- [ ] conftest guard covers every new path
- [ ] Site builds; equity curve unchanged
- [ ] A full `--run --no-commit` on a scratch copy works end to end
