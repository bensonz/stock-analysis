# Tracking layout — TODO

## Stage 1 (Complete)
- [x] Read snapshot builder, restore, reset; find snapshot sources
- [x] Check all snapshots on disk for shape (391, all pass)
- [x] Check closed files are not changed after exit (corporate actions: open only)
- [x] Check `exitSlot` (60 of 65 closed files have it; the fix does not need it)
- [x] Red tests in `tests/test_reset_to_date.py`
- [x] `position_manager.is_position_record`; readers use it
- [x] `plan_book_restore` / `apply_book_restore`; plan printed first
- [x] Dry-run the plan for every real snapshot vs the live book (0 errors)
- [x] RUNBOOK update
- [x] Full suite green

## Stage 2 (Not Started — after feat/event-triage merges)
- [ ] One module for tracking path constants
- [ ] Move files (git mv) to book/ ledgers/ calendar/
- [ ] Update writers/readers: position_manager, run_daily, corporate_actions,
      contracts, validator, doctor, build_site, event_calendar, event_inbox,
      hypothesis_manager, prediction_log, rotation_ledger, run_rules,
      evaluation_epoch, manual_full_pipeline_check, research/*, oneoff/* (record only)
- [ ] Doctor: ARTIFACT_EPOCHS entry for the new paths
- [ ] Root conftest guard: new paths
- [ ] Remove `tracking/daily/` and `DAILY_DIR`
- [ ] Rewrite `tracking/README.md`; update TRACKER_SCHEMA.md, CLAUDE.md, RUNBOOK
- [ ] Owner decision: rename the 42 undated closed files or not
