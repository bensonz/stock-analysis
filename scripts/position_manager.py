#!/usr/bin/env python3
"""
Position Manager — State machine for tracking stock positions.

Handles: load, open, close, update positions and regenerate positions.json.
All mutations go through this module to ensure positions.json stays in sync.
"""

import json
import shutil
import sys
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

DEFAULT_PORTFOLIO_CONFIG = {
    "starting_capital": 1000000,
    "max_position_pct": 10,
    "max_positions": 10,
    "min_cash_pct": 20,
}


class SameDaySellError(ValueError):
    """A-share T+1: selling shares bought the same session is illegal.

    Raised by close_position; run_daily records it as SKIP SELL (not ERROR —
    an impossible instruction refused is correct behaviour, not a defect)."""


def _trading_days_held(code: str, entry_date: str, exit_date: str) -> int:
    """Trading sessions in (entry, exit], preferring the price DB (which knows
    holidays and per-stock suspensions), falling back to weekday count."""
    try:
        import sqlite3
        db = sqlite3.connect(PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db")
        n = db.execute(
            "SELECT COUNT(DISTINCT date) FROM daily_prices WHERE code=? AND date>? AND date<=?",
            (str(code).split(".")[0], entry_date, exit_date)).fetchone()[0]
        db.close()
        if n:
            return n
    except Exception:
        pass
    from datetime import date as _date, timedelta as _td
    d, e, n = _date.fromisoformat(entry_date), _date.fromisoformat(exit_date), 0
    while d < e:
        d += _td(days=1)
        if d.weekday() < 5:
            n += 1
    return n


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
        return {**DEFAULT_PORTFOLIO_CONFIG, **_read_json(PORTFOLIO_CONFIG_FILE)}
    return dict(DEFAULT_PORTFOLIO_CONFIG)


def _lot_size_for_code(code: str) -> int:
    return 200 if str(code).split(".")[0].startswith("688") else 100


def _round_down_to_lot(raw_shares: int, code: str) -> int:
    lot_size = _lot_size_for_code(code)
    return (max(int(raw_shares), 0) // lot_size) * lot_size


def build_positions_snapshot(price_data: dict | None = None) -> dict:
    """Build the in-memory positions snapshot without writing positions.json."""
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

        if price_data and code in price_data:
            live = price_data[code]
            if live.get("price") and live["price"] > 0:
                current_price = live["price"]
                pnl_pct = round((current_price - entry_price) / entry_price * 100, 2)
            prev_close = live.get("prev_close")

        shares = p.get("shares")
        if not shares:
            raw = int((starting * max_pct / 100) // entry_price)
            shares = _round_down_to_lot(raw, code) or _lot_size_for_code(code)
        alloc_pct = p.get("allocation_pct", max_pct)
        allocated = round(shares * entry_price, 2)
        current_val = round(shares * current_price, 2)
        unrealized = round(current_val - allocated, 2)

        day_pnl = 0.0
        if prev_close and prev_close > 0:
            day_pnl = round((current_price - prev_close) * shares, 2)

        total_allocated += allocated
        total_current_value += current_val
        total_unrealized += unrealized
        total_day_pnl += day_pnl

        live_volume = None
        live_mavol30 = None
        live_volume_below_mavol30 = None
        if price_data and code in price_data:
            live = price_data[code]
            live_volume = live.get("volume")
            live_mavol30 = live.get("mavol30")
            if live.get("volume_below_mavol30") is not None:
                live_volume_below_mavol30 = live.get("volume_below_mavol30")
            elif live_volume is not None and live_mavol30 not in (None, 0):
                live_volume_below_mavol30 = live_volume < live_mavol30

        entry = {
            "code": code,
            "name": p["name"],
            "entryDate": p["entryDate"],
            "entrySlot": p.get("entrySlot"),
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
        }
        if live_volume is not None:
            entry["volume"] = live_volume
        if live_mavol30 is not None:
            entry["mavol30"] = live_mavol30
        if live_volume_below_mavol30 is not None:
            entry["volumeBelowMavol30"] = bool(live_volume_below_mavol30)

        entries.append(entry)

    realized = compute_realized_pnl()
    cash = round(starting - total_allocated + realized, 2)
    total_equity = round(cash + total_current_value, 2)
    total_pnl = round(total_unrealized + realized, 2)
    min_cash_pct = config.get("min_cash_pct", DEFAULT_PORTFOLIO_CONFIG["min_cash_pct"])
    min_cash_value = round(total_equity * min_cash_pct / 100, 2) if total_equity else 0.0
    deployable_cash = round(max(0.0, cash - min_cash_value), 2)

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
        "minCashPct": min_cash_pct,
        "minCashValue": min_cash_value,
        "deployableCash": deployable_cash,
    }

    return {
        "lastUpdated": _now_iso(),
        "portfolio": portfolio,
        "activePositions": entries,
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
                shares = _round_down_to_lot(raw, p.get("code", "")) or _lot_size_for_code(p.get("code", ""))
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
            # tracking/ also holds non-position state (events.json,
            # hypotheses.json, rotation_ledger.json — the last is a LIST and
            # crashed this loop with AttributeError on 2026-08-11). Anything
            # that isn't a position-shaped dict is simply not a position.
            if isinstance(pos, dict) and pos.get("status") == "active":
                positions.append(pos)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Warning: skipping {f.name}: {e}")
    return positions


def load_recent_exits(days: int = 14, today: str | None = None) -> list[dict]:
    """Round trips closed within the last `days` calendar days, newest first.

    Feeds the daily prompt: before 2026-08-13 the model re-decided a name with
    no knowledge that WE had just stopped out of it (600160 was re-opened two
    days after a -4.61% stop with zero context in the prompt)."""
    from datetime import date, timedelta
    ref = datetime.strptime(today, "%Y-%m-%d").date() if today else date.today()
    floor = (ref - timedelta(days=days)).isoformat()
    out = []
    for f in sorted(CLOSED_DIR.glob("*.json")):
        try:
            p = _read_json(f)
        except (json.JSONDecodeError, KeyError):
            continue
        if not isinstance(p, dict) or not p.get("exitDate"):
            continue
        if p["exitDate"] < floor or p["exitDate"] > ref.isoformat():
            continue
        out.append({
            "code": str(p.get("code", "")).split(".")[0],
            "name": p.get("name", ""),
            "entryDate": p.get("entryDate"), "exitDate": p["exitDate"],
            "exitSlot": p.get("exitSlot"),
            "entryPrice": p.get("entryPrice"), "exitPrice": p.get("exitPrice"),
            "returnPct": p.get("returnPct"), "holdingDays": p.get("holdingDays"),
            "exitReason": p.get("exitReason", ""),
            "lessonLearned": p.get("lessonLearned") or "",
        })
    return sorted(out, key=lambda x: x["exitDate"], reverse=True)


def prior_round_trips(code: str) -> list[dict]:
    """Closed round trips for a code, oldest first (empty when never traded)."""
    code6 = str(code).split(".")[0]
    trips = []
    for f in sorted(CLOSED_DIR.glob(f"{code6}*.json")):
        try:
            p = _read_json(f)
        except (json.JSONDecodeError, KeyError):
            continue
        if isinstance(p, dict) and str(p.get("code", "")).split(".")[0] == code6:
            trips.append(p)
    return sorted(trips, key=lambda x: x.get("exitDate") or "")


def load_all_tracking_files() -> list[dict]:
    """Read ALL tracking/*.json files including non-active ones."""
    positions = []
    for f in sorted(TRACKING_DIR.glob("*.json")):
        if f.name == "positions.json":
            continue
        try:
            data = _read_json(f)
            if isinstance(data, dict):  # skip non-position state (see above)
                positions.append(data)
        except (json.JSONDecodeError, KeyError):
            pass
    return positions


def close_position(
    code: str,
    reason: str,
    exit_price: float,
    lesson: str = "",
    date: Optional[str] = None,
    slot: Optional[str] = None,
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

    # A-share T+1: shares bought today cannot be sold today. The sim executed
    # 奥来德 688378 as a same-session round trip on 2026-07-10 (noon open,
    # afternoon sell) — impossible in reality, and at a price below the day's
    # low. Refuse; the caller records a SKIP and the next session may sell.
    if exit_date == pos.get("entryDate"):
        raise SameDaySellError(
            f"T+1: {code} was opened {pos.get('entryDate')} and cannot be sold "
            f"the same session; position stays open for the next run")

    pos["status"] = "closed"
    pos["exitDate"] = exit_date
    pos["exitPrice"] = exit_price
    pos["exitReason"] = reason
    pos["returnPct"] = round((exit_price - pos["entryPrice"]) / pos["entryPrice"] * 100, 2)
    # Trading sessions, not calendar days (unified 2026-08-19: every consumer —
    # the time stop, the audits, ANALYST.md — speaks in trading days, but this
    # field held calendar days since inception; 32 historical records recomputed).
    pos["holdingDays"] = _trading_days_held(code, pos["entryDate"], exit_date)
    pos["lessonLearned"] = lesson
    pos["updatedAt"] = _now_iso()
    if slot:
        pos["exitSlot"] = slot  # which run closed it (noon vs afternoon)

    # Add SELL to history
    pos.setdefault("history", []).append({
        "date": exit_date,
        **({"slot": slot} if slot else {}),
        "price": exit_price,
        "change_pct": pos["returnPct"],
        "action": "SELL",
        "note": f"{reason}: {lesson}" if lesson else reason,
    })

    # Write to closed dir and remove from tracking root.
    # Filename includes exitDate: plain {code}.json silently OVERWROTE the
    # previous round-trip when a stock was re-entered and re-closed, erasing
    # its realized PnL from compute_realized_pnl (found 2026-08-06: 9 lost
    # round-trips incl. two +30% winners; recovered from git history as
    # {code}_{exitDate}.json). All readers glob closed/*.json, names are free.
    _write_json(CLOSED_DIR / f"{code}_{exit_date}.json", pos)
    pos_file.unlink()

    regenerate_positions_json()
    return pos


def _reentry_stamp(code: str) -> dict:
    """{} for a first-time name; re-entry provenance otherwise (2026-08-13).
    Makes repeat trades self-describing instead of needing a cross-file join."""
    prior = prior_round_trips(code)
    if not prior:
        return {}
    last = prior[-1]
    return {"reentry": True, "priorTrips": len(prior), "priorExit": {
        "exitDate": last.get("exitDate"), "returnPct": last.get("returnPct"),
        "exitReason": str(last.get("exitReason", ""))[:120],
        "exitPrice": last.get("exitPrice"),
    }}


def open_position(data: dict) -> dict:
    """Create a new position file in tracking/.

    Args:
        data: Must contain at minimum: code, name, entryPrice, targetPrice, stopLoss, thesis.
              Optional: rating, rps120, sector, catalysts, confidence, allocation_pct.
              Optional: day_ohlc — dict with {open, high, low, close} for OHLC validation.

    Returns:
        The created position dict.
    """
    code = data["code"].split(".")[0]  # Strip exchange suffix
    today = datetime.now().strftime("%Y-%m-%d")
    entry_price = data.get("entryPrice")
    stop_loss = data.get("stopLoss")
    target_price = data.get("targetPrice")

    # Validate required numeric fields
    if not isinstance(entry_price, (int, float)) or entry_price <= 0:
        raise ValueError(f"Missing or invalid entryPrice for {code}: {entry_price!r}")
    if not isinstance(stop_loss, (int, float)) or stop_loss <= 0:
        raise ValueError(f"Missing or invalid stopLoss for {code}: {stop_loss!r}")
    if not isinstance(target_price, (int, float)) or target_price <= 0:
        raise ValueError(f"Missing or invalid targetPrice for {code}: {target_price!r}")

    # V2 hard rule: every new position carries stop = entry × 0.95 from day 0.
    # Mechanically enforced, no discretion — 2026-08-02 audit found 三环集团
    # opened with a -10.1% stop the LLM had argued for, and no rule engine
    # checks stop PLACEMENT (only proximity). Looser AND tighter values are
    # both overridden: uniform placement is what the rules' track record
    # (and the -5% stop's measured -8.44% average realization) is built on.
    hard_stop = round(entry_price * 0.95, 2)
    if abs(stop_loss - hard_stop) > 0.005:
        print(f"  [stop-enforce] {code}: overriding provided stop {stop_loss} "
              f"-> {hard_stop} (entry {entry_price} x 0.95)", file=sys.stderr)
    stop_loss = hard_stop
    data = {**data, "stopLoss": hard_stop, "currentStop": hard_stop}

    # OHLC validation: entry price must be within the day's tradable range
    day_ohlc = data.get("day_ohlc")
    if day_ohlc:
        day_low = day_ohlc.get("low")
        day_high = day_ohlc.get("high")
        if (
            isinstance(day_low, (int, float))
            and isinstance(day_high, (int, float))
            and day_low > 0
            and day_high > 0
        ):
            if entry_price < day_low or entry_price > day_high:
                raise ValueError(
                    f"Entry price {entry_price} for {code} is outside the day's "
                    f"tradable range [{day_low}, {day_high}]"
                )

    pos_file = TRACKING_DIR / f"{code}.json"
    if pos_file.exists():
        raise FileExistsError(f"Position already exists for {code}")

    config = load_portfolio_config()
    active = load_active_positions()
    if len(active) >= config["max_positions"]:
        raise ValueError(f"Max positions reached ({config['max_positions']})")

    alloc_pct = data.get("allocation_pct") or config["max_position_pct"]
    if not isinstance(alloc_pct, (int, float)) or alloc_pct <= 0:
        raise ValueError(f"Missing or invalid allocation_pct for {code}: {alloc_pct!r}")

    snapshot = build_positions_snapshot()
    portfolio = snapshot.get("portfolio", {})
    current_cash = float(portfolio.get("cash", config["starting_capital"]))
    deployable_cash = float(portfolio.get("deployableCash", current_cash))
    min_cash_pct = float(config.get("min_cash_pct", DEFAULT_PORTFOLIO_CONFIG["min_cash_pct"]))
    min_cash_value = float(portfolio.get("minCashValue", 0.0))

    if deployable_cash <= 0:
        raise ValueError(
            f"Insufficient deployable cash for {code}: cash={current_cash:.2f}, reserve={min_cash_value:.2f} ({min_cash_pct:.1f}%)"
        )

    lot_size = _lot_size_for_code(code)
    lot_cost = lot_size * entry_price
    target_capital = deployable_cash * float(alloc_pct) / 100
    shares = _round_down_to_lot(int(target_capital // entry_price), code)
    max_affordable_shares = _round_down_to_lot(int(deployable_cash // entry_price), code)
    shares = min(shares, max_affordable_shares)

    if shares < lot_size:
        # The requested allocation cannot buy one lot. That is NOT automatically
        # a rejection. STAR Market (688xxx) trades in 200-share lots, so a
        # high-priced name overshoots a modest alloc_pct while still being tiny
        # against the cap that actually governs (config max_position_pct).
        #
        # 2026-08-17: this branch had rejected 5 opens, every one a 688 code with
        # six-figure idle cash, under the message "Insufficient deployable cash
        # for minimum lot" — which was false and sent the diagnosis the wrong way
        # each time. 安集科技 688019 @248.20 was refused for exceeding a 7%
        # *request* while the lot was 5.01% of equity against a 10% *cap*. The
        # effect was a systematic exclusion of high-priced STAR names — exactly
        # where this strategy's semiconductor/materials momentum lives.
        equity = float(portfolio.get("totalEquity") or config["starting_capital"])
        max_pos_pct = float(config.get("max_position_pct",
                                       DEFAULT_PORTFOLIO_CONFIG["max_position_pct"]))
        cap_value = equity * max_pos_pct / 100
        blockers = []
        if lot_cost > deployable_cash:
            blockers.append(
                f"one lot ({lot_size}sh x {entry_price:.2f} = {lot_cost:.2f}) "
                f"exceeds deployable cash {deployable_cash:.2f}")
        if current_cash - lot_cost < min_cash_value:
            blockers.append(
                f"one lot ({lot_cost:.2f}) would breach the min cash reserve "
                f"{min_cash_value:.2f} ({min_cash_pct:.1f}%) against cash {current_cash:.2f}")
        if lot_cost > cap_value:
            blockers.append(
                f"one lot ({lot_cost:.2f}) exceeds max_position_pct {max_pos_pct:g}% "
                f"of equity {equity:.2f} = {cap_value:.2f}")
        if blockers:
            raise ValueError(
                f"Cannot open {code}: " + "; ".join(blockers)
                + f" [requested alloc {alloc_pct:g}% of deployable = {target_capital:.2f}]")
        # Affordable, within the reserve, and under the cap → round UP to one lot.
        print(f"  [lot-round-up] {code}: alloc {alloc_pct:g}% of deployable "
              f"({target_capital:.2f}) buys {int(target_capital // entry_price)}sh, "
              f"below the {lot_size}sh lot; rounding up to {lot_size}sh "
              f"({lot_cost:.2f} = {lot_cost / equity * 100:.2f}% of equity, "
              f"cap {max_pos_pct:g}%)", file=sys.stderr)
        shares = lot_size

    allocated_capital = round(shares * entry_price, 2)
    if current_cash - allocated_capital < min_cash_value:
        raise ValueError(
            f"Opening {code} would breach min cash reserve: cash={current_cash:.2f}, reserve={min_cash_value:.2f}, allocation={allocated_capital:.2f}"
        )

    pos = {
        "code": code,
        "name": data["name"],
        "status": "active",
        "thesis": data.get("thesis", ""),
        "entryDate": data.get("entryDate", today),
        "entrySlot": data.get("slot"),  # which run opened it (noon vs afternoon)
        **_reentry_stamp(code),         # if we traded this name before, say so
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
                **({"slot": data["slot"]} if data.get("slot") else {}),
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

    _write_json(pos_file, pos)
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
        entry_slot = history_entry.get("slot")
        # Replace the entry for the same date+action+SLOT (a re-run of one
        # slot overwrites itself); noon and afternoon entries coexist so the
        # audit trail says which run acted (2026-08-11).
        replaced = False
        for i, h in enumerate(history):
            if (h.get("date") == entry_date and h.get("action") == entry_action
                    and h.get("slot") == entry_slot):
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
    positions_data = build_positions_snapshot(price_data=price_data)
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
