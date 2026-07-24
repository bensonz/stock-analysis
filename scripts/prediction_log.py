#!/usr/bin/env python3
"""
prediction_log.py — the prediction-scoring loop: log → resolve → score.

Every probability the system emits is a bet. This module writes each bet down
in a resolvable form at the moment it's made (tracking/predictions.jsonl),
resolves the auto-resolvable ones against the price DB / disclosure tables,
and Brier-scores the ledger so we can measure — not assert — calibration.

Record kinds:
  price_drawdown  — "min adjusted close within H sessions <= entry*(1-dd%)"
                    auto-resolved from the price DB; resolves 1 EARLY on hit,
                    0 only after the horizon has fully elapsed.
  earnings_decel  — "target period's cumulative net-profit YoY < threshold"
                    auto-resolved from the 业绩报表 table when it publishes.
  manual          — judgment bets (policy/competition/lawsuits) from the
                    writer's predictions block; flagged needs_review at expiry
                    for the weekly audit to resolve with cited evidence.

Scoring: Brier = (p - outcome)^2, plus calibration buckets (stated p vs
observed frequency). For band predictions the midpoint is scored.

Usage:
    python3 scripts/prediction_log.py status
    python3 scripts/prediction_log.py resolve [--human]
    python3 scripts/prediction_log.py score [--human]
"""

import json
import sqlite3
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRED_FILE = PROJECT_ROOT / "tracking" / "predictions.jsonl"


# --------------------------------------------------------------------------- #
# Ledger I/O
# --------------------------------------------------------------------------- #
def load_all(path: Path | None = None) -> list:
    path = path or PRED_FILE
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _write_all(records: list, path: Path | None = None) -> None:
    path = path or PRED_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8")


def append(records: list, path: Path | None = None) -> int:
    """Append new records, deduped by id (reruns of the same report same day
    must not double-log). Returns the number actually added."""
    existing = load_all(path)
    seen = {r["id"] for r in existing}
    fresh = [r for r in records if r["id"] not in seen]
    if fresh:
        _write_all(existing + fresh, path)
    return len(fresh)


# --------------------------------------------------------------------------- #
# Resolution
# --------------------------------------------------------------------------- #
def _covered_dates_after(conn, made: str, min_codes: int) -> list:
    return [r[0] for r in conn.execute(
        "SELECT date FROM daily_prices WHERE date > ? "
        "GROUP BY date HAVING COUNT(DISTINCT code) >= ? ORDER BY date",
        (made, min_codes)).fetchall()]


def _resolve_price_drawdown(rec: dict, conn, min_codes: int, today: str) -> None:
    import price_adjust

    p = rec["params"]
    dates = _covered_dates_after(conn, rec["made"], min_codes)[:p["horizon_sessions"]]
    if not dates:
        return
    rows = conn.execute(
        f"SELECT {price_adjust.adjusted_close_sql()} FROM daily_prices d"
        f"{price_adjust.adj_join_sql()} WHERE d.code=? AND d.date IN "
        f"({','.join('?' * len(dates))})",
        [rec["code"], *dates]).fetchall()
    closes = [float(r[0]) for r in rows if r[0] is not None]
    if not closes:
        return
    threshold = rec["entry_adj"] * (1 - p["drawdown_pct"] / 100.0)
    if min(closes) <= threshold:
        _mark(rec, 1, today, f"min_adj_close={min(closes):.4f} <= {threshold:.4f}")
    elif len(_covered_dates_after(conn, rec["made"], min_codes)) >= p["horizon_sessions"]:
        _mark(rec, 0, today, f"horizon elapsed; min_adj_close={min(closes):.4f} > {threshold:.4f}")


def _resolve_earnings_decel(rec: dict, today: str) -> None:
    import fundamentals

    p = rec["params"]
    df = fundamentals._load_table("yjbb", p["target_period"])
    if df is None:
        return
    row = df[df["股票代码"] == rec["code"]]
    if not len(row):
        return
    yoy = fundamentals._num(row.iloc[0].get("净利润-同比增长"))
    if yoy is None:
        return
    hit = 1 if yoy < p["decel_below_pct"] else 0
    _mark(rec, hit, today, f"{fundamentals.period_label(p['target_period'])} yoy={yoy:.2f}%")


