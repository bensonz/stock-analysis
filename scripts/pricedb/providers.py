"""
pricedb.providers — every network fetcher, and nothing that owns state.

Extracted from __init__.py on 2026-08-31, the last cut of the pricedb split.
This module is where the outside world enters: five active-or-retired provider
chains (iFinD, akshare, sina; eastmoney, tushare, baostock kept for forensics),
their retry/worker tuning, and the bulk-fetch orchestration over them.

Ownership rule for tests, learned the hard way on 2026-08-30 when a moved
function left a monkeypatch silently inert while the REAL fetcher ran inside a
test: **patch the module that owns the name.** Fetch internals now live here,
so tests that fake them patch `pricedb.providers`, not `pricedb`.

Three names are deliberately NOT owned here and are read late-bound through the
package namespace at call time (`from pricedb import X` inside the function):

  _budget_exceeded / _UPDATE_DEADLINE — mutable deadline set by cmd_update,
      patched by three test files on `pricedb`; both stay in __init__.
  SINA_REPAIR_SLEEP_SEC / SINA_REPAIR_WORKERS — shared with the repair path in
      __init__ and patched on `pricedb` by test_provider_chain.
  IFIND_BATCH_TIMEOUT_SEC — shared with the factor layer.

Everything else in here calls its siblings directly, like normal code.
"""

import json
import math
import os
import requests
import threading
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import ifind_client
from pricedb.bars import (
    _akshare_hist_row_to_tuple, _baostock_rows, _eastmoney_kline_to_tuple,
    _eastmoney_payload_to_rows, _eastmoney_kline_url, _eastmoney_secid, _exchange_from_code,
    _frame_close_series, _frame_empty, _ifind_tables_to_rows,
    _is_a_share_equity, _iso_to_yyyymmdd, _return_ratio_factors, _safe_float,
    _safe_int, _sina_symbol, _split_baostock_code, _split_tushare_code,
    _weekday_list, _yyyymmdd_to_iso,
)
from pricedb.storage import write_bars

AKSHARE_DEFAULT_WORKERS = 12

AKSHARE_RETRIES = 3

AKSHARE_RETRY_DELAY = 0.5

DATACENTER_EXDIV_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

EASTMONEY_CLIST_FIELDS = "f12,f14,f2,f3,f6,f15,f16,f17,f18,f5"

EASTMONEY_CLIST_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

EASTMONEY_CLIST_PAGE_SIZE = 50

EASTMONEY_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"

EASTMONEY_DEFAULT_WORKERS = 12

EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

EASTMONEY_RETRIES = 3

EASTMONEY_RETRY_DELAY = 0.5

IFIND_BAR_INDICATORS = "open,high,low,close,volume,amount"

IFIND_BATCH_CODES = int(os.getenv("IFIND_BATCH_CODES", "1000"))

PRICEDB_CALL_TIMEOUT_SEC = float(os.getenv("PRICEDB_CALL_TIMEOUT", "30"))

PROVIDER_BAOSTOCK = "baostock"

PROVIDER_EASTMONEY = "eastmoney_direct"

PROVIDER_EASTMONEY_CLIST = "eastmoney_clist"

PROVIDER_IFIND = "ifind"

PROVIDER_TUSHARE = "tushare"

SINA_HFQ_URL = "https://finance.sina.com.cn/realstock/company/{sym}/hfq.js"

SINA_KLINE_URL = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/x=/"
                  "CN_MarketDataService.getKLineData")

TUSHARE_RETRIES = 3

TUSHARE_RETRY_DELAY = 0.5

TUSHARE_TOKEN_ENV_NAMES = ("TUSHARE_TOKEN", "TUSHARE_PRO_TOKEN", "TS_TOKEN")

_PROXY_ENV_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy",
)

class _TimeoutError(RuntimeError):
    """Raised when a pricedb network call exceeds PRICEDB_CALL_TIMEOUT_SEC."""

