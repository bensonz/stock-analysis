#!/usr/bin/env python3
"""
cost_of_caution.py — price what the system declined to buy (weekly audit input).

Stops make bad ENTRIES visible; nothing made bad NON-entries visible. This
closes the loop: every skip_list decision is replayed as if taken, under the
SAME exit discipline a real position would have faced (Rule 5: -3% within 3
sessions, -5% hard stop; horizon cap), at the same fill/cost model as the
backtest engine. The naive "it went up 8% after we skipped" number is a lie
if the path dipped through a stop first — this script does not tell it.

Two symmetric outputs per skip: would-be return if the exit rules had run,
and the verdict bucket (disaster_avoided / small_loss_avoided / noise /
win_missed). Weekly aggregation answers: is our caution net saving or net
costing, and which SKIP REASONS are earning their keep?

Reads runs/*/<slot>/response.json (local, git-ignored) + the price panel.
Read-only; no pipeline coupling. Run: python3 scripts/cost_of_caution.py --human
"""
import argparse
import json
import re
import sys
from datetime import date as _date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"

HORIZON = 10          # sessions a hypothetical position is allowed to run
EARLY_DAYS = 3        # Rule 5: -3% within the first N sessions
EARLY_STOP = -3.0
HARD_STOP = -5.0
ALLOC_PCT = 3.0       # standard starter size, for portfolio-impact framing

REASON_BUCKETS = [
    ("sector", r"板块|sector|冷门|bottom"),
    ("regime", r"regime|恐慌|panic|涨跌比|breadth|buy gate|空仓|市场|大盘"),
    ("event", r"事件|FOMC|CPI|议息|关税|地缘|霍尔木兹|风险窗口|event"),
    ("stock", r"MA|RPS|均线|催化|估值|放量|回撤|止损|技术|基本面|dist"),
]


def classify_reason(reason: str) -> str:
    for name, pat in REASON_BUCKETS:
        if re.search(pat, reason or "", re.I):
            return name
    return "other"


