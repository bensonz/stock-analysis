#!/usr/bin/env python3
"""
base_rates.py — Reference-class frequencies ("how often did this actually happen")
for deep-report risk quantification.

Philosophy: a probability claim needs a reference class and a count. This module
turns "概率：中" hand-waving into "该形态历史上 N 次中 X% 出现≥15%回撤" computed
deterministically from the local (dividend-adjusted) price DB and the exchange
disclosure tables. No LLM involvement — results are 〖内部数据〗-verifiable.

Guardrails against forking-path abuse: conditions are a FIXED MENU of named
configurations (not free-form filters), and the only knobs are horizon and
drawdown threshold from small fixed sets. Every result carries its sample
window and a Wilson 95% CI.

Technical configs replicate the production MA-RPS math exactly (MA10 of
adjusted closes, delta vs. lookback, cross-sectional percentile — see
rps_calculator.compute_ma_rps), vectorized over the whole (date × stock) panel.

Known caveats (also emitted in every result):
- Sample = our DB range (~2025+), essentially ONE market regime.
- Episodes are state-entry events (first day the condition turns true), which
  removes same-stock day-to-day duplication, but cross-stock episodes still
  cluster in time — the CI understates regime correlation.
"""

import math
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HORIZONS = (20, 60, 120)          # trading days
DRAWDOWNS = (10, 15, 20)          # percent
MA_PERIOD = 10

_PANEL_CACHE: dict = {}           # db_path -> feature panel dict


# --------------------------------------------------------------------------- #
# Panel construction (one bulk load, vectorized features)
# --------------------------------------------------------------------------- #
COVERAGE_FLOOR = 0.9  # of distinct codes — mirrors rps_calculator's reference-date rule


def _load_closes(db_path: str):
    """Adjusted-close panel: DataFrame(index=date, columns=code).

    Under-covered dates (partial fetch days — the DB has ~50 of them since
    2026-03) are DROPPED, mirroring production: rps_calculator excludes them
    from reference-date resolution and MA windows, so a faithful replication
    must too. Rolling windows below therefore run over covered sessions, and
    windows simply reach further back across a dropped day — exactly like
    _load_trading_dates.
    """
    import pandas as pd
    import price_adjust

    conn = sqlite3.connect(db_path)
    try:
        price_adjust.ensure_adj_schema(conn)
        total = conn.execute("SELECT COUNT(DISTINCT code) FROM daily_prices").fetchone()[0]
        min_codes = int(total * COVERAGE_FLOOR)
        sql = (
            f"SELECT d.code AS code, d.date AS date, "
            f"{price_adjust.adjusted_close_sql()} AS close "
            f"FROM daily_prices d{price_adjust.adj_join_sql()} "
            f"WHERE d.date IN (SELECT date FROM daily_prices "
            f"                 GROUP BY date HAVING COUNT(DISTINCT code) >= {min_codes})"
        )
        df = pd.read_sql_query(sql, conn)
    finally:
        conn.close()
    return df.pivot(index="date", columns="code", values="close").sort_index()


def _cross_rank_pct(df):
    """Row-wise percentile rank 0–100, matching compute_ma_rps:
    rank/(count-1)*100 with ordinal ranks; single-survivor rows get 50."""
    rank = df.rank(axis=1, method="first")
    count = df.notna().sum(axis=1)
    denom = (count - 1).clip(lower=1)
    pct = rank.sub(1, axis=0).div(denom, axis=0) * 100
    return pct.mask(df.notna() & (count == 1).values[:, None], 50.0)


def get_panel(db_path: str | None = None) -> dict:
    """Feature panel over the full DB: rps{20,60,120,250}, dist_ma10_pct,
    plus the raw close matrix. Cached per db_path."""
    if db_path is None:
        import pricedb
        db_path = str(pricedb.DB_PATH)
    if db_path in _PANEL_CACHE:
        return _PANEL_CACHE[db_path]

    closes = _load_closes(db_path)
    ma10 = closes.rolling(MA_PERIOD, min_periods=MA_PERIOD).mean()
    panel = {"closes": closes, "dist_ma10_pct": (closes / ma10 - 1.0) * 100}
    for lb in (20, 60, 120, 250):
        panel[f"rps{lb}"] = _cross_rank_pct(ma10 / ma10.shift(lb))
    _PANEL_CACHE[db_path] = panel
    return panel


# --------------------------------------------------------------------------- #
# Named configurations — the fixed menu
# --------------------------------------------------------------------------- #
def _cond_extended_high_momentum(p):
    return (p["rps60"] >= 90) & (p["dist_ma10_pct"] < 0)


def _cond_high_momentum_healthy(p):
    return (p["rps60"] >= 90) & (p["dist_ma10_pct"] >= 0)


def _cond_momentum_gate_pass(p):
    return (p["rps60"] >= 80) & (p["rps120"] >= 80) & (p["rps250"] >= 80)


TECHNICAL_CONFIGS = {
    "extended_high_momentum": (
        "高动量但短线破位：RPS60≥90 且 收盘价跌破MA10（强势股洗盘/出货形态）",
        _cond_extended_high_momentum,
    ),
    "high_momentum_healthy": (
        "高动量且结构健康：RPS60≥90 且 收盘价站上MA10（对照组）",
        _cond_high_momentum_healthy,
    ),
    "momentum_gate_pass": (
        "通过动量闸门：RPS60/120/250 全部≥80（我们的可买池条件）",
        _cond_momentum_gate_pass,
    ),
}


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple:
    """95% Wilson score interval for k hits out of n, in percent (2dp)."""
    if n == 0:
        return (0.0, 100.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, center - half) * 100, 2),
            round(min(1.0, center + half) * 100, 2))


