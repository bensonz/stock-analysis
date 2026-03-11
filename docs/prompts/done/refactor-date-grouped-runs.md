# Refactor: Date-Grouped Runs with Position Snapshots & Reset

## Goal

Restructure the stock analysis pipeline so every daily run is **self-contained under `runs/YYYY-MM-DD/`**, making runs re-inspectable, re-runnable, and resettable to any prior date.

## Current Structure (to be replaced)

```
data/crawl/YYYY-MM-DD.json        → strategy pool snapshot
data/market/YYYY-MM-DD.json       → market overview
data/prices/YYYY-MM-DD.json       → position prices
data/phase1_YYYY-MM-DD.json       → full Phase 1 blob
watchlist/YYYY-MM-DD.json         → LLM watchlist output
reports/YYYY-MM-DD.md             → LLM report output
tracking/daily/YYYY-MM-DD.json    → daily summary
logs/YYYY-MM-DD.json              → run log
```

Global mutable state (keep these, but snapshot them):
```
tracking/*.json                   → individual position files
tracking/closed/*.json            → closed positions
tracking/positions.json           → aggregated view
tracking/portfolio_config.json    → config
LEARNINGS.md                      → append-only lessons
```

## New Structure

```
runs/
  2026-03-05/
    input/                         # State at START of run (before any mutations)
      crawl.json                   # strategy pool
      market.json                  # market overview
      prices.json                  # position prices
      iv_sentiment.json            # IV sentiment data
      positions_snapshot.json      # full snapshot (see schema below)
    phase1.json                    # full collected data blob (same as old data/phase1_*.json)
    prompt.md                      # the exact LLM prompt that was built
    response.json                  # the raw LLM response (saved by --apply)
    output/                        # State AFTER apply
      watchlist.json               # generated watchlist
      report.md                    # generated report
      daily_summary.json           # actions taken
      positions_snapshot.json      # full snapshot after mutations
    log.json                       # run log (same as old logs/*.json)

tracking/                          # Global mutable state (unchanged structure)
  portfolio_config.json
  positions.json
  300684.json
  600096.json
  closed/
    688630.json
    ...

LEARNINGS.md                       # Global, append-only (unchanged)
agents/                            # Unchanged
scripts/                           # Unchanged
```

### positions_snapshot.json Schema

```json
{
  "snapshot_time": "2026-03-05T14:30:00+08:00",
  "snapshot_type": "pre_run" | "post_run",
  "date": "2026-03-05",
  "portfolio_config": {
    "starting_capital": 1000000,
    "max_position_pct": 10,
    "max_positions": 10
  },
  "positions_json": {
    // ... exact copy of tracking/positions.json content
  },
  "active_positions": {
    "300684": { /* full content of tracking/300684.json */ },
    "600096": { /* full content of tracking/600096.json */ },
    "600499": { /* full content of tracking/600499.json */ }
  },
  "closed_positions": {
    "688630": { /* full content of tracking/closed/688630.json */ },
    "600988": { /* full content of tracking/closed/600988.json */ }
  },
  "learnings_md": "# LEARNINGS.md\n..."
}
```

## Files to Modify

### 1. `scripts/run_daily.py` (main orchestrator)

**Changes:**

#### a) Replace directory constants
```python
# OLD
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# NEW
RUNS_DIR = PROJECT_ROOT / "runs"
```

#### b) Add `get_run_dir(date)` helper
```python
def get_run_dir(date: str) -> Path:
    """Get the run directory for a date, creating subdirs as needed."""
    run_dir = RUNS_DIR / date
    (run_dir / "input").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    return run_dir
```

#### c) Add snapshot functions