def _run_with_timeout(label: str, func, timeout: float | None = None):
    """Run func() in a daemon thread; raise _TimeoutError if it exceeds `timeout`.

    The hung thread is abandoned (daemon), so the process can still exit;
    sockets will be reaped by the OS on process teardown.
    """
    if timeout is None:
        timeout = PRICEDB_CALL_TIMEOUT_SEC

    result: list = [None]
    error: list[BaseException | None] = [None]

    def _target():
        try:
            result[0] = func()
        except BaseException as e:
            error[0] = e

    t = threading.Thread(target=_target, name=f"pricedb:{label}", daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        raise _TimeoutError(f"{label} exceeded {timeout:.0f}s timeout")

    if error[0] is not None:
        raise error[0]

    return result[0]

@contextmanager
def _no_proxy_env():
    """Temporarily force DIRECT connections for libraries we don't control.

    Why: Surge and similar local proxies intercept *.eastmoney.com and break
    price fetches. Stripping HTTP(S)_PROXY is NOT enough on macOS — python
    `requests` falls back to the *system* proxy configuration
    (urllib.request.getproxies), which routed the factor backfill through a
    local Privoxy that collapsed under load ("Unable to connect to proxy").
    Setting NO_PROXY='*' wins over both env and system config in requests'
    should_bypass_proxies check, making the bypass actually stick.
    """
    touched = set(_PROXY_ENV_KEYS) | {
        "HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
        "NO_PROXY", "no_proxy",
    }
    saved = {k: os.environ.get(k) for k in touched}  # snapshot BEFORE mutating
    for k in _PROXY_ENV_KEYS:
        os.environ.pop(k, None)
    # Escape hatch: PRICEDB_FORCE_PROXY=<url> routes price fetches THROUGH a
    # proxy instead of bypassing it — used when the direct IP is throttled by
    # a provider and the user has routed the proxy's exit appropriately
    # (e.g. Clash global mode). Explicit opt-in only; default stays direct.
    forced = os.getenv("PRICEDB_FORCE_PROXY", "").strip()
    if forced:
        os.environ["HTTP_PROXY"] = forced
        os.environ["HTTPS_PROXY"] = forced
        os.environ["http_proxy"] = forced
        os.environ["https_proxy"] = forced
        os.environ.pop("NO_PROXY", None)
        os.environ.pop("no_proxy", None)
    else:
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

def _positive_int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        print(f"  Ignoring invalid {name}={value!r}; using {default}", file=sys.stderr)
        return default
    if parsed < 1:
        print(f"  Ignoring invalid {name}={value!r}; using {default}", file=sys.stderr)
        return default
    return parsed

def _read_env_file() -> dict[str, str]:
    from pricedb import ENV_FILE  # late-bound, owned by __init__
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values

def fetch_trade_dates_free(beg: str, end: str) -> list[str]:
    """Fetch open trading dates [beg, end] inclusive using akshare (no auth).

    beg/end: 'YYYYMMDD'. Returns sorted list of 'YYYYMMDD' strings.
    Falls back to weekday-only list if akshare fails.
    """
    try:
        import akshare as ak
    except Exception as e:
        print(f"  akshare not available for trade calendar: {e}", file=sys.stderr)
        return _weekday_list(beg, end)

    try:
        with _no_proxy_env():
            df = _run_with_timeout(
                "akshare trade_cal",
                lambda: ak.tool_trade_date_hist_sina(),
            )
    except Exception as e:
        print(f"  akshare trade_cal failed: {e}", file=sys.stderr)
        return _weekday_list(beg, end)

    if df is None or getattr(df, "empty", True):
        return _weekday_list(beg, end)

    col = "trade_date" if "trade_date" in getattr(df, "columns", []) else df.columns[0]
    dates: list[str] = []
    for raw in df[col]:
        if hasattr(raw, "strftime"):
            s = raw.strftime("%Y%m%d")
        else:
            s = str(raw).replace("-", "").strip()[:8]
        if len(s) == 8 and s.isdigit() and beg <= s <= end:
            dates.append(s)
    return sorted(dates)

def get_tushare_token() -> str | None:
    """Get Tushare token from env or `.env`."""
    for name in TUSHARE_TOKEN_ENV_NAMES:
        value = os.getenv(name)
        if value:
            return value.strip()

    file_values = _read_env_file()
    for name in TUSHARE_TOKEN_ENV_NAMES:
        value = file_values.get(name)
        if value:
            return value.strip()

    return None

def iter_providers() -> Iterable[tuple[str, object]]:
    """Yield available providers in preferred price-bar order.

    Doctrine (2026-08-25, user decision): **iFinD primary, AkShare → Sina
    fallback.** We now hold a paid iFinD seat, and it beat the free chain on
    every axis measured in docs/IFIND_EVAL/FINDINGS.md — 1320/1320 bars matched
    the local DB exactly, the full universe pulls in 2.4s against ~30s for the
    sina snapshot, and it carries `amount`, which the sina path writes as NULL.

    The free chain is deliberately KEPT behind it rather than retired: iFinD is
    a single commercial dependency whose token can lapse, and db_health gates
    the pipeline, so a vendor outage with no fallback would hard-stop the run.

    Supersedes the 2026-08-01 "AkShare primary, Sina fallback" doctrine, which
    followed the eastmoney IP-throttle outage. eastmoney direct/clist, baostock
    and tushare remain RETIRED for price bars — do not re-add them. Their
    fetchers survive only as internal helpers (factor derivation, f18 same-day
    sync, repair fallbacks). See docs/pricedb_repair/PROGRESS.md.
    """
    from pricedb import PROVIDER_AKSHARE, PROVIDER_SINA  # late-bound, owned by __init__
    if ifind_client.is_available():
        yield PROVIDER_IFIND, None
    else:
        print("  iFinD unavailable (no IFIND_REFRESH_TOKEN) — falling back",
              file=sys.stderr)
    try:
        with _no_proxy_env():
            import akshare as ak
        yield PROVIDER_AKSHARE, ak
    except Exception as e:
        print(f"  Could not initialize AkShare: {e}", file=sys.stderr)
    yield PROVIDER_SINA, None

def close_provider(provider_name: str, provider: object):
    """Close provider resources if needed."""
    if provider_name == PROVIDER_BAOSTOCK:
        try:
            _run_with_timeout("BaoStock logout", lambda: provider.logout(), timeout=5)
        except Exception:
            pass

def _fetch_eastmoney_json_urllib(url: str) -> str:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "close",
            "User-Agent": "Mozilla/5.0 pricedb-eastmoney-direct",
        },
    )
    with opener.open(request, timeout=PRICEDB_CALL_TIMEOUT_SEC) as response:
        return response.read().decode("utf-8")

def _fetch_eastmoney_json_curl(url: str) -> str:
    # Honors PRICEDB_FORCE_PROXY: curl's TLS fingerprint differs from python's,
    # which matters when a provider fingerprint-blocks the python stack.
    proxy = os.getenv("PRICEDB_FORCE_PROXY", "").strip()
    completed = subprocess.run(
        [
            "curl",
            "-sS",
            "--max-time",
            str(max(1, int(PRICEDB_CALL_TIMEOUT_SEC))),
            "-H",
            "User-Agent: Mozilla/5.0 pricedb",
            "-x",
            proxy,  # "" == explicit no-proxy (curl treats empty as direct)
            url,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=PRICEDB_CALL_TIMEOUT_SEC + 2,
    )
    return completed.stdout

def _fetch_eastmoney_json(url: str) -> dict:
    if os.getenv("PRICEDB_FORCE_PROXY", "").strip():
        # python's urllib shares the (potentially blocked) python TLS
        # fingerprint — in forced-proxy mode go straight to curl
        raw = _run_with_timeout("Eastmoney curl", lambda: _fetch_eastmoney_json_curl(url))
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"eastmoney curl returned non-JSON: {raw[:80]!r}") from e
    try:
        raw = _run_with_timeout("Eastmoney urllib", lambda: _fetch_eastmoney_json_urllib(url))
    except Exception as urllib_error:
        try:
            raw = _run_with_timeout("Eastmoney curl", lambda: _fetch_eastmoney_json_curl(url))
        except Exception as curl_error:
            raise RuntimeError(f"urllib failed: {urllib_error}; curl failed: {curl_error}") from curl_error

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"invalid Eastmoney JSON: {e}") from e

def _fetch_klines_eastmoney(stock: dict, beg: str, end: str) -> list[tuple]:
    secid = _eastmoney_secid(stock)
    if not secid:
        return []
    payload = _fetch_eastmoney_json(_eastmoney_kline_url(secid, beg, end))
    return _eastmoney_payload_to_rows(stock, payload)

def _fetch_klines_eastmoney_with_retries(stock: dict, beg: str, end: str) -> list[tuple]:
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    last_error: BaseException | None = None
    for attempt in range(EASTMONEY_RETRIES):
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        try:
            return _fetch_klines_eastmoney(stock, beg, end)
        except Exception as e:
            last_error = e
            if attempt == EASTMONEY_RETRIES - 1:
                raise RuntimeError(f"Eastmoney hist {stock['code']} failed: {e}") from e
            time.sleep(EASTMONEY_RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"Eastmoney hist {stock['code']} failed: {last_error}")

