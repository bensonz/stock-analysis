#!/usr/bin/env python3
"""regime_detector.py — read-only regime label for the daily report.

v1 (2026-08-04, commissioned after three independent measurements located
the same Apr-Jun-trend vs Jul-reversal boundary: the rank-IC audit, the
Stage-2 experiment matrix, and the cost-of-caution sign flip — see
docs/backtest/RESULTS.md and docs/WORKLOG_2026-07-27_to_07-31.md).

Two trailing, price-only components, both computed from the local DB
(base_rates panel — same math as production RPS):

  1. rolling rank-IC of rps60 within the momentum-gate pool
     (Spearman of signal rank vs forward-H-session return rank, averaged
     over the last IC_WINDOW resolved dates — "is momentum being paid?")
  2. trailing pool stop-rate (share of gate-pool names that fell
     STOP_PCT from close within STOP_HORIZON sessions — "is the pool
     getting people stopped out?")

Label rule v1.1 — 2-D, after the v1 1-D gate FAILED its pre-registered
answer key and the failure was diagnostic (2026-08-04 retro): April read
"reversal" under v1 because its rolling IC was genuinely negative
(-0.025) — yet its pool stop-rate was the LOWEST of Mar-Jul (0.22).
The components measure different dimensions: stop-rate = "is the pool
dangerous" (level), IC = "does the rps60 ranking work" (ordering). The
original answer key ("April = trend") came from cost-of-caution regret,
a LEVEL instrument. Hence three labels:

  逆风(回撤市)   — stop_rate > STOP_ELEVATED or rolling IC < IC_DEEP_NEG
                   (pool is dangerous; Jul reads 23/23, Mar too)
  顺风(趋势市)   — rolling IC > +IC_BAND and stop_rate ≤ STOP_ELEVATED
                   (ranking paid and pool safe; May-Jun)
  涨潮无序      — stop_rate ≤ STOP_ELEVATED and IC ≤ +IC_BAND
                   (pool safe but ranking has no edge; April — the month
                   where selectivity itself was the measured cost)

HONESTY NOTE: STOP_ELEVATED=0.40 and IC_DEEP_NEG=-0.05 were calibrated
ON the Mar-Jul sample after the v1 failure — they are post-hoc. The real
test is out-of-sample August+ live readings.

READ-ONLY BY DESIGN: rides into input/regime.json and a report section.
It is NOT in the LLM prompt and NO rule consumes it. Graduation path
(per three-tier doctrine): read-only → Tier-2 prompt advice → Tier-1
mechanical dials, each step gated on measured evidence.

Known limitation, stated upfront: trailing inputs flip AFTER turns. This
reduces mid-regime bleed; the event calendar remains the only early
instrument. `--retro` prints the validation table and the flip lag.
"""
import json
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import base_rates

IC_HORIZON = 5        # sessions of forward return the IC resolves against
IC_WINDOW = 20        # resolved dates averaged into the rolling IC
IC_BAND = 0.02        # deadband: |rolling IC| below this is noise
IC_DEEP_NEG = -0.05   # ordering this inverted = hostile on its own (post-hoc)
STOP_PCT = -5.0       # the hard-stop level the pool is tested against
STOP_HORIZON = 3      # sessions within which a stop counts
STOP_WINDOW = 10      # resolved dates averaged into the stop-rate
STOP_ELEVATED = 0.40  # ~p65 of Mar-Jul; separates Jul(min .38)/Mar(.39)
                      # from Apr/May(≤.30) (post-hoc calibration)

LABEL_TREND = "顺风(趋势市)"
LABEL_REVERSAL = "逆风(回撤市)"
LABEL_NEUTRAL = "涨潮无序(池安全但排序无效)"


def _gate_mask(panel):
    return ((panel["rps60"] >= 80) & (panel["rps120"] >= 80)
            & (panel["rps250"] >= 80))


def compute_ic_series(panel, horizon: int = IC_HORIZON) -> pd.Series:
    """Per-date Spearman rank-IC of rps60 vs forward return, gate pool only.
    A date's IC exists once its forward window has fully resolved."""
    closes = panel["closes"]
    fwd = closes.shift(-horizon) / closes - 1.0
    gate = _gate_mask(panel)
    out = {}
    for i, date in enumerate(closes.index):
        if i + horizon >= len(closes.index):
            break
        row_mask = gate.loc[date]
        pool = row_mask[row_mask].index
        if len(pool) < 30:
            continue
        sig = panel["rps60"].loc[date, pool]
        ret = fwd.loc[date, pool]
        ok = sig.notna() & ret.notna()
        if ok.sum() < 30:
            continue
        out[date] = sig[ok].rank().corr(ret[ok].rank())
    return pd.Series(out).sort_index()


