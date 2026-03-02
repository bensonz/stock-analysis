#!/usr/bin/env python3
"""
Position Manager — State machine for tracking stock positions.

Handles: load, open, close, update positions and regenerate positions.json.
All mutations go through this module to ensure positions.json stays in sync.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
TRACKING_DIR = PROJECT_ROOT / "tracking"
CLOSED_DIR = TRACKING_DIR / "closed"
DAILY_DIR = TRACKING_DIR / "daily"
POSITIONS_FILE = TRACKING_DIR / "positions.json"

CLOSED_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_active_positions() -> list[dict]:
    """Read all tracking/*.json files (skip positions.json, README.md).
    Returns list of position dicts for active positions only.
    """
    positions = []
    for f in sorted(TRACKING_DIR.glob("*.json")):
        if f.name == "positions.json":
            continue
        try:
            pos = _read_json(f)
            if pos.get("status") == "active":
                positions.append(pos)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Warning: skipping {f.name}: {e}")
    return positions


def load_all_tracking_files() -> list[dict]:
    """Read ALL tracking/*.json files including non-active ones."""
    positions = []
    for f in sorted(TRACKING_DIR.glob("*.json")):
        if f.name == "positions.json":
            continue
        try:
            positions.append(_read_json(f))
        except (json.JSONDecodeError, KeyError):
            pass
    return positions


def close_position(
    code: str,
    reason: str,
    exit_price: float,
    lesson: str = "",
    date: Optional[str] = None,
) -> dict:
    """Close a position: update fields and move to tracking/closed/.

    Args:
        code: Stock code (e.g., "600988")
        reason: Exit reason (target_hit, stop_hit, thesis_invalid, time_decay, etc.)
        exit_price: Price at exit
        lesson: Lesson learned from this trade
        date: Exit date (defaults to today)

    Returns:
        The updated position dict.
    """
    pos_file = TRACKING_DIR / f"{code}.json"
    if not pos_file.exists():
        raise FileNotFoundError(f"Position file not found: {pos_file}")

    pos = _read_json(pos_file)
    exit_date = date or datetime.now().strftime("%Y-%m-%d")

    pos["status"] = "closed"
    pos["exitDate"] = exit_date
    pos["exitPrice"] = exit_price
    pos["exitReason"] = reason
    pos["returnPct"] = round((exit_price - pos["entryPrice"]) / pos["entryPrice"] * 100, 2)
    entry_dt = datetime.strptime(pos["entryDate"], "%Y-%m-%d")
    exit_dt = datetime.strptime(exit_date, "%Y-%m-%d")
    pos["holdingDays"] = (exit_dt - entry_dt).days
    pos["lessonLearned"] = lesson
    pos["updatedAt"] = _now_iso()

    # Add SELL to history
    pos.setdefault("history", []).append({
        "date": exit_date,
        "price": exit_price,
        "change_pct": pos["returnPct"],
        "action": "SELL",
        "note": f"{reason}: {lesson}" if lesson else reason,
    })

    # Write to closed dir and remove from tracking root
    _write_json(CLOSED_DIR / f"{code}.json", pos)
    pos_file.unlink()

    regenerate_positions_json()
    return pos


def open_position(data: dict) -> dict:
    """Create a new position file in tracking/.

    Args:
        data: Must contain at minimum: code, name, entryPrice, targetPrice, stopLoss, thesis.
              Optional: rating, rps120, sector, catalysts, confidence.

    Returns:
        The created position dict.
    """
    code = data["code"].split(".")[0]  # Strip exchange suffix
    today = datetime.now().strftime("%Y-%m-%d")

    pos = {
        "code": code,
        "name": data["name"],
        "status": "active",
        "thesis": data.get("thesis", ""),
        "entryDate": data.get("entryDate", today),
        "entryPrice": data["entryPrice"],
        "targetPrice": data["targetPrice"],
        "stopLoss": data["stopLoss"],
        "currentStop": data.get("currentStop", data["stopLoss"]),
        "rating": data.get("rating", 2),
        "rps120": data.get("rps120"),
        "sector": data.get("sector", ""),
        "catalysts": data.get("catalysts", []),
        "sourceWatchlist": data.get("sourceWatchlist", today),
        "history": [
            {
                "date": data.get("entryDate", today),
                "price": data["entryPrice"],
                "change_pct": 0,
                "action": "OPEN",
                "note": data.get("note", f"开仓 {data['name']}"),
            }
        ],
        "exitDate": None,
        "exitPrice": None,
        "exitReason": None,
        "returnPct": None,
        "holdingDays": None,
        "lessonLearned": None,
        "createdAt": _now_iso(),
        "updatedAt": _now_iso(),
        "trackerVersion": "2.0",
    }

    _write_json(TRACKING_DIR / f"{code}.json", pos)
    regenerate_positions_json()
    return pos


def update_position(code: str, updates: dict) -> dict:
    """Update an existing position's fields and append to history.

    Args:
        code: Stock code
        updates: Dict with fields to update. Special keys:
            - "history_entry": dict to append to history
            - "new_stop": float to update currentStop (only raises, never lowers)
            - Other keys update the position directly.

    Returns:
        The updated position dict.
    """
    pos_file = TRACKING_DIR / f"{code}.json"
    if not pos_file.exists():
        raise FileNotFoundError(f"Position file not found: {pos_file}")

    pos = _read_json(pos_file)

    # Handle history entry
    history_entry = updates.pop("history_entry", None)
    if history_entry:
        pos.setdefault("history", []).append(history_entry)

    # Handle stop raise (never lower)
    new_stop = updates.pop("new_stop", None)
    if new_stop is not None:
        current = pos.get("currentStop", pos.get("stopLoss", 0))
        if new_stop > current:
            pos["currentStop"] = new_stop

    # Apply remaining updates
    for key, value in updates.items():
        if key not in ("code", "history"):  # Don't overwrite code or full history
            pos[key] = value

    pos["updatedAt"] = _now_iso()
    _write_json(pos_file, pos)
    regenerate_positions_json()
    return pos


def regenerate_positions_json() -> dict:
    """Scan tracking/*.json, build positions.json from active positions.
    ALWAYS called after any mutation.

    Returns:
        The positions.json content.
    """
    active = load_active_positions()

    positions_data = {
        "lastUpdated": _now_iso(),
        "activePositions": [
            {
                "code": p["code"],
                "name": p["name"],
                "entryDate": p["entryDate"],
                "entryPrice": p["entryPrice"],
                "currentPrice": p.get("currentPrice", p["entryPrice"]),
                "pnl_pct": p.get("pnl_pct", 0.0),
                "stopLoss": p["stopLoss"],
                "currentStop": p.get("currentStop", p["stopLoss"]),
                "targetPrice": p["targetPrice"],
                "status": "active",
                "sector": p.get("sector", ""),
            }
            for p in active
        ],
    }

    _write_json(POSITIONS_FILE, positions_data)
    return positions_data


def save_daily_summary(date: str, actions: list[dict], **extra) -> Path:
    """Write tracking/daily/YYYY-MM-DD.json.

    Args:
        date: Date string "YYYY-MM-DD"
        actions: List of action dicts (code, name, action, price, pnl_pct, note)
        **extra: Additional top-level keys (closedPositionNote, newPositions,
                 portfolioStats, marketContext)

    Returns:
        Path to written file.
    """
    summary = {"date": date, "actions": actions, **extra}
    out = DAILY_DIR / f"{date}.json"
    _write_json(out, summary)
    return out


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python position_manager.py list       # List active positions")
        print("  python position_manager.py regen      # Regenerate positions.json")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        for p in load_active_positions():
            print(f"  {p['code']} {p['name']} entry={p['entryPrice']} stop={p.get('currentStop')}")
    elif cmd == "regen":
        result = regenerate_positions_json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Unknown command: {cmd}")