def _bulk_fetch_eastmoney(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    _provider,
):
    """Bulk fetch daily bars from Eastmoney with bounded worker concurrency."""
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    if not stocks:
        print("  Total: 0 rows inserted", file=sys.stderr)
        return

    supported_count = sum(1 for stock in stocks if _eastmoney_secid(stock))
    if supported_count == 0:
        print("  Eastmoney: no supported SH/SZ symbols in universe", file=sys.stderr)
        print("  Total: 0 rows inserted", file=sys.stderr)
        return

    workers = min(_positive_int_from_env("PRICEDB_EASTMONEY_WORKERS", EASTMONEY_DEFAULT_WORKERS), len(stocks))
    total_inserted = 0
    completed = 0
    next_index = 0
    failures: list[str] = []
    futures = {}

    def submit_next(executor: ThreadPoolExecutor):
        nonlocal next_index
        if next_index >= len(stocks):
            return
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        stock = stocks[next_index]
        next_index += 1
        future = executor.submit(_fetch_klines_eastmoney_with_retries, stock, beg, end)
        futures[future] = stock

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pricedb-eastmoney") as executor:
        for _ in range(workers):
            submit_next(executor)

        while futures:
            if _budget_exceeded():
                for future in futures:
                    future.cancel()
                raise RuntimeError("update budget exceeded")

            done, _pending = wait(futures, timeout=1.0, return_when=FIRST_COMPLETED)
            if not done:
                continue

            for future in done:
                stock = futures.pop(future)
                completed += 1
                try:
                    rows = future.result()
                except Exception as e:
                    failures.append(f"{stock['code']}: {e}")
                    rows = []

                if rows:
                    write_bars(conn, rows)
                    total_inserted += len(rows)

                if completed % 100 == 0 or completed == len(stocks):
                    print(
                        f"  [Eastmoney {completed}/{len(stocks)}] last: {stock['code']} -> {len(rows)} rows",
                        file=sys.stderr,
                    )

                if next_index < len(stocks):
                    submit_next(executor)

    if failures:
        sample = "; ".join(failures[:5])
        print(f"  Eastmoney skipped {len(failures)} symbols after retries: {sample}", file=sys.stderr)
    if total_inserted == 0:
        if failures:
            raise RuntimeError(f"Eastmoney returned no rows; first failures: {'; '.join(failures[:3])}")
        raise RuntimeError(f"Eastmoney returned no rows for {supported_count} supported symbols")

    print(f"  Total: {total_inserted:,} rows inserted", file=sys.stderr)

def _eastmoney_clist_url(page: int) -> str:
    query = urllib.parse.urlencode(
        {
            "pn": page,
            "pz": EASTMONEY_CLIST_PAGE_SIZE,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "fs": EASTMONEY_CLIST_FS,
            "fields": EASTMONEY_CLIST_FIELDS,
        },
        safe=",:+",
    )
    return f"{EASTMONEY_CLIST_URL}?{query}"

def _fetch_clist_page(page: int) -> dict:
    """Fetch a single Eastmoney clist page, bypassing any local proxy."""
    import requests

    with _no_proxy_env():
        session = requests.Session()
        session.trust_env = False
        try:
            response = session.get(
                _eastmoney_clist_url(page),
                headers={
                    "Accept": "application/json,text/plain,*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "User-Agent": "Mozilla/5.0 pricedb-eastmoney-clist",
                },
                proxies={"http": "", "https": ""},
                timeout=PRICEDB_CALL_TIMEOUT_SEC,
            )
            response.raise_for_status()
            return response.json()
        finally:
            session.close()

def _iter_clist_diff(payload: dict):
    data = payload.get("data") or {}
    diff = data.get("diff")
    if isinstance(diff, list):
        return diff
    if isinstance(diff, dict):
        return list(diff.values())
    return []

def _parse_clist_page(payload: dict, target_date: str) -> list[tuple]:
    """Convert a clist JSON payload into (code, date, ohlcv) tuples for ``target_date``."""
    rows: list[tuple] = []
    for item in _iter_clist_diff(payload):
        if not isinstance(item, dict):
            continue
        code = str(item.get("f12") or "").strip()
        if not code or not code.isdigit():
            continue
        close_p = _safe_float(item.get("f2"))
        open_p = _safe_float(item.get("f17"))
        high_p = _safe_float(item.get("f15"))
        low_p = _safe_float(item.get("f16"))
        if close_p is None or close_p <= 0:
            continue
        if open_p is None or high_p is None or low_p is None:
            continue
        if open_p <= 0 or high_p <= 0 or low_p <= 0:
            continue
        volume = _safe_int(item.get("f5")) or 0
        amount = _safe_float(item.get("f6")) or 0.0
        rows.append((code, target_date, open_p, high_p, low_p, close_p, volume, amount))
    return rows

def _bulk_fetch_eastmoney_clist(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    _provider,
):
    """Bulk daily snapshot via Eastmoney clist.

    Single-day path only — if the caller requests a multi-day backfill, raise so
    the next provider (per-stock kline) takes over.
    """
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    if not stocks:
        print("  Total: 0 rows inserted", file=sys.stderr)
        return

    today_yyyymmdd = datetime.now().strftime("%Y%m%d")
    if beg != end:
        raise RuntimeError(
            f"eastmoney_clist supports single-day fetch only ({beg}→{end}); falling through to per-stock"
        )
    if end != today_yyyymmdd:
        raise RuntimeError(
            f"eastmoney_clist only fetches today's bar (asked {end}, today={today_yyyymmdd})"
        )

    target_iso = _yyyymmdd_to_iso(end)
    valid_codes = {stock["code"] for stock in stocks}

    if _budget_exceeded():
        raise RuntimeError("update budget exceeded")
    first_payload = _run_with_timeout(
        "Eastmoney clist page 1",
        lambda: _fetch_clist_page(1),
    )
    data = first_payload.get("data") or {}
    total = int(data.get("total") or 0)
    if total == 0:
        raise RuntimeError("eastmoney_clist returned 0 records on page 1")
    total_pages = (total + EASTMONEY_CLIST_PAGE_SIZE - 1) // EASTMONEY_CLIST_PAGE_SIZE
    all_rows: list[tuple] = list(_parse_clist_page(first_payload, target_iso))

    workers = _positive_int_from_env("PRICEDB_CLIST_WORKERS", EASTMONEY_DEFAULT_WORKERS)
    failures: list[str] = []
    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pricedb-clist") as executor:
            futures = {
                executor.submit(_fetch_clist_page, page): page
                for page in range(2, total_pages + 1)
            }
            while futures:
                if _budget_exceeded():
                    for f in futures:
                        f.cancel()
                    raise RuntimeError("update budget exceeded")
                done, _pending = wait(futures, timeout=1.0, return_when=FIRST_COMPLETED)
                if not done:
                    continue
                for future in done:
                    page = futures.pop(future)
                    try:
                        payload = future.result()
                    except Exception as e:
                        failures.append(f"page {page}: {e}")
                        continue
                    all_rows.extend(_parse_clist_page(payload, target_iso))

    filtered = [row for row in all_rows if row[0] in valid_codes]
    if not filtered:
        raise RuntimeError(
            f"eastmoney_clist parsed {len(all_rows)} rows but none matched known universe ({len(valid_codes)} codes)"
        )

    write_bars(conn, filtered)
    if failures:
        print(f"  clist: {len(failures)} page(s) failed: {failures[0]}", file=sys.stderr)
    print(
        f"  [Clist] {len(filtered):,} rows inserted for {target_iso} "
        f"({total_pages} pages, {total} total records)",
        file=sys.stderr,
    )

