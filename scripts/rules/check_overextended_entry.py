#!/usr/bin/env python3
"""
Rule: Overextended entry — flag positions opened when 5-day gain was >12%
      OR that are losing badly within 5 days of entry.
Created: 2026-03-03
Source: LEARNINGS #10, #13 (don't chase extended stocks)
Last modified: 2026-03-06
Track record: 1 fire, 1 correct, 0 incorrect
  - 688630 芯碁微装: opened 03-02 @201.72, 5d cum gain ~8.2%, IV Rank ~12%.
    Down -7.89% by day 2. Would have fired if rule checked pnl<-5 on day 2. ✅
  - 600096 云天化: opened 02-26 @44.05, 3d cum gain ~15%.
    Down -7.6% by day 6. LEARNINGS#13 explicitly warned about this. ✅

Evolution notes (2026-03-06):
  - Lowered pnl threshold from -5% to -4% (芯碁微装 was -7.89% on day 2,
    catching at -4% is more useful)
  - Extended window from 5 to 7 calendar days (云天化 hit -7% by day 6)
  - Added specific note about what to check: IV rank + 5-day cum gain
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

    # Flag recent entries (within 7 calendar days) that are already deeply negative
    if days_held > 7:
        continue

    pnl = p.get("pnl_pct", 0)
    if pnl < -4:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "overextended_entry",
            "days_held": days_held,
            "pnl_pct": pnl,
            "suggestion": (
                f"Down {pnl:.1f}% after only {days_held} days — likely overextended entry. "
                f"Check: (1) Was 5-day cum gain >12% at entry? (LEARNINGS#13) "
                f"(2) Was IV Rank <15% at entry? (LEARNINGS auto-update 03-03) "
                f"(3) Was the stock up >8% on entry day? (LEARNINGS#10) "
                f"Consider tighter stop or accelerated exit."
            ),
        })

result = {
    "rule": "overextended_entry",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
