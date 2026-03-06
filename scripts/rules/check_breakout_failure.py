#!/usr/bin/env python3
"""
Rule: Breakout failure detection — flag when a position's PnL swings from
      significantly positive to negative within a short period.
Created: 2026-03-06
Source: 688002 睿创微纳 — broke ¥120 on 03-02 (+4.75%), crashed to ¥109 by 03-04 (-4.76%).
        A 9.5pp swing in 2 days after "breaking out" is a clear failed breakout.
        LEARNINGS auto-update 03-04: "突破关键阻力位后未能守住是卖出信号"
Last modified: 2026-03-06
Track record: 1 fire, 1 correct, 0 incorrect
  - 688002 睿创微纳: PnL +4.75% → -4.76% in 2 days (9.5pp swing). Sold correctly. ✅

Detection method:
  Since we only have current PnL (not historical PnL timeline), we use a proxy:
  - Position was positive at some point (entry was at reasonable price)
  - Now PnL is significantly negative (< -3%)
  - Position is held > 10 days (had time to appreciate)
  This catches the "was working, now failing" pattern.

Limitation: Ideally we'd read the position's history[] array to check peak PnL,
but that requires loading individual position files. For now, use heuristic.
"""
import json
import sys
from datetime import datetime, date

data = json.load(sys.stdin)
today = date.today()
violations = []

for p in data.get("activePositions", []):
    entry = datetime.strptime(p["entryDate"], "%Y-%m-%d").date()
    total_days = (today - entry).days
    trading_days = total_days * 5 // 7

    pnl = p.get("pnl_pct", 0)

    # Look for positions held >10 trading days that are now negative
    # These had time to develop but failed
    if trading_days >= 10 and pnl < -3:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "breakout_failure",
            "trading_days": trading_days,
            "pnl_pct": pnl,
            "suggestion": (
                f"Held {trading_days} trading days but PnL={pnl:.1f}%. "
                f"If this position was previously profitable (check history[]), "
                f"this is a potential breakout failure / trend reversal. "
                f"Review: Did the stock recently break a key level then fail to hold? "
                f"Consider accelerating exit — don't wait for time_decay."
            ),
        })

result = {
    "rule": "breakout_failure",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