def _call_tushare(label: str, func):
    """Call a Tushare API with retries and per-call timeout."""
    last_error: BaseException | None = None
    for attempt in range(TUSHARE_RETRIES):
        try:
            return _run_with_timeout(label, func)
        except _TimeoutError as e:
            last_error = e
            # Don't sleep on timeout — the socket is dead, retry immediately
            # with a fresh call.
            if attempt == TUSHARE_RETRIES - 1:
                raise RuntimeError(f"{label} failed: {e}") from e
        except Exception as e:
            last_error = e
            if attempt == TUSHARE_RETRIES - 1:
                raise RuntimeError(f"{label} failed: {e}") from e
            time.sleep(TUSHARE_RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"{label} failed: {last_error}")

def fetch_stock_list_tushare(pro) -> list[dict]:
    """Fetch current A-share universe from Tushare stock_basic."""
    frame = _call_tushare(
        "Tushare stock_basic",
        lambda: pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,list_date",
        ),
    )
    if _frame_empty(frame):
        raise RuntimeError("Tushare stock_basic returned no rows")

    stocks = []
    for row in frame.itertuples(index=False):
        ts_code = getattr(row, "ts_code", "")
        code, exchange = _split_tushare_code(ts_code)
        if exchange not in {"SH", "SZ", "BJ"} or not code or not _is_a_share_equity(code, exchange):
            continue
        stocks.append(
            {
                "code": code,
                "name": getattr(row, "name", code),
                "exchange": exchange,
                "listed_date": _yyyymmdd_to_iso(getattr(row, "list_date", None)),
            }
        )

    return stocks

def fetch_trade_dates_tushare(pro, beg: str, end: str) -> list[str]:
    """Fetch open trading days from Tushare trade_cal."""
    frame = _call_tushare(
        "Tushare trade_cal",
        lambda: pro.trade_cal(
            exchange="SSE",
            start_date=beg,
            end_date=end,
            is_open="1",
            fields="cal_date,is_open",
        ),
    )
    if _frame_empty(frame):
        return []

    dates = [str(getattr(row, "cal_date")) for row in frame.itertuples(index=False)]
    return sorted(dates)

def _bulk_fetch_tushare(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    pro,
):
    """Bulk fetch all daily bars using Tushare `daily(trade_date=...)`."""
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    # Use akshare's free trade calendar instead of Tushare trade_cal,
    # which most free-tier accounts can no longer access.
    trade_dates = fetch_trade_dates_free(beg, end)
    if not trade_dates:
        raise RuntimeError(f"No trading dates returned for {beg} → {end}")

    valid_codes = {stock["code"] for stock in stocks}
    total_inserted = 0

    for index, trade_date in enumerate(trade_dates, start=1):
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        frame = _call_tushare(
            f"Tushare daily {trade_date}",
            lambda trade_date=trade_date: pro.daily(
                trade_date=trade_date,
                fields="ts_code,trade_date,open,high,low,close,vol,amount",
            ),
        )
        rows = []
        if not _frame_empty(frame):
            for row in frame.itertuples(index=False):
                code, _exchange = _split_tushare_code(getattr(row, "ts_code", ""))
                if code not in valid_codes:
                    continue
                open_price = _safe_float(getattr(row, "open", None))
                high_price = _safe_float(getattr(row, "high", None))
                low_price = _safe_float(getattr(row, "low", None))
                close_price = _safe_float(getattr(row, "close", None))
                if None in (open_price, high_price, low_price, close_price):
                    continue
                volume = _safe_int(getattr(row, "vol", None))
                amount = _safe_float(getattr(row, "amount", None))
                rows.append(
                    (
                        code,
                        _yyyymmdd_to_iso(getattr(row, "trade_date", None)),
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        int(volume * 100) if volume is not None else 0,
                        float(amount * 1000) if amount is not None else 0.0,
                    )
                )

        if rows:
            write_bars(conn, rows)
            total_inserted += len(rows)

        if index % 20 == 0 or index == len(trade_dates):
            print(
                f"  [Tushare {index}/{len(trade_dates)}] {trade_date} → {len(rows)} rows",
                file=sys.stderr,
            )
        time.sleep(0.12)

    print(f"  Total: {total_inserted:,} rows inserted", file=sys.stderr)

def _fetch_klines_akshare(ak, stock: dict, beg: str, end: str) -> list[tuple]:
    with _no_proxy_env():
        frame = _run_with_timeout(
            f"AkShare hist {stock['code']}",
            lambda: ak.stock_zh_a_hist(
                symbol=stock["code"],
                period="daily",
                start_date=beg,
                end_date=end,
                adjust="",
            ),
        )
    if _frame_empty(frame):
        return []

    rows = []
    for _, row in frame.iterrows():
        normalized = _akshare_hist_row_to_tuple(stock, row)
        if normalized is not None:
            rows.append(normalized)
    return rows

def _fetch_klines_akshare_with_retries(ak, stock: dict, beg: str, end: str) -> list[tuple]:
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    last_error: BaseException | None = None
    for attempt in range(AKSHARE_RETRIES):
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        try:
            return _fetch_klines_akshare(ak, stock, beg, end)
        except Exception as e:
            last_error = e
            if attempt == AKSHARE_RETRIES - 1:
                raise RuntimeError(f"AkShare hist {stock['code']} failed: {e}") from e
            time.sleep(AKSHARE_RETRY_DELAY * (attempt + 1))
    raise RuntimeError(f"AkShare hist {stock['code']} failed: {last_error}")

