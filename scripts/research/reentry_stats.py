#!/usr/bin/env python3
"""Re-entry performance: how do trades in a name we ALREADY traded do?

Motivated 2026-08-13 by 600160 巨化股份 (opened 08-10, stopped out 08-11 at
-4.61%, re-opened 08-13). First measurement: 9 completed re-entries, 1 win,
mean -3.71% vs the book's -0.61% per trade — suggestive at ~1.5 SE, NOT yet
grounds for a cooldown rule (新宙邦 re-entered 2 days after a -5.3% stop and
made +11.8%). Re-measure as n grows; the weekly audit calls this.

    python3 scripts/research/reentry_stats.py [--human]

Sources: tracking/closed/*.json (completed round trips) + active tracking
files (open re-entries shown as 持仓中, excluded from the averages).
"""

import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRACKING_DIR = PROJECT_ROOT / "tracking"
CLOSED_DIR = TRACKING_DIR / "closed"
SKIP = {"positions.json", "portfolio_config.json", "events.json",
        "hypotheses.json", "rotation_ledger.json"}


def _trips_by_code(tracking_dir: Path = TRACKING_DIR) -> dict:
    trips = defaultdict(list)
    for f in sorted((tracking_dir / "closed").glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(p, dict) and p.get("entryDate") and p.get("returnPct") is not None:
            trips[str(p["code"]).split(".")[0]].append(p)
    for f in sorted(tracking_dir.glob("*.json")):
        if f.name in SKIP:
            continue
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(p, dict) and p.get("status") == "active" and p.get("entryDate"):
            trips[str(p["code"]).split(".")[0]].append({**p, "returnPct": None})
    return {c: sorted(v, key=lambda x: x["entryDate"]) for c, v in trips.items()}


def compute(tracking_dir: Path = TRACKING_DIR) -> dict:
    trips = _trips_by_code(tracking_dir)
    pairs = []
    for code, v in trips.items():
        for prev, nxt in zip(v, v[1:]):
            if not prev.get("exitDate"):
                continue
            gap = (datetime.strptime(nxt["entryDate"], "%Y-%m-%d")
                   - datetime.strptime(prev["exitDate"], "%Y-%m-%d")).days
            px_delta = None
            if prev.get("exitPrice") and nxt.get("entryPrice"):
                px_delta = round((nxt["entryPrice"] / prev["exitPrice"] - 1) * 100, 2)
            pairs.append({
                "code": code, "name": prev.get("name", ""),
                "prev_exit_date": prev["exitDate"], "prev_return": prev["returnPct"],
                "reentry_date": nxt["entryDate"], "reentry_return": nxt["returnPct"],
                "gap_days": gap, "reentry_vs_exit_pct": px_delta,
                "open": nxt["returnPct"] is None,
            })
    done = [p for p in pairs if not p["open"]]
    rets = [p["reentry_return"] for p in done]

    all_trades = [t for v in trips.values() for t in v if t.get("returnPct") is not None]
    book_rets = [t["returnPct"] for t in all_trades]

    def block(rs):
        if not rs:
            return {"n": 0}
        return {"n": len(rs), "mean_pct": round(statistics.fmean(rs), 2),
                "wins": sum(1 for r in rs if r > 0),
                "win_rate_pct": round(sum(1 for r in rs if r > 0) / len(rs) * 100, 1)}

    return {
        "pairs": sorted(pairs, key=lambda p: p["reentry_date"]),
        "reentry": block(rets),
        "book": block(book_rets),
        "after_loss": block([p["reentry_return"] for p in done if p["prev_return"] < 0]),
        "after_win": block([p["reentry_return"] for p in done if p["prev_return"] > 0]),
        "bought_back_lower": block([p["reentry_return"] for p in done
                                    if (p["reentry_vs_exit_pct"] or 0) < 0]),
        "chased_back_higher": block([p["reentry_return"] for p in done
                                     if (p["reentry_vs_exit_pct"] or 0) > 0]),
        "open_reentries": [p for p in pairs if p["open"]],
    }


def main():
    out = compute()
    if "--human" not in sys.argv:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    r, b = out["reentry"], out["book"]
    print(f"重入交易表现 (同一代码的第2+次买入)")
    if not r.get("n"):
        print("  尚无已完成的重入样本")
    else:
        print(f"  重入: n={r['n']} 均值 {r['mean_pct']:+.2f}% 胜率 {r['win_rate_pct']}% "
              f"({r['wins']}胜)")
        print(f"  全账本对照: n={b['n']} 均值 {b['mean_pct']:+.2f}% 胜率 {b['win_rate_pct']}%")
        for k, label in (("after_loss", "上次亏损后重入"), ("after_win", "上次盈利后重入"),
                         ("bought_back_lower", "低于上次卖价买回"),
                         ("chased_back_higher", "高于上次卖价追回")):
            s = out[k]
            if s.get("n"):
                print(f"    {label}: n={s['n']} 均值 {s['mean_pct']:+.2f}% "
                      f"胜率 {s['win_rate_pct']}%")
        print(f"  判读: n={r['n']} 仍小；除非 n≥20 且劣势持续，不因此加冷却期规则"
              f"（新宙邦 -5.3% 后2日重入 +11.8% 证明重入可行）")
    for p in out["open_reentries"]:
        print(f"  [持仓中] {p['code']} {p['name']}: 上次 {p['prev_exit_date']} "
              f"{p['prev_return']:+.1f}% → {p['reentry_date']} 重入"
              f"（间隔{p['gap_days']}天，价格{p['reentry_vs_exit_pct']:+.1f}% vs 上次卖价）")


if __name__ == "__main__":
    main()
