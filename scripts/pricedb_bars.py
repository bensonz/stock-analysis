#!/usr/bin/env python3
"""
pricedb_bars.py — pure transforms for price bars. No I/O, no database, no clock.

Extracted from pricedb.py on 2026-08-30. Every function here maps one provider's
payload shape onto our row tuple, or normalises a code/date/number. None of them
opens a connection, makes a request, or reads the clock — which is the whole
point: they are testable against captured fixtures with **zero mocking**.

Before the split these lived inside a 3,649-line module whose import pulls in
ifind_client, akshare and the sqlite schema, so exercising a 7-line date
converter meant standing up the world. Tests reached for private names
(`_fetch_klines_sina`, `_fetch_clist_page`) because there was no seam to aim at.

Nothing in here should ever grow a `conn` argument or a network call. If a
transform starts needing one, it belongs in pricedb_storage or pricedb_providers
instead — that boundary is the reason this file is worth having.

Imported back into pricedb.py under the original names, so every existing caller
and test is untouched.
"""

import urllib.parse
from datetime import datetime, timedelta

EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

ADJ_EVENT_THRESHOLD = 0.005

def _weekday_list(beg: str, end: str) -> list[str]:
    """Generate Mon-Fri YYYYMMDD strings in [beg, end] (lossy fallback)."""
    try:
        start = datetime.strptime(beg, "%Y%m%d").date()
        stop = datetime.strptime(end, "%Y%m%d").date()
    except ValueError:
        return []
    out: list[str] = []
    d = start
    while d <= stop:
        if d.weekday() < 5:
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out

def _yyyymmdd_to_iso(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value)
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value

def _iso_to_yyyymmdd(value: str) -> str:
    return value.replace("-", "")

def _split_tushare_code(ts_code: str) -> tuple[str, str]:
    code, _, suffix = str(ts_code).partition(".")
    suffix = suffix.upper()
    exchange_map = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}
    return code, exchange_map.get(suffix, suffix or "")

def _split_baostock_code(code_full: str) -> tuple[str, str]:
    prefix, _, code = str(code_full).partition(".")
    prefix = prefix.lower()
    exchange_map = {"sh": "SH", "sz": "SZ", "bj": "BJ"}
    return code, exchange_map.get(prefix, prefix.upper())

def _safe_float(value) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _safe_int(value) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return int(round(numeric))

def _is_a_share_equity(code: str, exchange: str) -> bool:
    if exchange == "SH":
        return code.startswith(("600", "601", "603", "605", "688", "689"))
    if exchange == "SZ":
        return code.startswith(("000", "001", "002", "003", "300", "301"))
    if exchange == "BJ":
        return code.startswith(("4", "8", "92"))
    return False

def _frame_empty(frame) -> bool:
    return frame is None or bool(getattr(frame, "empty", False))

def _eastmoney_secid(stock: dict) -> str | None:
    code = str(stock.get("code") or "").strip()
    exchange = str(stock.get("exchange") or "").strip().upper()
    if not code:
        return None
    if exchange == "SH":
        return f"1.{code}"
    if exchange == "SZ":
        return f"0.{code}"
    if exchange == "BJ":
        return None
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"1.{code}"
    if code.startswith(("000", "001", "002", "003", "300", "301")):
        return f"0.{code}"
    return None

def _eastmoney_kline_url(secid: str, beg: str, end: str) -> str:
    query = urllib.parse.urlencode(
        {
            "secid": secid,
            "fields1": "f1",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",
            "fqt": "0",
            "beg": beg,
            "end": end,
        },
        safe=",",
    )
    return f"{EASTMONEY_KLINE_URL}?{query}"

def _eastmoney_kline_to_tuple(stock: dict, kline: str) -> tuple | None:
    parts = str(kline).split(",")
    if len(parts) < 7:
        return None

    date_iso = _yyyymmdd_to_iso(parts[0])
    open_price = _safe_float(parts[1])
    close_price = _safe_float(parts[2])
    high_price = _safe_float(parts[3])
    low_price = _safe_float(parts[4])
    if not date_iso or None in (open_price, high_price, low_price, close_price):
        return None

    return (
        stock["code"],
        date_iso,
        open_price,
        high_price,
        low_price,
        close_price,
        _safe_int(parts[5]) or 0,
        _safe_float(parts[6]) or 0.0,
    )

def _eastmoney_payload_to_rows(stock: dict, payload: dict) -> list[tuple]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    klines = data.get("klines")
    if not isinstance(klines, list):
        return []

    rows = []
    for kline in klines:
        normalized = _eastmoney_kline_to_tuple(stock, kline)
        if normalized is not None:
            rows.append(normalized)
    return rows

