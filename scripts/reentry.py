"""Re-entry record: how trades in a name we ALREADY traded have done.

Moved up from research/reentry_stats.py on 2026-11-21 so the prompt can print
the live figure — it had hardcoded the first measurement (n=9, −3.71%, from
2026-08-13) for three months while the real record moved on. The pipeline
must not import research/, so the shared piece lives here; the CLI
(`python3 scripts/research/reentry_stats.py --human`) imports it.

Sources: tracking/book/closed/*.json (completed round trips) + active files
(open re-entries, excluded from the averages). Only re-entries and book trades
with entryDate on/after `since` count; the PRIOR trip of a pair may predate it.
"""
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from tracking_paths import TRACKING_DIR, Layout


def _trips_by_code(tracking_dir: Path = TRACKING_DIR) -> dict:
    trips = defaultdict(list)
    book = Layout(tracking_dir)
    for f in sorted(book.closed.glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(p, dict) and p.get("entryDate") and p.get("returnPct") is not None:
            trips[str(p["code"]).split(".")[0]].append(p)
    for f in sorted(book.active.glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(p, dict) and p.get("status") == "active" and p.get("entryDate"):
            trips[str(p["code"]).split(".")[0]].append({**p, "returnPct": None})
    return {c: sorted(v, key=lambda x: x["entryDate"]) for c, v in trips.items()}


def compute(tracking_dir: Path = TRACKING_DIR, since: str | None = None) -> dict:
    """since: first entryDate (ISO) a re-entry or book trade must have to be
    counted; None = all history."""
    trips = _trips_by_code(tracking_dir)
    pairs = []
    for code, v in trips.items():
        for prev, nxt in zip(v, v[1:]):
            if not prev.get("exitDate"):
                continue
            if since and nxt["entryDate"] < since:
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

    all_trades = [t for v in trips.values() for t in v
                  if t.get("returnPct") is not None
                  and (not since or t["entryDate"] >= since)]
    book_rets = [t["returnPct"] for t in all_trades]

    def block(rs):
        if not rs:
            return {"n": 0}
        return {"n": len(rs), "mean_pct": round(statistics.fmean(rs), 2),
                "wins": sum(1 for r in rs if r > 0),
                "win_rate_pct": round(sum(1 for r in rs if r > 0) / len(rs) * 100, 1)}

    return {
        "since": since,
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