def _bulk_fetch_akshare(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    ak,
):
    """Bulk fetch daily bars from AkShare with bounded worker concurrency."""
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    if not stocks:
        print("  Total: 0 rows inserted", file=sys.stderr)
        return

    workers = min(_positive_int_from_env("PRICEDB_AKSHARE_WORKERS", AKSHARE_DEFAULT_WORKERS), len(stocks))
    total_inserted = 0
    completed = 0
    next_index = 0
    failures: list[str] = []
    futures = {}

    def submit_next(executor: ThreadPoolExecutor):
        nonlocal next_index
        if next_index >= len(stocks):
            return
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        stock = stocks[next_index]
        next_index += 1
        future = executor.submit(_fetch_klines_akshare_with_retries, ak, stock, beg, end)
        futures[future] = stock

    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pricedb-akshare") as executor:
        for _ in range(workers):
            submit_next(executor)

        while futures:
            if _budget_exceeded():
                for future in futures:
                    future.cancel()
                raise RuntimeError("update budget exceeded")

            done, _pending = wait(futures, timeout=1.0, return_when=FIRST_COMPLETED)
            if not done:
                continue

            for future in done:
                stock = futures.pop(future)
                completed += 1
                try:
                    rows = future.result()
                except Exception as e:
                    failures.append(f"{stock['code']}: {e}")
                    rows = []

                if rows:
                    write_bars(conn, rows)
                    total_inserted += len(rows)

                if completed % 100 == 0 or completed == len(stocks):
                    print(
                        f"  [AkShare {completed}/{len(stocks)}] last: {stock['code']} → {len(rows)} rows",
                        file=sys.stderr,
                    )

                if next_index < len(stocks):
                    submit_next(executor)

    if failures:
        sample = "; ".join(failures[:5])
        print(f"  AkShare skipped {len(failures)} symbols after retries: {sample}", file=sys.stderr)
    if total_inserted == 0 and failures:
        raise RuntimeError(f"AkShare returned no rows; first failures: {'; '.join(failures[:3])}")

    print(f"  Total: {total_inserted:,} rows inserted", file=sys.stderr)

