#!/usr/bin/env python3
"""
entry_drift.py — Does the entry filter select positive EXCESS drift?

The martingale framing (2026-09-29)
-----------------------------------
ANALYST.md bets that a stock passing the RPS gate is a *submartingale*: in the
Doob decomposition X = M + A, its compensator A is increasing, i.e. it has
positive conditional drift. Doob's optional stopping theorem says that on a
martingale no bounded stopping rule — a stop-loss, a trailing stop, a
time-decay exit — can change the expected value; it only reshapes the P&L
distribution (more small wins and a few big losses, or the reverse). So if the
strategy has an edge, ALL of it has to come from the entry filter, and it must
be visible BEFORE any exit rule acts.

This script measures exactly that: the fixed-horizon forward return of each
cohort from the run date's close, minus the whole market's forward return over
the identical window.

Cohorts, per run date
---------------------
- `gate`          every code in `input/intersect.json` — the RPS>85 survivors
                  the LLM was shown that day.
- `in_band`       the part of `gate` with RPS120 <= 95 (ANALYST.md Rule 2 band).
- `over_extended` the part of `gate` with RPS120 > 95 — the prompt's
                  `OVER-EXTENDED` flag (llm_client.py uses the same cut).
- `bought`        codes the pipeline actually opened on that date (closed
                  trades + open positions, read-only from tracking/).
- `universe`      every code with a price on that date — the benchmark.

A day with both slots uses the afternoon run (latest settled state, same as
run_paths.find_run_dir); a noon-only day is still anchored on that day's close,
which slightly understates what the model knew — not look-ahead.

Measurement choices, and why
----------------------------
- Adjusted closes (close × hfq factor, via price_adjust's SQL fragments) so an
  ex-dividend gap does not read as a loss. The DB is opened read-only.
- Horizons count MARKET sessions, not a stock's own bars: the target date is
  the h-th trading day after the anchor, and a code with no bar on that exact
  date (suspended, or not settled yet) is skipped — never filled, never
  zero. That keeps every cohort on the same window as the universe.
- Phantom sessions are removed from the calendar. The DB carries 2026-05-04
  and 2026-05-05 (Labor Day holiday) bars: 100% of 05-05 and 54% of 05-04 are
  byte-identical copies of the previous bar, against a ~0.1% norm. Counting
  them as sessions would shift every h across that week by up to two days.
- Dates are the independent unit. Stocks on the same day share the market
  shock, and consecutive dates' h-day windows overlap, so the per-date excess
  series is autocorrelated for h>1 and its plain t-stat is optimistic. The
  `t_nonoverlap` column re-samples dates at least h sessions apart; trust it
  over `t` when they disagree.

What this does NOT measure
--------------------------
Exits and sizing. `optional_stopping` only contrasts the realized P&L of
closed trades with the same trades held for a fixed horizon, to show how much
the exit rules reshaped the distribution. `candidate_alpha.py` asks a related
question against 上证指数 per candidate row; this one benchmarks against the
equal-weight universe per date.

Usage:
    python3 scripts/research/entry_drift.py [--since ISO] [--json]
"""

import argparse
import bisect
import glob
import json
import math
import sqlite3
import statistics as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import price_adjust  # noqa: E402
import run_paths  # noqa: E402

DB_PATH = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"
RUNS_DIR = PROJECT_ROOT / "runs"
TRACKING_DIR = PROJECT_ROOT / "tracking"
HORIZONS = (1, 5, 10, 20)
COHORTS = ("gate", "in_band", "over_extended", "bought")

# Rule 2's ceiling, same cut as llm_client's OVER-EXTENDED flag.
RPS_CEILING = 95.0

# A real session has ~0.1% of codes repeating yesterday's close AND volume
# exactly (suspensions). The worst genuine day in the archive is 0.28%; the
# two phantom holiday days are 54% and 100%. 20% sits far from both.
PHANTOM_STALE_FRACTION = 0.20


# --------------------------------------------------------------------------- #
# Prices
# --------------------------------------------------------------------------- #

def connect_ro(db_path=None) -> sqlite3.Connection:
    """Read-only handle. Never call price_adjust.ensure_adj_schema on it —
    that issues CREATE TABLE and would fail (correctly) on a ro connection."""
    return sqlite3.connect(f"file:{db_path or DB_PATH}?mode=ro", uri=True)


