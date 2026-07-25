#!/usr/bin/env python3
"""
fundamentals.py — Exchange-disclosure financials for any A-share, for deep reports.

Why this exists: the deep-report writer used to web_search peer financials and
the citation-verify pipeline (rightly) killed most of them — news articles
rarely contain the exact figure. This module provides the numbers from the
structured disclosure tables instead, so the writer can cite them as
〖内部数据〗 and the verifier can confirm them mechanically against DATA.

Sources (each degrades gracefully to None):
  - Eastmoney datacenter via akshare, one BULK call per report period, cached:
      业绩报表 stock_yjbb_em   — quarterly/annual results (revenue, profit, YoY,
                                 EPS, ROE, gross margin, OCF/share)
      业绩预告 stock_yjyg_em   — earnings preannouncements (type, range text,
                                 midpoint, prior-year, reason)
      业绩快报 stock_yjkb_em   — express reports
  - CheeseForTune summary     — PE/PB/PS, valuation percentile, scores
  - Local price DB            — RPS momentum (rps60/120/250)

Units: money is emitted in 亿元 rounded to 2dp and percents to 2dp — the same
forms a writer would cite — so deep_verify.flatten_data_numbers matches them
mechanically. Raw disclosure text is kept verbatim (its digit runs are also
flattened into the match set).
"""

import os
import re
import sys
import warnings
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# akshare's bulk pagers spam tqdm bars for minutes — we log one line per fetch
# instead. Must be set before tqdm is first imported (akshare imports it), and
# nothing in this repo imports tqdm earlier, so module-top is early enough.
os.environ.setdefault("TQDM_DISABLE", "1")

# (kind, period) -> DataFrame | None (None = fetch failed / table not yet published)
_TABLE_CACHE: dict = {}

_QUARTER_ENDS = ("0331", "0630", "0930", "1231")


def report_periods(today: _date | None = None, n: int = 6) -> list:
    """Most recent `n` quarter-end period strings, NEWEST first.

    Starts from the next quarter end AFTER today: preannouncements for a
    period are published weeks before the period's report (亿纬's 2026H1
    预告 landed 6/15), so the upcoming period must be probed too.
    """
    today = today or _date.today()
    ends = []
    for year in (today.year + 1, today.year, today.year - 1, today.year - 2):
        for q in reversed(_QUARTER_ENDS):
            ends.append(f"{year}{q}")
    # keep those <= the next quarter end after today
    nxt = next(p for p in reversed(ends) if p > today.strftime("%Y%m%d"))
    return [p for p in ends if p <= nxt][:n]


def period_label(period: str) -> str:
    """'20260331' -> '2026一季报' (report-speak the writer can cite)."""
    names = {"0331": "一季报", "0630": "中报", "0930": "三季报", "1231": "年报"}
    return f"{period[:4]}{names.get(period[4:], period[4:])}"


_KIND_LABELS = {"yjbb": "业绩报表", "yjyg": "业绩预告", "yjkb": "业绩快报"}


def _load_table(kind: str, period: str):
    """One bulk datacenter table, cached. Returns DataFrame or None.

    One log line per network fetch (cache hits are silent) — this replaces
    the tqdm bars, which were the only 'progress' a run showed for minutes.
    """
    import time

    key = (kind, period)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    print(f"  [fundamentals] {_KIND_LABELS.get(kind, kind)}({period}) fetching ...",
          file=sys.stderr, end="", flush=True)
    t0 = time.time()
    df = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import akshare as ak
            fn = {"yjbb": ak.stock_yjbb_em, "yjyg": ak.stock_yjyg_em,
                  "yjkb": ak.stock_yjkb_em}[kind]
            df = fn(date=period)
            if df is not None and len(df) == 0:
                df = None
    except Exception:
        df = None
    n = len(df) if df is not None else 0
    print(f" {n} rows ({time.time() - t0:.1f}s)", file=sys.stderr)
    _TABLE_CACHE[key] = df
    return df


def _rows_for(kind: str, period: str, code6: str) -> list:
    df = _load_table(kind, period)
    if df is None:
        return []
    try:
        return [r._asdict() if hasattr(r, "_asdict") else dict(r)
                for _, r in df[df["股票代码"] == code6].iterrows()]
    except Exception:
        return []


def _num(v):
    """NaN/None-safe float."""
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _yi(v):
    """Raw yuan -> 亿元, 2dp."""
    f = _num(v)
    return round(f / 1e8, 2) if f is not None else None


def _pct(v):
    f = _num(v)
    return round(f, 2) if f is not None else None