def fetch_stock_list_baostock(bs) -> list[dict]:
    """Fetch current A-share universe from BaoStock query_all_stock."""
    rows: list[dict] = []
    for offset in range(10):
        day = (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d")
        with _no_proxy_env():
            rows = _baostock_rows(
                _run_with_timeout(
                    f"BaoStock query_all_stock {day}",
                    lambda day=day: bs.query_all_stock(day=day),
                )
            )
        if rows:
            break

    if not rows:
        raise RuntimeError("BaoStock query_all_stock returned no rows")

    stocks = []
    for row in rows:
        code_full = row.get("code", "")
        code, exchange = _split_baostock_code(code_full)
        if exchange not in {"SH", "SZ", "BJ"} or not code or not _is_a_share_equity(code, exchange):
            continue
        stocks.append(
            {
                "code": code,
                "name": row.get("code_name") or row.get("name") or code,
                "exchange": exchange,
                "listed_date": _yyyymmdd_to_iso(row.get("ipoDate")),
            }
        )

    return stocks

def _fetch_klines_baostock(bs, stock: dict, beg: str, end: str) -> list[tuple]:
    code_prefix = stock["exchange"].lower()
    code_full = f"{code_prefix}.{stock['code']}"
    with _no_proxy_env():
        result = _run_with_timeout(
            f"BaoStock k_data {stock['code']}",
            lambda: bs.query_history_k_data_plus(
                code_full,
                "date,code,open,high,low,close,volume,amount",
                start_date=_yyyymmdd_to_iso(beg),
                end_date=_yyyymmdd_to_iso(end),
                frequency="d",
                adjustflag="3",
            ),
        )
    rows = []
    for row in _baostock_rows(result):
        open_price = _safe_float(row.get("open"))
        high_price = _safe_float(row.get("high"))
        low_price = _safe_float(row.get("low"))
        close_price = _safe_float(row.get("close"))
        if None in (open_price, high_price, low_price, close_price):
            continue
        rows.append(
            (
                stock["code"],
                row.get("date"),
                open_price,
                high_price,
                low_price,
                close_price,
                _safe_int(row.get("volume")) or 0,
                _safe_float(row.get("amount")) or 0.0,
            )
        )
    return rows

def _bulk_fetch_baostock(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    bs,
):
    """Bulk fetch daily bars from BaoStock, one stock at a time."""
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import _budget_exceeded
    total_inserted = 0
    consecutive_empty = 0
    EARLY_ABORT_THRESHOLD = 100  # bail if first N stocks all return 0 rows

    for index, stock in enumerate(stocks, start=1):
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        rows = _fetch_klines_baostock(bs, stock, beg, end)
        if rows:
            write_bars(conn, rows)
            total_inserted += len(rows)
            consecutive_empty = 0
        else:
            consecutive_empty += 1

        if consecutive_empty >= EARLY_ABORT_THRESHOLD and total_inserted == 0:
            print(
                f"  [BaoStock] {EARLY_ABORT_THRESHOLD} consecutive stocks returned 0 rows — data not available yet, aborting early",
                file=sys.stderr,
            )
            break

        if index % 100 == 0 or index == len(stocks):
            print(
                f"  [BaoStock {index}/{len(stocks)}] last: {stock['code']} → {len(rows)} rows",
                file=sys.stderr,
            )

    print(f"  Total: {total_inserted:,} rows inserted", file=sys.stderr)

def fetch_stock_list_akshare(ak) -> list[dict]:
    """Full A-share universe (code, name) via akshare; exchange from prefix."""
    with _no_proxy_env():
        df = _run_with_timeout(
            "AkShare stock list", lambda: ak.stock_info_a_code_name()
        )
    if _frame_empty(df):
        return []
    out = []
    for _, row in df.iterrows():
        code = str(row.get("code") or "").strip().zfill(6)
        name = str(row.get("name") or "").strip()
        if code.isdigit() and len(code) == 6 and name:
            out.append({"code": code, "name": name,
                        "exchange": _exchange_from_code(code)})
    return out

def fetch_stock_list(provider_name: str, provider: object) -> list[dict]:
    from pricedb import PROVIDER_AKSHARE  # late-bound, owned by __init__
    if provider_name == PROVIDER_AKSHARE:
        return fetch_stock_list_akshare(provider)
    if provider_name == PROVIDER_TUSHARE:
        return fetch_stock_list_tushare(provider)
    if provider_name == PROVIDER_BAOSTOCK:
        return fetch_stock_list_baostock(provider)
    raise ValueError(f"Unknown provider: {provider_name}")

def _bulk_fetchers() -> dict:
    """{provider_name: bulk-fetch callable}, built fresh so tests can patch the
    individual functions on this module and still be seen.

    Only the first three are in `iter_providers` and reachable from the daily
    chain. The rest are RETIRED for price bars (see the doctrine note there) and
    stay callable for manual forensics only — do not put them back in the chain.
    """
    from pricedb import PROVIDER_AKSHARE, PROVIDER_SINA  # late-bound, owned by __init__
    return {
        PROVIDER_IFIND: _bulk_fetch_ifind,
        PROVIDER_AKSHARE: _bulk_fetch_akshare,
        PROVIDER_SINA: _bulk_fetch_sina,
        PROVIDER_TUSHARE: _bulk_fetch_tushare,
        PROVIDER_EASTMONEY_CLIST: _bulk_fetch_eastmoney_clist,
        PROVIDER_EASTMONEY: _bulk_fetch_eastmoney,
        PROVIDER_BAOSTOCK: _bulk_fetch_baostock,
    }

def bulk_fetch(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    provider_name: str,
    provider: object,
    *,
    dispatch: dict | None = None,
):
    """Route a fetch to its provider.

    `dispatch` is an injection seam for tests: pass {name: fake} to exercise the
    provider chain — fallback order, budget aborts, error propagation — without
    monkeypatching private fetch functions by name. Patching internals is what
    the pricedb split set out to stop needing, and it is fragile in a specific
    way: on 2026-08-30 a function moved modules and a `monkeypatch.setattr` went
    silently inert, so the REAL fetcher ran inside a test.

    Production never passes it, so the live path is the table below, unchanged.
    """
    table = dispatch if dispatch is not None else _bulk_fetchers()
    fn = table.get(provider_name)
    if fn is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    return fn(conn, stocks, beg, end, provider)

def _backfill_from_akshare_spot(conn: sqlite3.Connection, date_iso: str) -> int:
    """Backfill a single day's prices from AkShare real-time spot data."""
    try:
        import akshare as ak

        with _no_proxy_env():
            df = _run_with_timeout("AkShare spot", lambda: ak.stock_zh_a_spot_em())
        if df is None or df.empty:
            return 0

        known_codes = {
            row[0] for row in conn.execute("SELECT code FROM stocks")
        }

        rows = []
        for _, r in df.iterrows():
            code = str(r.get("代码", ""))
            if code not in known_codes:
                continue
            import math
            open_p = r.get("今开")
            high_p = r.get("最高")
            low_p = r.get("最低")
            close_p = r.get("最新价")
            try:
                open_p, high_p, low_p, close_p = float(open_p), float(high_p), float(low_p), float(close_p)
            except (ValueError, TypeError):
                continue
            if any(math.isnan(v) for v in (open_p, high_p, low_p, close_p)):
                continue
            if close_p <= 0:
                continue
            import math
            raw_vol = r.get("成交量", 0)
            raw_amt = r.get("成交额", 0)
            volume = int(raw_vol) if raw_vol and not (isinstance(raw_vol, float) and math.isnan(raw_vol)) else 0
            amount = float(raw_amt) if raw_amt and not (isinstance(raw_amt, float) and math.isnan(raw_amt)) else 0.0
            rows.append((code, date_iso, open_p, high_p, low_p, close_p, volume, amount))

        if rows:
            write_bars(conn, rows)

        return len(rows)
    except Exception as e:
        print(f"  AkShare spot fallback failed: {e}", file=sys.stderr)
        return 0

def _kline_closes_eastmoney(secid: str, beg: str, end: str, fqt: int) -> dict:
    """{iso_date: close} straight from eastmoney's kline API (curl-capable
    transport, honors PRICEDB_FORCE_PROXY)."""
    query = urllib.parse.urlencode({
        "secid": secid,
        "fields1": "f1",
        "fields2": "f51,f53",  # date, close
        "klt": "101",
        "fqt": str(fqt),
        "beg": beg,
        "end": end,
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    })
    payload = _fetch_eastmoney_json(f"{EASTMONEY_KLINE_URL}?{query}")
    klines = ((payload or {}).get("data") or {}).get("klines") or []
    out: dict = {}
    for line in klines:
        parts = str(line).split(",")
        if len(parts) >= 2:
            close = _safe_float(parts[1])
            if close and close > 0:
                out[parts[0][:10]] = close
    return out

def fetch_adj_factor_events_sina(code: str, exchange: str) -> list[tuple] | None:
    """Sparse hfq factor EVENTS for one stock straight from Sina.

    Sina publishes the cumulative hfq factor series directly (one row per
    corporate action since listing) — no derivation needed, one tiny request
    per stock, from the provider this repo already trusts for realtime quotes.
    Returns [(iso_date, factor)] ascending, or None when unsupported/parse
    failure (caller falls back to derivation). Factors are absolute-scale
    (since listing); only within-stock ratios matter downstream, and dates
    before the first event correctly default to factor 1.0.
    """
    sym = _sina_symbol(code, exchange)
    if not sym:
        return None
    import requests
    with _no_proxy_env():
        resp = requests.get(
            SINA_HFQ_URL.format(sym=sym),
            headers={"User-Agent": "Mozilla/5.0 pricedb", "Referer": "https://finance.sina.com.cn"},
            timeout=PRICEDB_CALL_TIMEOUT_SEC,
        )
    if resp.status_code != 200 or "=" not in resp.text:
        return None
    try:
        # payload is `var xxhfq={...};/* signature */` — raw_decode takes the
        # first JSON value and ignores the trailing comment block
        payload, _ = json.JSONDecoder().raw_decode(resp.text.split("=", 1)[1].strip())
        events = [
            (str(item["d"])[:10], float(item["f"]))
            for item in (payload.get("data") or [])
            if item.get("d") and item.get("f")
        ]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None
    events.sort()
    return events

def _fetch_klines_sina(stock: dict, datalen: int) -> list[tuple]:
    """Recent daily bars for one stock from Sina's kline service.

    Raw/unadjusted prices (verified against stored eastmoney bars, including
    the ex-div open drop on 601818 2026-07-30). Volume arrives in shares and
    is stored as 手 (÷100) to match the eastmoney convention; Sina does not
    publish turnover amount, so `amount` is NULL. Standard 8-tuples.
    """
    sym = _sina_symbol(stock["code"], stock.get("exchange", ""))
    if not sym:
        return []
    import requests
    with _no_proxy_env():
        resp = requests.get(
            SINA_KLINE_URL,
            params={"symbol": sym, "scale": "240", "ma": "no",
                    "datalen": str(datalen)},
            headers={"User-Agent": "Mozilla/5.0 pricedb",
                     "Referer": "https://finance.sina.com.cn"},
            timeout=PRICEDB_CALL_TIMEOUT_SEC,
        )
    text = resp.text
    if resp.status_code != 200 or "(" not in text:
        raise RuntimeError(f"sina kline bad response for {sym} "
                           f"(status {resp.status_code})")
    try:
        data = json.loads(text[text.index("(") + 1: text.rindex(")")])
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"sina kline unparseable for {sym}: {e}")
    rows = []
    for item in data or []:
        day = str((item or {}).get("day") or "")[:10]
        close = _safe_float(item.get("close"))
        if not day or close is None:
            continue
        vol = _safe_float(item.get("volume"))
        rows.append((
            stock["code"], day,
            _safe_float(item.get("open")), _safe_float(item.get("high")),
            _safe_float(item.get("low")), close,
            int(vol / 100) if vol else None, None,
        ))
    return rows

