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
PORTFOLIO_CONFIG_FILE = TRACKING_DIR / "portfolio_config.json"

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


def load_portfolio_config() -> dict:
    """Read tracking/portfolio_config.json."""
    if PORTFOLIO_CONFIG_FILE.exists():
        return _read_json(PORTFOLIO_CONFIG_FILE)
    return {
        "starting_capital": 1000000,
        "max_position_pct": 10,
        "max_positions": 10,
    }


def compute_realized_pnl() -> float:
    """Scan tracking/closed/*.json, compute total realized P&L in dollars."""
    config = load_portfolio_config()
    starting = config["starting_capital"]
    max_pct = config["max_position_pct"]
    realized = 0.0
    for f in CLOSED_DIR.glob("*.json"):
        try:
            p = _read_json(f)
            entry = p.get("entryPrice", 0)
            exit_p = p.get("exitPrice", 0)
            if not entry or not exit_p:
                continue
            shares = p.get("shares")
            if not shares:
                raw = int((starting * max_pct / 100) // entry)
                code = str(p.get("code", "")).split(".")[0]
                lot = 200 if code.startswith("688") else 100
                shares = (raw // lot) * lot or lot
            realized += (exit_p - entry) * shares
        except Exception:
            pass
    return round(realized, 2)


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
              Optional: rating, rps120, sector, catalysts, confidence, allocation_pct.

    Returns:
        The created position dict.
    """
    code = data["code"].split(".")[0]  # Strip exchange suffix
    today = datetime.now().strftime("%Y-%m-%d")
    entry_price = data["entryPrice"]

    # Compute position sizing
    config = load_portfolio_config()
    alloc_pct = data.get("allocation_pct") or config["max_position_pct"]
    capital = config["starting_capital"] * alloc_pct / 100
    shares = int(capital // entry_price)

    # A-share lot size rules:
    # - 科创板 (688xxx): min 200 shares, must be multiples of 200
    # - All others: min 100 shares, must be multiples of 100
    if code.startswith("688"):
        lot_size = 200
    else:
        lot_size = 100
    shares = (shares // lot_size) * lot_size
    if shares < lot_size:
        shares = lot_size

    allocated_capital = round(shares * entry_price, 2)

    pos = {
        "code": code,
        "name": data["name"],
        "status": "active",
        "thesis": data.get("thesis", ""),
        "entryDate": data.get("entryDate", today),
        "entryPrice": entry_price,
        "targetPrice": data["targetPrice"],
        "stopLoss": data["stopLoss"],
        "currentStop": data.get("currentStop", data["stopLoss"]),
        "allocation_pct": alloc_pct,
        "shares": shares,
        "allocatedCapital": allocated_capital,
        "rating": data.get("rating", 2),
        "rps120": data.get("rps120"),
        "sector": data.get("sector", ""),
        "catalysts": data.get("catalysts", []),
        "sourceWatchlist": data.get("sourceWatchlist", today),
        "history": [
            {
                "date": data.get("entryDate", today),
                "price": entry_price,
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
        "trackerVersion": "2.1",
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

    # Handle history entry — deduplicate by (date, action)
    history_entry = updates.pop("history_entry", None)
    if history_entry:
        history = pos.setdefault("history", [])
        entry_date = history_entry.get("date")
        entry_action = history_entry.get("action")
        # Replace existing entry for same date+action, or append if new
        replaced = False
        for i, h in enumerate(history):
            if h.get("date") == entry_date and h.get("action") == entry_action:
                history[i] = history_entry
                replaced = True
                break
        if not replaced:
            history.append(history_entry)

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


def regenerate_positions_json(price_data: dict | None = None) -> dict:
    """Scan tracking/*.json, build positions.json from active positions.
    ALWAYS called after any mutation.

    Args:
        price_data: Optional dict keyed by code with live price info
                    (e.g. from data_collector.fetch_position_prices).
                    If provided, updates currentPrice and pnl_pct with real data.
                    If None, falls back to stored values.

    Returns:
        The positions.json content (includes portfolio summary block).
    """
    active = load_active_positions()
    config = load_portfolio_config()
    starting = config["starting_capital"]
    max_pct = config["max_position_pct"]

    entries = []
    total_allocated = 0.0
    total_current_value = 0.0
    total_unrealized = 0.0
    total_day_pnl = 0.0

    for p in active:
        code = p["code"].split(".")[0]
        entry_price = p["entryPrice"]
        current_price = p.get("currentPrice", entry_price)
        pnl_pct = p.get("pnl_pct", 0.0)
        prev_close = None

        # Use live price data if available
        if price_data and code in price_data:
            live = price_data[code]
            if live.get("price") and live["price"] > 0:
                current_price = live["price"]
                pnl_pct = round((current_price - entry_price) / entry_price * 100, 2)
            prev_close = live.get("prev_close")

        # Compute shares (backfill for old positions without shares)
        shares = p.get("shares")
        if not shares:
            raw = int((starting * max_pct / 100) // entry_price)
            lot = 200 if code.startswith("688") else 100
            shares = (raw // lot) * lot or lot
        alloc_pct = p.get("allocation_pct", max_pct)
        allocated = round(shares * entry_price, 2)
        current_val = round(shares * current_price, 2)
        unrealized = round(current_val - allocated, 2)

        # Day P&L (if we have previous close)
        day_pnl = 0.0
        if prev_close and prev_close > 0:
            day_pnl = round((current_price - prev_close) * shares, 2)

        total_allocated += allocated
        total_current_value += current_val
        total_unrealized += unrealized
        total_day_pnl += day_pnl

        entries.append({
            "code": code,
            "name": p["name"],
            "entryDate": p["entryDate"],
            "entryPrice": entry_price,
            "currentPrice": current_price,
            "pnl_pct": pnl_pct,
            "stopLoss": p["stopLoss"],
            "currentStop": p.get("currentStop", p["stopLoss"]),
            "targetPrice": p["targetPrice"],
            "status": "active",
            "sector": p.get("sector", ""),
            "shares": shares,
            "allocation_pct": alloc_pct,
            "allocatedCapital": allocated,
            "currentValue": current_val,
            "unrealizedPnl": unrealized,
        })

    realized = compute_realized_pnl()
    cash = round(starting - total_allocated + realized, 2)
    total_equity = round(cash + total_current_value, 2)
    total_pnl = round(total_unrealized + realized, 2)

    # Compute weight_pct after we know total_equity
    for entry in entries:
        entry["weight_pct"] = round(entry["currentValue"] / total_equity * 100, 2) if total_equity else 0

    portfolio = {
        "startingCapital": starting,
        "totalEquity": total_equity,
        "cash": cash,
        "investedValue": round(total_current_value, 2),
        "unrealizedPnl": round(total_unrealized, 2),
        "realizedPnl": realized,
        "totalPnl": total_pnl,
        "totalReturnPct": round(total_pnl / starting * 100, 2) if starting else 0,
        "positionsUsed": len(entries),
        "positionsMax": config["max_positions"],
        "cashPct": round(cash / total_equity * 100, 2) if total_equity else 100,
        "dayPnl": round(total_day_pnl, 2),
    }

    positions_data = {
        "lastUpdated": _now_iso(),
        "portfolio": portfolio,
        "activePositions": entries,
    }

    _write_json(POSITIONS_FILE, positions_data)
    return positions_data


def save_daily_summary(date: str, actions: list[dict], output_dir: Path | None = None, **extra) -> Path:
    """Write daily summary JSON.

    Args:
        date: Date string "YYYY-MM-DD"
        actions: List of action dicts (code, name, action, price, pnl_pct, note)
        output_dir: If provided, write to output_dir/daily_summary.json instead of tracking/daily/YYYY-MM-DD.json
        **extra: Additional top-level keys (closedPositionNote, newPositions,
                 portfolioStats, marketContext)

    Returns:
        Path to written file.
    """
    summary = {"date": date, "actions": actions, **extra}
    if output_dir:
        out = output_dir / "daily_summary.json"
    else:
        out = DAILY_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
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
