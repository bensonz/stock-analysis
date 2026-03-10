#!/usr/bin/env python3
"""
One-time migration: parse existing LEARNINGS.md and historical run responses
into the hypothesis system.

Strategy:
1. Replay all new_learnings from runs/*/response.json (chronological)
2. Seed validated hypotheses from ANALYST.md's 5 core rules
3. Show summary

Run: python scripts/migrate_learnings.py [--dry-run]
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hypothesis_manager import (
    load_hypotheses, save_hypotheses, create_hypothesis,
    add_evidence, process_learnings, get_all_summary,
    HYPOTHESES_FILE,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"


def seed_core_rules(data: dict) -> int:
    """Seed the V2 core rules as pre-validated hypotheses."""
    rules = [
        {
            "text": "Only buy stocks in sectors trending up (top 30%). Dead sectors = no entries.",
            "type": "rule",
            "tags": ["sector", "entry-filter"],
            "mechanism": "Sector gravity dominates individual stock quality. A mediocre stock in a hot sector beats a great stock in a dead sector.",
            "status": "validated",
        },
        {
            "text": "RPS120 sweet spot 80-92%, extended 92-95% only if sector top 10% or 0 risk factors.",
            "type": "rule",
            "tags": ["entry-filter", "rps", "momentum"],
            "mechanism": "Momentum stocks in the 80-92% RPS range have the best risk/reward. Above 95% is chasing.",
            "status": "validated",
        },
        {
            "text": "Catalysts over valuation. PE 80 with 100% growth > PE 15 with -20% decline.",
            "type": "heuristic",
            "tags": ["entry-filter", "catalyst", "valuation"],
            "mechanism": "For momentum plays, valuation is noise. Catalyst freshness and strength determine short-term returns.",
            "status": "validated",
        },
        {
            "text": "-5% from entry = automatic SELL. No exceptions, no 'thesis still valid' cope.",
            "type": "rule",
            "tags": ["exit-rule", "stop-loss"],
            "mechanism": "Cutting fast preserves capital. V1's -10% stop let losers bleed. The extra 5% saved is real money.",
            "status": "validated",
        },
        {
            "text": "10 trading days with <3% gain = SELL. Time stop, no exceptions.",
            "type": "rule",
            "tags": ["exit-rule", "time-stop"],
            "mechanism": "If the catalyst hasn't moved the stock in 10 days, timing is wrong. Can always re-enter.",
            "status": "validated",
        },
        {
            "text": "IV Rank <15% = reduce new position sizing by 50%. Market is complacent.",
            "type": "signal",
            "tags": ["entry-filter", "iv-sentiment", "position-sizing"],
            "mechanism": "Low IV = market complacency → vol expansion imminent → sharp drawdowns in extended positions.",
            "status": "hypothesis",
        },
        {
            "text": "Breadth <0.5:1 (70%+ stocks falling) = no new entries regardless of setup quality.",
            "type": "signal",
            "tags": ["entry-filter", "market-regime", "breadth"],
            "mechanism": "When most stocks fall, even strong setups get dragged down by selling pressure.",
            "status": "hypothesis",
        },
        {
            "text": "Position sector goes cold (bottom 30% for 3+ days) = SELL regardless of individual stock performance.",
            "type": "rule",
            "tags": ["exit-rule", "sector"],
            "mechanism": "Sector gravity always wins. Individual stock quality cannot overcome persistent sector headwinds.",
            "status": "hypothesis",
        },
    ]

    count = 0
    for r in rules:
        create_hypothesis(
            data,
            text=r["text"],
            h_type=r["type"],
            tags=r["tags"],
            mechanism=r["mechanism"],
            status=r["status"],
            initial_evidence={"type": "supporting", "detail": "Seeded from ANALYST.md V2 core rules", "date": "2026-03-06"},
        )
        count += 1

    return count


def replay_historical_runs(data: dict) -> tuple[int, int]:
    """Replay all new_learnings from historical runs."""
    total_learnings = 0
    total_runs = 0

    if not RUNS_DIR.exists():
        return 0, 0

    for run_dir in sorted(RUNS_DIR.iterdir()):
        response_file = run_dir / "response.json"
        if not response_file.exists():
            continue
        try:
            response = json.loads(response_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        learnings = response.get("new_learnings", [])
        if not learnings:
            continue

        run_date = run_dir.name
        actions = process_learnings(data, learnings, run_date=run_date)
        total_learnings += len(learnings)
        total_runs += 1

        if actions:
            print(f"  {run_date}: {len(actions)} actions from {len(learnings)} learnings")

    return total_runs, total_learnings


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("  LEARNINGS.md → Hypothesis System Migration")
    print("=" * 60)

    data = {"version": 2, "lastUpdated": str(date.today()), "hypotheses": []}

    # Step 1: Seed core rules
    print("\n1. Seeding V2 core rules...")
    n_rules = seed_core_rules(data)
    print(f"   Created {n_rules} core rule hypotheses")

    # Step 2: Replay historical runs
    print("\n2. Replaying historical run learnings...")
    n_runs, n_learnings = replay_historical_runs(data)
    print(f"   Replayed {n_learnings} learnings from {n_runs} runs")

    # Summary
    print("\n3. Summary:")
    by_status = {}
    for h in data["hypotheses"]:
        by_status[h["status"]] = by_status.get(h["status"], 0) + 1
    print(f"   Total hypotheses: {len(data['hypotheses'])}")
    for s, c in sorted(by_status.items()):
        print(f"     {s}: {c}")

    if dry_run:
        print("\n[DRY RUN] Would save to:", HYPOTHESES_FILE)
        print("\nFull dashboard:")
        print(get_all_summary(data))
    else:
        save_hypotheses(data)
        print(f"\n   Saved to: {HYPOTHESES_FILE}")
        print("\nFull dashboard:")
        print(get_all_summary(data))


if __name__ == "__main__":
    main()