def _yjbb_block(row: dict, period: str) -> dict:
    return {
        "period": period_label(period),
        "revenue_亿元": _yi(row.get("营业总收入-营业总收入")),
        "revenue_yoy_pct": _pct(row.get("营业总收入-同比增长")),
        "net_profit_亿元": _yi(row.get("净利润-净利润")),
        "net_profit_yoy_pct": _pct(row.get("净利润-同比增长")),
        "eps_元": _num(row.get("每股收益")),
        "bvps_元": _num(row.get("每股净资产")),
        "roe_pct": _pct(row.get("净资产收益率")),
        "ocf_per_share_元": _num(row.get("每股经营现金流量")),
        "gross_margin_pct": _pct(row.get("销售毛利率")),
        "industry": row.get("所处行业"),
        "announced": str(row.get("最新公告日期") or ""),
    }


def _walk_first(kind: str, periods: list, code6: str):
    """First (rows, period) hit walking newest -> oldest."""
    for p in periods:
        rows = _rows_for(kind, p, code6)
        if rows:
            return rows, p
    return [], None


def _forecast_period_label(period: str) -> str:
    names = {"0331": "Q1", "0630": "H1", "0930": "Q1-Q3", "1231": "全年"}
    return f"{period[:4]}{names.get(period[4:], period[4:])}"


def _valuation(code: str) -> dict | None:
    try:
        from cheesefortune_client import CheeseFortuneClient, normalize_code
        full = code if "." in str(code) else normalize_code(code)
        s = CheeseFortuneClient().get_stock_summary(full) or {}
        keep = {k: s.get(k) for k in (
            "name", "pe", "pb", "ps_ttm", "pcf_ttm", "valuation_percentile",
            "score_company", "score_trend", "score_value") if s.get(k) is not None}
        return keep or None
    except Exception:
        return None


def _rps(code6: str) -> dict | None:
    try:
        import pricedb
        import rps_calculator
        rps = rps_calculator.get_ma_rps_for_stocks(str(pricedb.DB_PATH), [code6])
        t = (rps or {}).get(code6) or {}
        keep = {k: t.get(k) for k in ("rps60", "rps120", "rps250") if t.get(k) is not None}
        return keep or None
    except Exception:
        return None


def stock_snapshot(code: str, today: _date | None = None,
                   include_valuation: bool = True, include_rps: bool = True) -> dict:
    """Everything a deep report needs to cite exact numbers for one stock.

    Never raises; sections missing upstream are simply absent.
    """
    code6 = re.sub(r"\D", "", str(code).split(".")[0])[:6]
    periods = report_periods(today)
    out: dict = {
        "code": code6,
        "as_of": (today or _date.today()).strftime("%Y-%m-%d"),
        "source": "东方财富数据中心（交易所披露口径）",
        "unit_note": "金额单位为亿元（2位小数），比率为百分比数值",
    }

    rows, p = _walk_first("yjbb", periods, code6)
    if rows:
        out["latest_report"] = _yjbb_block(rows[0], p)
        out.setdefault("name", rows[0].get("股票简称"))
        # Most recent ANNUAL report too, if the latest hit wasn't one.
        if p and not p.endswith("1231"):
            arows, ap = _walk_first("yjbb", [q for q in periods if q.endswith("1231")], code6)
            if arows:
                out["annual_report"] = _yjbb_block(arows[0], ap)

    frows, fp = _walk_first("yjyg", periods, code6)
    if frows:
        out["forecast"] = [{
            "period": _forecast_period_label(fp),
            "type": r.get("预告类型"),
            "metric": r.get("预测指标"),
            "text": r.get("业绩变动"),
            "midpoint_亿元": _yi(r.get("预测数值")),
            "change_pct": _pct(r.get("业绩变动幅度")),
            "prior_year_亿元": _yi(r.get("上年同期值")),
            "reason": r.get("业绩变动原因"),
            "announced": str(r.get("公告日期") or ""),
        } for r in frows]
        out.setdefault("name", frows[0].get("股票简称"))

    krows, kp = _walk_first("yjkb", periods, code6)
    if krows:
        r = krows[0]
        out["express_report"] = {
            "period": period_label(kp),
            "revenue_亿元": _yi(r.get("营业收入-营业收入")),
            "revenue_yoy_pct": _pct(r.get("营业收入-同比增长")),
            "net_profit_亿元": _yi(r.get("净利润-净利润")),
            "net_profit_yoy_pct": _pct(r.get("净利润-同比增长")),
            "eps_元": _num(r.get("每股收益")),
            "roe_pct": _pct(r.get("净资产收益率")),
            "announced": str(r.get("公告日期") or ""),
        }
        out.setdefault("name", r.get("股票简称"))

    if include_valuation:
        v = _valuation(code)
        if v:
            out.setdefault("name", v.get("name"))
            v.pop("name", None)
            out["valuation"] = v
    if include_rps:
        r = _rps(code6)
        if r:
            out["technicals_rps"] = r

    if not any(k in out for k in ("latest_report", "forecast", "express_report")):
        out["note"] = "未在业绩报表/预告/快报中找到该代码（可能未披露或代码有误）"
    return out


if __name__ == "__main__":
    import json
    code = sys.argv[1] if len(sys.argv) > 1 else "002245"
    print(json.dumps(stock_snapshot(code), ensure_ascii=False, indent=2))
