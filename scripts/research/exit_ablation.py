#!/usr/bin/env python3
"""Which exit rule actually earns its keep? Replay our real entries under each.

The first weekly audit (docs/audits/WEEKLY_2026-08-16.md) found the book's
entries are roughly break-even at a fixed 10-session horizon (-0.12%/trade) while
realized results are -0.78%. That gap is the exit machinery. This script
decomposes it: take every position we actually opened, replay the real price path
forward, and settle it under each candidate exit policy.

Why not `backtest.py`: that models *mechanical* entries (RPS gate + MA alignment).
This uses the entries the pipeline actually made, so it isolates exits from
selection — the mechanical arm's picks are not the picks we are trying to explain.

Modelling choices, all deliberately pessimistic about stops:
- **T+1**: earliest possible exit is entry + 1 session (A-share rule).
- **Gaps**: a stop is filled at `min(open, stop)`, not at `stop`. A stock that
  gaps through the level fills at the open, which is what actually happens.
- **Intraday**: stops trigger on the session `low`, not the close — otherwise
  stop policies look better than they are.
- **Costs**: 0.30% round trip, charged to every policy equally.

Known limits: price limits (±10%) are NOT modelled, so a limit-down day lets a
stop exit here when reality would trap the position — this biases stop policies
*optimistically*, in the opposite direction from the rest of the modelling. n=54
over one broadly falling regime; this can reject a rule for this regime, it
cannot validate one in general.

Usage:
    python3 scripts/exit_ablation.py --human
    python3 scripts/exit_ablation.py --horizon 20 --human
"""
import argparse
import glob
import json
import sqlite3
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = ROOT / "data" / "pricedb" / "ashare_prices.db"

ROUND_TRIP_COST_PCT = 0.30

# (label, hard_stop_pct, early_stop_pct, early_days, time_days, time_min_gain)
# None disables that leg. Horizon exit (at close) applies when nothing fires.
POLICIES = [
    ("无止损 (纯持有到期)",         None, None, 0, None, None),
    ("仅硬止损 -5%",                -5.0, None, 0, None, None),
    ("仅硬止损 -8% (放宽)",         -8.0, None, 0, None, None),
    ("硬止损 + 头3日-3% (无时间止损)", -5.0, -3.0, 3, None, None),
    # Time-stop grid on top of hard+early. 10d/<3% vs 20d/<5% moves two knobs at
    # once (patience AND the bar); the crosses isolate which one is load-bearing.
    ("  └ +时间止损 10d/<3% (现行)", -5.0, -3.0, 3, 10, 3.0),
    ("  └ +时间止损 10d/<5%",       -5.0, -3.0, 3, 10, 5.0),
    ("  └ +时间止损 15d/<3%",       -5.0, -3.0, 3, 15, 3.0),
    ("  └ +时间止损 20d/<3%",       -5.0, -3.0, 3, 20, 3.0),
    ("  └ +时间止损 20d/<5% (旧值)", -5.0, -3.0, 3, 20, 5.0),
]


