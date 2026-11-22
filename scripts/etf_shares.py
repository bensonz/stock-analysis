"""Daily share counts of the broad-index ETFs 中央汇金 dominates — the proxy
for 国家队 buying shown in report.md (added 2026-11-22).

Why shares: an ETF's share count changes only through creation/redemption, so
a jump means net new money entered the fund. It does NOT name the buyer. The
link to 汇金 is that its two accounts (中央汇金投资 + 中央汇金资产管理) held
40–92% of each fund in WATCH at 2025-12-31, per each fund's 2025 annual
report (期末上市基金前十名持有人). The 2026 中期报告 dropped that table, so the
percentages cannot be refreshed from the same source; the report prints their
date beside them.

Sources — both free, both in 万份, both end-of-day:
- SSE: query.sse.com.cn ETF规模, one call per date, every ETF in it.
- SZSE: fund.szse.cn 基金规模, one call per fund for a date range.
akshare wraps both, but its SSE call has no timeout and raises KeyError on a
date with nothing published, and its SZSE call crashes on the installed pandas
and has no history — so this module calls the exchanges directly.

A session's count is published after that session closes (SZSE: T日晚间,
final on T+1 morning), so both daily slots normally show the previous session.
"""
import sqlite3
from pathlib import Path

import requests

from rps_calculator import _load_trading_dates

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"
HOLDER_ASOF = "2025-12-31"
# (code, exchange, name, 汇金's % of listed shares at HOLDER_ASOF)
WATCH = (
    ("510050", "SH", "上证50ETF华夏", 86.05),
    ("510180", "SH", "上证180ETF华安", 91.93),
    ("510300", "SH", "沪深300ETF华泰柏瑞", 82.76),
    ("510310", "SH", "沪深300ETF易方达", 84.88),
    ("510330", "SH", "沪深300ETF华夏", 88.62),
    ("159919", "SZ", "沪深300ETF嘉实", 86.97),
    ("510500", "SH", "中证500ETF南方", 74.58),
    ("512500", "SH", "中证500ETF华夏", 47.26),
    ("159922", "SZ", "中证500ETF嘉实", 44.32),
    ("512100", "SH", "中证1000ETF南方", 86.43),
    ("560010", "SH", "中证1000ETF广发", 91.86),
    ("159845", "SZ", "中证1000ETF华夏", 86.15),
    ("159915", "SZ", "创业板ETF易方达", 54.03),
    ("588080", "SH", "科创50ETF易方达", 41.95),
)
LONG_WINDOW = 5    # sessions for the longer change
ASOF_TRIES = 3     # newest sessions probed for a published count
TIMEOUT = 15
UA = {"User-Agent": "Mozilla/5.0"}


def fetch_sse(day: str) -> dict:
    """{code: 万份} for every SSE ETF at the close of `day`; {} when the
    exchange has published nothing for it (not yet, or not a session)."""
    r = requests.get(
        "https://query.sse.com.cn/commonQuery.do",
        params={"sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L", "STAT_DATE": day,
                "isPagination": "true", "pageHelp.pageSize": "10000",
                "pageHelp.pageNo": "1", "pageHelp.beginPage": "1",
                "pageHelp.cacheSize": "1", "pageHelp.endPage": "1"},
        headers={**UA, "Referer": "https://www.sse.com.cn/"}, timeout=TIMEOUT)
    r.raise_for_status()
    return {x["SEC_CODE"]: float(x["TOT_VOL"]) for x in r.json()["result"]}


def fetch_szse(code: str, beg: str, end: str) -> dict:
    """{date: 万份} for one SZSE fund, every session in [beg, end]."""
    r = requests.get(
        "https://fund.szse.cn/api/report/ShowReport/data",
        params={"SHOWTYPE": "JSON", "CATALOGID": "fund_jjgm", "TABKEY": "tab1",
                "txtDm": code, "txtStart": beg, "txtEnd": end},
        headers={**UA, "Referer": "https://fund.szse.cn/marketdata/fundslist/index.html"},
        timeout=TIMEOUT)
    r.raise_for_status()
    return {x["size_date"]: float(x["current_size"].replace(",", ""))
            for x in r.json()[0]["data"]}


def sse_series(dates: list) -> dict:
    """{code: {date: 万份}} for the SSE funds in WATCH on the three sessions
    the changes need: the newest published one, the one before it, and
    LONG_WINDOW back. `dates` is the trading calendar, newest first."""
    for i, day in enumerate(dates[:ASOF_TRIES]):
        latest = fetch_sse(day)
        if latest:
            break
    else:
        raise ValueError(f"上交所最近{ASOF_TRIES}个交易日均未公布ETF份额")
    by_date = {day: latest}
    for k in (1, LONG_WINDOW):
        by_date[dates[i + k]] = fetch_sse(dates[i + k])
    return {code: {d: v[code] for d, v in by_date.items() if code in v}
            for code, exchange, _, _ in WATCH if exchange == "SH"}


def changes(series: dict, dates: list) -> dict:
    """Newest published count in `series` {date: 万份} and its change over 1
    and LONG_WINDOW sessions of `dates` (newest first). A session the series
    lacks gives a None change, never a change against some other day."""
    have = [i for i, d in enumerate(dates) if d in series]
    if not have:
        return {"error": "区间内无份额数据"}
    i = have[0]
    now = series[dates[i]]

    def pct(k):
        past = series.get(dates[i + k]) if i + k < len(dates) else None
        return round((now / past - 1) * 100, 2) if past else None

    return {"asof": dates[i], "shares_wan": now,
            "chg1_pct": pct(1), "chg_long_pct": pct(LONG_WINDOW)}


def trading_dates(today: str, db_path: Path = DB_PATH) -> list:
    """The last ASOF_TRIES + LONG_WINDOW sessions up to today, newest first."""
    conn = sqlite3.connect(db_path)
    try:
        return _load_trading_dates(conn, today, ASOF_TRIES + LONG_WINDOW)
    finally:
        conn.close()


def collect(today: str) -> dict:
    """Pipeline entry point. Never raises: a fund whose fetch failed keeps its
    row with an `error`, and when nothing at all came back the whole block is
    {"error": ...} — the report says the data is missing instead of dropping
    the section."""
    try:
        dates = trading_dates(today)
        if len(dates) < ASOF_TRIES + LONG_WINDOW:
            return {"error": f"价格库只有{len(dates)}个交易日, 无法计算份额变化"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    try:
        sse, sse_error = sse_series(dates), None
    except Exception as e:
        sse, sse_error = {}, f"{type(e).__name__}: {e}"

    rows = []
    for code, exchange, name, huijin_pct in WATCH:
        row = {"code": code, "name": name, "exchange": exchange, "huijin_pct": huijin_pct}
        try:
            if exchange == "SH" and sse_error:
                row["error"] = sse_error
            else:
                series = sse[code] if exchange == "SH" else fetch_szse(code, dates[-1], dates[0])
                row.update(changes(series, dates))
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
        rows.append(row)

    asofs = [r["asof"] for r in rows if "asof" in r]
    if not asofs:
        return {"error": "; ".join(sorted({r["error"] for r in rows}))}
    return {"asof": max(asofs), "holder_asof": HOLDER_ASOF,
            "long_window": LONG_WINDOW, "rows": rows}
