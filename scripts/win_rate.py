#!/usr/bin/env python3
"""Win rate, measured three ways — because the pooled number lies.

`16 winners / 54 closed trades = 29.6%` is what the first weekly audit reported.
Three things are wrong with it:

1. **It pools across strategy eras.** ANALYST.md has been rewritten repeatedly
   (v2 momentum-first 03-06, Rule 2b 03-09, entry guardrails 03-24, the RPS-cap
   experiment 07-22, its reversion 07-31, rotation discipline 08-07). A single
   number describes an average of systems, none of which is the one running now.

2. **It attributes by exit date.** A trade entered under one ruleset and closed
   under the next belongs to the ruleset that *selected* it. Entry date is the
   correct key.

3. **It censors open positions — and the censoring is biased.** The book holds
   winners and cuts losers by design, so at any moment the open set is
   disproportionately winners and the closed set disproportionately losers.
   Ranking recent eras on closed trades alone therefore understates them, badly:
   the 07-31 era reads 0% on closed trades and 60% once its 6 open positions are
   marked.

The fix is `fixed`: mark every entry at a fixed horizon after entry, whether or
not it closed. No censoring (open positions count), no survivorship (winners
can't hide in the open set), comparable across eras, and available a fixed two
weeks after any strategy change rather than whenever trades happen to close.

Usage:
    python3 scripts/win_rate.py --human            # all three views
    python3 scripts/win_rate.py --horizon 20       # different fixed horizon
    python3 scripts/win_rate.py --json
"""
import argparse
import datetime as dt
import glob
import json
import sqlite3
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "pricedb" / "ashare_prices.db"

# Substantive strategy changes, from `git log -- agents/ANALYST.md scripts/rules/`.
# Commits that only touch wording or reporting are deliberately not boundaries.
ERAS = [
    ("2026-02-03", "v1 3-agent 架构"),
    ("2026-03-06", "v2 动量优先重写"),
    ("2026-03-09", "Rule 2b 反追高 + MA阈值"),
    ("2026-03-24", "入场护栏"),
    ("2026-07-16", "RPS>95 = 均值回归风险"),
    ("2026-07-22", "RPS 上限取消 (已证伪)"),
    ("2026-07-31", "RPS 75-95 带恢复 + 事件窗口"),
    ("2026-08-07", "满仓换仓纪律"),
    ("2026-08-16", "时间止损 10d/<3%"),
]


def era_of(entry_date):
    label = ERAS[0]
    for start, name in ERAS:
        if entry_date >= start:
            label = (start, name)
    return label