def load_entries(root=ROOT):
    """Every position ever opened, closed or not — the entry is what we replay."""
    out = []
    for f in sorted(glob.glob(str(root / "tracking" / "closed" / "*.json"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        for r in (d if isinstance(d, list) else [d]):
            out.append({"code": (r.get("code") or "").split(".")[0],
                        "name": r.get("name"), "entryDate": r.get("entryDate"),
                        "entryPrice": r.get("entryPrice"),
                        "actual": r.get("returnPct"), "open": False})
    pos = root / "tracking" / "positions.json"
    if pos.exists():
        with open(pos, encoding="utf-8") as fh:
            for a in json.load(fh).get("activePositions", []):
                ep, cp = a.get("entryPrice"), a.get("currentPrice")
                out.append({"code": a["code"].split(".")[0], "name": a.get("name"),
                            "entryDate": a.get("entryDate"), "entryPrice": ep,
                            "actual": (cp / ep - 1) * 100 if ep and cp else None,
                            "open": True})
    return [e for e in out if e["code"] and e["entryPrice"] and e["entryDate"]]


def bars_after(conn, code, entry_date, n):
    return conn.execute(
        "SELECT date, open, high, low, close FROM daily_prices "
        "WHERE code = ? AND date > ? ORDER BY date LIMIT ?",
        (code, entry_date, n)).fetchall()


def settle(bars, entry_price, hard, early, early_days, time_days, time_gain,
           fill="stop"):
    """Return (gross_pct, exit_reason, sessions_held) under one policy.

    `bars` starts at entry+1, so bars[i] is session i+1 — which makes T+1
    automatic: index 0 is already the first sellable session.

    `fill` picks the execution model for the *price-triggered* hard stop. The
    pipeline runs twice a day (~11:35 and ~15:35), so it is NOT sitting in the
    market with a resting stop order — it samples, and sells at whatever it sees.
    Measured on 21 real stop exits: mean **-2.56pp** past the stop level, median
    -1.56pp, worst -15.97pp, with 14 of 21 filling below the stop. Neither bound
    below is right on its own; run both and believe what survives.

      "stop"  — optimistic: triggers on the intraday low, fills at the stop
                (or the open if it gapped through). What a resting order gets.
      "close" — pessimistic: only a *close* below the stop is ever seen, and it
                fills at that close. What a system that only looks at 15:35 gets,
                ignoring intraday dips it would never have acted on.

    Date-triggered rules (early stop, time stop) already read the close and so
    are identical under both.
    """
    for i, (_d, o, _h, low, close) in enumerate(bars, start=1):
        if hard is not None:
            stop_px = entry_price * (1 + hard / 100.0)
            if fill == "close":
                if close <= stop_px:
                    return (close / entry_price - 1) * 100, "hard_stop", i
            elif low <= stop_px:
                # gap-through fills at the open, not at the stop level
                fill_px = min(o, stop_px)
                return (fill_px / entry_price - 1) * 100, "hard_stop", i
        pnl_close = (close / entry_price - 1) * 100
        if early is not None and i <= early_days and pnl_close <= early:
            return pnl_close, "early_stop", i
        if time_days is not None and i >= time_days and pnl_close < time_gain:
            return pnl_close, "time_stop", i
    if not bars:
        return None, None, 0
    return (bars[-1][4] / entry_price - 1) * 100, "horizon", len(bars)


def run(horizon=10, root=ROOT, db_path=DB_PATH, fill="stop"):
    entries = load_entries(root)
    conn = sqlite3.connect(db_path)
    results = {label: [] for (label, *_r) in POLICIES}
    reasons = {label: {} for (label, *_r) in POLICIES}
    replayed = []
    for e in entries:
        bars = bars_after(conn, e["code"], e["entryDate"], horizon)
        if len(bars) < horizon:
            continue                      # too fresh to settle at this horizon
        replayed.append(e)
        for (label, hard, early, edays, tdays, tgain) in POLICIES:
            gross, why, _held = settle(bars, e["entryPrice"], hard, early,
                                       edays, tdays, tgain, fill=fill)
            if gross is None:
                continue
            results[label].append(gross - ROUND_TRIP_COST_PCT)
            reasons[label][why] = reasons[label].get(why, 0) + 1
    conn.close()

    actual = [e["actual"] for e in replayed if e["actual"] is not None]
    return {
        "horizon": horizon,
        "fill": fill,
        "n_entries": len(entries),
        "n_replayed": len(replayed),
        "actual": _summ(actual),
        "policies": [{"label": lab, **(_summ(results[lab]) or {}),
                      "reasons": reasons[lab]}
                     for (lab, *_r) in POLICIES if results[lab]],
    }


def _summ(v):
    if not v:
        return None
    return {"n": len(v), "mean": statistics.mean(v), "median": statistics.median(v),
            "win_rate": sum(1 for x in v if x > 0) / len(v) * 100,
            "worst": min(v), "best": max(v),
            "sum": sum(v)}


def human(d):
    FILL = {"stop": "止损位成交 (乐观: 假设挂单在市)",
            "close": "破位当日收盘成交 (悲观: 只在15:35看得见)"}
    print(f"出场规则消融 — 用我们【真实的】{d['n_replayed']} 笔入场回放 "
          f"(持有上限 {d['horizon']} 个交易日, 含 0.30% 双边成本)")
    print(f"  成交模型: {FILL.get(d.get('fill'), d.get('fill'))}")
    print(f"  总入场 {d['n_entries']} 笔, 其中 {d['n_replayed']} 笔有满 {d['horizon']} 日行情可结算\n")
    a = d["actual"]
    if a:
        print(f"  {'【实际发生】':32s} n={a['n']:3d}  均值 {a['mean']:+6.2f}%  "
              f"中位 {a['median']:+6.2f}%  胜率 {a['win_rate']:5.1f}%   (不含成本口径)")
    print(f"\n  {'策略':32s} {'n':>4s} {'均值':>8s} {'中位':>8s} {'胜率':>7s} {'最差':>8s}")
    base = None
    for p in d["policies"]:
        if base is None:
            base = p["mean"]
        print(f"  {p['label']:32s} {p['n']:4d} {p['mean']:+7.2f}% {p['median']:+7.2f}% "
              f"{p['win_rate']:6.1f}% {p['worst']:+7.2f}%")
    print("\n  触发构成:")
    for p in d["policies"]:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(p["reasons"].items()))
        print(f"    {p['label']:32s} {parts}")
    print("\n  注: 实测21笔止损平仓平均滑点 -2.56pp (中位 -1.56pp, 最差 -15.97pp),")
    print("      14/21 成交在止损位之下 —— 系统一天只看两次, 抓不准止损价。")
    print("      两个成交模型是上下界, 真相在中间; 只信两边都成立的结论。")
    print("      未建模涨跌停 —— 跌停日现实中卖不掉, 此处允许成交,")
    print("      这一条对【带止损的策略偏乐观】, 与其余建模方向相反。")
    print("      n 小且只覆盖一个(整体下行的)行情, 只能证伪, 不能证明。")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--horizon", type=int, default=10)
    ap.add_argument("--fill", choices=("stop", "close"), default="stop",
                    help="hard-stop execution model; see settle() (default stop)")
    ap.add_argument("--human", action="store_true")
    args = ap.parse_args()
    d = run(horizon=args.horizon, fill=args.fill)
    if args.human:
        human(d)
    else:
        print(json.dumps(d, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
