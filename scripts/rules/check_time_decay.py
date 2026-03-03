#!/usr/bin/env python3
"""
Rule: Time decay — flag positions held >20 trading days with <5% gain.
Created: 2026-03-03
Source: LEARNINGS #1 (time_decay), #18 (catalyst exception), #19 (commodity 30d)
Last modified: 2026-03-03
Track record: 0 fires, 0 correct, 0 incorrect
"""
import json
import sys
from datetime import datetime, date

data = json.load(sys.stdin)
today = date.today()
violations = []

for p in data.get("activePositions", []):
    entry = datetime.strptime(p["entryDate"], "%Y-%m-%d").date()
    # Approximate trading days (weekdays only)
    total_days = (today - entry).days
    trading_days = total_days * 5 // 7

    pnl = p.get("pnl_pct", 0)
    sector = p.get("sector", "").lower()

    # Commodity stocks get 30 day grace (LEARNINGS #19)
    threshold = 30 if any(k in sector for k in ["化工", "黄金", "有色", "煤炭", "石油"]) else 20

    if trading_days > threshold and pnl < 5:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "time_decay",
            "trading_days": trading_days,
            "threshold": threshold,
            "pnl_pct": pnl,
            "suggestion": f"SELL — held {trading_days} trading days with only {pnl:.1f}% gain (threshold: {threshold}d / 5%)",
        })

result = {
    "rule": "time_decay",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