def _akshare_hist_row_to_tuple(stock: dict, row) -> tuple | None:
    getter = row.get
    open_price = _safe_float(getter("开盘"))
    high_price = _safe_float(getter("最高"))
    low_price = _safe_float(getter("最低"))
    close_price = _safe_float(getter("收盘"))
    if None in (open_price, high_price, low_price, close_price):
        return None

    raw_date = getter("日期")
    if raw_date is None:
        return None
    date_iso = _yyyymmdd_to_iso(str(raw_date))
    if not date_iso:
        return None

    return (
        stock["code"],
        date_iso,
        open_price,
        high_price,
        low_price,
        close_price,
        _safe_int(getter("成交量")) or 0,
        _safe_float(getter("成交额")) or 0.0,
    )

def _baostock_rows(result) -> list[dict]:
    """Convert a BaoStock ResultData object into dict rows."""
    error_code = getattr(result, "error_code", "0")
    if error_code != "0":
        raise RuntimeError(getattr(result, "error_msg", "BaoStock query failed"))

    fields = list(getattr(result, "fields", []) or [])
    rows: list[dict] = []
    while result.next():
        row = result.get_row_data()
        rows.append(dict(zip(fields, row)))
    return rows

def _exchange_from_code(code: str) -> str:
    if code.startswith(("6",)):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    return "BJ"

def _frame_close_series(frame) -> dict:
    """{iso_date: close} from an akshare hist frame."""
    out: dict = {}
    if _frame_empty(frame):
        return out
    for _, row in frame.iterrows():
        date_iso = str(row.get("日期"))[:10]
        close = _safe_float(row.get("收盘"))
        if len(date_iso) == 10 and close and close > 0:
            out[date_iso] = close
    return out

def _return_ratio_factors(raw_s: dict, hfq_s: dict) -> list[tuple]:
    """[(iso_date, factor)] from raw + adjusted close series.

    Any correctly-adjusted series works, additive or multiplicative: on a
    single day, (adj return) / (raw return) equals the corporate-action
    multiplier (1.0 on normal days). Thresholding kills rounding noise;
    cumprod rebuilds a proper multiplicative hfq factor, base 1.0 at start.
    """
    dates = sorted(set(raw_s) & set(hfq_s))
    if not dates:
        return []
    factor = 1.0
    out = [(dates[0], factor)]
    for prev, cur in zip(dates, dates[1:]):
        if raw_s[prev] <= 0 or hfq_s[prev] <= 0 or raw_s[cur] <= 0:
            m = 1.0
        else:
            m = (hfq_s[cur] / hfq_s[prev]) / (raw_s[cur] / raw_s[prev])
        if abs(m - 1.0) <= ADJ_EVENT_THRESHOLD:
            m = 1.0
        factor *= m
        out.append((cur, round(factor, 8)))
    return out

def _sina_symbol(code: str, exchange: str) -> str | None:
    exchange = (exchange or "").upper()
    if exchange == "SH" or code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"sh{code}"
    if exchange == "SZ" or code.startswith(("000", "001", "002", "003", "300", "301")):
        return f"sz{code}"
    return None

def _ifind_tables_to_rows(tables: list, ths_to_code: dict,
                          beg_iso: str, end_iso: str) -> list[tuple]:
    """Flatten iFinD history tables into pricedb's 8-tuples.

    Two conversions matter and both are silent if wrong:
      * volume arrives in SHARES; pricedb stores 手 (÷100), matching the
        eastmoney/sina convention already on disk.
      * `amount` is carried through — this is the whole point of the provider
        swap, since the sina snapshot path writes NULL there.
    """
    rows: list[tuple] = []
    for table in tables:
        code = ths_to_code.get(table.get("thscode"))
        if not code:
            continue
        cols = table.get("table") or {}
        dates = table.get("time") or []
        closes = cols.get("close") or []
        for i, day in enumerate(dates):
            day = str(day)[:10]
            if not (beg_iso <= day <= end_iso):
                continue
            close = closes[i] if i < len(closes) else None
            if close is None:
                continue  # suspended session — no bar to store

            def _at(name, idx=i):
                seq = cols.get(name) or []
                return seq[idx] if idx < len(seq) else None

            volume = _at("volume")
            rows.append((
                code, day, _at("open"), _at("high"), _at("low"), close,
                int(volume / 100) if volume else None, _at("amount"),
            ))
    return rows
