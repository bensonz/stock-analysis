#!/usr/bin/env python3
"""
candidate_alpha.py — Does picking from the candidate list beat picking blindly?

Every run writes `output/candidates.md`: the screened pool, each row carrying its
RPS, its distance from MA5/10/20, and a Status the screen assigned. The LLM then
chooses a handful of those rows to actually buy. This script asks whether that
choice adds anything a coin flip would not.

Method
------
For every candidate ROW (date, code) we take the adjusted close on that run's
date and measure the forward return over a FIXED horizon — 5, 10 or 20 sessions.
Fixed horizons matter: measuring "to exit" would fold our own sell discipline
into the answer and tell us about the exit rule instead of the pick.

Every return is reported as EXCESS over 上证指数 across the identical window, so
a falling market cannot masquerade as a bad screen (in this sample the market is
roughly flat and the screen is not, which is the whole point).

Prices come from the same adjusted panel RPS uses (daily_prices ⋈ adj_factors),
so a dividend does not read as a drawdown.

The comparison population is the LLM's real entries — every closed trade plus
every open position — measured the same way, and the two means are compared with
a Welch t-test because the sample sizes differ by more than an order of
magnitude and eyeballing them would be self-deception.

What this does NOT measure
--------------------------
Entry selection only. Exits, position sizing, and the decision to stay in cash
are all out of scope — and when the candidate universe underperforms, staying in
cash is itself a source of return. `exit_ablation.py` covers the exit side.

Usage:
    python3 scripts/candidate_alpha.py --human
    python3 scripts/candidate_alpha.py --horizon 20 --json
"""

import glob
import json
import math
import re
import sqlite3
import statistics as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

DB_PATH = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"
INDEX_FILE = PROJECT_ROOT / "data" / "index_cache" / "sh000001.json"
HORIZONS = (5, 10, 20)

# A row's Status is the screen's own verdict. PASS is what it considers buyable;
# ⏳ means RPS above the 95 ceiling (ANALYST.md's sweet spot is 75-95); ❌ is a
# Rule 2b breach (extended far ABOVE the MA — chasing); 🔻 is the below-band
# warning, split out of ❌ on 2026-08-28.
#
# Rows written BEFORE that split carry the merged two-sided ❌, so historical ❌
# buckets mix both sides and are not directly comparable with post-split runs.
# Nothing back-fills them: rewriting a past run's artifact to match today's
# labelling would destroy the record of what the screen actually said that day.
PASS, WAIT, REJECT, BELOW = "✅", "⏳", "❌", "🔻"


def load_panel(db_path=None):
    """{code: [(date, adjusted_close)]} ascending — the basis RPS computes on."""
    import price_adjust

    conn = sqlite3.connect(str(db_path or DB_PATH))
    try:
        price_adjust.ensure_adj_schema(conn)
        sql = (f"SELECT d.code, d.date, {price_adjust.adjusted_close_sql()} "
               f"FROM daily_prices d{price_adjust.adj_join_sql()}")
        panel: dict[str, list] = {}
        for code, date, close in conn.execute(sql):
            if close is not None:
                panel.setdefault(code, []).append((date, close))
    finally:
        conn.close()
    for code in panel:
        panel[code].sort()
    return panel


def load_index(path=None):
    idx = json.loads(Path(path or INDEX_FILE).read_text(encoding="utf-8"))
    return idx, sorted(idx)


def parse_candidates(runs_dir=None):
    """[(date, code, rps120, dist_ma5, dist_ma20, status_class)] over every run.

    Columns are resolved from each file's OWN header, never by position. The
    table has had at least two shapes:

        …| RPS120 | RPS60 | Trend | Co | MA5% | MA10% | MA20% | Status |   (≤2026-05)
        …| RPS120 | RPS60 | MA5% | MA10% | MA20% | Status |               (current)

    Hardcoding indices silently reads MA5% as MA20% for ~80% of the archive —
    which is exactly what an earlier version of this script did, producing a
    distance-bucket table that mixed two different measurements. Status and
    RPS120 happened to survive (last column, and index 2 in both), so only the
    MA-distance breakdown was wrong; that is luck, not design.
    """
    root = Path(runs_dir or PROJECT_ROOT / "runs")
    rows = []
    for f in sorted(root.glob("**/candidates.md")):
        try:
            date = str(f.relative_to(root)).split("/")[0]
        except ValueError:
            continue
        cols: dict[str, int] | None = None
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] == "Code":
                cols = {name: i for i, name in enumerate(cells)}
                continue
            if not re.match(r"^\d{6}$", cells[0] if cells else ""):
                continue
            if not cols:
                continue          # data before a header we can trust: skip loudly-empty

            def col(name):
                i = cols.get(name)
                return _num(cells[i]) if i is not None and i < len(cells) else None

            status = cells[cols["Status"]] if "Status" in cols else ""
            rows.append((date, cells[0], col("RPS120"),
                         col("MA5%"), col("MA20%"), status[:1]))
    return rows