def compute_stop_rate_series(panel, stop_pct: float = STOP_PCT,
                             horizon: int = STOP_HORIZON) -> pd.Series:
    """Per-date share of the gate pool whose low-side move from that close
    breached stop_pct within `horizon` sessions (close-to-close proxy —
    intraday lows are not in the panel)."""
    closes = panel["closes"]
    worst = closes.rolling(horizon).min().shift(-horizon)
    breach = (worst / closes - 1.0) * 100 <= stop_pct
    gate = _gate_mask(panel)
    out = {}
    for i, date in enumerate(closes.index):
        if i + horizon >= len(closes.index):
            break
        row_mask = gate.loc[date]
        pool = row_mask[row_mask].index
        if len(pool) < 30:
            continue
        out[date] = float(breach.loc[date, pool].mean())
    return pd.Series(out).sort_index()


def label_for(rolling_ic, stop_rate) -> str:
    if rolling_ic is None or stop_rate is None:
        return LABEL_NEUTRAL
    if stop_rate > STOP_ELEVATED or rolling_ic < IC_DEEP_NEG:
        return LABEL_REVERSAL
    if rolling_ic > IC_BAND:
        return LABEL_TREND
    return LABEL_NEUTRAL


def detect(db_path: str | None = None) -> dict:
    """Today's read-only regime block for the report."""
    panel = base_rates.get_panel(db_path)
    ic = compute_ic_series(panel)
    stops = compute_stop_rate_series(panel)
    rolling_ic = float(ic.tail(IC_WINDOW).mean()) if len(ic) else None
    ic_pos_days = int((ic.tail(IC_WINDOW) > 0).sum()) if len(ic) else 0
    stop_rate = float(stops.tail(STOP_WINDOW).mean()) if len(stops) else None
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "label": label_for(rolling_ic, stop_rate),
        "rolling_ic20": round(rolling_ic, 4) if rolling_ic is not None else None,
        "ic_positive_days": f"{ic_pos_days}/{min(IC_WINDOW, len(ic))}",
        "ic_last_resolved": str(ic.index[-1])[:10] if len(ic) else None,
        "pool_stop_rate10": round(stop_rate, 4) if stop_rate is not None else None,
        "params": {"ic_horizon": IC_HORIZON, "ic_window": IC_WINDOW,
                   "ic_band": IC_BAND, "stop_pct": STOP_PCT,
                   "stop_horizon": STOP_HORIZON,
                   "stop_elevated": STOP_ELEVATED},
        "read_only": True,
        "source": "内部复测 scripts/regime_detector.py (本地价格库可重算; --retro 验证)",
    }


def retro(db_path: str | None = None, start: str = "2026-03-01",
          end: str = "2026-07-31") -> pd.DataFrame:
    """Daily labels over [start, end] exactly as the live path would have
    seen them (only resolved dates enter each day's rolling windows)."""
    panel = base_rates.get_panel(db_path)
    ic = compute_ic_series(panel)
    stops = compute_stop_rate_series(panel)
    rows = []
    for date in panel["closes"].index:
        d = str(date)[:10]
        if not (start <= d <= end):
            continue
        ic_avail = ic[ic.index < date].tail(IC_WINDOW)
        st_avail = stops[stops.index < date].tail(STOP_WINDOW)
        r_ic = float(ic_avail.mean()) if len(ic_avail) >= 10 else None
        r_st = float(st_avail.mean()) if len(st_avail) >= 5 else None
        rows.append({"date": d, "rolling_ic": r_ic, "stop_rate": r_st,
                     "label": label_for(r_ic, r_st)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    if "--retro" in sys.argv:
        df = retro()
        df["month"] = df["date"].str[:7]
        print(df.groupby("month")["label"].value_counts().unstack(fill_value=0))
        print("\n7月标签逐日:")
        jul = df[df["month"] == "2026-07"]
        for _, r in jul.iterrows():
            ic_s = f"{r['rolling_ic']:+.3f}" if r["rolling_ic"] is not None else "  n/a"
            print(f"  {r['date']} ic20={ic_s} stop={r['stop_rate']:.2f} {r['label']}")
    else:
        out = detect()
        if "--human" in sys.argv:
            print(f"📉 市场机制读数 ({out['date']}) — 只读, 不接任何规则")
            print(f"  标签: {out['label']}")
            print(f"  RPS60滚动rank-IC({IC_WINDOW}日): {out['rolling_ic20']} "
                  f"(为正天数 {out['ic_positive_days']}, "
                  f"最近已结算日 {out['ic_last_resolved']})")
            print(f"  池内{STOP_HORIZON}日止损率({STOP_WINDOW}日均): "
                  f"{out['pool_stop_rate10']}")
        else:
            print(json.dumps(out, ensure_ascii=False, indent=2))