def technical_base_rate(config: str, horizon_days: int = 60, drawdown_pct: int = 15,
                        db_path: str | None = None) -> dict:
    """Frequency of a forward outcome after ENTERING a named technical state.

    Episode = first day the condition turns true for a stock (state entry).
    Outcomes over the next `horizon_days` sessions (t+1 .. t+H):
      - hit: minimum close falls >= drawdown_pct below the entry close
      - median end-of-horizon return (context: the other side of the coin)
    """
    if config not in TECHNICAL_CONFIGS:
        raise ValueError(f"unknown config {config!r}; menu: {sorted(TECHNICAL_CONFIGS)}")
    if horizon_days not in HORIZONS:
        raise ValueError(f"horizon_days must be one of {HORIZONS}")
    if drawdown_pct not in DRAWDOWNS:
        raise ValueError(f"drawdown_pct must be one of {DRAWDOWNS}")

    desc, cond_fn = TECHNICAL_CONFIGS[config]
    p = get_panel(db_path)
    closes = p["closes"]
    cond = cond_fn(p).fillna(False)
    entry = cond & ~cond.shift(1, fill_value=False)

    # forward min over t+1..t+H (reversed-rolling trick), and end-of-horizon close
    h = horizon_days
    fwd_min = closes.iloc[::-1].rolling(h, min_periods=h).min().iloc[::-1].shift(-1)
    fwd_min_ret = (fwd_min / closes - 1.0) * 100
    fwd_end_ret = (closes.shift(-h) / closes - 1.0) * 100

    mask = entry & fwd_min_ret.notna()
    n = int(mask.values.sum())
    hits = int((fwd_min_ret[mask] <= -drawdown_pct).values.sum())
    med = fwd_end_ret[mask].stack().median() if n else None

    dates = closes.index[mask.any(axis=1)]
    lo, hi = wilson_ci(hits, n)
    caveats = ("样本约一个市场周期（本地价格库范围）；跨个股的形态在时间上聚集，"
               "置信区间低估了行情相关性")
    if n and (dates.max()[:7] <= dates.min()[:7] or
              int(dates.max()[:4]) * 12 + int(dates.max()[5:7])
              - int(dates.min()[:4]) * 12 - int(dates.min()[5:7]) < 3):
        caveats += "；⚠️ 样本窗口不足3个月，仅代表单一行情阶段，参考价值有限"
    return {
        "config": config,
        "description": desc,
        "outcome": f"进入形态后{h}个交易日内最大回撤≥{drawdown_pct}%",
        "n_episodes": n,
        "n_hit": hits,
        "frequency_pct": round(hits / n * 100, 2) if n else None,
        "wilson95_pct": [lo, hi],
        "median_fwd_return_pct": round(float(med), 2) if med is not None else None,
        "sample_window": [str(dates.min()), str(dates.max())] if n else None,
        "caveats": caveats,
    }


# --------------------------------------------------------------------------- #
# Fundamental base rate: growth persistence
# --------------------------------------------------------------------------- #
def growth_persistence(min_growth_pct: float = 40.0, decel_below_pct: float = 20.0,
                       today=None) -> dict:
    """Of stocks reporting net-profit YoY >= min_growth_pct in one report period,
    how often does the NEXT period's (cumulative) YoY decelerate below
    decel_below_pct? Computed over consecutive disclosed 业绩报表 period pairs.

    The best-documented base rate in finance — high growth rarely persists —
    measured on A-shares directly instead of asserted.
    """
    import fundamentals

    periods = fundamentals.report_periods(today, n=8)  # newest first
    col = "净利润-同比增长"
    frames = {}
    for per in periods:
        df = fundamentals._load_table("yjbb", per)
        if df is not None and col in df.columns:
            frames[per] = df.set_index("股票代码")[col].apply(fundamentals._num).dropna()

    pairs = []
    avail = [p for p in periods if p in frames]  # newest first
    for newer, older in zip(avail, avail[1:]):
        pairs.append((older, newer))

    n = hits = 0
    for older, newer in pairs:
        high = frames[older][frames[older] >= min_growth_pct]
        nxt = frames[newer].reindex(high.index).dropna()
        n += len(nxt)
        hits += int((nxt < decel_below_pct).sum())

    lo, hi = wilson_ci(hits, n)
    return {
        "config": "growth_persistence",
        "description": (f"业绩持续性：某期归母净利同比≥{min_growth_pct:.0f}%的公司，"
                        f"下一报告期（累计口径）同比降速至{decel_below_pct:.0f}%以下的频率"),
        "n_episodes": n,
        "n_hit": hits,
        "frequency_pct": round(hits / n * 100, 2) if n else None,
        "wilson95_pct": [lo, hi],
        "periods_used": [f"{fundamentals.period_label(a)}→{fundamentals.period_label(b)}"
                         for a, b in pairs],
        "caveats": "同比为累计口径；样本期约两年；未剔除并表/非经常性损益带来的降速",
    }


def base_rate(config: str, horizon_days: int = 60, drawdown_pct: int = 15,
              db_path: str | None = None) -> dict:
    """Single entry point (the deep-report tool calls this)."""
    if config == "growth_persistence":
        return growth_persistence()
    return technical_base_rate(config, horizon_days, drawdown_pct, db_path)


if __name__ == "__main__":
    import json
    cfg = sys.argv[1] if len(sys.argv) > 1 else "extended_high_momentum"
    h = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    dd = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    print(json.dumps(base_rate(cfg, h, dd), ensure_ascii=False, indent=2))
