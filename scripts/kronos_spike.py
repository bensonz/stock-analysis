#!/usr/bin/env python3
"""
kronos_spike.py — audition Kronos (zero-shot) as the gate-pool picker.

SPIKE code: standalone, read-only against the price DB, writes scores to a
CSV. Not wired into the pipeline. Run with the DEDICATED venv (torch):

    /Users/bz/Work/Personal/Kronos/.venv-kronos/bin/python scripts/kronos_spike.py \
        --stride 3 --batch 64 --out /tmp/kronos_scores.csv

For every Nth gate-pool day, feeds each pool stock's last `lookback` adjusted
daily bars (OHLC ×factor; volume/amount raw) to Kronos-small and records the
predicted `pred_len`-session return from the sample-averaged path. Then
prints the daily rank-IC of that score vs realized forward returns, next to
RPS60's on the same days — the audition bar from docs/backtest/RESULTS.md:
RPS60 = -0.06 (inverted), random = 0.

The evaluation window (2026) postdates the model's release (2025-08), so
zero-shot scores here are genuinely out-of-sample.
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
KRONOS_REPO = Path("/Users/bz/Work/Personal/Kronos")
DB = REPO / "data" / "pricedb" / "ashare_prices.db"
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(KRONOS_REPO))


def load_ohlcva(db_path: str) -> dict:
    """Adjusted OHLC + raw volume/amount pivots on covered dates."""
    import price_adjust
    import rps_calculator

    conn = sqlite3.connect(db_path)
    try:
        price_adjust.ensure_adj_schema(conn)
        min_codes = rps_calculator._reference_date_min_codes(conn)
        cols = ", ".join(f"d.{c} * COALESCE(a.factor, 1.0) AS {c}"
                         for c in ("open", "high", "low", "close"))
        sql = (f"SELECT d.code AS code, d.date AS date, {cols}, "
               f"d.volume AS volume, d.amount AS amount "
               f"FROM daily_prices d{price_adjust.adj_join_sql()} "
               f"WHERE d.date IN (SELECT date FROM daily_prices "
               f"  GROUP BY date HAVING COUNT(DISTINCT code) >= {min_codes})")
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return {c: df.pivot(index="date", columns="code", values=c).sort_index()
            for c in ("open", "high", "low", "close", "volume", "amount")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=3, help="score every Nth pool day")
    ap.add_argument("--lookback", type=int, default=250)
    ap.add_argument("--pred-len", type=int, default=10)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--sample-count", type=int, default=3)
    ap.add_argument("--limit-days", type=int, default=None, help="sanity: only N days")
    ap.add_argument("--limit-pool", type=int, default=None, help="sanity: only N stocks/day")
    ap.add_argument("--model", default="NeoQuasar/Kronos-small")
    ap.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-base")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--out", default="/tmp/kronos_scores.csv")
    args = ap.parse_args()

    import base_rates
    panel = base_rates.get_panel(str(DB))
    gate = ((panel["rps60"] >= 80) & (panel["rps120"] >= 80)
            & (panel["rps250"] >= 80)).fillna(False)
    piv = load_ohlcva(str(DB))
    dates = list(piv["close"].index)

    pool_days = [d for d in dates
                 if gate.loc[d].sum() >= 50
                 and dates.index(d) >= args.lookback
                 and dates.index(d) + args.pred_len < len(dates)]
    score_days = pool_days[:: args.stride]
    if args.limit_days:
        score_days = score_days[: args.limit_days]
    print(f"pool days {len(pool_days)} → scoring {len(score_days)} "
          f"(stride {args.stride}), lookback {args.lookback}, "
          f"pred_len {args.pred_len}, sample_count {args.sample_count}",
          flush=True)

    from model import Kronos, KronosTokenizer, KronosPredictor
    tokenizer = KronosTokenizer.from_pretrained(args.tokenizer)
    model = Kronos.from_pretrained(args.model)
    model.eval()        # from_pretrained leaves training mode on; MPS SDPA
    tokenizer.eval()    # has no dropout kernel, and eval is correct anyway
    predictor = KronosPredictor(model, tokenizer, device=args.device, max_context=512)

    rows = []
    t_start = time.time()
    for di, d in enumerate(score_days):
        i = dates.index(d)
        ctx_dates = dates[i - args.lookback + 1: i + 1]
        fut_dates = dates[i + 1: i + 1 + args.pred_len]
        pool = list(gate.loc[d][gate.loc[d]].index)
        if args.limit_pool:
            pool = pool[: args.limit_pool]

        dfs, xts, yts, codes = [], [], [], []
        for code in pool:
            sub = pd.DataFrame({c: piv[c][code].reindex(ctx_dates).values
                                for c in ("open", "high", "low", "close",
                                          "volume", "amount")})
            if sub["close"].isna().sum() > args.lookback * 0.05:
                continue                        # too gappy for a clean context
            sub = sub.ffill().bfill()
            if sub.isna().any().any():
                continue
            dfs.append(sub)
            xts.append(pd.Series(pd.to_datetime(ctx_dates)))
            yts.append(pd.Series(pd.to_datetime(fut_dates)))
            codes.append(code)

        t0 = time.time()
        for s in range(0, len(dfs), args.batch):
            preds = predictor.predict_batch(
                df_list=dfs[s: s + args.batch],
                x_timestamp_list=xts[s: s + args.batch],
                y_timestamp_list=yts[s: s + args.batch],
                pred_len=args.pred_len,
                sample_count=args.sample_count, verbose=False)
            for code, sub, pred in zip(codes[s: s + args.batch],
                                       dfs[s: s + args.batch], preds):
                last = float(sub["close"].iloc[-1])
                rows.append({
                    "date": d, "code": code,
                    "kronos_ret": (float(pred["close"].iloc[-1]) / last - 1) * 100,
                    "kronos_min3": (float(pred["close"].iloc[:3].min()) / last - 1) * 100,
                })
        print(f"[{di + 1}/{len(score_days)}] {d}: {len(dfs)} stocks "
              f"in {time.time() - t0:.0f}s (total {(time.time() - t_start) / 60:.1f}m)",
              flush=True)
        pd.DataFrame(rows).to_csv(args.out, index=False)   # checkpoint each day

    # ---- verdict: daily rank-IC vs realized forward return, next to rps60 ----
    scores = pd.DataFrame(rows)
    closes = panel["closes"]
    fwd = (closes.shift(-args.pred_len) / closes - 1) * 100
    print("\ndate        n    IC(kronos)  IC(rps60)")
    ic_k, ic_r = [], []
    for d, grp in scores.groupby("date"):
        grp = grp.set_index("code")
        f = fwd.loc[d].reindex(grp.index).dropna()
        if len(f) < 30:
            continue
        k = float(grp.loc[f.index, "kronos_ret"].rank().corr(f.rank()))
        r = float(panel["rps60"].loc[d].reindex(f.index).rank().corr(f.rank()))
        ic_k.append(k)
        ic_r.append(r)
        print(f"{d}  {len(f):4d}  {k:+10.3f}  {r:+9.3f}")
    if ic_k:
        print(f"\nmean IC over {len(ic_k)} days:  kronos {np.mean(ic_k):+.3f}  "
              f"(pos {sum(x > 0 for x in ic_k)}/{len(ic_k)})   "
              f"rps60 {np.mean(ic_r):+.3f}")
    print(f"scores saved: {args.out}")


if __name__ == "__main__":
    main()
