#!/usr/bin/env python3
"""
Validator — Consistency checks for the pipeline.

- validate_data()   — Check Phase 1 output completeness
- validate_output() — Check all output files exist and are consistent
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from run_paths import find_run_dir
from tracking_paths import ACTIVE_DIR, POSITIONS_FILE

PROJECT_ROOT = Path(__file__).parent.parent
WATCHLIST_DIR = PROJECT_ROOT / "watchlist"
REPORTS_DIR = PROJECT_ROOT / "reports"


def validate_data(data: dict) -> list[str]:
    """Check Phase 1 data collection output for completeness.

    Args:
        data: The collected data dict from Phase 1.

    Returns:
        List of error/warning strings. Empty means all OK.
    """
    errors = []

    # Strategy pool
    pool = data.get("strategy_pool", {})
    if not pool:
        errors.append("CRITICAL: strategy_pool is missing")
    elif pool.get("error"):
        errors.append(f"WARNING: strategy_pool has error: {pool['error']}")
    elif pool.get("total_stocks", 0) == 0:
        errors.append("WARNING: strategy_pool has 0 stocks")

    # Market data
    market = data.get("market", {})
    if not market:
        errors.append("CRITICAL: market data is missing")
    else:
        if "indices_error" in market:
            errors.append(f"WARNING: indices fetch failed: {market['indices_error']}")
        elif not market.get("indices"):
            errors.append("WARNING: no index data")
        if "breadth_error" in market:
            errors.append(f"WARNING: breadth fetch failed: {market['breadth_error']}")
        if "sectors_error" in market:
            errors.append(f"WARNING: sectors fetch failed: {market['sectors_error']}")

    # Position prices
    positions = data.get("position_prices", {})
    if not positions and data.get("positions_count", 0) > 0:
        errors.append("WARNING: position prices are empty but have active positions")
    for code, price_data in positions.items():
        if isinstance(price_data, dict) and price_data.get("error"):
            errors.append(f"WARNING: price fetch failed for {code}: {price_data['error']}")

    # Learnings
    if not data.get("learnings"):
        errors.append("INFO: LEARNINGS.md is empty or missing")

    return errors


def validate_output(date: str, slot: str | None = None) -> list[str]:
    """Check all output files exist and are consistent after pipeline run.

    Checks:
    - positions.json matches the book/active/*.json active set
    - No closed positions in book/active/
    - watchlist exists and is valid JSON (runs/ then legacy)
    - report exists (runs/ then legacy)
    - daily summary exists (runs/ then legacy)

    Args:
        date: Date string "YYYY-MM-DD"
        slot: Optional run slot ("noon"/"afternoon"). When omitted, the canonical
            run for the date is used (afternoon preferred; legacy layout counts as
            afternoon).

    Returns:
        List of error strings. Empty means all OK.
    """
    errors = []
    run_dir = find_run_dir(date, slot)
    # Fall back to the legacy path when no run dir is found so the downstream
    # legacy fallbacks (watchlist/, reports/) still apply.
    output_dir = (run_dir / "output") if run_dir else (PROJECT_ROOT / "runs" / date / "output")

    # 1. positions.json matches book/active/*.json
    if POSITIONS_FILE.exists():
        try:
            pos_data = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
            pos_codes = {p["code"] for p in pos_data.get("activePositions", [])}
        except (json.JSONDecodeError, KeyError) as e:
            errors.append(f"CRITICAL: positions.json is invalid: {e}")
            pos_codes = set()

        # Scan book/active/*.json for active positions
        tracking_codes = set()
        for f in ACTIVE_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                # a position-shape check of its own, not position_manager's
                # (checks stay independent of the writers they audit)
                if isinstance(data, dict) and data.get("status") == "active":
                    tracking_codes.add(data["code"])
            except (json.JSONDecodeError, KeyError):
                errors.append(f"WARNING: cannot read {f.name}")

        if pos_codes != tracking_codes:
            diff = pos_codes.symmetric_difference(tracking_codes)
            errors.append(
                f"CRITICAL: positions.json mismatch with tracking files. "
                f"Diff: {diff}"
            )
    else:
        errors.append("CRITICAL: positions.json does not exist")

    # 2. No closed positions in book/active/
    for f in ACTIVE_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("status") == "closed":
                errors.append(
                    f"WARNING: {f.name} has status 'closed' but is not in closed/"
                )
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. Watchlist exists and is valid JSON
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

    # 4. Report exists
    report_file = output_dir / "report.md"
    if not report_file.exists():
        report_file = REPORTS_DIR / f"{date}.md"
    if not report_file.exists():
        errors.append(f"WARNING: no report found for {date}")

    # 5. Daily summary exists
    # (the tracking/daily/{date}.json fallback is gone: that directory was
    # empty from the 2026-03-05 runs/ migration until its removal 2026-10-12)
    daily_file = output_dir / "daily_summary.json"
    if daily_file.exists():
        try:
            json.loads(daily_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"WARNING: daily summary is invalid JSON: {e}")
    else:
        errors.append(f"INFO: no daily summary found for {date}")

    return errors


if __name__ == "__main__":
    import sys
    from datetime import datetime

    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    print(f"Validating output for {date}...\n")

    errors = validate_output(date)
    if errors:
        for e in errors:
            print(f"  {e}")
        print(f"\n{len(errors)} issue(s) found.")
    else:
        print("  All checks passed!")