def phantom_dates(conn, threshold=PHANTOM_STALE_FRACTION) -> set:
    """Dates where more than `threshold` of codes repeat the previous bar's
    close and volume exactly — copies, not sessions."""
    sql = (
        "SELECT date, AVG(same) FROM ("
        "  SELECT date, (close = LAG(close) OVER w AND volume = LAG(volume) OVER w)"
        "         AS same"
        "  FROM daily_prices WINDOW w AS (PARTITION BY code ORDER BY date)"
        ") WHERE same IS NOT NULL GROUP BY date"
    )
    return {d for d, frac in conn.execute(sql) if frac > threshold}


def load_closes(conn, since: str) -> dict:
    """{date: {code: adjusted_close}} for every bar on/after `since`."""
    sql = (f"SELECT d.date, d.code, {price_adjust.adjusted_close_sql()} "
           f"FROM daily_prices d{price_adjust.adj_join_sql()} WHERE d.date >= ?")
    closes: dict[str, dict] = {}
    for date, code, close in conn.execute(sql, (since,)):
        if close:
            closes.setdefault(date, {})[code] = close
    return closes


def build_calendar(closes: dict, phantoms: set) -> list:
    """Ascending trading dates, phantom sessions removed."""
    return sorted(d for d in closes if d not in phantoms)


def forward_return(closes, calendar, code, date, h):
    """% return from `date`'s close to the close h sessions later, or None.

    None whenever the answer would need a guess: the anchor is not a session,
    the code has no bar on either end, or the target session has not happened.
    """
    i = bisect.bisect_left(calendar, date)
    if i >= len(calendar) or calendar[i] != date or i + h >= len(calendar):
        return None
    p0 = closes.get(date, {}).get(code)
    p1 = closes.get(calendar[i + h], {}).get(code)
    if not p0 or not p1:
        return None
    return (p1 / p0 - 1) * 100


def universe_mean(closes, calendar, date, h):
    """Equal-weight mean forward return of every code priced on `date`."""
    rets = [r for r in (forward_return(closes, calendar, c, date, h)
                        for c in closes.get(date, {})) if r is not None]
    return st.mean(rets) if rets else None


# --------------------------------------------------------------------------- #
# Cohorts
# --------------------------------------------------------------------------- #

def load_gate_cohorts(runs_dir=None) -> dict:
    """{date: {"gate": [...], "in_band": [...], "over_extended": [...]}}.

    One run per date — afternoon when present. A stock with no RPS120 lands in
    `gate` only: an absent measurement is neither in-band nor over-extended.
    """
    chosen: dict[str, tuple] = {}
    for date, slot, run_dir in run_paths.iter_run_dirs(Path(runs_dir or RUNS_DIR)):
        f = run_dir / "input" / "intersect.json"
        if not f.exists():
            continue
        if date not in chosen or slot == "afternoon":
            chosen[date] = (slot, f)

    out = {}
    for date, (_slot, f) in chosen.items():
        stocks = json.loads(f.read_text(encoding="utf-8")).get("stocks") or []
        if not stocks:
            continue
        gate, in_band, over = [], [], []
        for s in stocks:
            code = str(s.get("code", "")).split(".")[0]
            if not code:
                continue
            gate.append(code)
            rps = s.get("rps120")
            if isinstance(rps, (int, float)):
                (over if rps > RPS_CEILING else in_band).append(code)
        out[date] = {"gate": gate, "in_band": in_band, "over_extended": over}
    return out


def load_trades(tracking_dir=None) -> tuple[list, list]:
    """(closed, open) trade dicts from tracking/. Read-only."""
    t = Path(tracking_dir or TRACKING_DIR)
    closed = [json.loads(Path(f).read_text(encoding="utf-8"))
              for f in sorted(glob.glob(str(t / "closed" / "*.json")))]
    pos = json.loads((t / "positions.json").read_text(encoding="utf-8"))
    return closed, list(pos.get("activePositions") or [])


def bought_by_date(trades) -> dict:
    """{entryDate: [code, ...]} over every trade with both fields."""
    out: dict[str, list] = {}
    for tr in trades:
        if tr.get("entryDate") and tr.get("code"):
            out.setdefault(tr["entryDate"], []).append(str(tr["code"]))
    return out


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #

