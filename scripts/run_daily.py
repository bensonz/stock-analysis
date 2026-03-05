#!/usr/bin/env python3
"""
run_daily.py — Main orchestrator for the daily stock analysis pipeline.

Phase 1: DATA COLLECTION (pure Python)
Phase 2: ANALYSIS (LLM — single call, outputs prompt to stdout)
Phase 3: EXECUTION (pure Python — apply LLM decisions)
Phase 4: VALIDATION + COMMIT

Usage:
    python scripts/run_daily.py                    # Full pipeline (stops at Phase 2 output)
    python scripts/run_daily.py --phase1           # Data collection only
    python scripts/run_daily.py --apply FILE       # Apply LLM response from file (Phase 3+4)
    python scripts/run_daily.py --validate         # Run validation only
    python scripts/run_daily.py --validate DATE    # Validate specific date
    python scripts/run_daily.py --reset-to DATE    # Reset state to end of DATE
    python scripts/run_daily.py --list-runs        # Show all runs with status
"""

import json
import os
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
    fetch_market_overview,
    fetch_position_prices,
    fetch_missed_opportunity_prices,
    load_recent_watchlists,
    save_crawl_data,
    save_market_data,
    save_price_data,
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
from report_generator import generate_watchlist_json, generate_report_md
from run_rules import run_all_rules
from validator import validate_data, validate_output

# Directories
RUNS_DIR = PROJECT_ROOT / "runs"

LLM_PROMPT_START = "=== LLM_PROMPT_START ==="
LLM_PROMPT_END = "=== LLM_PROMPT_END ==="


def get_run_dir(date: str) -> Path:
    """Get the run directory for a date, creating subdirs as needed."""
    run_dir = RUNS_DIR / date
    (run_dir / "input").mkdir(parents=True, exist_ok=True)
    (run_dir / "output").mkdir(parents=True, exist_ok=True)
    return run_dir


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


def check_snapshot_consistency(date: str, current_snapshot: dict) -> list[str]:
    """Check if current state matches the previous day's post-run snapshot."""
    warnings = []

    if not RUNS_DIR.exists():
        return []

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


def reset_to_date(target_date: str) -> None:
    """Reset all position state to the end-of-day state of target_date.

    Reads runs/<target_date>/output/positions_snapshot.json and restores
    tracking/ state from it. Also deletes any run dirs after target_date.
    """
    run_dir = RUNS_DIR / target_date
    snapshot_file = run_dir / "output" / "positions_snapshot.json"

    if not snapshot_file.exists():
        # Try input snapshot if output doesn't exist (run never completed)
        snapshot_file = run_dir / "input" / "positions_snapshot.json"
        if not snapshot_file.exists():
            print(f"No snapshot found for {target_date}", file=sys.stderr)
            if RUNS_DIR.exists():
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
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir()):
            if d.is_dir() and d.name > target_date:
                shutil.rmtree(d)
                deleted.append(d.name)
    if deleted:
        print(f"  Deleted runs: {', '.join(deleted)}", file=sys.stderr)

    # Restore
    restore_snapshot(snapshot)

    # Regenerate positions.json with current data (no live prices)
    regenerate_positions_json()

    print(f"\n✓ State restored to end of {target_date}", file=sys.stderr)


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