def load_trades(root=ROOT):
    """Every position ever opened: closed ones at their exit, open ones marked."""
    out = []
    for f in sorted(glob.glob(str(root / "tracking" / "closed" / "*.json"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        for r in (d if isinstance(d, list) else [d]):
            out.append({
                "code": (r.get("code") or "").split(".")[0],
                "name": r.get("name"), "entryDate": r.get("entryDate"),
                "entryPrice": r.get("entryPrice"), "ret": r.get("returnPct"),
                "open": False,
            })
    pos_file = root / "tracking" / "positions.json"
    if pos_file.exists():
        with open(pos_file, encoding="utf-8") as fh:
            for a in json.load(fh).get("activePositions", []):
                ep, cp = a.get("entryPrice"), a.get("currentPrice")
                out.append({
                    "code": a["code"].split(".")[0], "name": a.get("name"),
                    "entryDate": a.get("entryDate"), "entryPrice": ep,
                    "ret": (cp / ep - 1) * 100 if ep and cp else None,
                    "open": True,
                })
    return [t for t in out if t["entryDate"] and t["ret"] is not None]


def fixed_horizon_returns(trades, horizon, db_path=DB_PATH):
    """Return at `horizon` sessions after entry, ignoring the actual exit.

    Trades younger than `horizon` sessions are dropped — not counted as zero —
    so a fresh era shows a small n rather than a diluted number.
    """
    if not Path(db_path).exists():
        return {}
    conn = sqlite3.connect(db_path)
    out = {}
    for t in trades:
        if not (t["code"] and t["entryPrice"]):
            continue
        px = conn.execute(
            "SELECT close FROM daily_prices WHERE code = ? AND date > ? "
            "ORDER BY date LIMIT ?", (t["code"], t["entryDate"], horizon)).fetchall()
        if len(px) < horizon:
            continue
        out[id(t)] = (px[horizon - 1][0] / t["entryPrice"] - 1) * 100
    conn.close()
    return out


def summarize(values):
    if not values:
        return None
    return {
        "n": len(values),
        "win_rate": sum(1 for v in values if v > 0) / len(values) * 100,
        "mean": statistics.mean(values),
        "median": statistics.median(values),
    }


def build(horizon=10, root=ROOT, db_path=DB_PATH):
    trades = load_trades(root)
    fixed = fixed_horizon_returns(trades, horizon, db_path)

    by_era = {}
    for t in trades:
        key = era_of(t["entryDate"])
        b = by_era.setdefault(key, {"realized": [], "marked": [], "fixed": [], "open": 0})
        b["marked"].append(t["ret"])
        if t["open"]:
            b["open"] += 1
        else:
            b["realized"].append(t["ret"])
        if id(t) in fixed:
            b["fixed"].append(fixed[id(t)])

    by_week = {}
    for t in trades:
        y, w, _ = dt.date.fromisoformat(t["entryDate"]).isocalendar()
        by_week.setdefault(f"{y}-W{w:02d}", []).append(t["ret"])

    return {
        "horizon": horizon,
        "eras": [{"start": s, "name": n,
                  "open": by_era[(s, n)]["open"],
                  "realized": summarize(by_era[(s, n)]["realized"]),
                  "marked": summarize(by_era[(s, n)]["marked"]),
                  "fixed": summarize(by_era[(s, n)]["fixed"])}
                 for (s, n) in ERAS if (s, n) in by_era],
        "weekly": {w: summarize(v) for w, v in sorted(by_week.items())},
        "pooled_realized": summarize([t["ret"] for t in trades if not t["open"]]),
        "pooled_fixed": summarize(list(fixed.values())),
    }


def _row(label, s):
    if not s:
        return f"  {label:30s}    —"
    return (f"  {label:30s} {s['n']:4d} {s['win_rate']:6.1f}% "
            f"{s['mean']:+8.2f}% {s['median']:+8.2f}%")


def human(d):
    print(f"胜率三视图 (固定持有期 = {d['horizon']} 个交易日)\n")
    print("【1】按策略纪元, 以【入场日】归属 —— 选股决策属于当时生效的策略")
    for e in d["eras"]:
        print(f"\n  {e['start']}  {e['name']}"
              + (f"   ({e['open']} 笔未平仓)" if e["open"] else ""))
        print(f"{'':32s} {'n':>4s} {'胜率':>6s} {'均值':>8s} {'中位':>8s}")
        print(_row("已平仓 (有删失偏差)", e["realized"]))
        print(_row("含未平仓按现价 (有幸存偏差)", e["marked"]))
        print(_row(f"固定{d['horizon']}日 (无偏, 推荐)", e["fixed"]))

    print("\n【2】按周 —— 样本太小, 基本是二值噪声")
    ns = [s["n"] for s in d["weekly"].values()]
    binary = sum(1 for s in d["weekly"].values() if s["win_rate"] in (0.0, 100.0))
    print(f"  {len(ns)} 周, 每周中位 {statistics.median(ns):.0f} 笔 (范围 {min(ns)}-{max(ns)}); "
          f"{binary}/{len(ns)} 周的胜率恰好是 0% 或 100%")
    print("  → 周度胜率无法分辨策略变化与运气, 不建议作为跟踪指标")

    print("\n【3】全账本对照")
    print(f"{'':32s} {'n':>4s} {'胜率':>6s} {'均值':>8s} {'中位':>8s}")
    print(_row("已平仓合计", d["pooled_realized"]))
    print(_row(f"固定{d['horizon']}日合计", d["pooled_fixed"]))
    r, f = d["pooled_realized"], d["pooled_fixed"]
    if r and f:
        print(f"\n  胜率差 {f['win_rate'] - r['win_rate']:+.1f}pp, 但均值只差 "
              f"{f['mean'] - r['mean']:+.2f}pp —— 止损把「本会回本」的仓位变成小额实亏,\n"
              f"  同时也砍掉了灾难。对均值几乎是中性的, 对胜率是毁灭性的。\n"
              f"  低胜率是紧止损系统的固有特征, 不是选股失败的证据。")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--horizon", type=int, default=10,
                    help="sessions after entry for the uncensored view (default 10)")
    ap.add_argument("--human", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    d = build(horizon=args.horizon)
    if args.json or not args.human:
        print(json.dumps(d, ensure_ascii=False, indent=2))
    else:
        human(d)


if __name__ == "__main__":
    main()