def _bulk_fetch_sina(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    _provider,
):
    """Bulk daily bars via sina per-code klines (the fallback provider).

    INSERT OR IGNORE: whatever the primary already landed stays canonical
    (sina rows carry NULL amount). Respects the update budget; raises when a
    weekday window yields nothing so cmd_update can report a real failure.
    """
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import SINA_REPAIR_SLEEP_SEC, SINA_REPAIR_WORKERS, _budget_exceeded
    beg_iso, end_iso = _yyyymmdd_to_iso(beg), _yyyymmdd_to_iso(end)
    n_dates = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_prices WHERE date >= ?",
        (beg_iso,)
    ).fetchone()[0]
    datalen = min(1023, max(20, n_dates + 15))

    supported = [s for s in stocks if _sina_symbol(s["code"], s.get("exchange", ""))]
    print(f"  Sina: {len(supported)} supported symbols (datalen={datalen})",
          file=sys.stderr)

    def _one(stock):
        time.sleep(SINA_REPAIR_SLEEP_SEC)
        return _fetch_klines_sina(stock, datalen)

    inserted = 0
    completed = 0
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=SINA_REPAIR_WORKERS,
                            thread_name_prefix="pricedb-sina") as pool:
        futures = {pool.submit(_one, s): s for s in supported}
        for future in as_completed(futures):
            stock = futures[future]
            completed += 1
            if _budget_exceeded():
                for f in futures:
                    f.cancel()
                raise RuntimeError("update budget exceeded")
            try:
                rows = [r for r in future.result() if beg_iso <= r[1] <= end_iso]
            except Exception as e:
                failures.append(f"{stock['code']}: {str(e)[:60]}")
                rows = []
            if rows:
                inserted += write_bars(conn, rows, replace=False)
            if completed % 250 == 0 or completed == len(supported):
                print(f"  [Sina {completed}/{len(supported)}] "
                      f"+{inserted} rows, {len(failures)} failed",
                      file=sys.stderr)

    if failures:
        print(f"  Sina skipped {len(failures)} symbols: "
              f"{'; '.join(failures[:5])}", file=sys.stderr)
    if inserted == 0 and supported and _weekday_list(beg, end):
        raise RuntimeError(
            f"Sina returned no rows for {len(supported)} symbols in a "
            f"weekday window {beg}-{end}")
    if not supported:
        # e.g. a BJ-only backfill batch: nothing sina COULD fetch — vacuous
        # success, not a provider failure (akshare covers BJ when healthy).
        print("  Sina: no supported symbols in batch — nothing to do",
              file=sys.stderr)
    print(f"  Total: {inserted:,} rows inserted", file=sys.stderr)

def _bulk_fetch_ifind(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    _provider,
):
    """Bulk daily bars via iFinD — the primary provider since 2026-08-25.

    Batch-native, so this is far simpler than the per-code providers: the whole
    5207-code universe for one day lands in ~2.4s. Chunked here (rather than
    leaving it all to the client) so the update budget is checked between
    chunks and progress is reportable.

    INSERT OR IGNORE preserves first-writer-wins. Raises when a weekday window
    yields nothing, so cmd_update can report a real failure and fall through to
    akshare→sina.
    """
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import IFIND_BATCH_TIMEOUT_SEC, _budget_exceeded
    beg_iso, end_iso = _yyyymmdd_to_iso(beg), _yyyymmdd_to_iso(end)
    ths_to_code = {
        ifind_client.to_ths_code(s["code"], s.get("exchange")): s["code"]
        for s in stocks
    }
    all_ths = list(ths_to_code)
    print(f"  iFinD: {len(all_ths)} codes, {beg_iso} → {end_iso}", file=sys.stderr)

    client = ifind_client.get_client()
    chunk = IFIND_BATCH_CODES
    inserted = 0
    failures: list[str] = []

    for start in range(0, len(all_ths), chunk):
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        batch = all_ths[start:start + chunk]
        try:
            tables = _run_with_timeout(
                "iFinD history",
                lambda b=batch: client.history_quotation(
                    b, IFIND_BAR_INDICATORS, beg_iso, end_iso),
                timeout=IFIND_BATCH_TIMEOUT_SEC)
        except Exception as e:
            failures.append(f"{batch[0]}..{batch[-1]}: {str(e)[:80]}")
            continue

        rows = _ifind_tables_to_rows(tables, ths_to_code, beg_iso, end_iso)
        if rows:
            inserted += write_bars(conn, rows, replace=False)
        done = min(start + chunk, len(all_ths))
        print(f"  [iFinD {done}/{len(all_ths)}] +{inserted} rows, "
              f"{len(failures)} batches failed", file=sys.stderr)

    if failures:
        print(f"  iFinD failed {len(failures)} batch(es): "
              f"{'; '.join(failures[:3])}", file=sys.stderr)
    if inserted == 0 and all_ths and _weekday_list(beg, end):
        raise RuntimeError(
            f"iFinD returned no rows for {len(all_ths)} codes in a "
            f"weekday window {beg}-{end}")
    print(f"  Total: {inserted:,} rows inserted "
          f"(dataVol={client.data_vol:,})", file=sys.stderr)