def excess_series(closes, calendar, cohort_by_date, h, since=None,
                  bench_cache=None) -> dict:
    """{date: cohort_mean - universe_mean} for dates where both exist.

    `bench_cache` ({(date, h): mean}) lets several cohorts share one universe
    pass — it is ~5,500 returns per date, and every cohort needs the same one.
    """
    cache = {} if bench_cache is None else bench_cache
    out = {}
    for date, codes in sorted(cohort_by_date.items()):
        if since and date < since:
            continue
        rets = [r for r in (forward_return(closes, calendar, c, date, h)
                            for c in codes) if r is not None]
        if not rets:
            continue
        if (date, h) not in cache:
            cache[(date, h)] = universe_mean(closes, calendar, date, h)
        bench = cache[(date, h)]
        if bench is None:
            continue
        out[date] = st.mean(rets) - bench
    return out


def t_stat(values):
    """One-sample t against zero; None when undefined."""
    if len(values) < 2:
        return None
    sd = st.stdev(values)
    if sd == 0:
        return None
    return st.mean(values) / (sd / math.sqrt(len(values)))


def non_overlapping(dates, calendar, h) -> list:
    """Greedy subset of `dates` whose h-session windows do not overlap."""
    picked, next_ok = [], -1
    pos = {d: i for i, d in enumerate(calendar)}
    for d in sorted(dates):
        i = pos.get(d)
        if i is not None and i >= next_ok:
            picked.append(d)
            next_ok = i + h
    return picked


def skew(values):
    """Sample skewness (population moments). None below 3 obs."""
    if len(values) < 3:
        return None
    m = st.mean(values)
    sd = st.pstdev(values)
    if sd == 0:
        return None
    return sum((v - m) ** 3 for v in values) / len(values) / sd ** 3


def summarize_excess(series: dict, calendar, h) -> dict:
    vals = list(series.values())
    if not vals:
        return {"n_dates": 0}
    sparse = [series[d] for d in non_overlapping(series, calendar, h)]
    return {
        "n_dates": len(vals),
        "mean": st.mean(vals),
        "median": st.median(vals),
        "hit_pct": 100 * sum(v > 0 for v in vals) / len(vals),
        "t": t_stat(vals),
        "n_nonoverlap": len(sparse),
        "mean_nonoverlap": st.mean(sparse) if sparse else None,
        "t_nonoverlap": t_stat(sparse),
    }


def describe(vals) -> dict:
    if not vals:
        return {"n": 0}
    return {"n": len(vals), "mean": st.mean(vals), "median": st.median(vals),
            "win_pct": 100 * sum(v > 0 for v in vals) / len(vals),
            "stdev": st.stdev(vals) if len(vals) > 1 else None,
            "skew": skew(vals)}


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #

def optional_stopping(closes, calendar, closed_trades) -> dict:
    """Realized P&L vs the same trades held a fixed horizon from entry close.

    Realized returnPct is on raw fill prices (entry/exit intraday), so a
    dividend inside the hold costs it a little that the adjusted fixed-horizon
    number does not, and a noon fill differs from the close the fixed hold is
    anchored on (see `entry_fill_gap`). Each horizon compares only trades whose
    forward bar exists, so both columns always describe the same set; the
    paired difference is per trade, so its t is on the trade, not the date.
    """
    out = {}
    for h in HORIZONS:
        realized, fixed = [], []
        for tr in closed_trades:
            r = forward_return(closes, calendar, str(tr.get("code")),
                               tr.get("entryDate"), h)
            if r is None or tr.get("returnPct") is None:
                continue
            realized.append(float(tr["returnPct"]))
            fixed.append(r)
        diff = [a - b for a, b in zip(realized, fixed)]
        out[h] = {"realized": describe(realized), "fixed": describe(fixed),
                  "paired_diff_mean": st.mean(diff) if diff else None,
                  "paired_diff_t": t_stat(diff)}
    return out


def entry_fill_gap(conn, closed_trades) -> dict:
    """% from entryPrice (the fill) to that day's raw close.

    The fixed-horizon hold starts at the close, realized P&L at the fill; a
    positive gap means the fixed column starts that much behind for reasons
    that have nothing to do with exits. Raw close on purpose: it is compared
    with a raw fill on the same day, so no factor can intervene.
    """
    gaps = []
    for tr in closed_trades:
        if not tr.get("entryPrice"):
            continue
        row = conn.execute(
            "SELECT close FROM daily_prices WHERE code = ? AND date = ?",
            (str(tr.get("code")), tr.get("entryDate"))).fetchone()
        if row and row[0]:
            gaps.append((row[0] / float(tr["entryPrice"]) - 1) * 100)
    return describe(gaps)


