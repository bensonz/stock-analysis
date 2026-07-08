# Worker Prompt: Separate noon vs afternoon runs (stop overwriting run folders)

## Context / Problem

The daily pipeline (`scripts/run_daily.py`) writes all artifacts to `runs/<YYYY-MM-DD>/`.
It runs **twice per trading day**:

- **11:35 CST** — noon / intraday run (market still open, data is UNSETTLED)
- **15:35 CST** — afternoon / post-close run (settled close data)

Because both runs use the same `runs/<date>/` directory, **the 15:35 run overwrites the
11:35 run's files**. The noon run's data is permanently lost (only recoverable from the
prior git commit). This makes it impossible to compare the intraday read vs the settled
close — which is exactly the comparison we care about.

**Goal:** Give each run its own subfolder so both survive, while keeping "latest run"
discovery working for downstream code.

## Required behavior

1. Runs must be separated by **slot**, derived from wall-clock time at run start:
   - hour < 13  → slot = `noon`
   - hour >= 13 → slot = `afternoon`
   - New path layout: `runs/<YYYY-MM-DD>/<slot>/input/...` and `runs/<YYYY-MM-DD>/<slot>/output/...`
   - Also write `manifest.json`, `phase1.json`, `prompt.md`, `log.json`, `llm_meta.json`,
     `response*.json`, `gpt_response.txt`, etc. INSIDE the slot folder (everything that
     currently lands in `runs/<date>/`).

2. Add a `--slot {noon,afternoon}` CLI override (optional). If not passed, auto-derive from
   the local clock as above. This lets us force a slot for manual reruns/backfills.

3. **Stamp identity into `manifest.json`** (top level), so a run self-identifies without
   inspecting paths:
   - `"slot": "noon" | "afternoon"`
   - `"run_started_at": "<ISO-8601 local tz>"`  (already have `snapshot_time`-style stamps elsewhere; reuse `datetime.now().astimezone().isoformat()`)

4. **"Latest run" discovery must still work.** Downstream code loads the most recent
   watchlist / positions snapshot. Today that logic assumes `runs/<date>/output/...`.
   After this change it becomes `runs/<date>/<slot>/output/...`. Update ALL discovery/read
   sites (see "Code sites" below) so they:
   - Walk `runs/*/*/output/` (date, then slot), OR a helper that returns run dirs sorted by
     actual `run_started_at` (preferred — don't rely on lexical slot ordering, since
     "afternoon" < "noon" alphabetically which would sort WRONG).
   - When multiple slots exist for the same date, the **afternoon** run is the newer/canonical
     one for "latest settled state".

## Code sites to update (verified locations, 2026-07-08)

`scripts/run_daily.py`:
- **L87** `RUNS_DIR = PROJECT_ROOT / "runs"`
- **L189-194** `get_run_dir(date)` — the central path builder. Add slot: `get_run_dir(date, slot)`.
  This is the main change; make the slot subdir here and have callers pass the resolved slot.
- **L246** existing `snapshot_time` stamp — mirror/extend for `run_started_at` + `slot` in manifest.
- **L300-319** `snapshot_aux_state` / `restore_aux_state` — operate on `run_dir/output`; must
  use the slot-aware run_dir.
- **L460-469, L504** rerun/restore path: `RUNS_DIR / target_date` and
  `run_dir/output/positions_snapshot.json` (fallback `input/`) — must resolve a slot.
  Decide + document: a bare `--rerun <date>` should default to the **afternoon** slot if present,
  else noon. Support `--rerun <date> --slot <slot>`.
- **L511-514** `list_runs()` — update to enumerate date/slot and show slot + `run_started_at`.
- **L655-656** `run_dir = get_run_dir(date)` in the collect phase — pass slot.
- **L1041-1043** `output_dir = RUNS_DIR / date / "output"` (candidates.md) — slot-aware.

`scripts/data_collector.py`:
- **L1388-1401** `load_recent_watchlists()` — scans `runs/*/output/watchlist.json`. Update the
  glob to `runs/*/*/output/watchlist.json` and sort by `run_started_at` from each slot's
  `manifest.json` (fall back to file mtime if manifest missing). Do NOT sort by directory name.

Search the repo for any other `RUNS_DIR / date`, `runs/<date>`, `/ "output"`, `/ "input"`
constructions and update them consistently. Grep suggestions:
```
grep -rnE "RUNS_DIR ?/|runs/\*|/ \"output\"|/ \"input\"|runs/" scripts/
```

## Backward compatibility / migration

- **Old runs** live at `runs/<date>/output/...` (no slot). Discovery/read helpers MUST still
  find legacy runs: if `runs/<date>/<slot>/` doesn't exist but `runs/<date>/output/` does,
  treat the legacy layout as an implicit `afternoon` (settled) run.
- Do **NOT** bulk-migrate/move existing folders. Just make readers tolerant of both layouts.
  (There is already a `scripts/migrate_to_runs.py` — do not repurpose it; leave it alone.)

## Tests

- Update existing tests that assume `runs/<date>/output` (e.g. `test_full_pipeline.py`,
  `test_pipeline.py`, `test_build_summary.py`) to the slot-aware layout.
- Add tests:
  1. `get_run_dir(date, "noon")` and `(date, "afternoon")` create distinct dirs; running both
     leaves BOTH intact (no overwrite).
  2. Slot auto-derivation: mock clock at 11:35 → `noon`; at 15:35 → `afternoon`.
  3. `--slot` override wins over clock.
  4. Latest-run discovery returns the **afternoon** run when both exist for a date, and sorts
     correctly across dates by `run_started_at` (regression guard against alphabetical
     "afternoon" < "noon" bug).
  5. Legacy `runs/<date>/output/` (no slot) is still discovered as afternoon.
- Run the full suite; keep it green.

## Acceptance criteria

- After a noon run and an afternoon run on the same day, `runs/<date>/noon/` and
  `runs/<date>/afternoon/` both exist and neither is overwritten.
- `manifest.json` in each contains `slot` + `run_started_at`.
- `python scripts/run_daily.py --list-runs` shows slot + start time per run.
- Downstream watchlist/position discovery returns the correct latest (settled) state and passes
  tests, including legacy layout.
- No hardcoded assumption that `afternoon` sorts after `noon` lexically.

## Do NOT

- Do not change the cron schedule or the 11:35/15:35 times.
- Do not move/delete existing run folders.
- Do not alter analysis logic, LLM prompts, or hypothesis handling — this is purely
  run-directory partitioning + discovery.
