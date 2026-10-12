# Tracking layout — implementation plan

## Stage 1: `--reset-to` must not lose data

**Goal**: A reset rolls back the portfolio book only and loses no closed trade.
**Success Criteria**:
- Non-position state in `tracking/` (hypotheses, events, ledgers, inbox,
  predictions, README) is never deleted or rewritten by the book restore.
- Closed trades with `exitDate <= target` stay byte-identical; two trades in
  one code both survive; no file is ever written to `closed/` by a reset.
- Trades not yet closed at the snapshot are removed; the position comes back
  active from the snapshot's full record (noon slot handled).
- The plan is printed before any change; a missing, malformed or
  contradictory snapshot exits 1 and changes nothing.
- One shared "is this a position" test (`position_manager.is_position_record`)
  used by the readers and the reset.
**Tests**: `tests/test_reset_to_date.py` (14 cases). Full suite green.
**Status**: Complete

## Stage 2: Move `tracking/` to book / ledgers / calendar

Owner-approved. **Waits for the `feat/event-triage` merge** (it edits
`event_inbox.py`, the run_daily phase-1 event-inbox block and the doctor —
the same files this stage must touch).

**Goal**: Split `tracking/` by kind, so a "book" operation cannot reach
non-book state by a glob:

```
tracking/
  book/      config.json, positions.json,
             active/{code}.json, closed/{code}_{exitDate}.json
  ledgers/   hypotheses.json, predictions.jsonl, rotation_ledger.json
  calendar/  events.json, event_inbox.md, event_inbox_ledger.json
```

**Success Criteria**:
- Every writer and reader uses path constants from one place (today they
  are spread over ~25 modules, see TODO.md).
- `is_position_record` stays as a guard, but `book/active/` holds positions
  only, so the root-glob class of bug (2026-08-11 list crash, 2026-10-12
  reset data loss) goes away.
- The doctor still reads OLD runs at the OLD paths — gate the new paths with
  an `ARTIFACT_EPOCHS` entry, never rewrite history.
- The root `conftest.py` sha256 guard covers the new paths (`LIVE_STATE` and
  the `tracking/[0-9]*.json` / `tracking/closed/*.json` globs).
- Snapshots: `snapshot_positions` / `plan_book_restore` read the new paths;
  old snapshots on disk still restore (format unchanged).
- The site (`build_site.py`) and `research/` tools read the new paths.

**Tests**: conftest guard trips on a write to each new path; reset tests
move to the new layout; doctor test that a pre-epoch run is judged at the old
paths; full suite green.

**Notes**:
- The 42 undated legacy closed files (`{code}.json`) stay as they are unless
  the owner decides otherwise. All readers glob, so names are free.
- `tracking/daily/` is empty, a leftover of migration ef461f8 (2026-03-05);
  `DAILY_DIR` is still created at import by `position_manager`. Remove both.
- `tracking/README.md` is out of date (says every `.json` is a position).
  Rewrite it for the new layout.
- `TRACKER_SCHEMA.md` rule 1 ("position_manager is the only writer") lists
  `--reset-to` as a violation; after stage 1 the reset writes through
  `position_manager._write_json`, but the plan still lives in `run_daily`.
  Decide in stage 2 whether to move `plan_book_restore` into
  `position_manager`.

**Status**: Not Started
