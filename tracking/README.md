# tracking/ — the live state

Split by kind since 2026-10-12 (`docs/TRACKING_LAYOUT/`). The paths are named
once, in `scripts/tracking_paths.py`; schema in `TRACKER_SCHEMA.md`.

```
book/        the portfolio — written only by scripts/position_manager.py
  active/    {code}.json, one per OPEN position (nothing else lives here)
  closed/    {code}_{exitDate}.json on close (pre-2026-08-06 trades: {code}.json)
  positions.json   aggregate, regenerated every run — never hand-edit
  config.json      hard limits (starting capital, max positions, max %)
ledgers/     hypotheses.json, predictions.jsonl, rotation_ledger.json
calendar/    events.json, event_inbox.md (the owner ticks here),
             event_inbox_ledger.json
```

## Position lifecycle
1. **Opened** by `position_manager.open_position` → `book/active/{code}.json`
2. **Updated** twice per trading day by the pipeline
3. **Closed** by `position_manager.close_position` → moved to `book/closed/`

`python3 scripts/run_daily.py --reset-to DATE` rolls back `book/` only.
Everything here is git-committed by every successful run.