def _fetch_clist_prev_close_map() -> dict:
    """{code: f18} from today's clist snapshot. f18 (昨收) is the exchange's
    ex-rights reference price — on an ex-div/split day it differs from the
    literal previous close, which is exactly the event signal we want."""
    out: dict = {}
    page = 1
    while True:
        payload = _fetch_clist_page(page)
        items = _iter_clist_diff(payload)
        if not items:
            break
        for item in items:
            if not isinstance(item, dict):
                continue
            code = str(item.get("f12") or "").strip()
            f18 = _safe_float(item.get("f18"))
            if code and code.isdigit() and f18 and f18 > 0:
                out[code] = f18
        if len(items) < EASTMONEY_CLIST_PAGE_SIZE:
            break
        page += 1
    return out

def _ifind_af_series(codes: list, ex_map: dict, beg: str, end: str) -> dict:
    """{code: {date: af}} from iFinD's ths_af_stock over [beg, end].

    `ths_af_stock` is iFinD's own cumulative adjustment factor. Note it uses a
    DIFFERENT base from ours (theirs is anchored at listing, ours at the start
    of our history), so absolute values are not interchangeable with the stored
    table — only ratios within one code are. Callers must respect that.
    """
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import IFIND_BATCH_TIMEOUT_SEC
    client = ifind_client.get_client()
    ths_to_code = {ifind_client.to_ths_code(c, ex_map.get(c)): c for c in codes}
    out: dict = {}
    batch = IFIND_BATCH_CODES
    all_ths = list(ths_to_code)
    for i in range(0, len(all_ths), batch):
        chunk = all_ths[i:i + batch]
        tables = _run_with_timeout(
            "iFinD af series",
            lambda c=chunk: client.date_sequence(
                c, [{"indicator": "ths_af_stock", "indiparams": [""]}], beg, end),
            timeout=IFIND_BATCH_TIMEOUT_SEC)
        for table in tables:
            code = ths_to_code.get(table.get("thscode"))
            if not code:
                continue
            afs = (table.get("table") or {}).get("ths_af_stock") or []
            series = {}
            for j, day in enumerate(table.get("time") or []):
                af = afs[j] if j < len(afs) else None
                if af:
                    series[str(day)[:10]] = af
            if series:
                out[code] = series
    return out

def _fetch_ex_div_codes_datacenter(date_iso: str) -> set | None:
    """Codes whose ex-dividend/ex-rights date is `date_iso`.

    Uses the eastmoney datacenter report API — a different host from the
    push2 clist endpoint, so it stays reachable when clist is throttled
    (the exact outage this function exists for). Returns None on fetch
    failure so the caller can distinguish "no events" from "couldn't ask".
    """
    import requests
    codes: set = set()
    page = 1
    while True:
        try:
            with _no_proxy_env():
                resp = requests.get(
                    DATACENTER_EXDIV_URL,
                    params={
                        "reportName": "RPT_SHAREBONUS_DET",
                        "columns": "SECURITY_CODE,EX_DIVIDEND_DATE",
                        "filter": f"(EX_DIVIDEND_DATE='{date_iso}')",
                        "pageSize": "500",
                        "pageNumber": str(page),
                    },
                    headers={"User-Agent": "Mozilla/5.0 pricedb"},
                    timeout=PRICEDB_CALL_TIMEOUT_SEC,
                )
            payload = resp.json()
        except Exception:
            return None
        rows = ((payload or {}).get("result") or {}).get("data") or []
        for item in rows:
            code = str((item or {}).get("SECURITY_CODE") or "").strip()
            if code.isdigit():
                codes.add(code)
        if len(rows) < 500:
            break
        page += 1
    return codes

def _snapshot_via_ifind(conn: sqlite3.Connection, codes: list, target: str):
    """Today's settled bar from iFinD's real-time feed. (rows, stats) or (None, None).

    Returns None to signal "fall back to sina" — a snapshot is best-effort by
    design, and the caller already has a working sina path.

    Applies the SAME guards as snapshot_bars.parse_quote_line, because the
    failure they prevent is identical: a suspended name keeps reporting its last
    session, and writing that stamped as today looks like real trading.

    Unit trap: `real_time_quotation` returns volume in 手 (lots) — already the
    stored convention — while `cmd_history_quotation` returns SHARES. Do not
    divide here; _bulk_fetch_ifind does. Verified 2026-08-25 on 600519
    (real-time 21111 lots vs history 2111118 shares).
    """
    # Late-bound: owned by __init__ (mutable/shared, patched on `pricedb`).
    from pricedb import IFIND_BATCH_TIMEOUT_SEC
    if not ifind_client.is_available():
        return None, None
    import snapshot_bars  # local, mirroring cmd_snapshot's import

    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}
    ths_to_code = {ifind_client.to_ths_code(c, ex_map.get(c)): c for c in codes}

    client = ifind_client.get_client()
    try:
        tables = _run_with_timeout(
            "iFinD snapshot",
            lambda: client.real_time(list(ths_to_code),
                                     "latest,open,high,low,volume,amount"),
            timeout=IFIND_BATCH_TIMEOUT_SEC)
    except Exception as e:
        print(f"  iFinD snapshot failed ({str(e)[:100]}) — falling back to sina",
              file=sys.stderr)
        return None, None

    rows, rejected = [], 0
    for table in tables:
        code = ths_to_code.get(table.get("thscode"))
        cols = table.get("table") or {}
        stamps = table.get("time") or []
        if not code or not stamps:
            rejected += 1
            continue

        # The feed's own timestamp must be today's session, at/after the close.
        stamp = str(stamps[0])
        if stamp[:10] != target or stamp[11:19] < snapshot_bars.SETTLE_AFTER:
            rejected += 1
            continue

        def _first(name):
            seq = cols.get(name) or []
            return seq[0] if seq else None

        o, h, low = _first("open"), _first("high"), _first("low")
        c = _first("latest")
        vol_lots, amount = _first("volume"), _first("amount")
        if None in (o, h, low, c) or not vol_lots:
            rejected += 1
            continue
        if min(o, h, low, c) <= 0 or vol_lots <= 0:
            rejected += 1                      # suspended / no trade
            continue
        if not (low <= min(o, c) and max(o, c) <= h):
            rejected += 1                      # incoherent bar, do not trust it
            continue
        rows.append((code, target, o, h, low, c, int(vol_lots), amount))

    stats = {"rows": len(rows), "skipped_unsupported": 0,
             "rejected": rejected, "failed_batches": 0}
    print(f"  iFinD snapshot: {len(rows)} bars parsed, {rejected} rejected "
          f"(dataVol={client.data_vol:,})", file=sys.stderr)
    if not rows:
        print("  iFinD snapshot returned nothing — falling back to sina",
              file=sys.stderr)
        return None, None
    return rows, stats
