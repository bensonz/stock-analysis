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

## Stage 2 (Complete)
- [x] One module for tracking path constants (`scripts/tracking_paths.py`)
- [x] Move files (git mv) to book/ ledgers/ calendar/ — `scripts/oneoff/migrate_tracking_layout.py`
- [x] Update writers/readers: position_manager, run_daily, corporate_actions,
      contracts, validator, doctor (text only), build_site, event_calendar,
      event_inbox, event_triage (doc), hypothesis_manager, prediction_log,
      rotation_ledger, run_rules, evaluation_epoch (doc),
      manual_full_pipeline_check, test_simulation, research/{backtest,
      candidate_alpha, entry_drift, exit_ablation, index_event_study,
      reentry_stats, win_rate}. oneoff/* left as the record.
- [x] Doctor: checked — reads runs/ only, no ARTIFACT_EPOCHS entry needed (D13); test pins it
- [x] Root conftest guard: whole tracking/ tree (`scripts/live_state_guard.py`, D12)
- [x] Remove `tracking/daily/` and `DAILY_DIR` (+ save_daily_summary / validator fallbacks, D15)
- [x] Rewrite `tracking/README.md`; update TRACKER_SCHEMA.md, CLAUDE.md, RUNBOOK, agents/*.md
- [x] `plan_book_restore` → position_manager (D9); reset order book → aux → run dirs (D10)
- [x] Owner decision taken by lead: keep the 42 undated closed filenames
- [x] Gate-3 tests made hermetic (D16)
- [ ] At merge: re-run the migrate script on master's tracking/ (D17)