def analyse(since=None, db_path=None, runs_dir=None, tracking_dir=None) -> dict:
    gates = load_gate_cohorts(runs_dir)
    closed, active = load_trades(tracking_dir)
    bought = bought_by_date(closed + active)

    cohorts = {name: {d: v[name] for d, v in gates.items()}
               for name in ("gate", "in_band", "over_extended")}
    cohorts["bought"] = bought

    first = min([d for c in cohorts.values() for d in c] or ["9999"])
    start = max(first, since) if since else first
    in_window = [t for t in closed if t.get("entryDate", "") >= start]
    conn = connect_ro(db_path)
    try:
        phantoms = phantom_dates(conn)
        closes = load_closes(conn, start)
        fill_gap = entry_fill_gap(conn, in_window)
    finally:
        conn.close()
    calendar = build_calendar(closes, phantoms)

    result = {"since": start, "phantom_sessions_dropped": sorted(phantoms),
              "run_dates": len([d for d in gates if d >= start]),
              "horizons": {}}
    bench_cache: dict = {}
    for h in HORIZONS:
        per = {}
        for name in COHORTS:
            series = excess_series(closes, calendar, cohorts[name], h,
                                   since=start, bench_cache=bench_cache)
            per[name] = summarize_excess(series, calendar, h)
        result["horizons"][h] = per

    result["optional_stopping"] = optional_stopping(closes, calendar, in_window)
    result["optional_stopping_holding_days"] = describe(
        [float(t["holdingDays"]) for t in in_window
         if t.get("holdingDays") is not None])
    result["entry_fill_gap"] = fill_gap
    return result


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def _f(x, fmt="+6.2f"):
    return format(x, fmt) if isinstance(x, (int, float)) else "   n/a"


def human(r):
    print(f"Run dates since {r['since']}: {r['run_dates']}   "
          f"phantom sessions dropped: {', '.join(r['phantom_sessions_dropped']) or 'none'}")
    print("\nEXCESS FORWARD DRIFT = cohort mean − universe mean, per date (%)\n")
    print(f"{'h':>3} {'cohort':14} {'n':>4} {'mean':>7} {'median':>7} {'hit%':>6} "
          f"{'t':>6} | {'n_no':>4} {'mean_no':>7} {'t_no':>6}")
    for h, per in r["horizons"].items():
        for name, s in per.items():
            if not s.get("n_dates"):
                print(f"{h:>3} {name:14} {0:>4}")
                continue
            print(f"{h:>3} {name:14} {s['n_dates']:>4} {_f(s['mean'], '+7.2f')} "
                  f"{_f(s['median'], '+7.2f')} {_f(s['hit_pct'], '6.1f')} "
                  f"{_f(s['t'], '+6.2f')} | {s['n_nonoverlap']:>4} "
                  f"{_f(s['mean_nonoverlap'], '+7.2f')} {_f(s['t_nonoverlap'], '+6.2f')}")
        print()
    print("(_no = non-overlapping dates, >= h sessions apart; the honest t for h>1)\n")

    print("OPTIONAL STOPPING — closed trades: realized P&L vs fixed-horizon hold (%)\n")
    hd = r["optional_stopping_holding_days"]
    if hd.get("n"):
        print(f"holdingDays: n={hd['n']} mean {hd['mean']:.1f} median {hd['median']:.1f}")
    fg = r["entry_fill_gap"]
    if fg.get("n"):
        print(f"entry fill -> same-day close: mean {fg['mean']:+.2f}% "
              f"median {fg['median']:+.2f}% (fixed column starts this far behind)")
    print()
    print(f"{'h':>3} {'':9} {'n':>4} {'mean':>7} {'median':>7} {'win%':>6} "
          f"{'stdev':>6} {'skew':>6}")
    for h, pair in r["optional_stopping"].items():
        for label in ("realized", "fixed"):
            d = pair[label]
            if not d.get("n"):
                print(f"{h:>3} {label:9} {0:>4}")
                continue
            print(f"{h:>3} {label:9} {d['n']:>4} {_f(d['mean'], '+7.2f')} "
                  f"{_f(d['median'], '+7.2f')} {_f(d['win_pct'], '6.1f')} "
                  f"{_f(d['stdev'], '6.2f')} {_f(d['skew'], '+6.2f')}")
        print(f"{'':3} realized−fixed per trade: {_f(pair['paired_diff_mean'], '+.2f')}  "
              f"t={_f(pair['paired_diff_t'], '+.2f')}")
        print()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--since", help="first run date to include (ISO)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    r = analyse(since=args.since)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    else:
        human(r)


if __name__ == "__main__":
    main()
