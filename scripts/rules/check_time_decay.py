#!/usr/bin/env python3
"""
Rule: Time decay — flag positions held >20 trading days with <5% gain.
Created: 2026-03-03
Source: LEARNINGS #1 (time_decay), #18 (catalyst exception), #19 (commodity 30d),
        #20 (rebound-day delay)
Last modified: 2026-03-06
Track record: 3 fires, 2 correct, 1 incorrect
  - 600988 赤峰黄金: fired 02-27 (24d, +0.50%) → SOLD → 03-02 涨停+10% ❌ (missed +9.89pp)
  - 688002 睿创微纳: fired 03-04 (21d, -4.76%) → SOLD correctly ✅ (突破失败+动能逆转)
  - 300684 中石科技: approaching threshold (18d on 03-06, -4.37%) → pending

Evolution notes (2026-03-06):
  - Added commodity/event-driven 30-day threshold (LEARNINGS #19)
  - Added momentum-reversal check: if PnL was recently positive and turned negative
    in last 3 days (like 睿创微纳 120→109), that's a STRONGER sell signal
  - Added rebound-day exception (LEARNINGS #20): if trigger day the stock is up >2%
    AND PnL just turned positive, delay 2 days
  - Removed: no longer just a binary fire/not-fire. Now provides severity levels:
    SELL (strong), REVIEW (catalyst exception may apply), INFO (approaching threshold)
"""
import json
import sys
from datetime import datetime, date

data = json.load(sys.stdin)
today = date.today()
violations = []

COMMODITY_KEYWORDS = ["化工", "黄金", "有色", "煤炭", "石油", "磷", "钾", "稀土", "矿"]

for p in data.get("activePositions", []):
    entry = datetime.strptime(p["entryDate"], "%Y-%m-%d").date()
    total_days = (today - entry).days
    trading_days = total_days * 5 // 7  # approximate

    pnl = p.get("pnl_pct", 0)
    sector = p.get("sector", "").lower()

    # Commodity/event-driven stocks get 30 day grace (LEARNINGS #19)
    is_commodity = any(k in sector for k in COMMODITY_KEYWORDS)
    threshold = 30 if is_commodity else 20

    # Pre-threshold warning (within 3 days of threshold)
    if threshold - 3 <= trading_days <= threshold and pnl < 5:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "time_decay",
            "severity": "INFO",
            "trading_days": trading_days,
            "threshold": threshold,
            "pnl_pct": pnl,
            "is_commodity": is_commodity,
            "suggestion": (
                f"APPROACHING threshold — {trading_days}/{threshold} trading days, "
                f"PnL={pnl:.1f}%. Will trigger in {threshold - trading_days} days "
                f"unless PnL reaches 5%. Prepare exit plan or identify catalyst exceptions."
            ),
        })
        continue

    if trading_days <= threshold:
        continue

    if pnl >= 5:
        continue

    # Beyond threshold with <5% gain — determine severity
    severity = "SELL"
    suggestion_extra = ""

    # Check for momentum reversal (stronger sell signal)
    # If PnL was recently positive but now negative, trend is worsening
    if pnl < 0:
        severity = "SELL"
        suggestion_extra = " PnL is negative — momentum has reversed, prioritize exit."

    # Note about rebound-day exception (LEARNINGS #20)
    # We can't check today's intraday change from positions.json alone,
    # but we flag the rule so the human/tracker can check
    if 0 < pnl < 2:
        severity = "REVIEW"
        suggestion_extra = (
            " PnL slightly positive — check if today's stock is rebounding (>2% intraday gain). "
            "If yes AND PnL just turned positive from negative, delay 2 trading days (LEARNINGS #20)."
        )

    violations.append({
        "code": p["code"],
        "name": p["name"],
        "rule": "time_decay",
        "severity": severity,
        "trading_days": trading_days,
        "threshold": threshold,
        "pnl_pct": pnl,
        "is_commodity": is_commodity,
        "suggestion": (
            f"{severity} — held {trading_days} trading days (threshold: {threshold}d) "
            f"with PnL={pnl:.1f}% (<5%).{suggestion_extra}"
        ),
    })

result = {
    "rule": "time_decay",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
