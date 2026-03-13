#!/usr/bin/env python3
"""
Rule: Volume confirmation — flag active positions when latest daily volume is below MAVOL30.
Created: 2026-03-12
Source: User request after adding richer daily volume data.

Interpretation:
  Breakouts and trend continuation setups should usually have at least average volume.
  If volume today is below MAVOL30, momentum confirmation is weaker.

Data contract:
  Expects activePositions entries to contain:
    - volume
    - mavol30
    - volumeBelowMavol30 (optional precomputed bool)
"""
import json
import sys


data = json.load(sys.stdin)
violations = []

for position in data.get("activePositions", []):
    volume = position.get("volume")
    mavol30 = position.get("mavol30")
    if volume is None or mavol30 in (None, 0):
        continue

    below = position.get("volumeBelowMavol30")
    if below is None:
        below = volume < mavol30

    if not below:
        continue

    ratio_pct = round(volume / mavol30 * 100, 1) if mavol30 else None
    violations.append({
        "code": position.get("code"),
        "name": position.get("name", ""),
        "rule": "volume_below_mavol30",
        "volume": volume,
        "mavol30": round(mavol30, 2),
        "ratio_pct": ratio_pct,
        "suggestion": (
            f"Latest volume {volume:,} is below MAVOL30 {mavol30:,.0f}"
            f" ({ratio_pct:.1f}% of average). Momentum confirmation is weak; "
            "avoid adding and review closely if price action stalls or reverses."
        ),
    })

result = {
    "rule": "volume_below_mavol30",
    "status": "ok" if not violations else "violations",
    "violations": violations,
}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
