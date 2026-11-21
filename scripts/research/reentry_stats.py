#!/usr/bin/env python3
"""Re-entry performance: how do trades in a name we ALREADY traded do?

Motivated 2026-08-13 by 600160 巨化股份 (opened 08-10, stopped out 08-11 at
-4.61%, re-opened 08-13). First measurement: 9 completed re-entries, 1 win,
mean -3.71% vs the book's -0.61% per trade — suggestive at ~1.5 SE, NOT yet
grounds for a cooldown rule (新宙邦 re-entered 2 days after a -5.3% stop and
made +11.8%). Re-measure as n grows; the weekly audit calls this.

    python3 scripts/research/reentry_stats.py [--human] [--since ISO | --all-history]

Sources: tracking/book/closed/*.json (completed round trips) + active tracking
files (open re-entries shown as 持仓中, excluded from the averages).

Scope: only re-entries (and book trades) whose entryDate is on/after the
evaluation epoch count — earlier trades are a retired system. The PRIOR trip
of a pair may predate the epoch: the current system still sees that history
when it re-buys, so it stays as pairing context.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluation_epoch import EVALUATION_EPOCH  # noqa: E402

from reentry import compute  # noqa: E402  (moved up 2026-11-21 so the prompt can use it)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--human", action="store_true", help="readable summary instead of JSON")
    ap.add_argument("--since", default=EVALUATION_EPOCH,
                    help=f"first re-entry/book entryDate to include (ISO; default: "
                         f"evaluation epoch {EVALUATION_EPOCH} — earlier trades are a "
                         f"retired system)")
    ap.add_argument("--all-history", action="store_true",
                    help="include pre-epoch trades (forensics only)")
    args = ap.parse_args()
    out = compute(since=None if args.all_history else args.since)
    if not args.human:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    r, b = out["reentry"], out["book"]
    scope = f"入场 ≥ {out['since']}" if out["since"] else "全部历史"
    print(f"重入交易表现 (同一代码的第2+次买入; {scope})")
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
