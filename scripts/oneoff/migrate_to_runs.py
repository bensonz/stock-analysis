#!/usr/bin/env python3
"""
migrate_to_runs.py — Move historical flat files into runs/YYYY-MM-DD/ structure.

Copies (not moves) files from old locations into the new runs/ layout.
Missing files for a given date are expected and skipped silently.

Usage:
    python3 scripts/migrate_to_runs.py             # Dry run (show what would happen)
    python3 scripts/migrate_to_runs.py --execute    # Actually copy files
"""

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"

# Old source directories
OLD_CRAWL = PROJECT_ROOT / "data" / "crawl"
OLD_MARKET = PROJECT_ROOT / "data" / "market"
OLD_PRICES = PROJECT_ROOT / "data" / "prices"
OLD_PHASE1 = PROJECT_ROOT / "data"  # phase1_YYYY-MM-DD.json
OLD_WATCHLIST = PROJECT_ROOT / "watchlist"
OLD_REPORTS = PROJECT_ROOT / "reports"
OLD_DAILY = PROJECT_ROOT / "tracking" / "daily"
OLD_LOGS = PROJECT_ROOT / "logs"


def collect_all_dates() -> list[str]:
    """Find all unique dates across all old directories."""
    dates = set()
    for d in [OLD_CRAWL, OLD_MARKET, OLD_PRICES, OLD_WATCHLIST, OLD_REPORTS, OLD_DAILY, OLD_LOGS]:
        if d.exists():
            for f in d.iterdir():
                stem = f.stem
                # Validate date format
                if len(stem) == 10 and stem[4] == "-" and stem[7] == "-":
                    dates.add(stem)
    # Also check phase1 files
    for f in OLD_PHASE1.glob("phase1_*.json"):
        stem = f.stem.replace("phase1_", "")
        if len(stem) == 10:
            dates.add(stem)
    return sorted(dates)


def migrate_date(date: str, dry_run: bool = True) -> dict:
    """Migrate all files for a single date into runs/<date>/.

    Returns a summary dict of what was copied.
    """
    run_dir = RUNS_DIR / date
    input_dir = run_dir / "input"
    output_dir = run_dir / "output"

    actions = {"date": date, "copied": [], "skipped": []}

    # Mapping: (source_path, dest_path)
    file_map = [
        # Input files
        (OLD_CRAWL / f"{date}.json", input_dir / "crawl.json"),
        (OLD_MARKET / f"{date}.json", input_dir / "market.json"),
        (OLD_PRICES / f"{date}.json", input_dir / "prices.json"),
        (OLD_PHASE1 / f"phase1_{date}.json", run_dir / "phase1.json"),

        # Output files
        (OLD_WATCHLIST / f"{date}.json", output_dir / "watchlist.json"),
        (OLD_REPORTS / f"{date}.md", output_dir / "report.md"),
        (OLD_DAILY / f"{date}.json", output_dir / "daily_summary.json"),

        # Log
        (OLD_LOGS / f"{date}.json", run_dir / "log.json"),
    ]

    for src, dst in file_map:
        if src.exists():
            if dry_run:
                actions["copied"].append(f"{src.relative_to(PROJECT_ROOT)} → {dst.relative_to(PROJECT_ROOT)}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                actions["copied"].append(str(dst.relative_to(PROJECT_ROOT)))
        else:
            actions["skipped"].append(str(src.relative_to(PROJECT_ROOT)))

    return actions


def main():
    dry_run = "--execute" not in sys.argv
    dates = collect_all_dates()

    if not dates:
        print("No historical data found to migrate.")
        return

    mode = "DRY RUN" if dry_run else "EXECUTING"
    print(f"{'=' * 60}")
    print(f"Migration to runs/ structure — {mode}")
    print(f"Found {len(dates)} dates: {dates[0]} → {dates[-1]}")
    print(f"{'=' * 60}\n")

    total_copied = 0
    total_skipped = 0

    for date in dates:
        result = migrate_date(date, dry_run=dry_run)
        copied = len(result["copied"])
        skipped = len(result["skipped"])
        total_copied += copied
        total_skipped += skipped

        icon = "✓" if copied > 0 else "○"
        print(f"  {icon} {date}: {copied} copied, {skipped} missing")

        if dry_run and result["copied"]:
            for item in result["copied"]:
                print(f"      {item}")

    print(f"\n{'=' * 60}")
    print(f"Total: {total_copied} files {'would be ' if dry_run else ''}copied, {total_skipped} missing (expected)")
    if dry_run:
        print(f"\nRun with --execute to actually copy files:")
        print(f"  python3 scripts/migrate_to_runs.py --execute")
    else:
        print(f"\n✓ Migration complete. Old files left in place (safe to delete later).")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