def collect_skips(days: int, today: _date | None = None,
                  runs_dir: Path | None = None) -> list:
    """(date, code, name, reason) from skip_lists in the window, deduped to
    the EARLIEST skip per code (the original moment of caution)."""
    today = today or _date.today()
    cutoff = (today - timedelta(days=days)).isoformat()
    runs_dir = runs_dir or RUNS_DIR
    seen: dict = {}
    for resp in sorted(runs_dir.glob("*/*/response.json")) + sorted(runs_dir.glob("*/response.json")):
        run_date = resp.parent.parent.name if resp.parent.name in ("noon", "afternoon") \
            else resp.parent.name
        if not (cutoff <= run_date <= today.isoformat()):
            continue
        try:
            decisions = json.loads(resp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(decisions, dict):   # some legacy runs stored a list
            continue
        for s in decisions.get("skip_list") or []:
            code = str(s.get("code", "")).split(".")[0]
            if not code:
                continue
            if code not in seen or run_date < seen[code]["skip_date"]:
                seen[code] = {"skip_date": run_date, "code": code,
                              "name": s.get("name", ""),
                              "reason": s.get("reason", ""),
                              "bucket": classify_reason(s.get("reason", ""))}
    return sorted(seen.values(), key=lambda x: (x["skip_date"], x["code"]))


def simulate_if_taken(code: str, skip_date: str, panels: dict) -> dict | None:
    """Entry at next session's open after the skip, exits per Rule 5, capped
    at HORIZON sessions. Costs via the backtest engine's multipliers.
    Returns {ret_pct, exit_kind, sessions} or None (no data)."""
    import backtest as bt

    closes, opens = panels["closes"], panels["opens"]
    if code not in closes.columns:
        return None
    dates = [d for d in closes.index if d > skip_date]
    if not dates:
        return None
    entry_open = opens.loc[dates[0], code]
    if not bt._is_num(entry_open):
        return None
    px_eff = float(entry_open) * bt._entry_mult(bt.DEFAULT_CONFIG)
    xm = bt._exit_mult(bt.DEFAULT_CONFIG)
    for i, d in enumerate(dates[:HORIZON], start=1):
        c = closes.loc[d, code]
        if not bt._is_num(c):
            continue
        pnl = (float(c) * xm / px_eff - 1.0) * 100
        if i > 1:  # T+1: no exit on the entry session itself
            if pnl <= HARD_STOP:
                return {"ret_pct": round(pnl, 2), "exit_kind": "hard_stop", "sessions": i}
            if i <= EARLY_DAYS and pnl <= EARLY_STOP:
                return {"ret_pct": round(pnl, 2), "exit_kind": "early_stop", "sessions": i}
    # survived: mark at last available close within horizon
    avail = [d for d in dates[:HORIZON] if bt._is_num(closes.loc[d, code])]
    if not avail:
        return None
    last = avail[-1]
    pnl = (float(closes.loc[last, code]) * xm / px_eff - 1.0) * 100
    kind = "horizon" if len(avail) >= HORIZON else "open"
    return {"ret_pct": round(pnl, 2), "exit_kind": kind, "sessions": len(avail)}


def _verdict(ret: float) -> str:
    if ret <= -5.0:
        return "disaster_avoided"
    if ret < 0:
        return "small_loss_avoided"
    if ret < 5.0:
        return "noise"
    return "win_missed"


def report(days: int = 28, today: _date | None = None,
           runs_dir: Path | None = None, panels: dict | None = None) -> dict:
    if panels is None:
        import backtest as bt
        panels = bt.load_engine_panels()
    rows = []
    for s in collect_skips(days, today, runs_dir):
        sim = simulate_if_taken(s["code"], s["skip_date"], panels)
        rows.append({**s, **(sim or {"ret_pct": None, "exit_kind": "no_data",
                                     "sessions": None})})
    scored = [r for r in rows if r["ret_pct"] is not None]
    for r in scored:
        r["verdict"] = _verdict(r["ret_pct"])

    by_bucket: dict = {}
    for r in scored:
        b = by_bucket.setdefault(r["bucket"], {"n": 0, "sum": 0.0})
        b["n"] += 1
        b["sum"] += r["ret_pct"]
    total = sum(r["ret_pct"] for r in scored)
    return {
        "window_days": days,
        "n_skips": len(rows),
        "n_scored": len(scored),
        # + = skipping SAVED money (avoided losses exceed missed wins)
        "net_savings_pct_sum": round(-total, 2),
        "portfolio_impact_pp": round(-total * ALLOC_PCT / 100, 2),
        "verdicts": {v: sum(1 for r in scored if r["verdict"] == v)
                     for v in ("disaster_avoided", "small_loss_avoided",
                               "noise", "win_missed")},
        "by_reason_bucket": {k: {"n": v["n"],
                                 "mean_would_be_ret_pct": round(v["sum"] / v["n"], 2)}
                             for k, v in sorted(by_bucket.items())},
        "skips": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--human", action="store_true")
    a = ap.parse_args()
    rep = report(days=a.days)
    if not a.human:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return
    print(f"谨慎成本核算 — 最近{rep['window_days']}天, "
          f"{rep['n_scored']}/{rep['n_skips']}条skip可回放")
    v = rep["verdicts"]
    print(f"  避开重亏(≤-5%): {v['disaster_avoided']}  避开小亏: {v['small_loss_avoided']}  "
          f"噪音(±5%内): {v['noise']}  错过大涨(≥+5%): {v['win_missed']}")
    sign = "净节省" if rep["net_savings_pct_sum"] >= 0 else "净成本"
    print(f"  合计: {sign} {abs(rep['net_savings_pct_sum']):.1f}% "
          f"(按{ALLOC_PCT:.0f}%仓位≈组合 {rep['portfolio_impact_pp']:+.2f}pp)")
    print("  ⚠️ 组合影响为『每条skip都按标准仓位买入』的后悔上界——实际仓位上限只容纳"
          "一小部分，读方向与量级，勿当作可实现的替代收益")
    print("  按理由分类:")
    for k, b in rep["by_reason_bucket"].items():
        print(f"    {k:8s} n={b['n']:3d}  平均如果买入 {b['mean_would_be_ret_pct']:+6.2f}%")
    print("  明细 (skip日期 | 代码 名称 | 如果买入 | 判定 | 理由类):")
    for r in rep["skips"]:
        ret = f"{r['ret_pct']:+6.2f}%" if r["ret_pct"] is not None else "  无数据"
        print(f"    {r['skip_date']} | {r['code']} {r['name']:8s} | {ret} "
              f"| {r.get('verdict', '-'):18s} | {r['bucket']}")


if __name__ == "__main__":
    main()
