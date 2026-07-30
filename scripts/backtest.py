#!/usr/bin/env python3
"""
backtest.py — Stage-1 backtest harness (see docs/backtest/IMPLEMENTATION_PLAN.md).

The ENGINE knows only market microstructure and accounting: t+1-open fills,
A-share T+1 (no same-day exit), price-limit constraints, costs, equity marking.
ALL entry selection and exit logic lives in strategy callables:

    entries_fn(date, panels) -> list[str]
        Codes desired, best-first, decided from data at `date`'s close.
        They fill at the NEXT session's open (queue trimmed to free slots).
    exits_fn(date, panels, positions) -> list[str] | list[(code, reason)]
        Codes to sell at `date`'s close. `positions` is a read-only view
        carrying entry_date / days_held / pnl_pct, so stop rules are pure
        functions of it.

Prices are ADJUSTED (same space as base_rates.get_panel), so P&L and stops are
dividend-safe returns and an ex-div gap can never fire a phantom stop.
Accounting is percent-of-equity (no integer share lots — documented Stage-2
realism knob). Costs default to A-share reality: commission 0.025%/side,
stamp 0.05% on sells, slippage 0.10%/side ≈ 0.30% round trip.

Price limits are approximated in adjusted space with a small tolerance
(exchange limits round raw prices to 0.01 CNY; adjusted ratios blur that).
ST 5% limits are not modeled — the momentum gate essentially never admits ST
names. Board caps by code prefix: 30/68 → 20%, 4/8/92 (BJ) → 30%, else 10%.
"""
import math
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_CONFIG = {
    "alloc_pct": 3.0,           # % of current equity per new position
    "positions_max": 10,
    "commission_pct": 0.025,    # per side
    "stamp_sell_pct": 0.05,     # sell side only
    "slippage_pct": 0.10,       # per side
    "limit_tolerance": 0.004,   # adjusted-space slack when detecting limit prices
}


def board_limit(code: str) -> float:
    """Daily price-limit fraction by board (main 10%, ChiNext/STAR 20%, BJ 30%)."""
    c = str(code)
    if c.startswith(("30", "68")):
        return 0.20
    if c.startswith(("4", "8", "92")):
        return 0.30
    return 0.10


def _entry_mult(cfg: dict) -> float:
    return 1.0 + (cfg["slippage_pct"] + cfg["commission_pct"]) / 100.0


def _exit_mult(cfg: dict) -> float:
    return 1.0 - (cfg["slippage_pct"] + cfg["commission_pct"] + cfg["stamp_sell_pct"]) / 100.0


def _is_num(v) -> bool:
    # float() rather than isinstance: numpy int64/float64 must pass too
    try:
        return not math.isnan(float(v))
    except (TypeError, ValueError):
        return False


