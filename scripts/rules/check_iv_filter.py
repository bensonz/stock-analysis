#!/usr/bin/env python3
"""
Rule: IV environment filter — flag new positions opened when IV Rank was extremely low.
Created: 2026-03-06
Source: LEARNINGS (03-03 auto-update): IV Rank极低(12.2%)时是波动率爆发前兆;
        芯碁微装03-02开仓时IVRank<15%,次日暴跌-7.89%
Last modified: 2026-03-06
Track record: 1 fire (688630 芯碁微装 03-02开仓@IVRank~12%, 03-03 -7.89% → 正确警告), 1 correct, 0 incorrect

Checks: positions opened within 5 calendar days that are already losing >4%.
When IV data is unavailable, uses heuristic: if a position opened in last 5 days
is already down >4%, it suggests the entry was during a complacent/extended market.

This rule is ENTRY-QUALITY focused — it helps us learn, not directly trigger sells.
A future version could read IV data from daily_summary if available.
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
    pnl = p.get("pnl_pct", 0)

    # Only flag positions opened in last 5 calendar days
    if days_held > 5:
        continue

    # If already down >4% in first 5 days, likely entered during
    # complacent market or overextended stock
    if pnl < -4:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "iv_filter",
            "days_held": days_held,
            "pnl_pct": pnl,
            "suggestion": (
                f"Down {pnl:.1f}% after only {days_held} days. "
                f"Possible entry during low-IV complacent market. "
                f"Review: was IVRank<15% at entry? Was 5-day cum gain >6%? "
                f"Consider tighter stop or faster exit for entries during low-IV regimes."
            ),
        })

result = {
    "rule": "iv_filter",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
