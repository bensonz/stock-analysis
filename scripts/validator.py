#!/usr/bin/env python3
"""
Validator — Consistency checks for the pipeline.

- validate_data()   — Check Phase 1 output completeness
- validate_output() — Check all output files exist and are consistent
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TRACKING_DIR = PROJECT_ROOT / "tracking"
WATCHLIST_DIR = PROJECT_ROOT / "watchlist"
REPORTS_DIR = PROJECT_ROOT / "reports"
DAILY_DIR = TRACKING_DIR / "daily"
POSITIONS_FILE = TRACKING_DIR / "positions.json"


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


def validate_output(date: str) -> list[str]:
    """Check all output files exist and are consistent after pipeline run.

    Checks:
    - positions.json matches tracking/*.json active set
    - No closed positions in tracking/ root
    - watchlist/YYYY-MM-DD.json exists and is valid JSON
    - reports/YYYY-MM-DD.md exists
    - daily summary exists

    Args:
        date: Date string "YYYY-MM-DD"

    Returns:
        List of error strings. Empty means all OK.
    """
    errors = []

    # 1. positions.json matches tracking/*.json
    if POSITIONS_FILE.exists():
        try:
            pos_data = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
            pos_codes = {p["code"] for p in pos_data.get("activePositions", [])}
        except (json.JSONDecodeError, KeyError) as e:
            errors.append(f"CRITICAL: positions.json is invalid: {e}")
            pos_codes = set()

        # Scan tracking/*.json for active positions
        tracking_codes = set()
        for f in TRACKING_DIR.glob("*.json"):
            if f.name == "positions.json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("status") == "active":
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

    # 2. No closed positions in tracking/ root
    for f in TRACKING_DIR.glob("*.json"):
        if f.name == "positions.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") == "closed":
                errors.append(
                    f"WARNING: {f.name} has status 'closed' but is not in closed/"
                )
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. Watchlist exists and is valid JSON
    wl_file = WATCHLIST_DIR / f"{date}.json"
    if wl_file.exists():
        try:
            wl = json.loads(wl_file.read_text(encoding="utf-8"))
            if "recommendations" not in wl:
                errors.append(f"WARNING: watchlist/{date}.json missing 'recommendations' key")
        except json.JSONDecodeError as e:
            errors.append(f"CRITICAL: watchlist/{date}.json is invalid JSON: {e}")
    else:
        errors.append(f"WARNING: watchlist/{date}.json does not exist")

    # 4. Report exists
    report_file = REPORTS_DIR / f"{date}.md"
    if not report_file.exists():
        errors.append(f"WARNING: reports/{date}.md does not exist")

    # 5. Daily summary exists
    daily_file = DAILY_DIR / f"{date}.json"
    if daily_file.exists():
        try:
            json.loads(daily_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"WARNING: daily/{date}.json is invalid JSON: {e}")
    else:
        errors.append(f"INFO: tracking/daily/{date}.json does not exist yet")

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