```python
def snapshot_positions(snapshot_type: str, date: str) -> dict:
    """Create a full snapshot of all position state.
    
    Args:
        snapshot_type: "pre_run" or "post_run"
        date: Date string
    
    Returns:
        The snapshot dict.
    """
    from position_manager import (
        load_active_positions, load_all_tracking_files,
        load_portfolio_config, TRACKING_DIR, CLOSED_DIR, POSITIONS_FILE
    )
    
    # Read all active position files
    active = {}
    for f in sorted(TRACKING_DIR.glob("*.json")):
        if f.name in ("positions.json", "portfolio_config.json"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") == "active":
                active[data["code"]] = data
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Read all closed position files
    closed = {}
    for f in sorted(CLOSED_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            closed[data["code"]] = data
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Read positions.json
    positions_json = {}
    if POSITIONS_FILE.exists():
        positions_json = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    
    # Read LEARNINGS.md
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    learnings = learnings_file.read_text(encoding="utf-8") if learnings_file.exists() else ""
    
    return {
        "snapshot_time": datetime.now().astimezone().isoformat(),
        "snapshot_type": snapshot_type,
        "date": date,
        "portfolio_config": load_portfolio_config(),
        "positions_json": positions_json,
        "active_positions": active,
        "closed_positions": closed,
        "learnings_md": learnings,
    }


def restore_snapshot(snapshot: dict) -> None:
    """Restore tracking state from a snapshot.
    
    WARNING: This overwrites all tracking/*.json, tracking/closed/*.json,
    tracking/positions.json, tracking/portfolio_config.json, and LEARNINGS.md.
    """
    from position_manager import TRACKING_DIR, CLOSED_DIR, POSITIONS_FILE, PORTFOLIO_CONFIG_FILE
    
    # Clear active positions (but not the directory itself)
    for f in TRACKING_DIR.glob("*.json"):
        if f.name in ("positions.json", "portfolio_config.json"):
            continue
        f.unlink()
    
    # Clear closed positions
    for f in CLOSED_DIR.glob("*.json"):
        f.unlink()
    
    # Write active positions
    for code, data in snapshot.get("active_positions", {}).items():
        path = TRACKING_DIR / f"{code}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    
    # Write closed positions
    for code, data in snapshot.get("closed_positions", {}).items():
        path = CLOSED_DIR / f"{code}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    
    # Write positions.json
    if snapshot.get("positions_json"):
        POSITIONS_FILE.write_text(
            json.dumps(snapshot["positions_json"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
    
    # Write portfolio_config.json
    if snapshot.get("portfolio_config"):
        PORTFOLIO_CONFIG_FILE.write_text(
            json.dumps(snapshot["portfolio_config"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8"
        )
    
    # Write LEARNINGS.md
    if "learnings_md" in snapshot:
        learnings_file = PROJECT_ROOT / "LEARNINGS.md"
        learnings_file.write_text(snapshot["learnings_md"], encoding="utf-8")
```

#### d) Modify `phase1_collect()` 

At the **start** of phase1_collect, before any data fetching:
1. Create `run_dir = get_run_dir(date)`
2. Take a pre-run snapshot: `pre_snap = snapshot_positions("pre_run", date)`
3. Save it: `run_dir / "input" / "positions_snapshot.json"`

Change all save calls to write into `runs/YYYY-MM-DD/input/` instead of `data/crawl/`, `data/market/`, `data/prices/`:
- `save_crawl_data(date, ...)` → write to `run_dir / "input" / "crawl.json"`
- `save_market_data(date, ...)` → write to `run_dir / "input" / "market.json"`
- `save_price_data(date, ...)` → write to `run_dir / "input" / "prices.json"`
- IV sentiment → write to `run_dir / "input" / "iv_sentiment.json"`

Save the full Phase 1 blob to `run_dir / "phase1.json"` instead of `data/phase1_YYYY-MM-DD.json`.

**Important:** The `save_crawl_data`, `save_market_data`, `save_price_data` functions in `data_collector.py` should NOT be changed — instead, just stop calling them from `run_daily.py` and do direct writes into the run dir. OR update them to accept a `run_dir` parameter (your choice — pick whichever is cleaner). The functions still exist for backward compat but the orchestrator controls where files land.

#### e) Modify `phase2_build_prompt()`

After building the prompt string, save it:
```python
run_dir = get_run_dir(data["date"])
(run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
```

#### f) Modify `phase3_apply()`

At the start of phase3_apply:
```python
run_dir = get_run_dir(date)
```

Save the raw LLM response:
```python
# Save response.json into the run dir (called from --apply handler)
```

Change output file locations:
- `generate_watchlist_json()` → write to `run_dir / "output" / "watchlist.json"` instead of `watchlist/YYYY-MM-DD.json`
- `generate_report_md()` → write to `run_dir / "output" / "report.md"` instead of `reports/YYYY-MM-DD.md`
- `save_daily_summary()` → write to `run_dir / "output" / "daily_summary.json"` instead of `tracking/daily/YYYY-MM-DD.json`

At the **end** of phase3_apply (after all mutations):
1. Take a post-run snapshot: `post_snap = snapshot_positions("post_run", date)`
2. Save it: `run_dir / "output" / "positions_snapshot.json"`

#### g) Modify `phase4_validate_and_log()`

Save log to `run_dir / "log.json"` instead of `logs/YYYY-MM-DD.json`.

#### h) Modify `--apply` handler in `main()`

When loading Phase 1 data, look for `runs/YYYY-MM-DD/phase1.json` instead of `data/phase1_YYYY-MM-DD.json`.