def run(panels: dict, entries_fn, exits_fn, config: dict | None = None,
        start: str | None = None, end: str | None = None) -> dict:
    """Simulate. panels must contain 'closes' and 'opens' (DataFrames,
    index=date str, columns=code, ADJUSTED prices). Returns
    {equity_curve: [(date, equity)], trades: [...], open_positions: [...],
     config, dates: [first, last]}.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    closes, opens = panels["closes"], panels["opens"]
    dates = [d for d in closes.index
             if (start is None or d >= start) and (end is None or d <= end)]
    if not dates:
        raise ValueError("no dates in range")

    em, xm = _entry_mult(cfg), _exit_mult(cfg)
    tol = cfg["limit_tolerance"]
    cash, equity = 1.0, 1.0
    positions: dict = {}    # code -> {entry_date, px_eff, alloc, entry_i}
    pending: list = []
    deferred: dict = {}     # code -> reason (exit wanted but unfillable)
    equity_curve, trades = [], []

    for i, d in enumerate(dates):
        o_row, c_row = opens.loc[d], closes.loc[d]
        pc_row = closes.loc[dates[i - 1]] if i else None

        # 1) fill queued entries at today's open
        for code in pending:
            if len(positions) >= cfg["positions_max"] or code in positions:
                continue
            op = o_row.get(code)
            pc = pc_row.get(code) if pc_row is not None else None
            if not _is_num(op):
                continue                                   # no trade today: order dies
            if _is_num(pc) and op >= pc * (1 + board_limit(code) - tol):
                continue                                   # limit-up open, unfillable
            alloc = cfg["alloc_pct"] / 100.0 * equity
            if alloc > cash + 1e-12:
                continue                                   # out of cash
            positions[code] = {"entry_date": d, "entry_i": i,
                               "px_eff": op * em, "alloc": alloc}
            cash -= alloc
        pending = []

        # 2) exits at today's close (T+1: never on the entry day)
        view = {
            code: {"entry_date": p["entry_date"],
                   "days_held": i - p["entry_i"],
                   "pnl_pct": (c_row.get(code) / p["px_eff"] - 1.0) * 100
                   if _is_num(c_row.get(code)) else None}
            for code, p in positions.items()
        }
        raw = exits_fn(d, panels, view) or []
        wanted = {}
        for item in raw:
            code, reason = item if isinstance(item, tuple) else (item, "strategy")
            wanted[code] = reason
        wanted.update(deferred)
        deferred = {}
        for code, reason in wanted.items():
            p = positions.get(code)
            if p is None:
                continue
            if p["entry_date"] == d:                       # T+1
                deferred[code] = reason
                continue
            px = c_row.get(code)
            pc = pc_row.get(code) if pc_row is not None else None
            if not _is_num(px):                            # suspended
                deferred[code] = reason
                continue
            if _is_num(pc) and px <= pc * (1 - board_limit(code) + tol):
                deferred[code] = reason                    # sealed limit-down
                continue
            pnl = px * xm / p["px_eff"] - 1.0
            cash += p["alloc"] * (1.0 + pnl)
            trades.append({"code": code, "entry_date": p["entry_date"],
                           "exit_date": d, "pnl_pct": round(pnl * 100, 4),
                           "days_held": i - p["entry_i"], "reason": reason})
            del positions[code]

        # 3) mark to market
        invested = 0.0
        for code, p in positions.items():
            px = c_row.get(code)
            invested += p["alloc"] * (px / p["px_eff"] if _is_num(px) else 1.0)
        equity = cash + invested
        equity_curve.append((d, round(equity, 6)))

        # 4) queue tomorrow's fills from today's close signals
        if i < len(dates) - 1 and len(positions) < cfg["positions_max"]:
            pending = list(entries_fn(d, panels) or [])

    last = dates[-1]
    open_positions = [
        {"code": code, "entry_date": p["entry_date"],
         "pnl_pct": round((closes.loc[last].get(code) / p["px_eff"] - 1.0) * 100, 4)
         if _is_num(closes.loc[last].get(code)) else None}
        for code, p in positions.items()
    ]
    return {"equity_curve": equity_curve, "trades": trades,
            "open_positions": open_positions, "config": cfg,
            "dates": [dates[0], last]}


def metrics(result: dict) -> dict:
    """Headline stats from a run() result."""
    curve = [e for _, e in result["equity_curve"]]
    peak, max_dd = 0.0, 0.0
    for e in curve:
        peak = max(peak, e)
        max_dd = max(max_dd, 1.0 - e / peak)
    trades = result["trades"]
    wins = [t["pnl_pct"] for t in trades if t["pnl_pct"] > 0]
    losses = [t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0]
    return {
        "total_return_pct": round((curve[-1] - 1.0) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "n_trades": len(trades),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2) if trades else None,
        "avg_win_pct": round(sum(wins) / len(wins), 2) if wins else None,
        "avg_loss_pct": round(sum(losses) / len(losses), 2) if losses else None,
        "median_days_held": (sorted(t["days_held"] for t in trades)[len(trades) // 2]
                             if trades else None),
        "open_positions": len(result["open_positions"]),
    }


# --------------------------------------------------------------------------- #
# Data loading (live DB → engine panels)
# --------------------------------------------------------------------------- #
def load_engine_panels(db_path: str | None = None) -> dict:
    """base_rates feature panel + an adjusted OPEN panel on the same covered
    dates. Read-only against the price DB."""
    import base_rates
    import price_adjust
    import rps_calculator

    if db_path is None:
        import pricedb
        db_path = str(pricedb.DB_PATH)
    panels = dict(base_rates.get_panel(db_path))

    import pandas as pd
    conn = sqlite3.connect(db_path)
    try:
        price_adjust.ensure_adj_schema(conn)
        min_codes = rps_calculator._reference_date_min_codes(conn)
        sql = (
            f"SELECT d.code AS code, d.date AS date, "
            f"d.open * COALESCE(a.factor, 1.0) AS open "
            f"FROM daily_prices d{price_adjust.adj_join_sql()} "
            f"WHERE d.open IS NOT NULL AND d.date IN "
            f"  (SELECT date FROM daily_prices "
            f"   GROUP BY date HAVING COUNT(DISTINCT code) >= {min_codes})"
        )
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    opens = df.pivot(index="date", columns="code", values="open").sort_index()
    panels["opens"] = opens.reindex(index=panels["closes"].index,
                                    columns=panels["closes"].columns)
    return panels


# --------------------------------------------------------------------------- #
# Stage 1b — arm (a): the mechanical-ANALYST baseline
# --------------------------------------------------------------------------- #
# Deliberately dumb stand-in for the LLM's seat (plan D4): it measures the
# RULES of ANALYST.md executed with no judgment. Parameters in one dict so
# Stage-2 experiments are one-line diffs.
ANALYST_RULES = {
    "gate_rps": 80.0,           # rps60/120/250 all >= this (the hard gate)
    "dist_ma5_max": 6.0,        # Rule 2b extension guard: skip if above
    "dist_ma10_max": 8.0,
    "dist_ma20_max": 12.0,
    "hard_stop_pct": -5.0,      # Rule 5: automatic sell, no exceptions
    "early_stop_pct": -3.0,     # Rule 5: -3% within the first N sessions
    "early_days": 3,
    "time_decay_days": 20,      # held > N sessions with < min_gain → sell
    "time_decay_min_gain": 5.0,
    "rank_by": "rps60",
    "queue_depth": 15,          # candidates offered per day (engine trims)
}


def prepare_analyst_features(panels: dict) -> dict:
    """Rolling MAs the baseline needs, computed once and cached in panels."""
    closes = panels["closes"]
    for w in (5, 20, 120, 250):
        key = f"ma{w}"
        if key not in panels:
            panels[key] = closes.rolling(w, min_periods=w).mean()
    return panels


def make_mechanical_analyst(rules: dict | None = None):
    """Returns (entries_fn, exits_fn) for run()."""
    r = {**ANALYST_RULES, **(rules or {})}

    def entries(d, panels):
        p = prepare_analyst_features(panels)
        c = p["closes"].loc[d]
        gate = ((p["rps60"].loc[d] >= r["gate_rps"])
                & (p["rps120"].loc[d] >= r["gate_rps"])
                & (p["rps250"].loc[d] >= r["gate_rps"]))
        align = ((p["ma20"].loc[d] > p["ma120"].loc[d])
                 & (p["ma120"].loc[d] > p["ma250"].loc[d]))
        d5 = (c / p["ma5"].loc[d] - 1.0) * 100
        d20 = (c / p["ma20"].loc[d] - 1.0) * 100
        not_extended = ((d5 <= r["dist_ma5_max"])
                        & (p["dist_ma10_pct"].loc[d] <= r["dist_ma10_max"])
                        & (d20 <= r["dist_ma20_max"]))
        ok = (gate & align & not_extended).fillna(False)
        ranked = p[r["rank_by"]].loc[d][ok].dropna().sort_values(ascending=False)
        return list(ranked.index[: r["queue_depth"]])

    def exits(d, panels, positions):
        out = []
        for code, v in positions.items():
            pnl, held = v["pnl_pct"], v["days_held"]
            if pnl is None:
                continue
            if pnl <= r["hard_stop_pct"]:
                out.append((code, "rule5_hard_stop"))
            elif held <= r["early_days"] and pnl <= r["early_stop_pct"]:
                out.append((code, "rule5_early"))
            elif held > r["time_decay_days"] and pnl < r["time_decay_min_gain"]:
                out.append((code, "time_decay"))
        return out

    return entries, exits


# --------------------------------------------------------------------------- #
# Stage 1b — arm (b): replay of actual trades (fidelity check, plan D5)
# --------------------------------------------------------------------------- #
def load_closed_trades(closed_dir: str | Path | None = None) -> list:
    """Flatten tracking/closed/*.json into trade dicts with the fields the
    replay needs. Entries without dates or a recorded return are skipped."""
    import json
    d = Path(closed_dir) if closed_dir else (
        Path(__file__).resolve().parent.parent / "tracking" / "closed")
    out = []
    for f in sorted(d.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for t in (data if isinstance(data, list) else [data]):
            if t.get("entryDate") and t.get("exitDate") and t.get("returnPct") is not None:
                out.append(t)
    return out


def _raw_fill_prices(db_path: str | None, code: str, ed: str, xd: str):
    """(raw entry-day open, raw exit-day close) for fill-timing attribution."""
    if db_path is None:
        import pricedb
        db_path = str(pricedb.DB_PATH)
    conn = sqlite3.connect(db_path)
    try:
        r1 = conn.execute("SELECT open FROM daily_prices WHERE code=? AND date=?",
                          (code, ed)).fetchone()
        r2 = conn.execute("SELECT close FROM daily_prices WHERE code=? AND date=?",
                          (code, xd)).fetchone()
    finally:
        conn.close()
    return (r1[0] if r1 else None), (r2[0] if r2 else None)


def replay_closed_trades(panels: dict | None = None, config: dict | None = None,
                         closed_dir=None, db_path: str | None = None) -> dict:
    """Run each recorded trade through the fill+cost model and reconcile
    against the recorded returnPct.

    Live fills were intraday; sim fills are entry-day OPEN → exit-day CLOSE
    with costs, so per-trade differences are expected. To separate model error
    from irreducible fill-timing noise, each row also carries the raw-price
    attribution: entry_fill_diff_pct (our open vs the actual entry fill) and
    exit_fill_diff_pct (our close vs the actual exit fill). If diff_pp is
    explained by those two, the cost/adjustment model itself is sound."""
    panels = panels if panels is not None else load_engine_panels()
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    em, xm = _entry_mult(cfg), _exit_mult(cfg)
    closes, opens = panels["closes"], panels["opens"]

    rows, tol = [], 1.5
    for t in load_closed_trades(closed_dir):
        code, ed, xd = t["code"], t["entryDate"], t["exitDate"]
        rec = {"code": code, "name": t.get("name"), "entry_date": ed,
               "exit_date": xd, "recorded_pct": round(float(t["returnPct"]), 2)}
        if code not in closes.columns:
            rec["status"] = "no_price_data"
        elif ed not in closes.index or xd not in closes.index:
            rec["status"] = "date_uncovered"       # pre-DB or dropped partial day
        else:
            entry_open, exit_close = opens.loc[ed, code], closes.loc[xd, code]
            if not (_is_num(entry_open) and _is_num(exit_close)):
                rec["status"] = "price_missing"
            else:
                sim = (exit_close * xm / (entry_open * em) - 1.0) * 100
                rec.update(status="ok", sim_pct=round(float(sim), 2),
                           diff_pp=round(float(sim) - rec["recorded_pct"], 2))
                raw_open, raw_close = _raw_fill_prices(db_path, code, ed, xd)
                if raw_open and t.get("entryPrice"):
                    rec["entry_fill_diff_pct"] = round(
                        (raw_open / float(t["entryPrice"]) - 1.0) * 100, 2)
                if raw_close and t.get("exitPrice"):
                    rec["exit_fill_diff_pct"] = round(
                        (raw_close / float(t["exitPrice"]) - 1.0) * 100, 2)
        rows.append(rec)

    oks = [r for r in rows if r["status"] == "ok"]
    within = [r for r in oks if abs(r["diff_pp"]) <= tol]

    def _mean_abs(key):
        vals = [abs(r[key]) for r in oks if key in r]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "trades": rows,
        "summary": {
            "total": len(rows),
            "replayable": len(oks),
            "within_tolerance": len(within),
            "tolerance_pp": tol,
            "match_rate_pct": round(len(within) / len(oks) * 100, 1) if oks else None,
            "mean_abs_diff_pp": _mean_abs("diff_pp"),
            # attribution: how much of the diff is fill-timing, by side
            "mean_abs_entry_fill_diff_pct": _mean_abs("entry_fill_diff_pct"),
            "mean_abs_exit_fill_diff_pct": _mean_abs("exit_fill_diff_pct"),
        },
    }


if __name__ == "__main__":
    import json as _json
    cmd = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    panels = load_engine_panels()
    if cmd == "replay":
        rep = replay_closed_trades(panels)
        print(_json.dumps(rep["summary"], ensure_ascii=False, indent=1))
        for r in rep["trades"]:
            print(r)
    else:
        entries_fn, exits_fn = make_mechanical_analyst()
        res = run(panels, entries_fn, exits_fn,
                  start=sys.argv[2] if len(sys.argv) > 2 else None)
        print(_json.dumps(metrics(res), ensure_ascii=False, indent=1))
