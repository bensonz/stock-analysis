#!/usr/bin/env python3
"""
Rule: Stop proximity — flag positions within 3% of stop loss.
Created: 2026-03-03
Source: Observation from 2026-03-03 crash (扬杰科技, 芯碁微装 both sold near stops)
Last modified: 2026-03-03
Track record: 0 fires, 0 correct, 0 incorrect
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

    if distance_pct < 3:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "stop_proximity",
            "currentPrice": price,
            "stopLoss": stop,
            "distance_pct": round(distance_pct, 2),
            "suggestion": f"WARNING — only {distance_pct:.1f}% above stop. Prepare to sell or widen stop with justification.",
        })

result = {
    "rule": "stop_proximity",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