def _num(s):
    try:
        return float(str(s).replace("+", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def llm_picks(tracking_dir=None):
    """Every entry the LLM actually made: closed trades + still-open positions."""
    t = Path(tracking_dir or PROJECT_ROOT / "tracking")
    out = []
    for f in glob.glob(str(t / "closed" / "*.json")):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if d.get("entryDate") and d.get("code"):
            out.append((d["entryDate"], str(d["code"])))
    pos = json.loads((t / "positions.json").read_text(encoding="utf-8"))
    for p in pos.get("activePositions") or []:
        if p.get("entryDate") and p.get("code"):
            out.append((p["entryDate"], str(p["code"])))
    return out


def forward(panel, code, date, h):
    """Return over h sessions from the first close on/after `date`."""
    s = panel.get(code)
    if not s:
        return None
    i = next((k for k, (d, _) in enumerate(s) if d >= date), None)
    if i is None or i + h >= len(s) or not s[i][1]:
        return None
    return (s[i + h][1] / s[i][1] - 1) * 100


def index_forward(idx, idx_dates, date, h):
    i = next((k for k, d in enumerate(idx_dates) if d >= date), None)
    if i is None or i + h >= len(idx_dates):
        return None
    return (idx[idx_dates[i + h]] / idx[idx_dates[i]] - 1) * 100


def excess(panel, idx, idx_dates, items, h):
    """[stock_return - index_return] over the same window, for each (date, code)."""
    out = []
    for date, code in items:
        r = forward(panel, code, date, h)
        m = index_forward(idx, idx_dates, date, h)
        if r is not None and m is not None:
            out.append(r - m)
    return out


def describe(vals):
    if len(vals) < 8:
        return {"n": len(vals), "thin": True}
    return {"n": len(vals), "thin": False,
            "mean": st.mean(vals), "median": st.median(vals),
            "stdev": st.stdev(vals),
            "beat_pct": 100 * sum(1 for v in vals if v > 0) / len(vals)}


def cluster_by_code(panel, idx, idx_dates, items, h):
    """One observation per CODE, not per row.

    A name sits on the list for a median of 16 sessions (max 117), so the raw
    row count is not a sample size — the same stock's overlapping windows are
    near-duplicates of each other. Collapsing to a per-code mean first drops the
    effective n from thousands to hundreds and is the honest denominator for any
    confidence claim. The row-level numbers stay in the output because they are
    the right description of "what a random pick on a random day got"; these are
    the right basis for "how sure are we".
    """
    per: dict[str, list] = {}
    for date, code in items:
        r = forward(panel, code, date, h)
        m = index_forward(idx, idx_dates, date, h)
        if r is not None and m is not None:
            per.setdefault(code, []).append(r - m)
    return [st.mean(v) for v in per.values()]


def welch(a, b):
    """Two-sample t with unequal variances. n differs by ~20x here, so the
    pooled version would understate the standard error badly."""
    if len(a) < 3 or len(b) < 3:
        return None
    se = math.sqrt(st.variance(a) / len(a) + st.variance(b) / len(b))
    if se == 0:
        return None
    t = (st.mean(a) - st.mean(b)) / se
    return {"diff": st.mean(a) - st.mean(b), "se": se, "t": t,
            "significant": abs(t) >= 1.96}


def analyse(runs_dir=None, tracking_dir=None, db_path=None, index_file=None):
    panel = load_panel(db_path)
    idx, idx_dates = load_index(index_file)
    rows = parse_candidates(runs_dir)
    picks = llm_picks(tracking_dir)

    def sub(pred):
        return [(d, c) for d, c, _rps, _ma5, _ma20, s in rows if pred(s)]

    groups = {
        "blind_all": sub(lambda s: True),
        "blind_pass": sub(lambda s: s == PASS),
        "blind_wait_rps_over_95": sub(lambda s: s == WAIT),
        # Pre-2026-08-28 rows merge both sides into ❌; post-split runs separate
        # them. Grouping the two together keeps this series continuous across
        # the change rather than making it look like ❌ suddenly collapsed.
        "blind_ma_rejected": sub(lambda s: s in (REJECT, BELOW)),
        "blind_below_band_only": sub(lambda s: s == BELOW),
        "llm_picks": picks,
    }

    result = {"universe": {"candidate_rows": len(rows),
                           "distinct_codes": len({r[1] for r in rows}),
                           "distinct_dates": len({r[0] for r in rows}),
                           "llm_entries": len(picks)},
              "horizons": {}}

    for h in HORIZONS:
        ex = {k: excess(panel, idx, idx_dates, v, h) for k, v in groups.items()}
        cl = {k: cluster_by_code(panel, idx, idx_dates, v, h)
              for k, v in groups.items()}
        result["horizons"][h] = {
            "groups": {k: describe(v) for k, v in ex.items()},
            "clustered": {k: describe(v) for k, v in cl.items()},
            "llm_vs_blind_pass": welch(ex["llm_picks"], ex["blind_pass"]),
            "llm_vs_blind_pass_clustered": welch(cl["llm_picks"], cl["blind_pass"]),
        }

    # Is the MA gate actually helping? REJECT rows span every RPS level while
    # PASS rows are capped at 95, so a raw PASS-vs-REJECT comparison confounds
    # the two gates. Hold RPS fixed and vary only MA.
    result["ma_gate_holding_rps_fixed"] = {}
    for h in HORIZONS:
        cells = {}
        for lo, hi in ((75, 95), (95, 101)):
            for label, want_reject in (("ma_ok", False), ("ma_fail", True)):
                items = [(d, c) for d, c, rps, _ma5, _ma20, s in rows
                         if rps is not None and lo <= rps < hi
                         and (s in (REJECT, BELOW)) == want_reject]
                cells[f"rps{lo}_{hi}_{label}"] = describe(
                    excess(panel, idx, idx_dates, items, h))
        result["ma_gate_holding_rps_fixed"][h] = cells

    # If REJECT outperforms, is it mean reversion? Then the further below the
    # MA a name sits, the better it should do.
    result["ma20_distance_buckets"] = {}
    for h in HORIZONS:
        buckets = {}
        for lo, hi, name in ((-1e9, -20, "below_20pct"), (-20, -10, "below_10_20"),
                             (-10, 0, "below_0_10"), (0, 10, "above_0_10"),
                             (10, 1e9, "above_10pct")):
            items = [(d, c) for d, c, _rps, _ma5, ma, _s in rows
                     if ma is not None and lo <= ma < hi]
            buckets[name] = describe(excess(panel, idx, idx_dates, items, h))
        result["ma20_distance_buckets"][h] = buckets

    return result


def _fmt(d):
    if d.get("thin"):
        return f"n={d['n']:<5} (thin)"
    return (f"n={d['n']:<5} mean {d['mean']:+6.2f}%  med {d['median']:+6.2f}%  "
            f"beat {d['beat_pct']:5.1f}%")


def human(r):
    u = r["universe"]
    print(f"Candidate rows {u['candidate_rows']}  codes {u['distinct_codes']}  "
          f"dates {u['distinct_dates']}  |  LLM entries {u['llm_entries']}")
    print("\nEXCESS RETURN vs 上证指数 over the same window\n")
    for h in HORIZONS:
        print(f"--- horizon {h}d ---")
        for k, v in r["horizons"][h]["groups"].items():
            print(f"  {k:24} {_fmt(v)}")
        w = r["horizons"][h]["llm_vs_blind_pass"]
        if w:
            print(f"  → LLM vs blind PASS (rows): diff {w['diff']:+.2f}pt  t={w['t']:+.2f}  "
                  f"{'SIGNIFICANT' if w['significant'] else 'indistinguishable'}")
        print("  clustered one-obs-per-code (the honest denominator):")
        for k, v in r["horizons"][h]["clustered"].items():
            print(f"    {k:22} {_fmt(v)}")
        wc = r["horizons"][h]["llm_vs_blind_pass_clustered"]
        if wc:
            print(f"  → LLM vs blind PASS (clustered): diff {wc['diff']:+.2f}pt  "
                  f"t={wc['t']:+.2f}  "
                  f"{'SIGNIFICANT' if wc['significant'] else 'indistinguishable'}")
        print()
    print("MA GATE, HOLDING RPS FIXED (does MA alignment add anything?)\n")
    for h in HORIZONS:
        print(f"--- horizon {h}d ---")
        for k, v in r["ma_gate_holding_rps_fixed"][h].items():
            print(f"  {k:24} {_fmt(v)}")
        print()
    print("BY DISTANCE FROM MA20 (is REJECT outperformance mean reversion?)\n")
    for h in HORIZONS:
        print(f"--- horizon {h}d ---")
        for k, v in r["ma20_distance_buckets"][h].items():
            print(f"  {k:24} {_fmt(v)}")
        print()


def main():
    args = sys.argv[1:]
    r = analyse()
    if "--json" in args:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    else:
        human(r)


if __name__ == "__main__":
    main()