def phase1_collect(date: str) -> dict:
    """Phase 1: Collect all data. Pure Python, no LLM.

    Runs independent tasks in parallel:
      - Strategy pool fetch (fast, ~5s) runs first since enrichment depends on it
      - Then enrichment, market, positions, and watchlists run concurrently
    """
    log = {"phase": "collect", "start": time.time(), "errors": []}
    data = {"date": date}

    print("Phase 1: Collecting data...", file=sys.stderr)

    # Create run directory and take pre-run snapshot
    run_dir = get_run_dir(date)
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

    # Step 1: Strategy pool (must complete before enrichment can start)
    print("  [1/5] Fetching strategy pool...", file=sys.stderr)
    try:
        data["strategy_pool"] = fetch_strategy_pool()
        save_crawl_data(date, data["strategy_pool"], output_dir=input_dir)
        print(f"    → {data['strategy_pool'].get('total_stocks', 0)} stocks", file=sys.stderr)
    except Exception as e:
        data["strategy_pool"] = {"error": str(e), "stocks": []}
        log["errors"].append(f"strategy_pool: {e}")

    # Load positions and watchlists synchronously (instant, local files)
    positions = load_active_positions()
    data["positions"] = positions
    data["positions_count"] = len(positions)
    data["recent_watchlists"] = load_recent_watchlists(days=5)

    # Prepare enrichment candidates
    pool_stocks = data["strategy_pool"].get("stocks", [])
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
        sig = result.get("overall_sentiment", {}).get("signal", "?")
        rank = result.get("overall_sentiment", {}).get("avg_iv_rank", 0)
        print(f"    → {sig} (avg IV rank {rank*100:.1f}%)", file=sys.stderr)
        return "iv_sentiment", result

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_enrich): "enrich",
            executor.submit(_market): "market",
            executor.submit(_prices): "position_prices",
            executor.submit(_missed): "watchlists",
            executor.submit(_iv_sentiment): "iv_sentiment",
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

    # Save IV sentiment to input dir
    if data.get("iv_sentiment") and "error" not in data["iv_sentiment"]:
        (input_dir / "iv_sentiment.json").write_text(
            json.dumps(data["iv_sentiment"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Learnings (local file, instant)
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    if learnings_file.exists():
        data["learnings"] = learnings_file.read_text(encoding="utf-8")
    else:
        data["learnings"] = ""

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

    log["end"] = time.time()
    log["duration_sec"] = round(log["end"] - log["start"], 1)
    data["_log_phase1"] = log

    print(f"\nPhase 1 complete in {log['duration_sec']}s", file=sys.stderr)
    if log["errors"]:
        print(f"  Errors: {log['errors']}", file=sys.stderr)
    if data["collection_errors"]:
        print(f"  Warnings: {data['collection_errors']}", file=sys.stderr)

    return data


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
        "enriched_candidates": data.get("enriched", []),
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
                "history": p.get("history", [])[-3:],  # Last 3 history entries
            }
            for p in data.get("positions", [])
        ],
        "position_prices": data.get("position_prices", {}),
        "missed_opportunity_prices": data.get("missed_opportunity_prices", []),
        "iv_sentiment": data.get("iv_sentiment", {}),
        "rule_violations": data.get("rule_violations", {}),
        "collection_errors": data.get("collection_errors", []),
    }

    # Truncate learnings to last 200 lines (avoid context overflow)
    learnings = data.get("learnings", "")
    learnings_lines = learnings.strip().split("\n")
    if len(learnings_lines) > 200:
        learnings = "\n".join(learnings_lines[:200]) + "\n\n[... truncated ...]"
    payload["learnings_excerpt"] = learnings

    prompt = f"""{analyst_prompt}

## 今日数据 (由 run_daily.py 自动收集)

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```

请根据以上数据进行分析，按照 Required Output JSON 格式返回你的决策。
"""

    # Save prompt to run dir
    run_dir = get_run_dir(data["date"])
    (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    return prompt


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
    run_dir = get_run_dir(date)
    output_dir = run_dir / "output"

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
    for p in decisions.get("new_positions", []):
        try:
            open_position({
                "code": p["code"],
                "name": p.get("name", ""),
                "entryPrice": p["entry_price"],
                "targetPrice": p.get("target", p.get("targetPrice", 0)),
                "stopLoss": p.get("stop", p.get("stopLoss", 0)),
                "allocation_pct": p.get("allocation_pct"),
                "thesis": p.get("thesis", ""),
                "rating": p.get("rating", 2),
                "rps120": p.get("rps120"),
                "sector": p.get("sector", ""),
                "catalysts": p.get("catalysts", []),
                "sourceWatchlist": date,
                "note": p.get("note", f"LLM开仓 {p.get('name', '')}"),
            })
            log["actions"].append(f"OPEN {p['code']}")
            daily_actions.append({
                "code": str(p["code"]).split(".")[0],
                "name": p.get("name", ""),
                "action": "OPEN",
                "price": p["entry_price"],
                "note": p.get("thesis", ""),
            })
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
            newPositions=[
                {"code": str(p["code"]).split(".")[0], "name": p.get("name")}
                for p in decisions.get("new_positions", [])
            ],
            marketContext={
                "summary": decisions.get("market_summary", ""),
            },
        )
        log["actions"].append("Saved daily summary")
    except Exception as e:
        log["actions"].append(f"ERROR daily summary: {e}")

    # 6. Update learnings
    if decisions.get("new_learnings"):
        try:
            _append_learnings(decisions["new_learnings"])
            log["actions"].append("Updated LEARNINGS.md")
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

    # 9. Take post-run snapshot
    post_snap = snapshot_positions("post_run", date)
    (output_dir / "positions_snapshot.json").write_text(
        json.dumps(post_snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    log["end"] = time.time()
    log["duration_sec"] = round(log["end"] - log["start"], 1)
    return log


def phase4_validate_and_log(date: str, logs: list[dict]) -> list[str]:
    """Phase 4: Validate output and save run log."""
    errors = validate_output(date)

    # Run final rule check
    try:
        rule_results = run_all_rules()
        if rule_results.get("total_violations", 0) > 0:
            for r in rule_results.get("rules", []):
                for v in r.get("violations", []):
                    errors.append(f"RULE {r['rule']}: {v.get('code', '?')} — {v.get('suggestion', '')}")
    except Exception:
        pass

    # Save run log to runs/<date>/log.json
    run_dir = get_run_dir(date)
    run_log = {
        "date": date,
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


def _append_learnings(lessons: list[str]) -> None:
    """Append new learnings to LEARNINGS.md."""
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    content = learnings_file.read_text(encoding="utf-8") if learnings_file.exists() else ""
    today = datetime.now().strftime("%Y-%m-%d")

    additions = [f"\n### 自动更新 ({today})\n"]
    for lesson in lessons:
        additions.append(f"- {lesson}")
    additions.append("")

    content += "\n".join(additions)
    learnings_file.write_text(content, encoding="utf-8")


def main():
    date = datetime.now().strftime("%Y-%m-%d")
    args = sys.argv[1:]

    if "--list-runs" in args:
        list_runs()
        return

    if "--reset-to" in args:
        idx = args.index("--reset-to")
        if idx + 1 >= len(args):
            print("Usage: --reset-to YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
        target_date = args[idx + 1]
        reset_to_date(target_date)
        return

    if "--validate" in args:
        idx = args.index("--validate")
        if idx + 1 < len(args) and not args[idx + 1].startswith("--"):
            validate_date = args[idx + 1]
        else:
            validate_date = date
        errors = validate_output(validate_date)
        if errors:
            for e in errors:
                print(f"  {e}")
        else:
            print("All checks passed!")
        return

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
        run_dir = get_run_dir(date)
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
            data = phase1_collect(date)

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
        errors = phase4_validate_and_log(date, all_logs)
        if errors:
            print(f"  Validation issues: {errors}", file=sys.stderr)
        else:
            print("  All checks passed!", file=sys.stderr)
        return

    # Full pipeline: Phase 1 + Phase 2 output
    print(f"{'='*60}", file=sys.stderr)
    print(f"Stock Analysis Pipeline — {date}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Phase 1
    data = phase1_collect(date)

    # Save Phase 1 data to run dir for later use with --apply
    run_dir = get_run_dir(date)
    phase1_file = run_dir / "phase1.json"
    # Strip learnings text (too large) before saving
    save_data = {k: v for k, v in data.items() if k != "learnings"}
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
    """Try to extract JSON from LLM response text.

    Handles cases where JSON is wrapped in ```json blocks or
    mixed with explanatory text.
    """
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract from ```json blocks
    import re
    json_blocks = re.findall(r"```json\s*(.*?)```", text, re.DOTALL)
    for block in json_blocks:
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue

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
