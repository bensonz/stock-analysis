#!/usr/bin/env python3
"""Rotation (换仓) opportunity ledger — measures the cost of NOT swapping.

Doctrine context (ANALYST.md 换仓纪律, 2026-08-07): in a momentum system the
current book is usually already the strongest available — swaps are rare by
design. This ledger tests that belief with data instead of trusting it:
whenever the book is FULL (positionsUsed >= max), we mechanically record the
day's top gate-passing candidates we could NOT buy plus the weakest current
holding. Later, `backtest` replays every entry from the local price DB and
answers: how much did we miss by not actively swapping?

- record_if_full(date, data): called from run_daily Phase 3 (non-fatal,
  deterministic — no LLM involvement). Appends to tracking/rotation_ledger.json.
- backtest CLI: forward return of each logged candidate vs the weakest holding
  over N sessions (close-to-close from pricedb). Spread > 0 = we missed alpha.

Usage:
    python3 scripts/rotation_ledger.py backtest [--horizon 10] [--human]
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEDGER_FILE = PROJECT_ROOT / "tracking" / "rotation_ledger.json"
TOP_N = 3


def _load_ledger(path: Path = LEDGER_FILE) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_ledger(entries: list, path: Path = LEDGER_FILE) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def weakest_holding(positions: list[dict], prices: dict) -> dict | None:
    """Weakest current holding by live pnl_pct (falls back to stored pnl)."""
    scored = []
    for p in positions:
        code = str(p.get("code", "")).split(".")[0]
        entry = p.get("entryPrice")
        live = (prices.get(code) or {}).get("price")
        if live and entry:
            pnl = round((live - entry) / entry * 100, 2)
        else:
            pnl = p.get("pnl_pct", 0.0)
        scored.append({"code": code, "name": p.get("name", ""),
                       "entryDate": p.get("entryDate"), "pnl_pct": pnl})
    if not scored:
        return None
    return min(scored, key=lambda x: x["pnl_pct"])


def record_if_full(date: str, data: dict, ledger_path: Path = LEDGER_FILE,
                   max_positions: int | None = None,
                   positions: list[dict] | None = None) -> dict | None:
    """Append a ledger entry when the book is full. Returns the entry or None.

    Fullness is judged on the POST-apply live state (position_manager), not the
    phase-1 snapshot in `data` — a same-run sell/open changes the answer.
    Candidates = top TOP_N of the gate-passed pool (already sorted by RPS in
    data_collector) excluding codes we hold. Dedupes on (date, slot).
    """
    sys.path.insert(0, str(Path(__file__).parent))
    if positions is None:
        try:
            from position_manager import load_active_positions
            positions = load_active_positions()
        except Exception:
            positions = data.get("positions") or []
    if max_positions is None:
        try:
            from position_manager import load_portfolio_config
            max_positions = load_portfolio_config().get("max_positions", 10)
        except Exception:
            max_positions = 10
    if len(positions) < max_positions:
        return None

    # phase-1 key is `strategy_pool` (intersect.json is only the FILENAME —
    # 2026-08-10: the wrong key made the first-ever 10/10 day record nothing)
    pool = ((data.get("strategy_pool") or data.get("intersect") or {}).get("stocks")) or []
    held = {str(p.get("code", "")).split(".")[0] for p in positions}
    candidates = [
        {"code": str(s.get("code", "")).split(".")[0], "name": s.get("name", ""),
         "rps60": s.get("rps60"), "rps120": s.get("rps120"), "rps250": s.get("rps250")}
        for s in pool if str(s.get("code", "")).split(".")[0] not in held
    ][:TOP_N]
    if not candidates:
        return None

    entry = {
        "date": date,
        "slot": data.get("slot", ""),
        "book_size": len(positions),
        "weakest": weakest_holding(positions, data.get("position_prices") or {}),
        "candidates": candidates,
        "entry_regime_allowed": bool((data.get("entry_regime") or {}).get("allow_new_positions", True)),
    }
    ledger = _load_ledger(ledger_path)
    if any(e.get("date") == date and e.get("slot") == entry["slot"] for e in ledger):
        return None  # idempotent per run slot
    ledger.append(entry)
    _save_ledger(ledger, ledger_path)
    return entry


# ---------------------------------------------------------------- backtest

def forward_return(conn, code: str, date: str, horizon: int) -> float | None:
    """Close-to-close % return from last close <= date to `horizon` sessions
    later, using the code's own traded sessions. None if window incomplete."""
    rows = conn.execute(
        "SELECT date, close FROM daily_prices WHERE code=? AND date>=? "
        "ORDER BY date LIMIT ?", (code, date, horizon + 1)).fetchall()
    if len(rows) < horizon + 1 or not rows[0][1]:
        return None
    return round((rows[horizon][1] / rows[0][1] - 1) * 100, 2)