Save the response file content into `run_dir / "response.json"` before applying.

#### i) Add `--reset-to DATE` command

```python
if "--reset-to" in args:
    idx = args.index("--reset-to")
    if idx + 1 >= len(args):
        print("Usage: --reset-to YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    target_date = args[idx + 1]
    reset_to_date(target_date)
    return
```

```python
def reset_to_date(target_date: str) -> None:
    """Reset all position state to the end-of-day state of target_date.
    
    Reads runs/<target_date>/output/positions_snapshot.json and restores
    tracking/ state from it. Also deletes any run dirs after target_date.
    
    Example: --reset-to 2026-03-04
      → Restores positions to end-of-day 2026-03-04 state
      → Deletes runs/2026-03-05/, runs/2026-03-06/, etc.
      → Now you can re-run 2026-03-05 cleanly
    """
    run_dir = RUNS_DIR / target_date
    snapshot_file = run_dir / "output" / "positions_snapshot.json"
    
    if not snapshot_file.exists():
        # Try input snapshot if output doesn't exist (run never completed)
        snapshot_file = run_dir / "input" / "positions_snapshot.json"
        if not snapshot_file.exists():
            print(f"No snapshot found for {target_date}", file=sys.stderr)
            print(f"Available dates:", file=sys.stderr)
            for d in sorted(RUNS_DIR.iterdir()):
                if d.is_dir():
                    has_out = (d / "output" / "positions_snapshot.json").exists()
                    has_in = (d / "input" / "positions_snapshot.json").exists()
                    status = "✓ complete" if has_out else ("⚠ input only" if has_in else "✗ no snapshot")
                    print(f"  {d.name}  {status}", file=sys.stderr)
            sys.exit(1)
    
    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    
    # Confirm
    active_count = len(snapshot.get("active_positions", {}))
    closed_count = len(snapshot.get("closed_positions", {}))
    print(f"Resetting to {target_date} ({snapshot_file.parent.name} snapshot)", file=sys.stderr)
    print(f"  Active positions: {active_count}", file=sys.stderr)
    print(f"  Closed positions: {closed_count}", file=sys.stderr)
    
    # Delete run dirs after target_date
    deleted = []
    for d in sorted(RUNS_DIR.iterdir()):
        if d.is_dir() and d.name > target_date:
            shutil.rmtree(d)
            deleted.append(d.name)
    if deleted:
        print(f"  Deleted runs: {', '.join(deleted)}", file=sys.stderr)
    
    # Restore
    restore_snapshot(snapshot)
    
    # Regenerate positions.json with current data (no live prices)
    from position_manager import regenerate_positions_json
    regenerate_positions_json()
    
    print(f"\n✓ State restored to end of {target_date}", file=sys.stderr)
```

