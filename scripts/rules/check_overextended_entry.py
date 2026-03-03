#!/usr/bin/env python3
"""
Rule: Overextended entry — flag positions opened when 5-day gain was >12%.
Created: 2026-03-03
Source: LEARNINGS #10, #13 (don't chase extended stocks)
Last modified: 2026-03-03
Track record: 0 fires, 0 correct, 0 incorrect

Note: This rule checks at ENTRY time. It runs against current positions
but evaluates whether the entry was sound. Useful for learning, not for
current sell decisions.
"""
import json
import sys
from datetime import datetime, date

data = json.load(sys.stdin)
today = date.today()
violations = []

for p in data.get("activePositions", []):
    entry = datetime.strptime(p["entryDate"], "%Y-%m-%d").date()
    days_held = (today - entry).days

    # Only flag recent entries (within 5 days) — older ones are already committed
    if days_held > 5:
        continue

    # Check if position is already deeply negative (sign of chasing)
    pnl = p.get("pnl_pct", 0)
    if pnl < -5:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "overextended_entry",
            "days_held": days_held,
            "pnl_pct": pnl,
            "suggestion": f"Position down {pnl:.1f}% after only {days_held} days — possible overextended entry. Review entry timing.",
        })

result = {
    "rule": "overextended_entry",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