def backtest(horizon: int = 10, conn=None, ledger_path: Path = LEDGER_FILE) -> dict:
    """For each ledger entry old enough: avg candidate forward return vs the
    weakest holding's forward return. Positive spread = missed alpha."""
    if conn is None:
        sys.path.insert(0, str(Path(__file__).parent))
        from pricedb import get_db
        conn = get_db()
    results = []
    for e in _load_ledger(ledger_path):
        weak = e.get("weakest") or {}
        weak_ret = forward_return(conn, weak.get("code", ""), e["date"], horizon) \
            if weak.get("code") else None
        cand_rets = []
        for c in e.get("candidates", []):
            r = forward_return(conn, c["code"], e["date"], horizon)
            if r is not None:
                cand_rets.append({"code": c["code"], "name": c.get("name", ""), "ret": r})
        if weak_ret is None or not cand_rets:
            continue  # window not yet complete (or data gap)
        avg_cand = round(sum(c["ret"] for c in cand_rets) / len(cand_rets), 2)
        results.append({
            "date": e["date"], "slot": e.get("slot", ""),
            "weakest": {**weak, "fwd_ret": weak_ret},
            "candidates": cand_rets,
            "avg_candidate_ret": avg_cand,
            "spread": round(avg_cand - weak_ret, 2),
        })
    n = len(results)
    spreads = [r["spread"] for r in results]
    summary = {
        "horizon_sessions": horizon,
        "n_resolved": n,
        "mean_spread_pct": round(sum(spreads) / n, 2) if n else None,
        "positive_spread_days": sum(1 for s in spreads if s > 0),
        "conclusion": None,
    }
    if n:
        if summary["mean_spread_pct"] > 1.0 and summary["positive_spread_days"] / n > 0.5:
            summary["conclusion"] = "候选跑赢最弱持仓——不换仓有真实机会成本，考虑启用主动换仓"
        elif summary["mean_spread_pct"] < -1.0:
            summary["conclusion"] = "最弱持仓跑赢候选——不主动换仓是对的（动量持仓优势成立）"
        else:
            summary["conclusion"] = "谱系接近——维持保守换仓纪律，继续积累样本"
    return {"summary": summary, "entries": results}


def main():
    args = sys.argv[1:]
    if not args or args[0] != "backtest":
        print("usage: rotation_ledger.py backtest [--horizon N] [--human]",
              file=sys.stderr)
        sys.exit(2)
    horizon = int(args[args.index("--horizon") + 1]) if "--horizon" in args else 10
    out = backtest(horizon=horizon)
    if "--human" in args:
        s = out["summary"]
        print(f"换仓机会成本回测 (horizon={s['horizon_sessions']}日, "
              f"n={s['n_resolved']})")
        if s["n_resolved"]:
            print(f"  平均价差(候选-最弱持仓): {s['mean_spread_pct']:+.2f}pp | "
                  f"候选跑赢天数: {s['positive_spread_days']}/{s['n_resolved']}")
            print(f"  结论: {s['conclusion']}")
            for r in out["entries"]:
                cs = ", ".join(f"{c['name']}{c['ret']:+.1f}%" for c in r["candidates"])
                w = r["weakest"]
                print(f"  {r['date']} {r['slot']}: 最弱 {w.get('name')} "
                      f"{w['fwd_ret']:+.1f}% vs 候选均值 {r['avg_candidate_ret']:+.1f}% "
                      f"(价差 {r['spread']:+.1f}pp) [{cs}]")
        else:
            print("  尚无已到期样本（满仓日+horizon个交易日后才可结算）")
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
