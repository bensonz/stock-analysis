#!/usr/bin/env python3
"""
run_daily.py — Main orchestrator for the daily stock analysis pipeline.

Phase 1: DATA COLLECTION (pure Python)
Phase 2: ANALYSIS (LLM API call with tool-use loop)
Phase 3: EXECUTION (pure Python — apply LLM decisions)
Phase 4: VALIDATION + COMMIT

Usage:
    python scripts/run_daily.py --run                                  # Full pipeline: collect → LLM → apply → validate → commit
    python scripts/run_daily.py --run --llm-provider openai            # Full pipeline with GPT-5.4 only
    python scripts/run_daily.py --run --llm-provider hybrid            # Full pipeline with Claude→GPT handoff
    python scripts/run_daily.py --run --llm-provider anthropic         # Full pipeline with Claude only
    python scripts/run_daily.py --run --no-commit                      # Full pipeline without git commit
    python scripts/run_daily.py --run --legacy-llm                     # Full pipeline with old 4-pass LLM approach
    python scripts/run_daily.py                    # Phase 1+2 only (outputs prompt to stdout, legacy mode)
    python scripts/run_daily.py --phase1           # Data collection only
    python scripts/run_daily.py --apply FILE       # Apply LLM response from file (Phase 3+4)
    python scripts/run_daily.py --validate         # Run validation only
    python scripts/run_daily.py --validate DATE    # Validate specific date
    python scripts/run_daily.py --reset-to DATE    # Reset state to end of DATE (afternoon slot by default)
    python scripts/run_daily.py --list-runs        # Show all runs with status
    python scripts/run_daily.py --date DATE --slot afternoon --run
                                                   # Re-run a missed slot for a SETTLED past session
                                                   # (e.g. machine slept through it); refuses future dates

Run slots (noon vs afternoon):
    The pipeline runs twice per trading day and each run writes to its own slot
    subfolder so neither overwrites the other:
        runs/<date>/noon/       (hour < 13, intraday, UNSETTLED)
        runs/<date>/afternoon/  (hour >= 13, post-close, settled)
    The slot is auto-derived from the local clock at start. Override with
    --slot {noon,afternoon} on any command (e.g. manual reruns/backfills).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from data_collector import (
    fetch_strategy_pool,
    batch_enrich,
    fetch_ma_data,
    fetch_market_overview,
    fetch_position_prices,
    fetch_missed_opportunity_prices,
    load_recent_watchlists,
    save_crawl_data,
    save_intersect_data,
    save_market_data,
    save_price_data,
    save_strategy_pool_debug,
)
from position_manager import (
    load_active_positions,
    load_portfolio_config,
    compute_realized_pnl,
    close_position,
    open_position,
    update_position,
    regenerate_positions_json,
    save_daily_summary,
    TRACKING_DIR,
    CLOSED_DIR,
    POSITIONS_FILE,
    PORTFOLIO_CONFIG_FILE,
)
from report_generator import generate_candidates_md, generate_watchlist_json, generate_report_md
from run_rules import run_all_rules
from run_paths import (
    RUNS_DIR,
    get_run_dir,
    resolve_slot,
    find_run_dir,
    list_runs_sorted,
    run_started_at,
)
from validator import validate_data, validate_output
from contracts import (
    PipelineStatus,
    PipelineHardFail,
    RunManifest,
    validate_phase1_gate,
    validate_llm_output_gate,
    validate_phase3_gate,
    check_source_health,
)
from hypothesis_manager import (
    load_hypotheses,
    save_hypotheses,
    process_learnings as hypothesis_process_learnings,
    get_active_for_prompt as hypothesis_prompt,
)

# Directories (RUNS_DIR / get_run_dir now live in run_paths for slot-aware layout)
LEARNINGS_FILE = PROJECT_ROOT / "LEARNINGS.md"
HYPOTHESES_FILE = TRACKING_DIR / "hypotheses.json"

LLM_PROMPT_START = "=== LLM_PROMPT_START ==="
LLM_PROMPT_END = "=== LLM_PROMPT_END ==="
ENTRY_GATE_INDICES = ("上证指数", "深证成指", "创业板指")
INTERSECT_MIN_RPS = 85.0
WEAK_TAPE_SIZE_MULTIPLIER = 0.5
# Strong tape uses full sizing: "don't chase" is enforced per-stock via the
# dist_ma5/10/20 SKIP filters in ANALYST.md, not by shrinking every position
# market-wide. A strong tape should not reduce fresh size.
STRONG_TAPE_SIZE_MULTIPLIER = 1.0
# Unrealized PnL at or below this triggers a forced SELL, regardless of the LLM's
# decision (ANALYST.md Rule 5, "-5% → Automatic SELL. No exceptions.").
HARD_SELL_LOSS_PCT = -5.0


def _build_strategy_intersection(remote_strategy: dict, rps_data: dict) -> tuple[dict, dict]:
    """Build the working pool as remote CheeseFortune crawl intersected with RPS-filtered local names."""
    remote_stocks = remote_strategy.get("stocks", []) or []
    intersect_stocks = []
    seen_codes = set()
    remote_missing_rps = 0
    remote_below_rps_threshold = 0
    duplicate_remote_codes = 0

    for stock in remote_stocks:
        code = str(stock.get("code", "")).split(".")[0]
        if not code:
            continue
        if code in seen_codes:
            duplicate_remote_codes += 1
            continue
        seen_codes.add(code)

        metrics = rps_data.get(code)
        if not metrics:
            remote_missing_rps += 1
            continue

        if not all(
            metrics.get(key) is not None and float(metrics[key]) > INTERSECT_MIN_RPS
            for key in ("rps60", "rps120", "rps250")
        ):
            remote_below_rps_threshold += 1
            continue

        merged = dict(stock)
        merged["code"] = code
        merged["rps20"] = metrics.get("rps20")
        merged["rps60"] = metrics.get("rps60")
        merged["rps120"] = metrics.get("rps120")
        merged["rps250"] = metrics.get("rps250")
        merged["ma10"] = metrics.get("ma10_today")
        intersect_stocks.append(merged)

    intersect_stocks.sort(
        key=lambda item: (item.get("rps120", 0), item.get("rps250", 0), item.get("rps60", 0)),
        reverse=True,
    )

    debug = {
        "mode": "cheesefortune_intersection",
        "remote_strategy": {
            "source": remote_strategy.get("source"),
            "strategy_id": remote_strategy.get("strategy_id"),
            "date": remote_strategy.get("date"),
            "total_stocks": len(remote_stocks),
            "error": remote_strategy.get("error"),
        },
        "stage_counts": {
            "remote_strategy_total": len(remote_stocks),
            "rps_universe": len(rps_data),
            "intersection_total": len(intersect_stocks),
        },
        "drop_counts": {
            "remote_missing_rps": remote_missing_rps,
            "remote_below_rps_threshold": remote_below_rps_threshold,
            "duplicate_remote_codes": duplicate_remote_codes,
        },
        "criteria": {
            "rps60_gt": INTERSECT_MIN_RPS,
            "rps120_gt": INTERSECT_MIN_RPS,
            "rps250_gt": INTERSECT_MIN_RPS,
        },
        "fallback": {"used": False},
        "final_source": "cheesefortune_intersection",
        "final_total_stocks": len(intersect_stocks),
    }

    return {
        "source": "cheesefortune_intersection",
        "strategy_id": remote_strategy.get("strategy_id"),
        "date": remote_strategy.get("date"),
        "total_stocks": len(intersect_stocks),
        "stocks": intersect_stocks,
        "error": remote_strategy.get("error"),
        "debug": debug,
    }, debug


def snapshot_positions(snapshot_type: str, date: str) -> dict:
    """Create a full snapshot of all position state.

    Args:
        snapshot_type: "pre_run" or "post_run"
        date: Date string

    Returns:
        The snapshot dict.
    """
    # Read all active position files
    active = {}
    for f in sorted(TRACKING_DIR.glob("*.json")):
        if f.name in ("positions.json", "portfolio_config.json"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # non-position state lives here too (rotation_ledger.json is a
            # LIST — crashed this loop 2026-08-11); only dicts can be positions
            if isinstance(data, dict) and data.get("status") == "active":
                active[data["code"]] = data
        except (json.JSONDecodeError, KeyError):
            pass

    # Read closed positions — summary only (no history bloat)
    closed_summary = {}
    for f in sorted(CLOSED_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            closed_summary[data["code"]] = {
                "code": data["code"],
                "name": data.get("name"),
                "status": "closed",
                "entryDate": data.get("entryDate"),
                "exitDate": data.get("exitDate"),
                "entryPrice": data.get("entryPrice"),
                "exitPrice": data.get("exitPrice"),
                "returnPct": data.get("returnPct"),
                "holdingDays": data.get("holdingDays"),
                "sector": data.get("sector"),
                "lessonLearned": data.get("lessonLearned"),
            }
        except (json.JSONDecodeError, KeyError):
            pass

    # Read positions.json
    positions_json = {}
    if POSITIONS_FILE.exists():
        positions_json = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))

    return {
        "snapshot_time": datetime.now().astimezone().isoformat(),
        "snapshot_type": snapshot_type,
        "date": date,
        "portfolio_config": load_portfolio_config(),
        "positions_json": positions_json,
        "active_positions": active,
        "closed_positions": closed_summary,
    }


def restore_snapshot(snapshot: dict) -> None:
    """Restore tracking state from a snapshot.

    WARNING: This overwrites all tracking/*.json, tracking/closed/*.json,
    tracking/positions.json, and tracking/portfolio_config.json.
    Note: LEARNINGS.md is no longer included in snapshots (too large, lives in repo).
    """
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

    # LEARNINGS.md no longer stored in snapshots — lives in repo directly


def snapshot_aux_state(output_dir: Path) -> None:
    """Persist non-position mutable state needed for consistent reruns."""
    if HYPOTHESES_FILE.exists():
        shutil.copy2(HYPOTHESES_FILE, output_dir / "hypotheses_snapshot.json")
    if LEARNINGS_FILE.exists():
        shutil.copy2(LEARNINGS_FILE, output_dir / "LEARNINGS.md")


def restore_aux_state(run_dir: Path) -> list[str]:
    """Restore hypothesis / legacy learnings snapshots when available."""
    warnings = []
    output_dir = run_dir / "output"

    hyp_snapshot = output_dir / "hypotheses_snapshot.json"
    if hyp_snapshot.exists():
        shutil.copy2(hyp_snapshot, HYPOTHESES_FILE)
    else:
        warnings.append("No hypotheses snapshot found to restore")

    learnings_snapshot = output_dir / "LEARNINGS.md"
    if learnings_snapshot.exists():
        shutil.copy2(learnings_snapshot, LEARNINGS_FILE)
    else:
        warnings.append("No LEARNINGS snapshot found to restore")

    return warnings


def evaluate_new_entry_regime(market: dict) -> dict:
    """Classify tape quality for new entries and derive a sizing throttle."""
    breadth = (market or {}).get("breadth") or {}
    indices = (market or {}).get("indices") or {}
    distribution = breadth.get("distribution") or {}

    up = int(breadth.get("up") or 0)
    down = int(breadth.get("down") or 0)
    ratio = (up / down) if down else (float("inf") if up else 0.0)
    limit_downs = int(distribution.get("f10") or 0)
    limit_ups = int(distribution.get("r10") or 0)

    positive_indices = []
    negative_indices = []
    for name in ENTRY_GATE_INDICES:
        change = (indices.get(name) or {}).get("change_pct")
        if isinstance(change, (int, float)):
            if change > 0:
                positive_indices.append(name)
            elif change < 0:
                negative_indices.append(name)

    has_breadth = up > 0 or down > 0
    broad_index_support = len(positive_indices) >= 2
    panic_tape = has_breadth and (ratio < 0.35 or limit_downs >= 30)
    weak_tape = has_breadth and ratio < 1.0
    strong_tape = has_breadth and ratio >= 1.5 and broad_index_support

    allow_new_positions = has_breadth and not panic_tape
    regime = "balanced"
    sizing_multiplier = 1.0

    if not has_breadth:
        regime = "unknown"
        sizing_multiplier = 0.0
        reason = "Missing breadth data; defaulting to no new positions."
    elif panic_tape:
        regime = "panic"
        sizing_multiplier = 0.0
        reason = (
            f"Entry regime panic: breadth {ratio:.2f}:1, "
            f"{len(positive_indices)}/3 major indices green, {limit_ups} limit-ups / {limit_downs} limit-downs. "
            "Block new longs."
        )
    elif weak_tape:
        regime = "weak"
        sizing_multiplier = WEAK_TAPE_SIZE_MULTIPLIER
        reason = (
            f"Entry regime weak: breadth {ratio:.2f}:1, "
            f"{len(positive_indices)}/3 major indices green, {limit_ups} limit-ups / {limit_downs} limit-downs. "
            f"Allow entries only with {int(WEAK_TAPE_SIZE_MULTIPLIER * 100)}% sizing."
        )
    elif strong_tape:
        regime = "strong"
        sizing_multiplier = STRONG_TAPE_SIZE_MULTIPLIER
        reason = (
            f"Entry regime strong: breadth {ratio:.2f}:1, "
            f"{len(positive_indices)}/3 major indices green, {limit_ups} limit-ups / {limit_downs} limit-downs. "
            "Allow entries at full size; per-stock overextension is filtered individually (dist_ma)."
        )
    else:
        regime = "balanced"
        sizing_multiplier = 1.0
        reason = (
            f"Entry regime balanced: breadth {ratio:.2f}:1, "
            f"{len(positive_indices)}/3 major indices green, {limit_ups} limit-ups / {limit_downs} limit-downs. "
            "Allow normal sizing."
        )

    return {
        "allow_new_positions": allow_new_positions,
        "regime": regime,
        "breadth_ratio": round(ratio, 4) if has_breadth and ratio != float("inf") else None,
        "up": up,
        "down": down,
        "positive_indices": positive_indices,
        "negative_indices": negative_indices,
        "limit_ups": limit_ups,
        "limit_downs": limit_downs,
        "sizing_multiplier": sizing_multiplier,
        "hard_block": not allow_new_positions,
        "reason": reason,
    }


def check_snapshot_consistency(date: str, current_snapshot: dict) -> list[str]:
    """Check if current state matches the previous day's post-run snapshot."""
    warnings = []

    if not RUNS_DIR.exists():
        return []

    # Find the most recent prior run (any slot, earlier date) with a post-run
    # snapshot. list_runs_sorted orders by run_started_at, newest first, so the
    # first match on an earlier date is the latest settled state to compare to.
    prior_date = None
    prior_file = None
    for run_date, _slot, run_dir in list_runs_sorted():
        if run_date >= date:
            continue
        candidate = run_dir / "output" / "positions_snapshot.json"
        if candidate.exists():
            prior_date = run_date
            prior_file = candidate
            break

    if prior_file is None:
        return []  # No prior run to compare against

    prior = json.loads(prior_file.read_text(encoding="utf-8"))

    # Compare active position codes
    prior_codes = set(prior.get("active_positions", {}).keys())
    current_codes = set(current_snapshot.get("active_positions", {}).keys())

    if prior_codes != current_codes:
        added = current_codes - prior_codes
        removed = prior_codes - current_codes
        if added:
            warnings.append(f"Positions added outside pipeline since {prior_date}: {added}")
        if removed:
            warnings.append(f"Positions removed outside pipeline since {prior_date}: {removed}")

    # Compare closed positions count
    prior_closed = len(prior.get("closed_positions", {}))
    current_closed = len(current_snapshot.get("closed_positions", {}))
    if current_closed != prior_closed:
        warnings.append(
            f"Closed positions changed outside pipeline: {prior_closed} → {current_closed}"
        )

    return warnings


def reset_to_date(target_date: str, slot: str | None = None) -> None:
    """Reset mutable state to the end-of-day state of target_date.

    Restores tracking position files from the target date's post-run snapshot,
    deletes any run dirs after target_date, and restores auxiliary state
    snapshots like tracking/hypotheses.json and LEARNINGS.md when available.

    When multiple slots exist for target_date, the afternoon (settled) run is
    used by default; pass ``slot`` to force a specific one. Legacy layouts
    (runs/<date>/output with no slot) resolve as an implicit afternoon run.
    """
    run_dir = find_run_dir(target_date, slot)
    snapshot_file = run_dir / "output" / "positions_snapshot.json" if run_dir else None

    if snapshot_file is None or not snapshot_file.exists():
        # Try input snapshot if output doesn't exist (run never completed)
        if run_dir is not None:
            snapshot_file = run_dir / "input" / "positions_snapshot.json"
        if snapshot_file is None or not snapshot_file.exists():
            print(f"No snapshot found for {target_date}"
                  + (f" (slot={slot})" if slot else ""), file=sys.stderr)
            print(f"Available runs:", file=sys.stderr)
            for run_date, run_slot, d in list_runs_sorted():
                has_out = (d / "output" / "positions_snapshot.json").exists()
                has_in = (d / "input" / "positions_snapshot.json").exists()
                status = "✓ complete" if has_out else ("⚠ input only" if has_in else "✗ no snapshot")
                print(f"  {run_date}  {run_slot:9s}  {status}", file=sys.stderr)
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
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir()):
            if d.is_dir() and d.name > target_date:
                shutil.rmtree(d)
                deleted.append(d.name)
    if deleted:
        print(f"  Deleted runs: {', '.join(deleted)}", file=sys.stderr)

    # Restore
    restore_snapshot(snapshot)

    aux_warnings = restore_aux_state(run_dir)
    for warning in aux_warnings:
        print(f"  ⚠ {warning}", file=sys.stderr)

    print(f"\n✓ State restored to end of {target_date}", file=sys.stderr)


def list_runs() -> None:
    """List all run directories with slot, start time, and status."""
    runs = list_runs_sorted(reverse=False)
    if not runs:
        print("No runs yet.", file=sys.stderr)
        return

    for date, slot, d in runs:
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

        started = run_started_at(d)
        legacy = " (legacy)" if d.name == date else ""
        print(f"  {date}  {slot:9s}  {started:32s}  {status}{legacy}")


def preflight_pricedb_or_exit(manifest) -> None:
    """Refresh the local price DB and refuse to proceed on stale data.

    Runs ``pricedb.py update`` with a tighter budget than the in-phase fallback.
    After the update, queries the DB's latest date and compares against the most
    recent trading day. If still stale during trading hours on a trading day,
    print a clear error, record a failed health phase, and exit non-zero.
    """
    pricedb_path = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"
    if not pricedb_path.exists():
        print("  [preflight] pricedb missing — skipping freshness check", file=sys.stderr)
        return

    skip = os.getenv("PRICEDB_SKIP_UPDATE", "").strip().lower() in {"1", "true", "yes", "on"}
    update_err: str | None = None
    if skip:
        print("  [preflight] PRICEDB_SKIP_UPDATE set — using existing pricedb", file=sys.stderr)
    else:
        print("  [preflight] Refreshing local pricedb (akshare → sina fallback)...", file=sys.stderr)
        env = os.environ.copy()
        env.setdefault("PRICEDB_UPDATE_BUDGET", "300")
        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "pricedb.py"), "update"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                update_err = (result.stderr.strip() or result.stdout.strip()
                              or f"exit {result.returncode}")
                print(f"    ⚠ pricedb update failed: {update_err}", file=sys.stderr)
            else:
                print("    → pricedb update OK", file=sys.stderr)
        except Exception as e:
            update_err = str(e)
            print(f"    ⚠ pricedb update raised: {e}", file=sys.stderr)

    # Signal to phase1_collect that preflight already ran the update.
    os.environ["PRICEDB_SKIP_UPDATE"] = "1"

    try:
        import sqlite3 as _sql
        from datetime import datetime as _dt
        from pricedb import last_settled_trading_day, most_recent_trading_day

        with _sql.connect(str(pricedb_path)) as conn:
            row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
        latest = row[0] if row and row[0] else None
        if not latest:
            print("  ✗ pricedb has no daily_prices rows — refusing to proceed", file=sys.stderr)
            manifest.add_phase("preflight_pricedb", "failed",
                               details={"error": "empty", "update_err": update_err})
            manifest.finalize()
            sys.exit(2)

        now = _dt.now()
        today = now.date()
        latest_dt = _dt.strptime(latest, "%Y-%m-%d").date()
        # Session-aware expectation: mid-session today's bar is intentionally not
        # written (it would be an intraday snapshot), so the freshest legitimate
        # data is the last *closed* session, not today.
        latest_trading_day = last_settled_trading_day(now)

        if latest_dt >= latest_trading_day:
            print(f"  ✓ pricedb fresh (latest={latest}, target≥{latest_trading_day.isoformat()})",
                  file=sys.stderr)
            manifest.add_phase("preflight_pricedb", "ok",
                               details={"latest_date": latest, "target": latest_trading_day.isoformat()})
            return

        # Stale (latest is behind the last settled session). Only hard-refuse
        # during trading hours on a trading day. "Is today a trading day" is
        # computed independently of the freshness threshold, which is now the
        # last *closed* session.
        is_trading_today = (most_recent_trading_day(today) == today)
        after_market_open = (now.hour, now.minute) >= (9, 30)
        if is_trading_today and after_market_open:
            print(
                f"\n  ✗ Pricedb is stale — refusing to run analysis on stale data.\n"
                f"    latest={latest}, expected ≥ {latest_trading_day.isoformat()} (today is a trading day).\n"
                f"    Check eastmoney connectivity / proxy settings.\n"
                f"    Last update error: {update_err or 'n/a'}\n",
                file=sys.stderr,
            )
            manifest.add_phase("preflight_pricedb", "failed",
                               details={"latest_date": latest,
                                        "expected": latest_trading_day.isoformat(),
                                        "update_err": update_err})
            manifest.finalize()
            sys.exit(2)

        # Off-hours or non-trading day: warn and continue.
        print(
            f"  ⚠ pricedb stale (latest={latest}, expected ≥ {latest_trading_day.isoformat()}) "
            f"but outside trading hours — continuing with degraded data",
            file=sys.stderr,
        )
        manifest.add_phase("preflight_pricedb", "degraded",
                           details={"latest_date": latest,
                                    "expected": latest_trading_day.isoformat(),
                                    "update_err": update_err})
    except SystemExit:
        raise
    except Exception as e:
        print(f"  ⚠ preflight_pricedb check raised: {e}", file=sys.stderr)


def phase1_collect(date: str, slot: str) -> dict:
    """Phase 1: Collect all data. Pure Python, no LLM.

    Runs independent tasks in parallel:
      - Strategy pool fetch (fast, ~5s) runs first since enrichment depends on it
      - Then enrichment, market, positions, and watchlists run concurrently
    """
    log = {"phase": "collect", "start": time.time(), "errors": []}
    data = {"date": date, "slot": slot}

    print("Phase 1: Collecting data...", file=sys.stderr)

    # Create run directory and take pre-run snapshot
    run_dir = get_run_dir(date, slot)
    input_dir = run_dir / "input"

    pre_snap = snapshot_positions("pre_run", date)
    (input_dir / "positions_snapshot.json").write_text(
        json.dumps(pre_snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Check consistency with previous run
    drift_warnings = check_snapshot_consistency(date, pre_snap)
    if drift_warnings:
        print("  ⚠ Snapshot consistency warnings:", file=sys.stderr)
        for w in drift_warnings:
            print(f"    {w}", file=sys.stderr)

    pricedb_path = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"
    skip_pricedb_update = os.getenv("PRICEDB_SKIP_UPDATE", "").strip().lower() in {"1", "true", "yes", "on"}
    if pricedb_path.exists():
        if skip_pricedb_update:
            print("  [prep] Skipping local price DB update via PRICEDB_SKIP_UPDATE", file=sys.stderr)
        else:
            print("  [prep] Updating local price DB...", file=sys.stderr)
            try:
                pricedb_cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "pricedb.py"), "update"]
                result = subprocess.run(
                    pricedb_cmd,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    err = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
                    raise RuntimeError(err)
                print("    → local pricedb updated", file=sys.stderr)
            except Exception as e:
                log["errors"].append(f"pricedb_update: {e}")
                print(f"    ⚠ pricedb update failed: {e}", file=sys.stderr)
    else:
        print("  [prep] Local price DB not found; using remote strategy pool", file=sys.stderr)

    # Step 1: Strategy pool (must complete before enrichment can start)
    print("  [1/5] Fetching strategy pool...", file=sys.stderr)
    strategy_debug = {
        "mode": "cheesefortune_intersection",
        "remote_strategy": {},
        "stage_counts": {},
        "drop_counts": {},
        "fallback": {"used": False},
        "final_source": "cheesefortune_intersection",
        "final_total_stocks": 0,
    }
    try:
        data["strategy_crawl"] = fetch_strategy_pool()
        save_crawl_data(date, data["strategy_crawl"], output_dir=input_dir)
        strategy_source = data["strategy_crawl"].get("source", "unknown")
        print(
            f"    → {data['strategy_crawl'].get('total_stocks', 0)} stocks ({strategy_source})",
            file=sys.stderr,
        )
    except Exception as e:
        data["strategy_crawl"] = {"error": str(e), "stocks": []}
        log["errors"].append(f"strategy_pool: {e}")

    # Load positions and watchlists synchronously (instant, local files)
    positions = load_active_positions()
    data["positions"] = positions
    data["positions_count"] = len(positions)
    # What we RECENTLY exited — so a re-entry is an informed decision, not a
    # blind rediscovery (2026-08-13: 600160 was re-opened 2 days after its own
    # -4.61% stop with zero exit context in the prompt).
    try:
        from position_manager import load_recent_exits
        data["recent_exits"] = load_recent_exits(days=14, today=date)
    except Exception as e:
        data["recent_exits"] = []
        log["errors"].append(f"recent_exits: {e}")
    data["recent_watchlists"] = load_recent_watchlists(days=5)

    # VCP scan: add VCP data to strategy pool stocks + flag quality setups
    # Backtest-proven filters (n=280, Jan-Feb 2026):
    #   - Contraction ratio < 0.4: 55% WR, +7.7% avg 10d (best signal)
    #   - MA distance < 3%: necessary gate (0% WR when > 3%)
    #   - MA20 proximity better than MA10 for winners
    #   - Optimal hold: ~10 days, 20d returns negative
    data["strategy_pool"] = {
        "source": "cheesefortune_intersection",
        "strategy_id": data.get("strategy_crawl", {}).get("strategy_id"),
        "date": data.get("strategy_crawl", {}).get("date"),
        "total_stocks": 0,
        "stocks": [],
        "error": data.get("strategy_crawl", {}).get("error"),
        "debug": strategy_debug,
    }
    rps_output = {}
    vcp_output = []
    if pricedb_path.exists():
        try:
            from vcp_scanner import scan_vcp
            from rps_calculator import compute_ma_rps
            rps_data = compute_ma_rps(str(pricedb_path))

            data["strategy_pool"], strategy_debug = _build_strategy_intersection(
                data.get("strategy_crawl", {}),
                rps_data,
            )
            save_intersect_data(date, data["strategy_pool"], output_dir=input_dir)
            print(
                f"    → Intersect: {data['strategy_pool'].get('total_stocks', 0)} stocks "
                f"(crawl ∩ local RPS)",
                file=sys.stderr,
            )

            pool_stocks = data["strategy_pool"].get("stocks", [])

            vcp_results = scan_vcp(
                str(pricedb_path), rps_data=rps_data,
                min_rps120=0, base_days=120, top_n=500
            )
            vcp_by_code = {r["code"]: r for r in vcp_results}
            enriched_count = 0
            quality_count = 0
            for stock in pool_stocks:
                code = stock.get("code", "")
                vcp = vcp_by_code.get(code)
                if vcp:
                    stock["vcp_score"] = vcp["score"]
                    stock["vcp_contraction_ratio"] = vcp["contraction_ratio"]
                    stock["vcp_last_depth"] = vcp["last_depth"]
                    stock["vcp_dist_peak_pct"] = vcp["dist_from_peak_pct"]
                    stock["vcp_nearest_ma"] = vcp.get("nearest_ma", "")
                    stock["vcp_nearest_ma_dist"] = vcp.get("nearest_ma_dist", None)
                    stock["vcp_vol_declining"] = vcp.get("vol_declining", False)
                    stock["vcp_num_contractions"] = vcp["num_contractions"]
                    stock["vcp_depths"] = "→".join(vcp["depth_strs"])

                    # Quality flag: passes backtest-proven filters
                    ma_dist = vcp.get("nearest_ma_dist", 99)
                    cr = vcp.get("contraction_ratio", 1)
                    ma_type = vcp.get("nearest_ma", "")
                    is_quality = (
                        cr < 0.4              # tight contraction (the alpha)
                        and ma_dist < 3       # near MA support (the gate)
                    )
                    # Bonus: MA20 proximity is stronger than MA10
                    is_premium = is_quality and ma_type == "MA20"

                    stock["vcp_quality"] = "PREMIUM" if is_premium else "QUALITY" if is_quality else "SETUP"
                    if is_quality:
                        quality_count += 1
                    enriched_count += 1
                else:
                    stock["vcp_quality"] = None  # no VCP pattern detected
            print(
                f"    → VCP: {enriched_count} setups found, {quality_count} quality "
                f"(ratio<0.4 + MA<3%)",
                file=sys.stderr,
            )

            # Save standalone RPS + VCP data to input dir for inspection
            for code, vals in rps_data.items():
                rps_output[code] = {
                    "rps20": vals.get("rps20"),
                    "rps60": vals.get("rps60"),
                    "rps120": vals.get("rps120"),
                    "rps250": vals.get("rps250"),
                    "ma10": vals.get("ma10_today"),
                }
            print(f"    → RPS: {len(rps_output)} stocks saved to input/rps.json", file=sys.stderr)

            for r in vcp_results:
                vcp_entry = {
                    "code": r["code"],
                    "score": r["score"],
                    "contraction_ratio": r["contraction_ratio"],
                    "last_depth": r["last_depth"],
                    "dist_from_peak_pct": r["dist_from_peak_pct"],
                    "nearest_ma": r.get("nearest_ma", ""),
                    "nearest_ma_dist": r.get("nearest_ma_dist"),
                    "vol_declining": r.get("vol_declining", False),
                    "num_contractions": r["num_contractions"],
                    "depth_strs": r.get("depth_strs", []),
                }
                cr = vcp_entry["contraction_ratio"]
                md = vcp_entry["nearest_ma_dist"] or 99
                mt = vcp_entry["nearest_ma"]
                is_q = cr < 0.4 and md < 3
                vcp_entry["quality"] = "PREMIUM" if (is_q and mt == "MA20") else "QUALITY" if is_q else "SETUP"
                vcp_output.append(vcp_entry)
            print(f"    → VCP: {len(vcp_output)} setups saved to input/vcp.json", file=sys.stderr)

        except Exception as e:
            print(f"    ⚠ VCP scan failed: {e}", file=sys.stderr)
            data["strategy_pool"]["debug"] = strategy_debug
    else:
        save_intersect_data(date, data["strategy_pool"], output_dir=input_dir)

    if pricedb_path.exists() and not (input_dir / "intersect.json").exists():
        save_intersect_data(date, data["strategy_pool"], output_dir=input_dir)

    (input_dir / "rps.json").write_text(
        json.dumps(rps_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (input_dir / "vcp.json").write_text(
        json.dumps(vcp_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    save_strategy_pool_debug(date, strategy_debug, output_dir=input_dir)

    pool_stocks = data["strategy_pool"].get("stocks", [])

    # Prepare enrichment candidates
    candidates = [
        s for s in pool_stocks
        if s.get("rps120") and 75 <= float(s["rps120"]) <= 95
    ]
    print(f"    → {len(candidates)} in RPS 75-95% zone", file=sys.stderr)

    # Steps 2-5: Run in parallel (different APIs, no shared rate limits)
    def _enrich():
        print("  [2/5] Enriching candidates...", file=sys.stderr)
        result = batch_enrich(candidates)
        print(f"    → {len(result)} enriched", file=sys.stderr)
        return "enriched", result

    def _market():
        print("  [3/5] Fetching market overview...", file=sys.stderr)
        result = fetch_market_overview()
        save_market_data(date, result, output_dir=input_dir)
        return "market", result

    def _prices():
        print("  [4/5] Fetching position prices...", file=sys.stderr)
        result = fetch_position_prices(positions)
        save_price_data(date, result, output_dir=input_dir)
        print(f"    → {len(positions)} active positions", file=sys.stderr)
        return "position_prices", result

    def _missed():
        print("  [5/5] Fetching missed opportunity prices...", file=sys.stderr)
        result = fetch_missed_opportunity_prices(data["recent_watchlists"])
        return "missed_opportunity_prices", result

    def _iv_sentiment():
        print("  [6/6] Fetching IV sentiment...", file=sys.stderr)
        from fetch_iv_sentiment import fetch_all
        result = fetch_all()
        overall = result.get("overall_sentiment", {})
        sig = overall.get("signal", "?")
        rank = overall.get("avg_iv_rank", 0)
        based_on = overall.get("based_on", [])
        print(
            f"    → {sig} (core avg IV rank {rank*100:.1f}% across {len(based_on)} proxies)",
            file=sys.stderr,
        )
        return "iv_sentiment", result

    def _ma_data():
        print("  [7/7] Fetching MA data...", file=sys.stderr)
        # Fetch MA for ALL pool stocks, not just 75-95% candidates.
        # Stocks with RPS>95 are skipped by Rule 2 but the LLM still needs
        # MA distances to explain *why* in skip_list.
        result = fetch_ma_data(pool_stocks)
        print(f"    → {len(result)} stocks with MA data (pool={len(pool_stocks)})", file=sys.stderr)
        return "ma_data", result

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_enrich): "enrich",
            executor.submit(_market): "market",
            executor.submit(_prices): "position_prices",
            executor.submit(_missed): "watchlists",
            executor.submit(_iv_sentiment): "iv_sentiment",
            executor.submit(_ma_data): "ma_data",
        }
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                key, result = future.result()
                data[key] = result
            except Exception as e:
                log["errors"].append(f"{task_name}: {e}")
                print(f"    ✗ {task_name} failed: {e}", file=sys.stderr)
                # Set defaults for failed tasks
                if task_name == "enrich":
                    data["enriched"] = []
                elif task_name == "market":
                    data["market"] = {"error": str(e)}
                elif task_name == "position_prices":
                    data["position_prices"] = {}
                elif task_name == "watchlists":
                    data["missed_opportunity_prices"] = []
                elif task_name == "iv_sentiment":
                    data["iv_sentiment"] = {"error": str(e)}
                elif task_name == "ma_data":
                    data["ma_data"] = {}

    # Merge MA data into enrichment results AND strategy pool stocks
    ma_data = data.get("ma_data", {})
    if ma_data:
        # Merge into enriched candidates (75-95% RPS)
        for stock in data.get("enriched", []):
            code = str(stock.get("code", "")).split(".")[0]
            if code in ma_data:
                ma = ma_data[code]
                stock["current_price"] = ma.get("price")
                if stock.get("price") is None and ma.get("price") is not None:
                    stock["price"] = ma.get("price")
                stock["ma5"] = ma.get("ma5")
                stock["ma10"] = ma.get("ma10")
                stock["ma20"] = ma.get("ma20")
                stock["dist_ma5_pct"] = ma.get("dist_ma5_pct")
                stock["dist_ma10_pct"] = ma.get("dist_ma10_pct")
                stock["dist_ma20_pct"] = ma.get("dist_ma20_pct")
        # Also merge into strategy pool stocks (covers >95% RPS stocks
        # that aren't enriched — LLM needs MA distances for skip_list)
        for stock in data.get("strategy_pool", {}).get("stocks", []):
            code = str(stock.get("code", "")).split(".")[0]
            if code in ma_data:
                ma = ma_data[code]
                stock["ma5"] = ma.get("ma5")
                stock["ma10"] = ma.get("ma10")
                stock["ma20"] = ma.get("ma20")
                stock["dist_ma5_pct"] = ma.get("dist_ma5_pct")
                stock["dist_ma10_pct"] = ma.get("dist_ma10_pct")
                stock["dist_ma20_pct"] = ma.get("dist_ma20_pct")

    # Attach stock-specific IV proxies to candidates/positions
    iv_data = data.get("iv_sentiment") or {}
    if iv_data and "error" not in iv_data:
        from fetch_iv_sentiment import stock_iv_proxy

        market_cap_by_code = {
            str(s.get("code", "")).split(".")[0]: s.get("market_cap")
            for s in data.get("strategy_pool", {}).get("stocks", [])
        }

        for stock in data.get("enriched", []):
            code = str(stock.get("code", "")).split(".")[0]
            stock["iv_proxy"] = stock_iv_proxy(code, iv_data, market_cap=market_cap_by_code.get(code))

        for position in data.get("positions", []):
            code = str(position.get("code", "")).split(".")[0]
            position["iv_proxy"] = stock_iv_proxy(code, iv_data, market_cap=market_cap_by_code.get(code))

    # Attach per-stock margin financing (融资融券) flow — a corroborating risk flag
    # (are leveraged holders adding or fleeing). Free Eastmoney direct; degrades to
    # no `margin` key on failure. Disable with MARGIN_SIGNAL=0.
    if os.getenv("MARGIN_SIGNAL", "1") == "1":
        from margin_flow import fetch_margin_flow  # ThreadPoolExecutor imported at module level

        margin_rows = data.get("enriched", []) + data.get("positions", [])
        margin_codes = sorted({
            str(s.get("code", "")).split(".")[0]
            for s in margin_rows if str(s.get("code", "")).split(".")[0]
        })
        if margin_codes:
            with ThreadPoolExecutor(max_workers=8) as executor:
                margin_by_code = dict(zip(margin_codes, executor.map(fetch_margin_flow, margin_codes)))
            for stock in margin_rows:
                code = str(stock.get("code", "")).split(".")[0]
                if margin_by_code.get(code):
                    stock["margin"] = margin_by_code[code]
            n_ok = sum(1 for v in margin_by_code.values() if v)
            print(f"    [margin] {n_ok}/{len(margin_codes)} fetched", file=sys.stderr)

    # Save IV sentiment to input dir
    if data.get("iv_sentiment") and "error" not in data["iv_sentiment"]:
        (input_dir / "iv_sentiment.json").write_text(
            json.dumps(data["iv_sentiment"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Regime detector (READ-ONLY: report display only — deliberately NOT
    # in the LLM prompt; graduation requires out-of-sample evidence).
    try:
        from regime_detector import detect as _detect_regime
        data["regime"] = _detect_regime()
        (input_dir / "regime.json").write_text(
            json.dumps(data["regime"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"    [regime] {data['regime'].get('label', '?')} "
              f"(ic20={data['regime'].get('rolling_ic20')}, "
              f"stop10={data['regime'].get('pool_stop_rate10')})",
              file=sys.stderr)
    except Exception as e:  # noqa: BLE001 — read-only, never fail the run
        print(f"    [regime] unavailable: {e}", file=sys.stderr)

    # Gamma exposure (GEX) from the options-lab backend. Tier-2 advisory
    # context (read-only, no mechanical rule); degrades to absent.
    try:
        from fetch_gex import fetch_all as _fetch_gex
        gex = _fetch_gex()
        if gex.get("etf_gex_data"):
            data["gex"] = gex
            (input_dir / "gex.json").write_text(
                json.dumps(gex, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"    [gex] {gex['overall'].get('signal', '?')} "
                  f"(低于翻转点 {gex['overall'].get('below_flip', '?')})",
                  file=sys.stderr)
        else:
            print(f"    [gex] unavailable: {gex.get('error', 'no data')}",
                  file=sys.stderr)
    except Exception as e:  # noqa: BLE001 — never fail the run over GEX
        print(f"    [gex] unavailable: {e}", file=sys.stderr)

    # Foreseeable-event risk window (curated calendar + formulaic OpEx +
    # measured FOMC base rate). Advisory context for the LLM; degrades to
    # absent on any failure.
    try:
        from event_calendar import phase1_payload as _events_payload
        data["events"] = _events_payload()
        (input_dir / "events.json").write_text(
            json.dumps(data["events"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rw = data["events"].get("risk_window", {})
        print(f"    [events] risk window: {rw.get('level', '?')} "
              f"({len(data['events'].get('dated', []))} dated, "
              f"{len(data['events'].get('ongoing', []))} ongoing)",
              file=sys.stderr)
    except Exception as e:  # noqa: BLE001 — never fail the run over the calendar
        print(f"    [events] unavailable: {e}", file=sys.stderr)

    # Data-quality health block (staleness / partial days / factor lag /
    # cross-source spot audit). Loudness layer for the 2026-07-30 outage
    # class: rides into the prompt, the report banner, and the phase-1 gate.
    try:
        import pricedb as _pricedb
        _conn = _pricedb.get_db()
        try:
            data["db_health"] = _pricedb.db_health(_conn, spot_check=True)
        finally:
            _conn.close()
        (input_dir / "db_health.json").write_text(
            json.dumps(data["db_health"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _h = data["db_health"]
        print(f"    [db_health] ok={_h.get('ok')} "
              f"lag={_h.get('lag_sessions')} "
              f"warnings={len(_h.get('warnings', []))}", file=sys.stderr)
        for _w in _h.get("warnings", []):
            print(f"      ⚠ {_w}", file=sys.stderr)
    except Exception as e:  # noqa: BLE001 — health check must not kill the run
        print(f"    [db_health] unavailable: {e}", file=sys.stderr)

    # Hypothesis-based learnings (structured system)
    hyp_data = load_hypotheses()
    data["hypothesis_prompt"] = hypothesis_prompt(hyp_data)
    data["_hypothesis_data"] = hyp_data  # Carry forward for Phase 3

    # Legacy LEARNINGS.md (read-only, for backward compat during transition)
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    if learnings_file.exists():
        data["learnings"] = learnings_file.read_text(encoding="utf-8")
    else:
        data["learnings"] = ""

    # Refresh positions.json with live prices/signals before running rules
    try:
        regenerate_positions_json(price_data=data.get("position_prices", {}))
    except Exception as e:
        log["errors"].append(f"positions_json refresh: {e}")

    # Run rules on current portfolio state
    try:
        rule_results = run_all_rules()
        data["rule_violations"] = rule_results
        if rule_results.get("total_violations", 0) > 0:
            print(f"    Rules: {rule_results['total_violations']} violations found", file=sys.stderr)
    except Exception as e:
        data["rule_violations"] = {"error": str(e)}

    # Validate
    data["collection_errors"] = validate_data(data)
    data["entry_regime"] = evaluate_new_entry_regime(data.get("market", {}))

    log["end"] = time.time()
    log["duration_sec"] = round(log["end"] - log["start"], 1)
    data["_log_phase1"] = log

    print(f"\nPhase 1 complete in {log['duration_sec']}s", file=sys.stderr)
    if log["errors"]:
        print(f"  Errors: {log['errors']}", file=sys.stderr)
    if data["collection_errors"]:
        print(f"  Warnings: {data['collection_errors']}", file=sys.stderr)

    # Generate candidates.md — always available, even when regime blocks buys
    try:
        output_dir = run_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        cand_path = generate_candidates_md(date, data, output_dir=output_dir)
        print(f"  → Candidates list: {cand_path}", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠ candidates.md generation failed: {e}", file=sys.stderr)

    return data


_HTML_TAG_RE = re.compile(r"<[^>]+>")
# Event entries that merely restate relative price strength (already sent as
# rps120/rps60 structured numbers) — drop them as prompt-only noise.
_RPS_RESTATE_TAGS = {"股价走强", "股价走弱"}


def _clean_events(events: list | None) -> list:
    """Trim per-stock event feed for the prompt.

    Strips HTML markup from content and drops RPS-restatement entries (which
    duplicate rps120/rps60). Keeps genuine corporate events (中报/公告/解禁/
    定增/管理层变更 …). Returns a new list; never mutates the input.
    """
    cleaned = []
    for e in events or []:
        if not isinstance(e, dict):
            continue
        tags = e.get("tags") or []
        if any(t in _RPS_RESTATE_TAGS for t in tags):
            continue
        content = _HTML_TAG_RE.sub("", e.get("content") or "").strip()
        if not content:
            continue
        entry = {"content": content, "tags": tags}
        if e.get("date"):
            entry["date"] = e["date"]
        cleaned.append(entry)
    return cleaned


def _slim_iv_proxy(proxy: dict | None) -> dict | None:
    """Reduce iv_proxy to the fields ANALYST.md actually uses for sizing.

    Keeps primary_name (transparency), iv_rank (the throttle) and sizing
    (the bucket). Drops guidance prose, alternates, interpretation, basis,
    current_iv and iv_percentile — ~470 chars/stock down to ~55.
    """
    if not isinstance(proxy, dict):
        return proxy
    return {
        "primary_name": proxy.get("primary_name"),
        "iv_rank": proxy.get("iv_rank"),
        "sizing": proxy.get("sizing"),
    }


def _slim_candidate(cand: dict) -> dict:
    """Copy an enriched candidate with events cleaned and iv_proxy slimmed."""
    if not isinstance(cand, dict):
        return cand
    slim = dict(cand)
    if "events" in slim:
        slim["events"] = _clean_events(slim.get("events"))
    if "iv_proxy" in slim:
        slim["iv_proxy"] = _slim_iv_proxy(slim.get("iv_proxy"))
    return slim


def phase2_build_prompt(data: dict) -> str:
    """Phase 2: Build LLM prompt from collected data.

    Returns the full prompt string. This is printed to stdout for
    external LLM processing.
    """
    # Load the analyst prompt template
    analyst_prompt = (PROJECT_ROOT / "agents" / "ANALYST.md").read_text(encoding="utf-8")

    # Build portfolio snapshot (with live prices if available)
    positions_json = regenerate_positions_json(price_data=data.get("position_prices", {}))
    portfolio = positions_json.get("portfolio", {})

    # Build the data payload (strip heavy fields)
    payload = {
        "date": data["date"],
        "portfolio": portfolio,
        "market": data.get("market", {}),
        "strategy_pool": {
            "source": data.get("strategy_pool", {}).get("source"),
            "total_stocks": data.get("strategy_pool", {}).get("total_stocks"),
            "stocks": data.get("strategy_pool", {}).get("stocks", []),
        },
        "enriched_candidates": [_slim_candidate(c) for c in data.get("enriched", [])],
        "active_positions": [
            {
                "code": p["code"],
                "name": p["name"],
                "entryDate": p["entryDate"],
                "entryPrice": p["entryPrice"],
                "targetPrice": p["targetPrice"],
                "stopLoss": p["stopLoss"],
                "currentStop": p.get("currentStop"),
                "thesis": p.get("thesis", ""),
                "sector": p.get("sector", ""),
                "rps120": p.get("rps120"),
                "catalysts": p.get("catalysts", []),
                "shares": p.get("shares"),
                "allocation_pct": p.get("allocation_pct"),
                "iv_proxy": _slim_iv_proxy(p.get("iv_proxy")),
                "margin": p.get("margin"),
                "history": p.get("history", [])[-3:],  # Last 3 history entries
            }
            for p in data.get("positions", [])
        ],
        "position_prices": data.get("position_prices", {}),
        "missed_opportunity_prices": data.get("missed_opportunity_prices", []),
        "iv_sentiment": data.get("iv_sentiment", {}),
        "entry_regime": data.get("entry_regime", evaluate_new_entry_regime(data.get("market", {}))),
        "rule_violations": data.get("rule_violations", {}),
        "collection_errors": data.get("collection_errors", []),
        # Names WE just sold. Shipped 2026-08-13 into llm_client.build_summary,
        # which only feeds the hybrid GPT pass-2 — so the primary decision
        # prompt (this one) never carried it. Caught 2026-08-14.
        "recent_exits": data.get("recent_exits", []),
    }

    # Hypothesis-based learnings (compact, structured)
    hyp_prompt = data.get("hypothesis_prompt", "")
    if hyp_prompt:
        payload["active_learnings"] = hyp_prompt
    
    # Legacy learnings excerpt (transitional — will be removed once hypothesis system is proven)
    learnings = data.get("learnings", "")
    learnings_lines = learnings.strip().split("\n")
    if len(learnings_lines) > 100:
        learnings = "\n".join(learnings_lines[:100]) + "\n\n[... truncated, see hypothesis system for active rules ...]"
    payload["learnings_excerpt"] = learnings

    # Re-entry guard: JSON alone gets skimmed, so the instruction is spelled
    # out in prose too. Empty string when we sold nothing recently.
    exits = data.get("recent_exits") or []
    reentry_note = ""
    if exits:
        rows = "\n".join(
            f"- {e.get('exitDate')}"
            f"{ {'noon': '午盘', 'afternoon': '收盘'}.get(e.get('exitSlot') or '', '') } "
            f"卖出 {e.get('code')} {e.get('name')} @{e.get('exitPrice')} "
            f"({e.get('returnPct')}%, 持有{e.get('holdingDays')}天, 入场{e.get('entryPrice')}) "
            f"— {str(e.get('exitReason', ''))[:120]}"
            for e in exits[:8]
        )
        reentry_note = (
            "\n## 近期已平仓 (last 14 days — 我们自己刚卖出的标的)\n\n"
            f"{rows}\n\n"
            "若今日 new_positions 中出现上列代码, 这是**重入**: 必须在 reason 里写明"
            "「上次为何离场、这次有何不同」(价位/形态/催化变了什么); 说不出差别就不要买。"
            "实测记录: 重入 n=9 均值 -3.71% 胜率 11%, 全账本对照 -0.78%/笔 —— "
            "不是禁令, 但举证责任在重入这一边。\n"
        )

    prompt = f"""{analyst_prompt}

## 今日数据 (由 run_daily.py 自动收集)

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```
{reentry_note}
请根据以上数据进行分析，按照 Required Output JSON 格式返回你的决策。

重要提醒：请再次仔细阅读以上所有数据（特别是 enriched_candidates 中的详细指标、position_prices 中的实时价格、以及 iv_sentiment），严格按照 ANALYST.md 的5条规则和 Output Format 要求，返回完整的 JSON 决策。skip_list 中只能引用输入数据中实际存在的价格和指标，不要编造任何数据。

**new_learnings 格式更新**: 尽量使用结构化格式返回 new_learnings：
```json
"new_learnings": [
  {{
    "text": "具体、可操作的洞察",
    "type": "heuristic|signal|rule|observation",
    "tags": ["sector", "entry-filter", "exit-rule", "timing", "position-sizing"],
    "evidence_type": "supporting|contradicting",
    "related_hypothesis": "h001 (如果是对已有假设的新证据)",
    "mechanism": "为什么这个规律成立的解释"
  }}
]
```
也接受纯字符串格式(向后兼容)。如果 active_learnings 中有相关假设，请引用其 ID。
"""

    # Save prompt to run dir
    run_dir = get_run_dir(data["date"], data.get("slot") or resolve_slot())
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    return prompt


def enforce_hard_sells(decisions: dict, data: dict, log: dict) -> None:
    """Force-close positions that breach non-negotiable exit rules, in-place.

    Selling is otherwise 100% LLM discretion. These two rules from ANALYST.md
    Rule 5 are mechanical and enforced in code so a stop actually means something:
      1. price at or below the position's stop  -> reason "stop_hit"
      2. unrealized PnL <= HARD_SELL_LOSS_PCT    -> reason "hard_stop_loss"

    A position the LLM already marked SELL is left as-is. HOLD/RAISE_STOP on a
    breaching position is overridden to SELL; a breaching position the LLM never
    mentioned gets a SELL injected. Positions without a reliable live price are
    never force-sold (we don't sell blind) — they are logged and skipped.
    """
    prices = data.get("position_prices", {})
    decisions_by_code = {
        str(d.get("code", "")).split(".")[0]: d
        for d in decisions.get("position_decisions", [])
    }

    for pos in data.get("positions", []):
        code = str(pos.get("code", "")).split(".")[0]
        entry = float(pos.get("entryPrice") or 0)
        stop = float(pos.get("currentStop") or pos.get("stopLoss") or 0)
        price = float((prices.get(code) or {}).get("price") or 0)

        if price <= 0 or entry <= 0:
            log["actions"].append(
                f"HARD-SELL SKIP {code}: no reliable price, cannot evaluate stop"
            )
            continue

        pnl_pct = (price - entry) / entry * 100
        if stop > 0 and price <= stop:
            reason = "stop_hit"
        elif pnl_pct <= HARD_SELL_LOSS_PCT:
            reason = "hard_stop_loss"
        else:
            continue

        existing = decisions_by_code.get(code)
        if existing and existing.get("action") == "SELL":
            continue  # LLM already selling this name; nothing to force

        prior = existing.get("action") if existing else "LLM-silent"
        if existing:
            existing["action"] = "SELL"
            existing["reason"] = f"forced:{reason}"
            existing["exit_price"] = price
        else:
            decisions.setdefault("position_decisions", []).append({
                "code": code,
                "name": pos.get("name", ""),
                "action": "SELL",
                "reason": f"forced:{reason}",
                "exit_price": price,
                "pnl_pct": round(pnl_pct, 2),
            })
        log["actions"].append(
            f"HARD SELL {code}: {reason} price={price:.2f} stop={stop:.2f} "
            f"pnl={pnl_pct:.2f}% (was {prior})"
        )


def phase3_apply(date: str, decisions: dict, data: dict) -> dict:
    """Phase 3: Apply LLM decisions. Pure Python.

    Args:
        date: Date string
        decisions: Parsed LLM response JSON
        data: Original collected data from Phase 1

    Returns:
        Summary of actions taken.
    """
    log = {"phase": "apply", "start": time.time(), "actions": []}
    slot = data.get("slot") or resolve_slot()
    run_dir = get_run_dir(date, slot)
    output_dir = run_dir / "output"

    # 0. Enforce non-negotiable exits before applying LLM decisions. Stops and
    #    the -5% hard loss are mechanical, not subject to LLM discretion.
    enforce_hard_sells(decisions, data, log)

    # 1. Apply position decisions
    daily_actions = []
    for d in decisions.get("position_decisions", []):
        code = str(d.get("code", "")).split(".")[0]
        action = d.get("action", "HOLD")
        try:
            if action == "SELL":
                price_data = data.get("position_prices", {}).get(code, {})
                exit_price = price_data.get("price", d.get("exit_price", 0))
                close_position(
                    code=code,
                    reason=d.get("reason", "LLM decision"),
                    exit_price=exit_price,
                    lesson=d.get("lesson", ""),
                    date=date,
                    slot=slot,
                )
                log["actions"].append(f"SELL {code}")
            elif action == "RAISE_STOP":
                new_stop = d.get("new_stop")
                if new_stop:
                    update_position(code, {"new_stop": new_stop})
                    log["actions"].append(f"RAISE_STOP {code} → {new_stop}")
            # Always update history for active positions
            if action in ("HOLD", "RAISE_STOP"):
                price_data = data.get("position_prices", {}).get(code, {})
                price = price_data.get("price", 0)
                entry_price = 0
                for p in data.get("positions", []):
                    if p["code"] == code:
                        entry_price = p["entryPrice"]
                        break
                pnl_pct = round((price - entry_price) / entry_price * 100, 2) if entry_price else 0
                update_position(code, {
                    "history_entry": {
                        "date": date,
                        "slot": slot,
                        "price": price,
                        "change_pct": pnl_pct,
                        "action": action,
                        "note": d.get("reason", ""),
                    },
                })

            daily_actions.append({
                "code": code,
                "name": d.get("name", ""),
                "action": action,
                "price": data.get("position_prices", {}).get(code, {}).get("price"),
                "pnl_pct": d.get("pnl_pct"),
                "note": d.get("reason", ""),
            })
        except Exception as e:
            log["actions"].append(f"ERROR {action} {code}: {e}")

    # 2. Open new positions
    entry_regime = data.get("entry_regime", evaluate_new_entry_regime(data.get("market", {})))
    requested_new_positions = decisions.get("new_positions", []) or []
    sizing_multiplier = float(entry_regime.get("sizing_multiplier", 1.0) or 1.0)
    if entry_regime.get("allow_new_positions"):
        portfolio_config = load_portfolio_config()
        default_alloc = float(portfolio_config.get("max_position_pct", 10))
        allowed_new_positions = []
        for p in requested_new_positions:
            adjusted = dict(p)
            raw_alloc = adjusted.get("allocation_pct")
            base_alloc = float(raw_alloc) if raw_alloc not in (None, "", 0) else default_alloc
            scaled_alloc = round(base_alloc * sizing_multiplier, 2)
            adjusted["allocation_pct"] = scaled_alloc
            if scaled_alloc != base_alloc:
                log["actions"].append(
                    f"SIZE THROTTLE {str(p.get('code', ''))}: {base_alloc:g}% -> {scaled_alloc:g}% "
                    f"(regime={entry_regime.get('regime')})"
                )
            allowed_new_positions.append(adjusted)
    else:
        allowed_new_positions = []
    decisions["new_positions"] = allowed_new_positions
    if requested_new_positions and not allowed_new_positions:
        log["actions"].append(f"SKIP OPEN ALL: {entry_regime.get('reason')}")

    # Fetch real-time market prices for new position candidates.
    # This prevents stale pricedb data from being used as entry prices.
    new_candidate_prices = {}
    if allowed_new_positions:
        candidate_codes = [
            {"code": str(p["code"]).split(".")[0], "name": p.get("name", "")}
            for p in allowed_new_positions
        ]
        try:
            new_candidate_prices = fetch_position_prices(candidate_codes)
            fetched_count = sum(
                1 for v in new_candidate_prices.values()
                if isinstance(v, dict) and v.get("price") and not v.get("error")
            )
            print(
                f"  Fetched real-time prices for {fetched_count}/{len(candidate_codes)} new candidates",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"  ⚠ Failed to fetch new candidate prices: {e}", file=sys.stderr)

    for p in allowed_new_positions:
        try:
            code = str(p["code"]).split(".")[0]

            # --- Determine entry price from real market data first ---
            real_price_data = new_candidate_prices.get(code, {})
            real_price = None
            day_ohlc = None
            if isinstance(real_price_data, dict) and not real_price_data.get("error"):
                real_price = real_price_data.get("price")
                if real_price_data.get("open") and real_price_data.get("high") and real_price_data.get("low"):
                    day_ohlc = {
                        "open": real_price_data["open"],
                        "high": real_price_data["high"],
                        "low": real_price_data["low"],
                        "close": real_price_data.get("price"),
                    }

            # LLM-provided entry price (may be stale/wrong)
            llm_entry_price = p.get("entry_price")

            # Priority: real market price > LLM price > strategy pool price
            if real_price and real_price > 0:
                entry_price = float(real_price)
                # If LLM provided a price, check if it's tradable
                if llm_entry_price not in (None, "", 0) and day_ohlc:
                    llm_ep = float(llm_entry_price)
                    if llm_ep < day_ohlc["low"] or llm_ep > day_ohlc["high"]:
                        log["actions"].append(
                            f"PRICE_CORRECTED {code}: LLM={llm_ep} outside "
                            f"[{day_ohlc['low']},{day_ohlc['high']}], "
                            f"using market={entry_price}"
                        )
                    else:
                        # LLM price is within range, use it (it may be more
                        # specific, e.g., a breakout level)
                        entry_price = llm_ep
            else:
                # No real-time price available — fall back to LLM/pool prices
                entry_price = llm_entry_price
                if entry_price in (None, "", 0):
                    price_info = data.get("position_prices", {}).get(code, {})
                    if isinstance(price_info, dict):
                        entry_price = price_info.get("price") or price_info.get("current_price")

                if entry_price in (None, "", 0):
                    for s in data.get("strategy_pool", {}).get("stocks", []):
                        if str(s.get("code", "")).split(".")[0] == code:
                            entry_price = s.get("price") or s.get("close")
                            if entry_price not in (None, "", 0):
                                break

                if entry_price not in (None, "", 0):
                    entry_price = float(entry_price)
                    # Warn: using fallback price without OHLC validation
                    log["actions"].append(
                        f"WARN {code}: no real-time price, using fallback={entry_price}"
                    )

            stop_loss = p.get("stop", p.get("stopLoss"))
            target_price = p.get("target", p.get("targetPrice"))

            # Conservative defaults if model omitted execution numbers
            if entry_price not in (None, "", 0):
                entry_price = float(entry_price)
                if stop_loss in (None, "", 0):
                    stop_loss = round(entry_price * 0.95, 2)
                if target_price in (None, "", 0):
                    target_price = round(entry_price * 1.15, 2)

            if entry_price in (None, "", 0):
                log["actions"].append(f"SKIP OPEN {code}: missing entry price")
                continue

            # Block 涨停 (limit-up) stocks — cannot buy at +10% daily limit
            stock_pool = data.get("strategy_pool", {}).get("stocks", [])
            stock_change = None
            for s in stock_pool:
                if str(s.get("code", "")).split(".")[0] == code:
                    stock_change = s.get("change_pct")
                    break
            # Also check real-time change_pct from live data
            if stock_change is None and isinstance(real_price_data, dict):
                stock_change = real_price_data.get("change_pct")
            if stock_change is not None and stock_change >= 9.8:
                log["actions"].append(f"SKIP OPEN {code}: 涨停 (change {stock_change}%), cannot buy at daily limit")
                continue

            open_position({
                "code": code,
                "name": p.get("name", ""),
                "entryPrice": entry_price,
                "targetPrice": target_price,
                "stopLoss": stop_loss,
                "allocation_pct": p.get("allocation_pct"),
                "thesis": p.get("thesis", ""),
                "rating": p.get("rating", 2),
                "rps120": p.get("rps120"),
                "sector": p.get("sector", ""),
                "catalysts": p.get("catalysts", []),
                "sourceWatchlist": date,
                # Run date, NOT the wall clock: a slot that executes after
                # midnight (catch-up runs do) would otherwise stamp tomorrow
                # and start the time-stop clock a day late. close_position
                # already takes date=date; this keeps open symmetric.
                "entryDate": date,
                "slot": slot,
                "note": p.get("note", f"LLM开仓 {p.get('name', '')}"),
                "day_ohlc": day_ohlc,
            })
            log["actions"].append(f"OPEN {code} @ {entry_price}")
            daily_actions.append({
                "code": code,
                "name": p.get("name", ""),
                "action": "OPEN",
                "price": entry_price,
                "note": p.get("thesis", ""),
            })
        except (ValueError, FileExistsError) as e:
            log["actions"].append(f"SKIP OPEN {p.get('code')}: {e}")
        except Exception as e:
            log["actions"].append(f"ERROR OPEN {p.get('code')}: {e}")

    # 3. Ensure positions.json is in sync (with live prices)
    regenerate_positions_json(price_data=data.get("position_prices", {}))

    # 4. Generate report and watchlist (into run dir output)
    try:
        generate_watchlist_json(date, data, decisions, output_dir=output_dir)
        log["actions"].append("Generated watchlist")
    except Exception as e:
        log["actions"].append(f"ERROR watchlist: {e}")

    try:
        generate_report_md(date, data, decisions, output_dir=output_dir)
        log["actions"].append("Generated report")
    except Exception as e:
        log["actions"].append(f"ERROR report: {e}")

    # 5. Save daily summary (into run dir output)
    try:
        # Use portfolio data from positions.json (regenerated with live prices)
        pj = regenerate_positions_json(price_data=data.get("position_prices", {}))
        portfolio = pj.get("portfolio", {})

        active = load_active_positions()
        stats = {
            "totalPositions": portfolio.get("positionsUsed", len(active)),
            "totalEquity": portfolio.get("totalEquity", 0),
            "dayPnl": portfolio.get("dayPnl", 0),
            "dayReturnPct": round(portfolio.get("dayPnl", 0) / portfolio["totalEquity"] * 100, 2) if portfolio.get("totalEquity") else 0,
            "totalReturnPct": portfolio.get("totalReturnPct", 0),
            "unrealizedPnl": portfolio.get("unrealizedPnl", 0),
            "realizedPnl": portfolio.get("realizedPnl", 0),
            "cashPct": portfolio.get("cashPct", 0),
        }

        save_daily_summary(
            date,
            daily_actions,
            output_dir=output_dir,
            portfolioStats=stats,
            entryRegime=entry_regime,
            newPositions=[
                {"code": str(p["code"]).split(".")[0], "name": p.get("name")}
                for p in allowed_new_positions
            ],
            marketContext={
                "summary": decisions.get("market_summary", ""),
            },
        )
        log["actions"].append("Saved daily summary")
    except Exception as e:
        log["actions"].append(f"ERROR daily summary: {e}")

    # 6. Update learnings (hypothesis system + legacy LEARNINGS.md)
    if decisions.get("new_learnings"):
        try:
            # Primary: hypothesis-based system
            hyp_data = data.get("_hypothesis_data") or load_hypotheses()
            actions = hypothesis_process_learnings(
                hyp_data, decisions["new_learnings"], run_date=date
            )
            save_hypotheses(hyp_data)
            for a in actions:
                log["actions"].append(f"Hypothesis: {a}")

            # Legacy: also append to LEARNINGS.md (transitional)
            _append_learnings(decisions["new_learnings"])
            log["actions"].append("Updated LEARNINGS.md (legacy)")
        except Exception as e:
            log["actions"].append(f"ERROR learnings: {e}")

    # 7. Create/update agent-written rule scripts
    for script in decisions.get("new_scripts", []):
        try:
            path = PROJECT_ROOT / script["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(script["content"], encoding="utf-8")
            path.chmod(0o755)
            log["actions"].append(f"Created rule: {script['path']}")
        except Exception as e:
            log["actions"].append(f"ERROR creating rule {script.get('path')}: {e}")

    # 8. Run rules on updated state (post-apply check)
    try:
        post_rules = run_all_rules()
        if post_rules.get("total_violations", 0) > 0:
            log["post_apply_rule_violations"] = post_rules
    except Exception as e:
        log["actions"].append(f"ERROR post-apply rules: {e}")

    # 8b. Rotation opportunity ledger — when the book ends the run full,
    #     mechanically log the top gate-passing candidates we could not buy
    #     (vs weakest holding) so `rotation_ledger.py backtest` can measure
    #     the cost of not actively swapping. Never fails the run.
    try:
        from rotation_ledger import record_if_full
        rot = record_if_full(date, data)
        if rot:
            log["actions"].append(
                f"Rotation ledger: book full, logged {len(rot['candidates'])} "
                f"candidates vs weakest {rot['weakest']['code'] if rot.get('weakest') else '?'}")
    except Exception as e:
        print(f"  [rotation-ledger] failed (non-fatal): {e}", file=sys.stderr)

    # 9. Take post-run snapshot
    post_snap = snapshot_positions("post_run", date)
    (output_dir / "positions_snapshot.json").write_text(
        json.dumps(post_snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    snapshot_aux_state(output_dir)

    log["end"] = time.time()
    log["duration_sec"] = round(log["end"] - log["start"], 1)
    return log


def refresh_site() -> None:
    """Regenerate site/index.html. Never fails the run.

    site/ is git-ignored (2026-08-14) — a derived artifact, rebuildable from
    tracked data — so this no longer has to happen before the commit. It runs
    right after each manifest write instead, which means a run that dies at
    Gate 3 still leaves the page matching what actually landed in tracking/,
    with the failure banner on top. Before, a post-apply failure skipped the
    rebuild entirely and the site silently disagreed with the books (7/20 and
    8/14 both did exactly that)."""
    try:
        from build_site import build as _build_site
        _build_site()
    except Exception as e:
        print(f"  [site] regeneration failed (non-fatal): {e}", file=sys.stderr)


def write_manifest(manifest, run_dir: Path) -> None:
    """Finalize + persist the manifest, then refresh the site so its status
    banner matches the run that just ended. Kept together so the two can't
    drift out of sync."""
    manifest.finalize()
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    refresh_site()


def phase4_validate_and_log(date: str, logs: list[dict], slot: str) -> list[str]:
    """Phase 4: Validate output and save run log."""
    errors = validate_output(date, slot)

    # Run final rule check
    try:
        rule_results = run_all_rules()
        if rule_results.get("total_violations", 0) > 0:
            for r in rule_results.get("rules", []):
                for v in r.get("violations", []):
                    errors.append(f"RULE {r['rule']}: {v.get('code', '?')} — {v.get('suggestion', '')}")
    except Exception:
        pass

    # Save run log to runs/<date>/<slot>/log.json
    run_dir = get_run_dir(date, slot)
    run_log = {
        "date": date,
        "slot": slot,
        "runs": logs,
        "validation_errors": errors,
        "summary": {
            "totalPhases": len(logs),
            "totalDurationSec": sum(l.get("duration_sec", 0) for l in logs),
        },
    }
    log_file = run_dir / "log.json"
    log_file.write_text(
        json.dumps(run_log, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return errors


def _append_learnings(lessons: list) -> None:
    """Append new learnings to LEARNINGS.md (legacy, transitional).
    
    Accepts both string and dict format learnings.
    """
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    content = learnings_file.read_text(encoding="utf-8") if learnings_file.exists() else ""
    today = datetime.now().strftime("%Y-%m-%d")

    additions = [f"\n### 自动更新 ({today})\n"]
    for lesson in lessons:
        if isinstance(lesson, dict):
            text = lesson.get("text", "")
            if text:
                additions.append(f"- {text}")
        else:
            additions.append(f"- {lesson}")
    additions.append("")

    content += "\n".join(additions)
    learnings_file.write_text(content, encoding="utf-8")


def _parse_slot_arg(args: list[str]) -> str | None:
    """Extract an optional ``--slot {noon,afternoon}`` override from args."""
    if "--slot" not in args:
        return None
    idx = args.index("--slot")
    if idx + 1 >= len(args):
        print("Usage: --slot {noon,afternoon}", file=sys.stderr)
        sys.exit(1)
    value = args[idx + 1]
    if value not in ("noon", "afternoon"):
        print(f"Invalid --slot {value!r}; expected 'noon' or 'afternoon'", file=sys.stderr)
        sys.exit(1)
    return value


def attempt_partial_day_autoheal(data: dict) -> bool:
    """Run the proven partial-day cure in-place: budget-exempt sina repair
    sweep (factor heal rides inside) + RPS recompute for the damaged date.
    Returns True when the sweep succeeded and a re-collect is worthwhile.

    Only ever invoked after Gate 1 flags the latest price day as partial —
    i.e. a settled session with a died-mid-fetch bar set (eastmoney throttle
    signature). Failure here is not fatal to the caller; the run then halts
    exactly as it did before auto-heal existed (2026-08-10)."""
    day = (data.get("db_health") or {}).get("latest_price_date")
    if not day:
        return False
    pricedb_script = str(PROJECT_ROOT / "scripts" / "pricedb.py")
    print(f"\n⚙ AUTO-HEAL: latest price day {day} is partial — sina repair "
          f"sweep + RPS recompute (~10-12 min)...", file=sys.stderr)
    try:
        repair = subprocess.run(
            [sys.executable, pricedb_script, "repair", "--beg", day, "--end", day],
            cwd=str(PROJECT_ROOT), timeout=1800)
        if repair.returncode != 0:
            print("  ✗ auto-heal: repair sweep failed — halting as before",
                  file=sys.stderr)
            return False
        rps = subprocess.run(
            [sys.executable, pricedb_script, "rps", day],
            cwd=str(PROJECT_ROOT), timeout=1800)
        if rps.returncode != 0:
            print("  ⚠ auto-heal: RPS recompute failed — collect will retry "
                  "with cache invalidated", file=sys.stderr)
        print("  ✓ auto-heal complete — re-collecting phase 1", file=sys.stderr)
        return True
    except Exception as e:  # noqa: BLE001 — timeouts, spawn failures
        print(f"  ✗ auto-heal error: {e} — halting as before", file=sys.stderr)
        return False


def main():
    run_start = datetime.now().astimezone()
    date = run_start.strftime("%Y-%m-%d")
    args = sys.argv[1:]

    # --date YYYY-MM-DD: analyze a PAST (settled) session — for re-running a
    # slot the machine slept through (2026-08-07 afternoon: laptop woke at
    # 17:36 with no DNS, run failed, weekend re-run needed the override).
    # Only makes sense for the last settled trading day or later re-analysis;
    # refuses future dates.
    if "--date" in args:
        idx = args.index("--date")
        if idx + 1 >= len(args):
            print("Usage: --date YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        override = args[idx + 1]
        try:
            datetime.strptime(override, "%Y-%m-%d")
        except ValueError:
            print(f"Invalid --date {override!r}; expected YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        if override > date:
            print(f"--date {override} is in the future", file=sys.stderr)
            sys.exit(1)
        if override != date:
            print(f"⚠ Running with date override {override} (today is {date}) — "
                  "post-close re-analysis of a settled session", file=sys.stderr)
        date = override

    # Slot: --slot override wins, else derived from the local clock at run start.
    slot_override = _parse_slot_arg(args)
    slot = resolve_slot(slot_override, run_start)
    run_started_at_iso = run_start.isoformat()

    if "--list-runs" in args:
        list_runs()
        return

    if "--reset-to" in args:
        idx = args.index("--reset-to")
        if idx + 1 >= len(args):
            print("Usage: --reset-to YYYY-MM-DD [--slot {noon,afternoon}]", file=sys.stderr)
            sys.exit(1)
        target_date = args[idx + 1]
        reset_to_date(target_date, slot_override)
        return

    if "--validate" in args:
        idx = args.index("--validate")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            validate_date = args[idx + 1]
        else:
            validate_date = date
        errors = validate_output(validate_date, slot_override)
        if errors:
            for e in errors:
                print(f"  {e}")
        else:
            print("All checks passed!")
        return

    if "--run" in args:
        # Full automated pipeline: Phase 1 → LLM → Phase 3 → Phase 4 → git commit
        legacy_llm = "--legacy-llm" in args
        llm_provider = None
        if "--llm-provider" in args:
            pidx = args.index("--llm-provider")
            if pidx + 1 >= len(args):
                print("Usage: --run [--llm-provider openai|hybrid|anthropic] [--no-commit]", file=sys.stderr)
                sys.exit(1)
            llm_provider = args[pidx + 1]

        if legacy_llm:
            from llm_client import call_llm_v1 as call_llm
            provider_label = "legacy"
            if llm_provider:
                print("Warning: --llm-provider is ignored with --legacy-llm", file=sys.stderr)
        else:
            from llm_client import call_llm, normalize_llm_provider
            provider_label = normalize_llm_provider(llm_provider)

        no_commit = "--no-commit" in args

        print(f"{'='*60}", file=sys.stderr)
        print(f"Stock Analysis Pipeline — {date} [{slot}] (full auto, {provider_label})", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        # Pre-flight: Source health check
        print("Pre-flight: Checking data sources...", file=sys.stderr)
        health = check_source_health()
        for src, status in health.items():
            icon = "✓" if status.get("status") == "ok" else "✗" if status.get("status") in ("down", "proxy_blocked") else "⚠"
            latency = f" ({status['latency_ms']:.0f}ms)" if "latency_ms" in status else ""
            extra = f" — {status.get('error', '')}" if status.get("error") else ""
            if src == "pricedb" and status.get("latest_date"):
                extra = f" (latest: {status['latest_date']}, stale: {status.get('stale')})"
            print(f"  {icon} {src}: {status['status']}{latency}{extra}", file=sys.stderr)

        run_dir = get_run_dir(date, slot)
        manifest = RunManifest(
            date=date,
            status=PipelineStatus.SUCCESS,
            slot=slot,
            run_started_at=run_started_at_iso,
        )
        manifest.add_phase("health_check", "ok", details={"sources": health})

        # Warn if critical sources are all down
        sina_down = health.get("sina", {}).get("status") != "ok"
        cf_down = health.get("cheesefortune", {}).get("status") != "ok"
        if sina_down and cf_down:
            print("  ✗ ALL external data sources are down — pipeline will likely fail", file=sys.stderr)

        # Pre-flight: refresh local pricedb and hard-gate on staleness.
        # Done here (not inside phase1) so we refuse to start analysis on stale closes.
        preflight_pricedb_or_exit(manifest)

        # Phase 1: Collect (+ Gate 1), with ONE partial-day auto-heal retry.
        # Under the eastmoney throttle the settled-day fetch can die mid-sweep
        # (24-141 of ~5211 rows, three manual repairs in four sessions to
        # 2026-08-10); the cure is deterministic and proven, so the pipeline
        # now runs it itself: sina repair sweep (+factor heal inside) + RPS
        # recompute, then re-collect. Still halts if the sweep fails, and the
        # sweep only touches settled dates — never intraday bars.
        for gate1_attempt in (1, 2):
            data = phase1_collect(date, slot)

            # Save Phase 1 data
            phase1_file = run_dir / "phase1.json"
            save_data = {k: v for k, v in data.items() if k not in ("learnings", "_hypothesis_data", "hypothesis_prompt")}
            phase1_file.write_text(
                json.dumps(save_data, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )

            # Gate 1: Validate Phase 1 output
            print(f"\nGate 1: Validating Phase 1 data...", file=sys.stderr)
            gate1 = validate_phase1_gate(data)
            manifest.add_gate(gate1)
            manifest.add_phase("collect", "ok" if gate1.passed else "failed",
                               duration_sec=data.get("_log_phase1", {}).get("duration_sec", 0),
                               details={"errors": data.get("_log_phase1", {}).get("errors", [])})

            if gate1.soft_warns:
                for w in gate1.soft_warns:
                    print(f"  ⚠ {w}", file=sys.stderr)

            if gate1.passed:
                break
            if gate1_attempt == 1 and any("partial" in f for f in gate1.hard_fails) \
                    and attempt_partial_day_autoheal(data):
                manifest.add_phase("auto_heal", "ok")
                continue

            for f in gate1.hard_fails:
                print(f"  ✗ {f}", file=sys.stderr)
            write_manifest(manifest, run_dir)
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Pipeline FAILED at Gate 1 with {len(gate1.hard_fails)} hard failure(s)", file=sys.stderr)
            print(f"No LLM call made. No positions modified.", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            # Print machine-readable failure to stdout for cron
            print(json.dumps({
                "date": date,
                "status": "failed",
                "failed_at": "gate1_phase1_validation",
                "hard_fails": gate1.hard_fails,
                "soft_warns": gate1.soft_warns,
            }, ensure_ascii=False))
            sys.exit(1)

        print(f"  ✓ Gate 1 passed", file=sys.stderr)

        # Phase 2: Build prompt and call LLM
        phase2_label = "legacy 4-pass" if legacy_llm else provider_label
        print(f"\nPhase 2: Calling LLM ({phase2_label})...", file=sys.stderr)
        prompt = phase2_build_prompt(data)

        if legacy_llm:
            llm_result = call_llm(prompt, output_dir=run_dir)
        else:
            phase1_data = {k: v for k, v in data.items() if k not in ("learnings", "_hypothesis_data", "hypothesis_prompt")}
            llm_result = call_llm(
                prompt,
                output_dir=run_dir,
                phase1_data=phase1_data,
                provider=provider_label,
            )

        # Use GPT JSON (primary) or Claude JSON (fallback)
        decisions = llm_result.get("gpt_json") or llm_result.get("claude_json")
        if not decisions:
            decisions = _parse_llm_response(llm_result["text"])
        if not decisions:
            print("ERROR: Could not parse LLM response as JSON", file=sys.stderr)
            print(f"Response text ({len(llm_result['text'])} chars):", file=sys.stderr)
            print(llm_result["text"][:2000], file=sys.stderr)
            sys.exit(1)

        # Save responses
        (run_dir / "response.json").write_text(
            json.dumps(decisions, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if llm_result.get("claude_json"):
            (run_dir / "response_claude.json").write_text(
                json.dumps(llm_result["claude_json"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if llm_result.get("gpt_json"):
            (run_dir / "response_gpt.json").write_text(
                json.dumps(llm_result["gpt_json"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

        # Save LLM metadata
        llm_meta = {
            "provider": llm_result.get("provider", provider_label),
            "primary_model": llm_result.get("primary_model"),
            "decision_source": llm_result.get("decision_source"),
            "input_tokens": llm_result["input_tokens"],
            "output_tokens": llm_result["output_tokens"],
            "rounds": llm_result["rounds"],
            "duration_sec": llm_result["duration_sec"],
            "tool_calls": llm_result["tool_calls"],
            "fallback_used": llm_result.get("fallback_used", False),
        }
        (run_dir / "llm_meta.json").write_text(
            json.dumps(llm_meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        source = llm_result.get("decision_source") or ("fallback" if llm_result.get("fallback_used") else "primary")
        print(f"  LLM: {llm_result['rounds']} rounds, "
              f"{llm_result['input_tokens']}+{llm_result['output_tokens']} tokens, "
              f"{len(llm_result['tool_calls'])} tool calls, "
              f"{llm_result['duration_sec']}s ({source})", file=sys.stderr)

        # Gate 2: Validate LLM output
        print(f"\nGate 2: Validating LLM response...", file=sys.stderr)
        gate2 = validate_llm_output_gate(decisions, data)
        manifest.add_gate(gate2)
        manifest.add_phase("llm_analysis", "ok" if gate2.passed else "failed",
                           duration_sec=llm_result["duration_sec"])

        if gate2.soft_warns:
            for w in gate2.soft_warns:
                print(f"  ⚠ {w}", file=sys.stderr)

        if not gate2.passed:
            for f in gate2.hard_fails:
                print(f"  ✗ {f}", file=sys.stderr)
            write_manifest(manifest, run_dir)
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Pipeline FAILED at Gate 2 with {len(gate2.hard_fails)} hard failure(s)", file=sys.stderr)
            print(f"LLM ran but response is invalid. No positions modified.", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            print(json.dumps({
                "date": date,
                "status": "failed",
                "failed_at": "gate2_llm_validation",
                "hard_fails": gate2.hard_fails,
                "soft_warns": gate2.soft_warns,
            }, ensure_ascii=False))
            sys.exit(1)

        print(f"  ✓ Gate 2 passed", file=sys.stderr)

        # Phase 3: Apply
        print(f"\nPhase 3: Applying decisions...", file=sys.stderr)
        all_logs = []
        if data.get("_log_phase1"):
            all_logs.append(data["_log_phase1"])
        all_logs.append({
            "phase": "llm_analysis",
            "response_size_bytes": len(llm_result["text"]),
            "tokens": {
                "input_tokens": llm_result["input_tokens"],
                "output_tokens": llm_result["output_tokens"],
            },
            "rounds": llm_result["rounds"],
            "tool_calls_count": len(llm_result["tool_calls"]),
            "duration_sec": llm_result["duration_sec"],
            "fallback_used": llm_result.get("fallback_used", False),
            "provider": llm_result.get("provider", provider_label),
            "decision_source": llm_result.get("decision_source"),
            "primary_model": llm_result.get("primary_model"),
        })

        log3 = phase3_apply(date, decisions, data)
        print(f"  Actions: {log3['actions']}", file=sys.stderr)
        all_logs.append(log3)

        # Gate 3: Validate Phase 3 output
        print(f"\nGate 3: Validating apply results...", file=sys.stderr)
        gate3 = validate_phase3_gate(date, log3, data)
        manifest.add_gate(gate3)
        manifest.add_phase("apply", "ok" if gate3.passed else "failed",
                           duration_sec=log3.get("duration_sec", 0))

        if gate3.soft_warns:
            for w in gate3.soft_warns:
                print(f"  ⚠ {w}", file=sys.stderr)

        if not gate3.passed:
            for f in gate3.hard_fails:
                print(f"  ✗ {f}", file=sys.stderr)
            write_manifest(manifest, run_dir)
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Pipeline FAILED at Gate 3. Apply had errors. Review tracking state.", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            print(json.dumps({
                "date": date,
                "status": "failed",
                "failed_at": "gate3_apply_validation",
                "hard_fails": gate3.hard_fails,
            }, ensure_ascii=False))
            sys.exit(1)

        print(f"  ✓ Gate 3 passed", file=sys.stderr)

        # Phase 4: Validate
        print(f"\nPhase 4: Validating...", file=sys.stderr)
        errors = phase4_validate_and_log(date, all_logs, slot)
        critical_errors = [e for e in errors if isinstance(e, str) and e.startswith("CRITICAL")]
        if critical_errors:
            for e in critical_errors:
                print(f"  ✗ {e}", file=sys.stderr)
            print(f"  CRITICAL validation errors — skipping commit", file=sys.stderr)
        elif errors:
            print(f"  Validation issues: {errors}", file=sys.stderr)
        else:
            print("  All checks passed!", file=sys.stderr)

        # (site rebuild moved to write_manifest — it no longer rides into the
        # commit, so it can run after the manifest and reflect the real status)

        # Git commit (blocked by CRITICAL validation errors)
        if not no_commit and not critical_errors:
            print(f"\nPhase 5: Git commit...", file=sys.stderr)
            # Commit locally first. A push failure must NOT be reported as a
            # commit failure, so keep the two steps in separate try blocks.
            committed = False
            try:
                subprocess.run(["git", "add", "-A"], cwd=str(PROJECT_ROOT), check=True,
                               capture_output=True)
                subprocess.run(
                    ["git", "commit", "-m", f"分析: {date} 每日流水线"],
                    cwd=str(PROJECT_ROOT), check=True, capture_output=True,
                )
                committed = True
                print("  Committed.", file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print(f"  Git commit error: {e.stderr.decode() if e.stderr else e}",
                      file=sys.stderr)

            if committed:
                # Push with retry + backoff. Transient HTTP2 framing errors are
                # common with GitHub over HTTP/2, so fall back to HTTP/1.1 on the
                # final attempt. A push failure leaves the commit intact locally
                # to be pushed by the next run.
                max_attempts = 3
                for attempt in range(1, max_attempts + 1):
                    push_cmd = ["git", "push"]
                    if attempt == max_attempts:
                        # Final attempt: force HTTP/1.1 to dodge HTTP2 framing bugs.
                        push_cmd = ["git", "-c", "http.version=HTTP/1.1", "push"]
                    try:
                        subprocess.run(push_cmd, cwd=str(PROJECT_ROOT), check=True,
                                       capture_output=True)
                        print(f"  Pushed (attempt {attempt}).", file=sys.stderr)
                        break
                    except subprocess.CalledProcessError as e:
                        err = e.stderr.decode() if e.stderr else str(e)
                        print(f"  Git push error (attempt {attempt}/{max_attempts}): {err}",
                              file=sys.stderr)
                        if attempt < max_attempts:
                            time.sleep(2 ** attempt)  # 2s, 4s backoff
                        else:
                            print("  Push failed; commit is saved locally and will "
                                  "be pushed by the next run.", file=sys.stderr)

        # Summary
        total_sec = sum(l.get("duration_sec", 0) for l in all_logs)

        # Finalize manifest
        manifest.add_phase("validate", "ok" if not errors else "warnings",
                           details={"errors": errors})
        manifest.total_duration_sec = total_sec
        write_manifest(manifest, run_dir)

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Pipeline complete in {total_sec:.0f}s ({manifest.status.value})", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        # Print summary to stdout (for cron capture)
        actions = decisions.get("position_decisions", [])
        new_pos = decisions.get("new_positions", [])
        sells = [a for a in actions if a.get("action") == "SELL"]
        holds = [a for a in actions if a.get("action") in ("HOLD", "RAISE_STOP")]
        print(json.dumps({
            "date": date,
            "status": manifest.status.value,
            "sells": len(sells),
            "opens": len(new_pos),
            "holds": len(holds),
            "tool_calls": len(llm_result["tool_calls"]),
            "tokens": llm_result["input_tokens"] + llm_result["output_tokens"],
            "duration_sec": total_sec,
            "validation_errors": len(errors),
            "gate_warnings": sum(len(g["soft_warns"]) for g in manifest.gates.values()),
        }, ensure_ascii=False))
        sys.exit(manifest.exit_code)

    if "--apply" in args:
        # Phase 3+4: Apply LLM response from file
        idx = args.index("--apply")
        if idx + 1 >= len(args):
            print("Usage: --apply FILE [--tokens INPUT OUTPUT]", file=sys.stderr)
            sys.exit(1)
        response_file = Path(args[idx + 1])
        if not response_file.exists():
            print(f"File not found: {response_file}", file=sys.stderr)
            sys.exit(1)

        # Parse optional --tokens INPUT OUTPUT
        llm_tokens = None
        if "--tokens" in args:
            tidx = args.index("--tokens")
            if tidx + 2 < len(args):
                try:
                    llm_tokens = {
                        "input_tokens": int(args[tidx + 1]),
                        "output_tokens": int(args[tidx + 2]),
                    }
                except ValueError:
                    pass

        # Load LLM response
        response_text = response_file.read_text(encoding="utf-8")
        response_size = len(response_text)
        # Try to extract JSON from response
        decisions = _parse_llm_response(response_text)
        if not decisions:
            print("Could not parse LLM response as JSON", file=sys.stderr)
            sys.exit(1)

        # Save response.json into run dir
        run_dir = get_run_dir(date, slot)
        (run_dir / "response.json").write_text(
            json.dumps(decisions, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # Load Phase 1 data (new location first, then legacy)
        phase1_file = run_dir / "phase1.json"
        if not phase1_file.exists():
            # Legacy fallback
            legacy_file = PROJECT_ROOT / "data" / f"phase1_{date}.json"
            if legacy_file.exists():
                phase1_file = legacy_file

        if phase1_file.exists():
            data = json.loads(phase1_file.read_text(encoding="utf-8"))
        else:
            print("Warning: No Phase 1 data found, running Phase 1 first...", file=sys.stderr)
            data = phase1_collect(date, slot)

        # Build complete run log from all phases
        all_logs = []

        # Phase 1 log (from saved data)
        phase1_log = data.get("_log_phase1")
        if phase1_log:
            all_logs.append(phase1_log)
        else:
            # Reconstruct minimal Phase 1 log from data file timestamp
            all_logs.append({
                "phase": "collect",
                "duration_sec": 0,
                "note": "Phase 1 log not found in saved data",
            })

        # Phase 2 log (LLM analysis — happens outside this script)
        phase2_log = {
            "phase": "llm_analysis",
            "response_size_bytes": response_size,
            "response_file": str(response_file),
        }
        if llm_tokens:
            phase2_log["tokens"] = llm_tokens
        all_logs.append(phase2_log)

        # Phase 3: Apply
        print(f"\nPhase 3: Applying decisions...", file=sys.stderr)
        log3 = phase3_apply(date, decisions, data)
        print(f"  Actions: {log3['actions']}", file=sys.stderr)
        all_logs.append(log3)

        print(f"\nPhase 4: Validating...", file=sys.stderr)
        errors = phase4_validate_and_log(date, all_logs, slot)
        if errors:
            print(f"  Validation issues: {errors}", file=sys.stderr)
        else:
            print("  All checks passed!", file=sys.stderr)
        # --apply writes no manifest, so refresh directly. Without this, a
        # manual repair left the site on the pre-repair build (2026-08-14).
        refresh_site()
        return

    # Full pipeline: Phase 1 + Phase 2 output
    print(f"{'='*60}", file=sys.stderr)
    print(f"Stock Analysis Pipeline — {date}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Phase 1
    data = phase1_collect(date, slot)

    # Save Phase 1 data to run dir for later use with --apply
    run_dir = get_run_dir(date, slot)
    phase1_file = run_dir / "phase1.json"
    # Strip learnings text (too large) before saving
    save_data = {k: v for k, v in data.items() if k not in ("learnings", "_hypothesis_data", "hypothesis_prompt")}
    phase1_file.write_text(
        json.dumps(save_data, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    if "--phase1" in args:
        print(f"\nPhase 1 data saved to {phase1_file}", file=sys.stderr)
        return

    # Phase 2: Build and output LLM prompt
    print(f"\nPhase 2: Building LLM prompt...", file=sys.stderr)
    prompt = phase2_build_prompt(data)

    # Output prompt to stdout with markers
    print(LLM_PROMPT_START)
    print(prompt)
    print(LLM_PROMPT_END)

    print(f"\n{'='*60}", file=sys.stderr)
    print("LLM prompt printed to stdout.", file=sys.stderr)
    print("To apply the LLM response:", file=sys.stderr)
    print(f"  python scripts/run_daily.py --apply response.json", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)


def _parse_llm_response(text: str) -> dict:
    """Try to extract the decision JSON *object* from LLM response text.

    Handles cases where JSON is wrapped in ```json blocks or mixed with
    explanatory text. Prefers a dict: LLMs sometimes emit a standalone
    ``new_learnings`` array in its own ```json block before the full decision
    object, and grabbing the first parseable block would return that list and
    fail the phase-2 gate. Non-dict blocks are skipped in favor of the object.
    """
    # Try direct parse — only accept a dict. A bare top-level list means no
    # decision object is present; return {} so the gate fails cleanly instead
    # of brace-matching an inner element out of the list below.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {}
    except json.JSONDecodeError:
        pass

    # Try to extract from ```json blocks — first block that parses to a dict wins
    import re
    json_blocks = re.findall(r"```json\s*(.*?)```", text, re.DOTALL)
    for block in json_blocks:
        try:
            parsed = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    # Try to find JSON object in text
    brace_count = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if brace_count == 0:
                start = i
            brace_count += 1
        elif ch == "}":
            brace_count -= 1
            if brace_count == 0 and start is not None:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    start = None

    return {}


if __name__ == "__main__":
    main()