def _mark(rec: dict, outcome: int, today: str, evidence: str) -> None:
    rec["status"] = "resolved"
    rec["outcome"] = outcome
    rec["resolved_on"] = today
    rec["evidence"] = evidence
    rec["brier"] = round((_p(rec) - outcome) ** 2, 4)


def _p(rec: dict) -> float:
    if rec.get("p") is not None:
        return float(rec["p"])
    return (float(rec["p_low"]) + float(rec["p_high"])) / 2  # band → midpoint


def resolve_due(today: str | None = None, path: Path | None = None,
                db_path: str | None = None) -> dict:
    """Resolve everything resolvable; flag expired manual bets for review."""
    today = today or _date.today().isoformat()
    records = load_all(path)
    if db_path is None:
        import pricedb
        db_path = str(pricedb.DB_PATH)

    conn = sqlite3.connect(db_path) if Path(db_path).exists() else None
    try:
        min_codes = 0
        if conn is not None:
            total = conn.execute("SELECT COUNT(DISTINCT code) FROM daily_prices").fetchone()[0]
            min_codes = int((total or 0) * 0.9)
        for rec in records:
            if rec.get("status") not in (None, "open", "needs_review"):
                continue
            if rec["kind"] == "price_drawdown" and conn is not None:
                _resolve_price_drawdown(rec, conn, min_codes, today)
            elif rec["kind"] == "earnings_decel":
                _resolve_earnings_decel(rec, today)
            elif rec["kind"] == "manual" and rec.get("status") == "open" \
                    and str(rec.get("expires", "9999")) <= today:
                rec["status"] = "needs_review"
    finally:
        if conn is not None:
            conn.close()

    _write_all(records, path)
    return {
        "total": len(records),
        "open": sum(1 for r in records if r.get("status") == "open"),
        "resolved": sum(1 for r in records if r.get("status") == "resolved"),
        "needs_review": sum(1 for r in records if r.get("status") == "needs_review"),
    }


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def score(path: Path | None = None) -> dict:
    records = [r for r in load_all(path) if r.get("status") == "resolved"]
    if not records:
        return {"n_resolved": 0}
    briers = [r["brier"] for r in records]
    base_rate_recs = [r for r in records if str(r.get("source", "")).startswith("base_rate:")]
    judgment_recs = [r for r in records if r.get("source") == "judgment"]

    buckets = []
    for lo, hi in ((0, 20), (20, 40), (40, 60), (60, 80), (80, 100)):
        sub = [r for r in records if lo <= _p(r) * 100 < hi]
        if sub:
            buckets.append({
                "stated_pct": f"{lo}-{hi}",
                "n": len(sub),
                "mean_stated_pct": round(sum(_p(r) for r in sub) / len(sub) * 100, 1),
                "observed_pct": round(sum(r["outcome"] for r in sub) / len(sub) * 100, 1),
            })

    def _mean_brier(rs):
        return round(sum(r["brier"] for r in rs) / len(rs), 4) if rs else None

    return {
        "n_resolved": len(records),
        "brier_mean": _mean_brier(records),
        "brier_always_50pct": round(sum((0.5 - r["outcome"]) ** 2 for r in records) / len(records), 4),
        "brier_base_rate_sourced": _mean_brier(base_rate_recs),
        "brier_judgment_sourced": _mean_brier(judgment_recs),
        "calibration": buckets,
        "note": "brier: lower is better; judgment beating base_rate-sourced = measured LLM edge",
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    if cmd == "resolve":
        out = resolve_due()
    elif cmd == "score":
        out = score()
    else:
        records = load_all()
        out = {
            "total": len(records),
            "open": sum(1 for r in records if r.get("status") == "open"),
            "resolved": sum(1 for r in records if r.get("status") == "resolved"),
            "needs_review": sum(1 for r in records if r.get("status") == "needs_review"),
            "file": str(PRED_FILE),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
