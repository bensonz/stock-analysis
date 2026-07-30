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


if __name__ == "__main__":
    print("Stage 1a: engine only — strategy arms land in Stage 1b.",
          file=sys.stderr)