**Add `import shutil`** at the top of the file (it's not currently imported).

#### j) Add `--list-runs` command

```python
if "--list-runs" in args:
    list_runs()
    return
```

```python
def list_runs() -> None:
    """List all run directories with status."""
    if not RUNS_DIR.exists():
        print("No runs yet.", file=sys.stderr)
        return
    
    for d in sorted(RUNS_DIR.iterdir()):
        if not d.is_dir():
            continue
        has_phase1 = (d / "phase1.json").exists()
        has_prompt = (d / "prompt.md").exists()
        has_response = (d / "response.json").exists()
        has_output = (d / "output" / "positions_snapshot.json").exists()
        
        if has_output:
            status = "✓ complete"
        elif has_response:
            status = "⚠ applied but no post-snapshot"
        elif has_prompt:
            status = "◐ awaiting LLM response"
        elif has_phase1:
            status = "◑ phase1 done"
        else:
            status = "○ started"
        
        print(f"  {d.name}  {status}")
```

### 2. `scripts/data_collector.py`

The save functions (`save_crawl_data`, `save_market_data`, `save_price_data`) currently write to `data/crawl/`, `data/market/`, `data/prices/`. 

**Option A (recommended):** Add optional `output_dir` parameter to each:

```python
def save_crawl_data(date: str, data: dict, output_dir: Path | None = None) -> Path:
    """Save strategy pool crawl data."""
    if output_dir:
        out = output_dir / "crawl.json"
    else:
        out = CRAWL_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out

def save_market_data(date: str, data: dict, output_dir: Path | None = None) -> Path:
    if output_dir:
        out = output_dir / "market.json"
    else:
        out = MARKET_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out

def save_price_data(date: str, data: dict, output_dir: Path | None = None) -> Path:
    if output_dir:
        out = output_dir / "prices.json"
    else:
        out = PRICES_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
```

Then in `run_daily.py` phase1_collect, call them with `output_dir=run_dir / "input"`.

**Also add** `load_recent_watchlists` to look in `runs/*/output/watchlist.json` as well as the old `watchlist/` dir:

```python
def load_recent_watchlists(days: int = 5) -> list[dict]:
    """Load recent watchlist JSON files from runs/ and legacy watchlist/ dir."""
    watchlists = []
    
    # New location: runs/*/output/watchlist.json
    runs_dir = PROJECT_ROOT / "runs"
    if runs_dir.exists():
        for d in sorted(runs_dir.iterdir(), reverse=True):
            if len(watchlists) >= days:
                break
            wl_file = d / "output" / "watchlist.json"
            if wl_file.exists():
                try:
                    watchlists.append(json.loads(wl_file.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, IOError):
                    pass
    
    # Legacy fallback: watchlist/*.json
    if len(watchlists) < days:
        legacy_dir = PROJECT_ROOT / "watchlist"
        if legacy_dir.exists():
            files = sorted(legacy_dir.glob("*.json"), reverse=True)
            for f in files:
                if len(watchlists) >= days:
                    break
                try:
                    wl = json.loads(f.read_text(encoding="utf-8"))
                    # Avoid duplicates by date
                    existing_dates = {w.get("date") for w in watchlists}
                    if wl.get("date") not in existing_dates:
                        watchlists.append(wl)
                except (json.JSONDecodeError, IOError):
                    pass
    
    return watchlists
```

### 3. `scripts/report_generator.py`

Add optional `output_dir` parameter to both functions:

```python
def generate_watchlist_json(date: str, data: dict, decisions: dict, output_dir: Path | None = None) -> Path:
    # ... same logic ...
    if output_dir:
        out = output_dir / "watchlist.json"
    else:
        out = WATCHLIST_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # ... write ...

def generate_report_md(date: str, data: dict, decisions: dict, output_dir: Path | None = None) -> Path:
    # ... same logic ...
    if output_dir:
        out = output_dir / "report.md"
    else:
        out = REPORTS_DIR / f"{date}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    # ... write ...
```

### 4. `scripts/position_manager.py`

Add `output_dir` parameter to `save_daily_summary`:

```python
def save_daily_summary(date: str, actions: list[dict], output_dir: Path | None = None, **extra) -> Path:
    summary = {"date": date, "actions": actions, **extra}
    if output_dir:
        out = output_dir / "daily_summary.json"
    else:
        out = DAILY_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out, summary)
    return out
```

### 5. `scripts/validator.py`

Update `validate_output` to look in `runs/YYYY-MM-DD/output/` instead of the old flat dirs:

```python
def validate_output(date: str) -> list[str]:
    errors = []
    
    run_dir = PROJECT_ROOT / "runs" / date
    output_dir = run_dir / "output"
    
    # ... positions.json consistency checks stay the same (they read tracking/) ...
    
    # Watchlist: check runs/<date>/output/watchlist.json
    wl_file = output_dir / "watchlist.json"
    if not wl_file.exists():
        # Legacy fallback
        wl_file = WATCHLIST_DIR / f"{date}.json"
    if wl_file.exists():
        try:
            wl = json.loads(wl_file.read_text(encoding="utf-8"))
            if "recommendations" not in wl:
                errors.append(f"WARNING: watchlist missing 'recommendations' key")
        except json.JSONDecodeError as e:
            errors.append(f"CRITICAL: watchlist is invalid JSON: {e}")
    else:
        errors.append(f"WARNING: no watchlist found for {date}")
    
    # Report: check runs/<date>/output/report.md
    report_file = output_dir / "report.md"
    if not report_file.exists():
        report_file = REPORTS_DIR / f"{date}.md"
    if not report_file.exists():
        errors.append(f"WARNING: no report found for {date}")
    
    # Daily summary: check runs/<date>/output/daily_summary.json
    daily_file = output_dir / "daily_summary.json"
    if not daily_file.exists():
        daily_file = DAILY_DIR / f"{date}.json"
    if daily_file.exists():
        try:
            json.loads(daily_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"WARNING: daily summary is invalid JSON: {e}")
    else:
        errors.append(f"INFO: no daily summary found for {date}")
    
    return errors
```

### 6. `scripts/run_rules.py`

No changes needed — it reads `tracking/positions.json` which remains the global source of truth.

### 7. `.gitignore`

Add:
```
runs/*/phase1.json
runs/*/prompt.md
runs/*/response.json
```

These can be large and are regenerable. Keep `input/`, `output/`, and `log.json` tracked in git.

Actually — this is debatable. If you want full reproducibility in git, track everything. If you want a smaller repo, ignore the large blobs. Your call — just add a comment in `.gitignore` explaining the choice.

## Migration

The old directories (`data/`, `watchlist/`, `reports/`, `logs/`, `tracking/daily/`) should NOT be deleted — they contain historical data. The new code has legacy fallbacks (especially `load_recent_watchlists`). Over time, old data naturally becomes irrelevant as new runs accumulate in `runs/`.

Optionally, you can write a migration script later to move old data into `runs/` format, but it's not required for the refactor.

## Updated CLI

After refactor, the CLI should be:

```bash
# Standard daily pipeline
python scripts/run_daily.py                     # Phase 1 + 2 (collect + build prompt)
python scripts/run_daily.py --phase1            # Phase 1 only
python scripts/run_daily.py --apply FILE        # Phase 3 + 4 (apply LLM response)

# New commands
python scripts/run_daily.py --reset-to 2026-03-04   # Reset state to end of March 4
python scripts/run_daily.py --list-runs              # Show all runs with status
python scripts/run_daily.py --validate               # Validate today's output (unchanged)
python scripts/run_daily.py --validate 2026-03-04    # Validate specific date
```

## Consistency Check (new feature)

At the start of each run, after taking the pre-run snapshot, compare it to the previous day's post-run snapshot:

```python
def check_snapshot_consistency(date: str, current_snapshot: dict) -> list[str]:
    """Check if current state matches the previous day's post-run snapshot."""
    warnings = []
    
    # Find the most recent prior run with a post-run snapshot
    prior_dates = sorted(
        [d.name for d in RUNS_DIR.iterdir() 
         if d.is_dir() and d.name < date 
         and (d / "output" / "positions_snapshot.json").exists()],
        reverse=True
    )
    
    if not prior_dates:
        return []  # No prior run to compare against
    
    prior_file = RUNS_DIR / prior_dates[0] / "output" / "positions_snapshot.json"
    prior = json.loads(prior_file.read_text(encoding="utf-8"))
    
    # Compare active position codes
    prior_codes = set(prior.get("active_positions", {}).keys())
    current_codes = set(current_snapshot.get("active_positions", {}).keys())
    
    if prior_codes != current_codes:
        added = current_codes - prior_codes
        removed = prior_codes - current_codes
        if added:
            warnings.append(f"Positions added outside pipeline since {prior_dates[0]}: {added}")
        if removed:
            warnings.append(f"Positions removed outside pipeline since {prior_dates[0]}: {removed}")
    
    # Compare closed positions count
    prior_closed = len(prior.get("closed_positions", {}))
    current_closed = len(current_snapshot.get("closed_positions", {}))
    if current_closed != prior_closed:
        warnings.append(
            f"Closed positions changed outside pipeline: {prior_closed} → {current_closed}"
        )
    
    return warnings
```

Print warnings to stderr during Phase 1 if any drift is detected.

## Testing

After implementing, verify:

1. **Fresh run:** `python scripts/run_daily.py` creates `runs/YYYY-MM-DD/input/` with all files + `phase1.json` + `prompt.md`
2. **Apply:** `python scripts/run_daily.py --apply response.json` creates `runs/YYYY-MM-DD/output/` with all files + `response.json` saved
3. **List:** `python scripts/run_daily.py --list-runs` shows all runs with correct status
4. **Reset:** 
   - Run day 1, apply, verify output snapshot exists
   - Run day 2, apply
   - `--reset-to` day 1 → tracking state matches day 1's output snapshot
   - Re-run day 2 → produces same results (or different if you change the LLM response)
5. **Consistency check:** Manually edit a position file, run pipeline, verify warning printed
6. **Legacy compat:** `load_recent_watchlists` still finds old watchlists in `watchlist/` dir
7. **Existing tests pass:** Run `pytest` and fix any broken paths

## Notes for the implementer

- **Do NOT delete the old directories** (`data/`, `watchlist/`, `reports/`, `logs/`, `tracking/daily/`). They have historical data and the code has fallbacks.
- **All path changes are in the orchestrator** (`run_daily.py`) — individual modules (`data_collector.py`, `report_generator.py`, `position_manager.py`) get optional `output_dir` params but their defaults still work for standalone use.
- The `snapshot_positions` and `restore_snapshot` functions should be in `run_daily.py`, not `position_manager.py` — they're orchestration concerns, not position management.
- Keep the `tracking/daily/` directory and `save_daily_summary` default path working — it's used by the existing daily summary viewing flow. The orchestrator just overrides the output path.
- `prompt.md` should be saved as-is (the full prompt string including the ANALYST.md content + data JSON). This is the exact input the LLM received.
