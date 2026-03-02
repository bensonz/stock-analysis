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
"""

import json
import os
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
    close_position,
    open_position,
    update_position,
    regenerate_positions_json,
    save_daily_summary,
)
from report_generator import generate_watchlist_json, generate_report_md
from validator import validate_data, validate_output

# Directories
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LLM_PROMPT_START = "=== LLM_PROMPT_START ==="
LLM_PROMPT_END = "=== LLM_PROMPT_END ==="


def phase1_collect(date: str) -> dict:
    """Phase 1: Collect all data. Pure Python, no LLM.

    Runs independent tasks in parallel:
      - Strategy pool fetch (fast, ~5s) runs first since enrichment depends on it
      - Then enrichment, market, positions, and watchlists run concurrently
    """
    log = {"phase": "collect", "start": time.time(), "errors": []}
    data = {"date": date}

    print("Phase 1: Collecting data...", file=sys.stderr)

    # Step 1: Strategy pool (must complete before enrichment can start)
    print("  [1/5] Fetching strategy pool...", file=sys.stderr)
    try:
        data["strategy_pool"] = fetch_strategy_pool()
        save_crawl_data(date, data["strategy_pool"])
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
        save_market_data(date, result)
        return "market", result

    def _prices():
        print("  [4/5] Fetching position prices...", file=sys.stderr)
        result = fetch_position_prices(positions)
        save_price_data(date, result)
        print(f"    → {len(positions)} active positions", file=sys.stderr)
        return "position_prices", result

    def _missed():
        print("  [5/5] Fetching missed opportunity prices...", file=sys.stderr)
        result = fetch_missed_opportunity_prices(data["recent_watchlists"])
        return "missed_opportunity_prices", result

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_enrich): "enrich",
            executor.submit(_market): "market",
            executor.submit(_prices): "position_prices",
            executor.submit(_missed): "watchlists",
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

    # Learnings (local file, instant)
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    if learnings_file.exists():
        data["learnings"] = learnings_file.read_text(encoding="utf-8")
    else:
        data["learnings"] = ""

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

    # Build the data payload (strip heavy fields)
    payload = {
        "date": data["date"],
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
                "history": p.get("history", [])[-3:],  # Last 3 history entries
            }
            for p in data.get("positions", [])
        ],
        "position_prices": data.get("position_prices", {}),
        "missed_opportunity_prices": data.get("missed_opportunity_prices", []),
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

    # 3. Ensure positions.json is in sync
    regenerate_positions_json()

    # 4. Generate report and watchlist
    try:
        generate_watchlist_json(date, data, decisions)
        log["actions"].append("Generated watchlist")
    except Exception as e:
        log["actions"].append(f"ERROR watchlist: {e}")

    try:
        generate_report_md(date, data, decisions)
        log["actions"].append("Generated report")
    except Exception as e:
        log["actions"].append(f"ERROR report: {e}")

    # 5. Save daily summary
    try:
        # Build portfolio stats
        active = load_active_positions()
        stats = {}
        if active:
            pnls = []
            for p in active:
                prices = data.get("position_prices", {})
                price_info = prices.get(p["code"], {})
                price = price_info.get("price", p["entryPrice"])
                pnl = round((price - p["entryPrice"]) / p["entryPrice"] * 100, 2)
                pnls.append(pnl)
            stats = {
                "totalPositions": len(active),
                "avgPnl": round(sum(pnls) / len(pnls), 2) if pnls else 0,
                "winners": sum(1 for x in pnls if x > 0),
                "losers": sum(1 for x in pnls if x < 0),
                "totalPnl": round(sum(pnls), 2),
            }

        save_daily_summary(
            date,
            daily_actions,
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

    log["end"] = time.time()
    log["duration_sec"] = round(log["end"] - log["start"], 1)
    return log


def phase4_validate_and_log(date: str, logs: list[dict]) -> list[str]:
    """Phase 4: Validate output and save run log."""
    errors = validate_output(date)

    # Save run log
    run_log = {
        "date": date,
        "runs": logs,
        "validation_errors": errors,
        "summary": {
            "totalPhases": len(logs),
            "totalDurationSec": sum(l.get("duration_sec", 0) for l in logs),
        },
    }
    log_file = LOGS_DIR / f"{date}.json"
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

    if "--validate" in args:
        errors = validate_output(date)
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
            print("Usage: --apply FILE", file=sys.stderr)
            sys.exit(1)
        response_file = Path(args[idx + 1])
        if not response_file.exists():
            print(f"File not found: {response_file}", file=sys.stderr)
            sys.exit(1)

        # Load LLM response
        response_text = response_file.read_text(encoding="utf-8")
        # Try to extract JSON from response
        decisions = _parse_llm_response(response_text)
        if not decisions:
            print("Could not parse LLM response as JSON", file=sys.stderr)
            sys.exit(1)

        # Load Phase 1 data
        data_file = DATA_DIR / f"phase1_{date}.json"
        if data_file.exists():
            data = json.loads(data_file.read_text(encoding="utf-8"))
        else:
            print("Warning: No Phase 1 data found, running Phase 1 first...", file=sys.stderr)
            data = phase1_collect(date)

        print(f"\nPhase 3: Applying decisions...", file=sys.stderr)
        log3 = phase3_apply(date, decisions, data)
        print(f"  Actions: {log3['actions']}", file=sys.stderr)

        print(f"\nPhase 4: Validating...", file=sys.stderr)
        errors = phase4_validate_and_log(date, [log3])
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

    # Save Phase 1 data for later use with --apply
    phase1_file = DATA_DIR / f"phase1_{date}.json"
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
