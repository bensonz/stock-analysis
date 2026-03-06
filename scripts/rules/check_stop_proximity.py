#!/usr/bin/env python3
"""
Rule: Stop proximity — flag positions within 3% of stop loss.
Created: 2026-03-03
Source: Observation from 2026-03-03 crash (扬杰科技, 芯碁微装 both sold near stops)
Last modified: 2026-03-06
Track record: 3 fires, 3 correct, 0 incorrect
  - 300373 扬杰科技 03-03: 1.8% from stop → sold @79.0 (-8.21%) ✅ (proactive stop, correct)
  - 688630 芯碁微装 03-03: 2.1% from stop → sold @186.6 (-7.50%) ✅ (proactive stop, correct)
  - 600096 云天化 03-05: 2.7% from stop → HELD, recovered to -3.09% by 03-06 ⚠️ (borderline, still risky)

Evolution notes (2026-03-06):
  - Added severity tiers: CRITICAL (<2%), WARNING (<3%), WATCH (<5%)
  - For CRITICAL: strong recommendation to proactively stop-loss even if price
    hasn't technically hit stop. Gap risk (opening gap through stop) is real.
  - For WARNING: prepare sell order, tighten mental stop
  - For WATCH: monitor closely, no action needed yet
"""
import json
import sys

data = json.load(sys.stdin)
violations = []

for p in data.get("activePositions", []):
    price = p.get("currentPrice", 0)
    stop = p.get("currentStop") or p.get("stopLoss", 0)

    if price <= 0 or stop <= 0:
        continue

    distance_pct = (price - stop) / price * 100

    if distance_pct < 5:
        if distance_pct < 2:
            severity = "CRITICAL"
            suggestion = (
                f"🔴 CRITICAL — only {distance_pct:.1f}% above stop! "
                f"Gap risk is real (03-03 lesson: 扬杰科技 gapped to -8.37%). "
                f"Strongly recommend proactive stop-loss NOW. Don't wait for exact trigger."
            )
        elif distance_pct < 3:
            severity = "WARNING"
            suggestion = (
                f"🟡 WARNING — only {distance_pct:.1f}% above stop. "
                f"Prepare sell order. If market opens weak tomorrow, may gap through stop."
            )
        else:
            severity = "WATCH"
            suggestion = (
                f"🟠 WATCH — {distance_pct:.1f}% above stop. "
                f"Monitor closely. No immediate action but be ready."
            )

        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "stop_proximity",
            "severity": severity,
            "currentPrice": price,
            "stopLoss": stop,
            "distance_pct": round(distance_pct, 2),
            "suggestion": suggestion,
        })

result = {
    "rule": "stop_proximity",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
