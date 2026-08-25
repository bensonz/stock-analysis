#!/usr/bin/env python3
"""
pricedb.py — Local A-share price database management.

SQLite-backed price history for all A-share stocks.
Data sources:
- Stock list: Tushare Pro when available, BaoStock fallback
- Price bars: Tushare Pro, Eastmoney direct fallback, AkShare historical daily fallback, BaoStock fallback

Usage:
    python scripts/pricedb.py init          # Create DB, fetch stock list, download ALL historical data
    python scripts/pricedb.py update        # Incremental update: fetch missing dates since last update
    python scripts/pricedb.py status        # Show DB stats: total stocks, date range, last update
    python scripts/pricedb.py rps [DATE]    # Compute MA-based RPS for all stocks on DATE (default: latest)
    python scripts/pricedb.py query CODE    # Show a stock's recent prices + computed RPS values
"""

import bisect
import contextlib
import os
import socket
import sqlite3
import sys
import threading
import time
import json
import subprocess
import urllib.parse
import urllib.request
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from datetime import date as _date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ifind_client
import price_adjust

PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "data" / "pricedb"
DB_PATH = DB_DIR / "ashare_prices.db"
ENV_FILE = PROJECT_ROOT / ".env"

PROVIDER_TUSHARE = "tushare"
PROVIDER_EASTMONEY_CLIST = "eastmoney_clist"
# Kept as "eastmoney_direct" for backwards compatibility (manifest references).
PROVIDER_EASTMONEY = "eastmoney_direct"
PROVIDER_AKSHARE = "akshare"
PROVIDER_BAOSTOCK = "baostock"
PROVIDER_SINA = "sina"
PROVIDER_IFIND = "ifind"
TUSHARE_TOKEN_ENV_NAMES = ("TUSHARE_TOKEN", "TUSHARE_PRO_TOKEN", "TS_TOKEN")

# iFinD bulk-fetch tuning. 800 codes/request measured clean (perf 111ms); 500
# leaves headroom. The client threads within a batch, so this is the outer
# chunk at which the update budget is re-checked.
IFIND_BATCH_CODES = int(os.getenv("IFIND_BATCH_CODES", "1000"))
IFIND_BATCH_TIMEOUT_SEC = float(os.getenv("IFIND_BATCH_TIMEOUT", "120"))
IFIND_BAR_INDICATORS = "open,high,low,close,volume,amount"
# ths_af_stock is an exact published factor, not an inference, so only float
# noise needs suppressing — see the threshold note in sync_adj_factors_for_today.
IFIND_ADJ_EVENT_EPSILON = 1e-9

# History needed: 250-day RPS + 10-day MA buffer → use extra holiday margin
INIT_HISTORY_DAYS = 450
TUSHARE_RETRY_DELAY = 0.5
TUSHARE_RETRIES = 3
AKSHARE_RETRY_DELAY = 0.5
AKSHARE_RETRIES = 3
AKSHARE_DEFAULT_WORKERS = 12
EASTMONEY_RETRY_DELAY = 0.5
EASTMONEY_RETRIES = 3
EASTMONEY_DEFAULT_WORKERS = 12
EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_CLIST_PAGE_SIZE = 50
# A-share boards: SH main + SH STAR + SZ main + SZ ChiNext + BJ.
EASTMONEY_CLIST_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
EASTMONEY_CLIST_FIELDS = "f12,f14,f2,f3,f6,f15,f16,f17,f18,f5"

# Per-API-call hard timeout (socket read + connect). If a single call exceeds
# this, we fail fast and let the retry/provider-fallback logic handle it.
PRICEDB_CALL_TIMEOUT_SEC = float(os.getenv("PRICEDB_CALL_TIMEOUT", "30"))

# Per-update overall wall-clock budget. Enforced at the top of cmd_update.
# Default tightened to 300s — the clist bulk path should finish in ~60s.
PRICEDB_UPDATE_BUDGET_SEC = float(os.getenv("PRICEDB_UPDATE_BUDGET", "300"))

# Belt-and-suspenders: protect against any library that creates raw sockets
# without explicit timeouts (some baostock/urllib paths). Per-call thread
# wrappers below remain the primary defense.
socket.setdefaulttimeout(PRICEDB_CALL_TIMEOUT_SEC)

# Module-level deadline for cmd_update. Set at the start of cmd_update;
# checked from within bulk_fetch helpers via _budget_exceeded().
_UPDATE_DEADLINE: float | None = None


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


def _budget_exceeded() -> bool:
    """Return True if the current cmd_update has run past its wall-clock budget."""
    return _UPDATE_DEADLINE is not None and time.monotonic() > _UPDATE_DEADLINE


# Fraction of the known universe a date must cover to count as a "complete"
# trading day. Shared conceptually with rps_calculator's reference-date guard.
PRICEDB_COVERAGE_THRESHOLD = float(os.getenv("RPS_REFERENCE_DATE_MIN_COVERAGE", "0.9"))


def _now() -> datetime:
    """Wall clock, wrapped so tests can inject a fixed time."""
    return datetime.now()


def is_session_open(now: datetime | None = None) -> bool:
    """True while the A-share regular session is still open (before 15:00 local).

    During an open session, the only "today" bar available is a real-time spot
    snapshot, not a settled close — writing it into daily_prices corrupts MA/RPS.
    Env-overridable close time via RPS_SESSION_CLOSE_HHMM (e.g. "1500").
    """
    now = now or _now()
    raw = os.getenv("RPS_SESSION_CLOSE_HHMM", "1500").strip()
    try:
        close_h, close_m = int(raw[:2]), int(raw[2:4])
    except (ValueError, IndexError):
        close_h, close_m = 15, 0
    return (now.hour, now.minute) < (close_h, close_m)


def last_settled_trading_day(now: datetime | None = None) -> _date:
    """Most recent trading day whose session has fully closed.

    During an open session today's bar is not settled yet (and by design is not
    written to daily_prices), so the freshest *legitimate* data is the previous
    trading day. This is the correct "expected latest" for staleness checks and
    mirrors the cmd_update end-cap — without it, a mid-session staleness gate
    would demand a bar that intentionally does not exist yet.
    """
    now = now or _now()
    ref = now.date()
    if is_session_open(now):
        ref = ref - timedelta(days=1)
    return most_recent_trading_day(ref)


def _last_fully_covered_date(conn: sqlite3.Connection) -> str | None:
    """Latest date whose row count reaches PRICEDB_COVERAGE_THRESHOLD of the
    known universe. Used as the incremental cursor so partially-fetched recent
    days (truncated by the budget or a flaky provider) get re-fetched instead of
    being skipped forever once a later day advances MAX(date)."""
    total = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    if not total:
        return None
    min_codes = int(total * PRICEDB_COVERAGE_THRESHOLD)
    row = conn.execute(
        """
        SELECT date
        FROM daily_prices
        GROUP BY date
        HAVING COUNT(DISTINCT code) >= ?
        ORDER BY date DESC
        LIMIT 1
        """,
        (min_codes,),
    ).fetchone()
    return row[0] if row and row[0] else None


_PROXY_ENV_KEYS = (
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy",
)


@contextlib.contextmanager
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


# ---------------------------------------------------------------------------
# Trade calendar (no-auth, akshare-based with weekday fallback)
# ---------------------------------------------------------------------------


_TRADE_CALENDAR_CACHE: list[str] | None = None


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


def _get_trade_calendar_cached() -> list[str]:
    """Return cached trading-day list (YYYYMMDD strings) covering the last ~5 years to today."""
    global _TRADE_CALENDAR_CACHE
    if _TRADE_CALENDAR_CACHE is None:
        beg = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y%m%d")
        end = datetime.now().strftime("%Y%m%d")
        _TRADE_CALENDAR_CACHE = fetch_trade_dates_free(beg, end)
    return _TRADE_CALENDAR_CACHE


def _reset_trade_calendar_cache():
    """Test helper: clear the cached calendar."""
    global _TRADE_CALENDAR_CACHE
    _TRADE_CALENDAR_CACHE = None


def most_recent_trading_day(target: _date, calendar: list[str] | None = None) -> _date:
    """Return the most recent trading day on or before ``target``.

    Uses akshare calendar when available; falls back to walking back over weekends.
    """
    if calendar is None:
        calendar = _get_trade_calendar_cached()
    if calendar:
        key = target.strftime("%Y%m%d")
        idx = bisect.bisect_right(calendar, key) - 1
        if idx >= 0:
            return datetime.strptime(calendar[idx], "%Y%m%d").date()
    d = target
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def get_db() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def ensure_schema(conn: sqlite3.Connection):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stocks (
            code        TEXT PRIMARY KEY,
            name        TEXT,
            exchange    TEXT,
            listed_date TEXT,
            last_updated TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_prices (
            code    TEXT,
            date    TEXT,
            open    REAL,
            high    REAL,
            low     REAL,
            close   REAL,
            volume  INTEGER,
            amount  REAL,
            PRIMARY KEY (code, date)
        );

        CREATE INDEX IF NOT EXISTS idx_dp_date
            ON daily_prices(date);
        CREATE INDEX IF NOT EXISTS idx_dp_code_date
            ON daily_prices(code, date);

        CREATE TABLE IF NOT EXISTS rps_cache (
            date    TEXT,
            code    TEXT,
            rps20   REAL,
            rps60   REAL,
            rps120  REAL,
            rps250  REAL,
            ma10    REAL,
            PRIMARY KEY (date, code)
        );
        """
    )
    # adj_factors (read-time price adjustment) is owned by price_adjust.py —
    # single definition, shared by pricedb writers and indicator readers.
    price_adjust.ensure_adj_schema(conn)
    conn.commit()


def clear_all_data(conn: sqlite3.Connection):
    """Clear all data tables for a fresh init attempt."""
    conn.execute("DELETE FROM rps_cache")
    conn.execute("DELETE FROM daily_prices")
    conn.execute("DELETE FROM stocks")
    conn.commit()


def invalidate_rps_cache(conn: sqlite3.Connection, from_date: str | None = None):
    """Invalidate cached RPS rows from a given ISO date onward."""
    if from_date:
        conn.execute("DELETE FROM rps_cache WHERE date >= ?", (from_date,))
    else:
        conn.execute("DELETE FROM rps_cache")
    conn.commit()


def upsert_stocks(conn: sqlite3.Connection, stocks: list[dict]):
    """Insert or refresh stock metadata."""
    if not stocks:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.executemany(
        "INSERT OR REPLACE INTO stocks (code, name, exchange, listed_date, last_updated) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (
                stock["code"],
                stock.get("name"),
                stock.get("exchange"),
                stock.get("listed_date"),
                now,
            )
            for stock in stocks
        ],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------


def _read_env_file() -> dict[str, str]:
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


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Eastmoney direct provider
# ---------------------------------------------------------------------------


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


def _fetch_klines_eastmoney(stock: dict, beg: str, end: str) -> list[tuple]:
    secid = _eastmoney_secid(stock)
    if not secid:
        return []
    payload = _fetch_eastmoney_json(_eastmoney_kline_url(secid, beg, end))
    return _eastmoney_payload_to_rows(stock, payload)


def _fetch_klines_eastmoney_with_retries(stock: dict, beg: str, end: str) -> list[tuple]:
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
                    conn.executemany(
                        "INSERT OR REPLACE INTO daily_prices "
                        "(code,date,open,high,low,close,volume,amount) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        rows,
                    )
                    conn.commit()
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


# ---------------------------------------------------------------------------
# Eastmoney clist (bulk daily snapshot) provider
# ---------------------------------------------------------------------------


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

    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices "
        "(code,date,open,high,low,close,volume,amount) "
        "VALUES (?,?,?,?,?,?,?,?)",
        filtered,
    )
    conn.commit()
    if failures:
        print(f"  clist: {len(failures)} page(s) failed: {failures[0]}", file=sys.stderr)
    print(
        f"  [Clist] {len(filtered):,} rows inserted for {target_iso} "
        f"({total_pages} pages, {total} total records)",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Tushare provider
# ---------------------------------------------------------------------------


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
            conn.executemany(
                "INSERT OR REPLACE INTO daily_prices "
                "(code,date,open,high,low,close,volume,amount) "
                "VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
            conn.commit()
            total_inserted += len(rows)

        if index % 20 == 0 or index == len(trade_dates):
            print(
                f"  [Tushare {index}/{len(trade_dates)}] {trade_date} → {len(rows)} rows",
                file=sys.stderr,
            )
        time.sleep(0.12)

    print(f"  Total: {total_inserted:,} rows inserted", file=sys.stderr)


# ---------------------------------------------------------------------------
# AkShare provider
# ---------------------------------------------------------------------------


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
                    conn.executemany(
                        "INSERT OR REPLACE INTO daily_prices "
                        "(code,date,open,high,low,close,volume,amount) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        rows,
                    )
                    conn.commit()
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


# ---------------------------------------------------------------------------
# BaoStock provider
# ---------------------------------------------------------------------------


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
    total_inserted = 0
    consecutive_empty = 0
    EARLY_ABORT_THRESHOLD = 100  # bail if first N stocks all return 0 rows

    for index, stock in enumerate(stocks, start=1):
        if _budget_exceeded():
            raise RuntimeError("update budget exceeded")
        rows = _fetch_klines_baostock(bs, stock, beg, end)
        if rows:
            conn.executemany(
                "INSERT OR REPLACE INTO daily_prices "
                "(code,date,open,high,low,close,volume,amount) "
                "VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
            conn.commit()
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


# ---------------------------------------------------------------------------
# Unified provider API
# ---------------------------------------------------------------------------


def _exchange_from_code(code: str) -> str:
    if code.startswith(("6",)):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    return "BJ"


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
    if provider_name == PROVIDER_AKSHARE:
        return fetch_stock_list_akshare(provider)
    if provider_name == PROVIDER_TUSHARE:
        return fetch_stock_list_tushare(provider)
    if provider_name == PROVIDER_BAOSTOCK:
        return fetch_stock_list_baostock(provider)
    raise ValueError(f"Unknown provider: {provider_name}")


def bulk_fetch(
    conn: sqlite3.Connection,
    stocks: list[dict],
    beg: str,
    end: str,
    provider_name: str,
    provider: object,
):
    if provider_name == PROVIDER_IFIND:
        return _bulk_fetch_ifind(conn, stocks, beg, end, provider)
    if provider_name == PROVIDER_AKSHARE:
        return _bulk_fetch_akshare(conn, stocks, beg, end, provider)
    if provider_name == PROVIDER_SINA:
        return _bulk_fetch_sina(conn, stocks, beg, end, provider)
    # Retired providers (kept callable for manual forensics only — they are
    # NOT in iter_providers and must not return to the daily chain):
    if provider_name == PROVIDER_TUSHARE:
        return _bulk_fetch_tushare(conn, stocks, beg, end, provider)
    if provider_name == PROVIDER_EASTMONEY_CLIST:
        return _bulk_fetch_eastmoney_clist(conn, stocks, beg, end, provider)
    if provider_name == PROVIDER_EASTMONEY:
        return _bulk_fetch_eastmoney(conn, stocks, beg, end, provider)
    if provider_name == PROVIDER_BAOSTOCK:
        return _bulk_fetch_baostock(conn, stocks, beg, end, provider)
    raise ValueError(f"Unknown provider: {provider_name}")


# ---------------------------------------------------------------------------
# Provider-driven sync flows
# ---------------------------------------------------------------------------


def cleanup_failed_init_artifacts():
    """Remove partially created DB files after a failed init."""
    try:
        DB_PATH.unlink(missing_ok=True)
        DB_PATH.with_suffix(DB_PATH.suffix + ".wal").unlink(missing_ok=True)
        DB_PATH.with_suffix(DB_PATH.suffix + ".shm").unlink(missing_ok=True)
    except OSError:
        pass


def cmd_init():
    """Create DB, fetch stock list, download all historical data."""
    beg = (datetime.now() - timedelta(days=INIT_HISTORY_DAYS)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    provider_errors = []

    for provider_name, provider in iter_providers():
        if provider_name == PROVIDER_SINA:
            # sina has no stock-list endpoint; init needs list + history from
            # one provider (akshare). repair/update cover sina afterwards.
            close_provider(provider_name, provider)
            continue
        conn = get_db()
        ensure_schema(conn)
        clear_all_data(conn)
        try:
            print(f"Fetching A-share stock list via {provider_name}...", file=sys.stderr)
            stocks = fetch_stock_list(provider_name, provider)
            print(f"  Found {len(stocks)} stocks", file=sys.stderr)
            if not stocks:
                raise RuntimeError(f"{provider_name} returned no stocks")

            upsert_stocks(conn, stocks)
            invalidate_rps_cache(conn)

            print(f"Downloading historical data via {provider_name} ({beg} → {end})...", file=sys.stderr)
            bulk_fetch(conn, stocks, beg, end, provider_name, provider)
            conn.close()
            print(f"Init complete via {provider_name}.", file=sys.stderr)
            close_provider(provider_name, provider)
            return
        except Exception as e:
            provider_errors.append(f"{provider_name}: {e}")
            print(f"  {provider_name} init failed: {e}", file=sys.stderr)
            conn.close()
            close_provider(provider_name, provider)

    cleanup_failed_init_artifacts()
    print("Init failed. Providers tried:", file=sys.stderr)
    for err in provider_errors:
        print(f"  - {err}", file=sys.stderr)
    sys.exit(1)


def cmd_update():
    """Incremental update: fetch missing dates since last update."""
    if not DB_PATH.exists():
        print("DB not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = time.monotonic() + PRICEDB_UPDATE_BUDGET_SEC

    conn = get_db()
    ensure_schema(conn)

    row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
    latest = row[0] if row and row[0] else None
    if not latest:
        print("No price data in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Advance the incremental cursor from the last *fully-covered* day, not just
    # MAX(date). A day left partial by the budget or a flaky provider must be
    # re-fetched, but MAX(date) would skip it once any later day landed a single
    # row. Fall back to MAX(date) if no day yet clears the coverage bar.
    cursor_date = _last_fully_covered_date(conn) or latest
    if cursor_date != latest:
        print(
            f"Last fully-covered day is {cursor_date} (MAX(date)={latest}); "
            f"re-fetching partial days from {cursor_date} forward.",
            file=sys.stderr,
        )
    beg = (datetime.strptime(cursor_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
    # Never fetch today's bar while the session is open — every provider path
    # would return an unsettled intraday bar, which corrupts MA/RPS (RC1).
    # And never fetch a non-trading day at all: on weekends/holidays an
    # uncapped window made the per-code sweep hammer ~5.5k symbols for zero
    # rows until the budget died (surfaced 2026-08-01 by the akshare-primary
    # chain). Cap at the last settled trading day in both cases.
    end_date = _now().date()
    if is_session_open():
        end_date = most_recent_trading_day(end_date - timedelta(days=1))
        print(
            f"Session open — capping fetch window at last closed session {end_date.isoformat()} "
            f"(today's bar is not settled yet).",
            file=sys.stderr,
        )
    else:
        end_date = most_recent_trading_day(end_date)
    end = end_date.strftime("%Y%m%d")
    provider_errors = []

    stocks = [
        {"code": row[0], "name": row[1], "exchange": row[2]}
        for row in conn.execute("SELECT code, name, exchange FROM stocks")
    ]
    if not stocks:
        print("No stocks in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    for provider_name, provider in iter_providers():
        if _budget_exceeded():
            print(
                f"  Skipping {provider_name}: update budget exceeded "
                f"({PRICEDB_UPDATE_BUDGET_SEC:.0f}s)",
                file=sys.stderr,
            )
            close_provider(provider_name, provider)
            continue
        try:
            if provider_name == PROVIDER_AKSHARE:
                # Best-effort universe refresh (new listings). A list failure
                # must not cost us the price bars — degrade to the stored
                # universe and keep going.
                try:
                    print("Refreshing stock list via akshare...", file=sys.stderr)
                    latest_stocks = fetch_stock_list(provider_name, provider)
                    if latest_stocks:
                        upsert_stocks(conn, latest_stocks)
                        stocks = [
                            {"code": row[0], "name": row[1], "exchange": row[2]}
                            for row in conn.execute(
                                "SELECT code, name, exchange FROM stocks")
                        ]
                        print(f"  {len(latest_stocks)} stocks in universe",
                              file=sys.stderr)
                except Exception as list_err:
                    print(f"  stock-list refresh failed ({list_err}) — using "
                          f"stored universe of {len(stocks)}", file=sys.stderr)
            else:
                print(f"Using existing stock universe for {provider_name}: {len(stocks)} stocks", file=sys.stderr)

            missing_codes = {
                row[0]
                for row in conn.execute(
                    "SELECT s.code FROM stocks s "
                    "LEFT JOIN daily_prices d ON d.code = s.code "
                    "WHERE d.code IS NULL"
                )
            }

            if beg > end and not missing_codes:
                print(f"Already up to date (latest: {latest}).", file=sys.stderr)
                close_provider(provider_name, provider)
                conn.close()
                return

            if beg <= end:
                print(f"Updating {len(stocks)} stocks via {provider_name} ({beg} → {end})...", file=sys.stderr)
                invalidate_rps_cache(conn, _yyyymmdd_to_iso(beg))
                bulk_fetch(conn, stocks, beg, end, provider_name, provider)

            if missing_codes:
                missing_stocks = [stock for stock in stocks if stock["code"] in missing_codes]
                init_beg = (datetime.now() - timedelta(days=INIT_HISTORY_DAYS)).strftime("%Y%m%d")
                print(
                    f"Backfilling {len(missing_stocks)} newly discovered stocks via {provider_name} ({init_beg} → {end})...",
                    file=sys.stderr,
                )
                invalidate_rps_cache(conn, _yyyymmdd_to_iso(init_beg))
                bulk_fetch(conn, missing_stocks, init_beg, end, provider_name, provider)

            close_provider(provider_name, provider)

            # Check if today's data actually landed. Only backfill from the
            # AkShare real-time spot endpoint AFTER the session has closed —
            # mid-session that endpoint returns an intraday snapshot, and writing
            # it as today's "close" corrupts MA/RPS (RC1). Before close we leave
            # today absent so the last settled close stays the newest bar.
            today_iso = datetime.now().strftime("%Y-%m-%d")
            today_count = conn.execute(
                "SELECT COUNT(*) FROM daily_prices WHERE date = ?", (today_iso,)
            ).fetchone()[0]
            if today_count == 0 and beg <= end and not is_session_open():
                print(f"  {provider_name} returned no data for {today_iso}, trying AkShare spot...", file=sys.stderr)
                inserted = _backfill_from_akshare_spot(conn, today_iso)
                if inserted:
                    invalidate_rps_cache(conn, today_iso)
                    print(f"  AkShare spot: {inserted} rows inserted for {today_iso}", file=sys.stderr)
                else:
                    print(f"  AkShare spot: no data either", file=sys.stderr)
            elif today_count == 0 and beg <= end and is_session_open():
                print(
                    f"  Session still open — skipping intraday spot backfill for {today_iso} "
                    f"(would not be a settled close).",
                    file=sys.stderr,
                )

            # Best-effort adjustment-factor sync (same-day f18 fast path, or
            # gap heal via the ex-div calendar after downtime). Failure
            # degrades to forward-filled factors and self-heals next run.
            try:
                changed = _sync_or_heal_factors(conn)
                if changed:
                    invalidate_rps_cache(conn, changed)
            except Exception as factor_err:
                print(f"  WARNING: adjustment-factor sync failed: {factor_err} "
                      f"— indicators fall back to last known factors; "
                      f"run 'pricedb.py factors heal' to repair.",
                      file=sys.stderr)

            conn.close()
            if _budget_exceeded():
                print(
                    f"WARNING: update budget ({PRICEDB_UPDATE_BUDGET_SEC:.0f}s) exceeded via "
                    f"{provider_name}; recent-day coverage may be PARTIAL. "
                    f"Re-run 'pricedb update' — the cursor self-heals from the last full day.",
                    file=sys.stderr,
                )
            else:
                print(f"Update complete via {provider_name}.", file=sys.stderr)
            return
        except Exception as e:
            provider_errors.append(f"{provider_name}: {e}")
            print(f"  {provider_name} update failed: {e}", file=sys.stderr)
            close_provider(provider_name, provider)

    conn.close()
    print("Update failed. Providers tried:", file=sys.stderr)
    for err in provider_errors:
        print(f"  - {err}", file=sys.stderr)
    sys.exit(1)


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
            conn.executemany(
                "INSERT OR REPLACE INTO daily_prices "
                "(code,date,open,high,low,close,volume,amount) "
                "VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
            conn.commit()

        return len(rows)
    except Exception as e:
        print(f"  AkShare spot fallback failed: {e}", file=sys.stderr)
        return 0


# --------------------------------------------------------------------------- #
# Adjustment factors (read-time price adjustment; see price_adjust.py)
# --------------------------------------------------------------------------- #
# A daily return ratio |m-1| below this is rounding noise from eastmoney's
# 2-dp adjusted closes, not a corporate action. Dividends below 0.5% are
# negligible for MA/RPS anyway.
ADJ_EVENT_THRESHOLD = 0.005
# Politeness for the factor backfill. The first run hammered eastmoney's kline
# API at ~3 req/s with no sleep and got this IP temporarily banned (empty
# replies on push2his AND push2 — which also starves the daily pipeline).
# Never again: pace requests, and circuit-break on failure bursts.
ADJ_BACKFILL_SLEEP_SEC = float(os.getenv("ADJ_BACKFILL_SLEEP_SEC", "0.4"))

# Sina repair sweep: 4 workers × 0.25s/request ≈ 15 req/s — polite enough to
# stay under sina's IP-ban radar while covering ~5.5k codes in a few minutes.
SINA_REPAIR_WORKERS = int(os.getenv("SINA_REPAIR_WORKERS", "4"))
SINA_REPAIR_SLEEP_SEC = float(os.getenv("SINA_REPAIR_SLEEP_SEC", "0.25"))
ADJ_BACKFILL_COOLDOWN_SEC = float(os.getenv("ADJ_BACKFILL_COOLDOWN_SEC", "300"))
ADJ_BACKFILL_MAX_COOLDOWNS = 3


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


def derive_factors_eastmoney(code: str, exchange: str, beg: str, end: str) -> list[tuple]:
    """Return-ratio factors from eastmoney's own raw (fqt=0) + hfq (fqt=2)
    klines. Preferred over the akshare path: two curl fetches, no pandas, and
    immune to python-TLS fingerprint blocks."""
    secid = _eastmoney_secid({"code": code, "exchange": exchange})
    if not secid:
        return []
    with _no_proxy_env():
        raw_s = _kline_closes_eastmoney(secid, beg, end, fqt=0)
        hfq_s = _kline_closes_eastmoney(secid, beg, end, fqt=2)
    return _return_ratio_factors(raw_s, hfq_s)


SINA_HFQ_URL = "https://finance.sina.com.cn/realstock/company/{sym}/hfq.js"


def _sina_symbol(code: str, exchange: str) -> str | None:
    exchange = (exchange or "").upper()
    if exchange == "SH" or code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"sh{code}"
    if exchange == "SZ" or code.startswith(("000", "001", "002", "003", "300", "301")):
        return f"sz{code}"
    return None  # BJ codes: sina hfq.js unsupported


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


SINA_KLINE_URL = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/x=/"
                  "CN_MarketDataService.getKLineData")


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
                cur = conn.executemany(
                    "INSERT OR IGNORE INTO daily_prices "
                    "(code,date,open,high,low,close,volume,amount) "
                    "VALUES (?,?,?,?,?,?,?,?)", rows)
                inserted += cur.rowcount
                conn.commit()
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
            cur = conn.executemany(
                "INSERT OR IGNORE INTO daily_prices "
                "(code,date,open,high,low,close,volume,amount) "
                "VALUES (?,?,?,?,?,?,?,?)", rows)
            inserted += cur.rowcount
            conn.commit()
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


def _expand_events_to_code_dates(conn: sqlite3.Connection, code: str,
                                 events: list) -> list[tuple]:
    """Map sparse factor events onto a code's actual traded dates (dense rows).

    Applicable factor for date d = factor of the latest event <= d, else 1.0
    (the pre-first-event hfq base). Guarantees the table is dense for the code
    so COALESCE never mixes scales inside one window (hazard F1).
    """
    event_dates = [d for d, _ in events]
    rows = []
    for (d,) in conn.execute(
        "SELECT date FROM daily_prices WHERE code = ? ORDER BY date", (code,)
    ):
        i = bisect.bisect_right(event_dates, d) - 1
        factor = events[i][1] if i >= 0 else 1.0
        rows.append((code, d, round(factor, 8)))
    return rows


def derive_factors_from_akshare(ak, code: str, beg: str, end: str) -> list[tuple]:
    """Return-ratio factors via akshare raw + hfq histories (fallback path)."""
    with _no_proxy_env():
        raw = _run_with_timeout(
            f"AkShare raw {code}",
            lambda: ak.stock_zh_a_hist(symbol=code, period="daily",
                                       start_date=beg, end_date=end, adjust=""),
        )
        hfq = _run_with_timeout(
            f"AkShare hfq {code}",
            lambda: ak.stock_zh_a_hist(symbol=code, period="daily",
                                       start_date=beg, end_date=end, adjust="hfq"),
        )
    return _return_ratio_factors(_frame_close_series(raw), _frame_close_series(hfq))


def upsert_adj_factors(conn: sqlite3.Connection, rows: list) -> str | None:
    """INSERT OR REPLACE (code, date, factor) rows with diff detection.

    Returns the earliest date whose *effective* value changed, so the caller
    can invalidate rps_cache from there. A fresh insert counts as a change
    only when factor != 1.0 (a missing row already read as 1.0 via COALESCE).
    """
    earliest_changed: str | None = None
    cur = conn.cursor()
    for code, date_iso, factor in rows:
        old = cur.execute(
            "SELECT factor FROM adj_factors WHERE code = ? AND date = ?",
            (code, date_iso),
        ).fetchone()
        effective_old = old[0] if old is not None else 1.0
        if abs(effective_old - factor) < 1e-9:
            if old is None and abs(factor - 1.0) < 1e-9:
                # still write the 1.0 row: presence marks the code as processed
                cur.execute("INSERT OR REPLACE INTO adj_factors VALUES (?, ?, ?)",
                            (code, date_iso, factor))
            continue
        cur.execute("INSERT OR REPLACE INTO adj_factors VALUES (?, ?, ?)",
                    (code, date_iso, factor))
        if earliest_changed is None or date_iso < earliest_changed:
            earliest_changed = date_iso
    conn.commit()
    return earliest_changed


def _forward_fill_factors(conn: sqlite3.Connection) -> int:
    """Densify: any (code, date) in daily_prices missing a factor gets the
    code's most recent PRIOR factor. Dates before a code's first factor row
    stay absent (COALESCE 1.0 == the pre-event base, which is correct).
    Codes with no factor rows at all are untouched (unprocessed => raw)."""
    filled = 0
    codes = [r[0] for r in conn.execute("SELECT DISTINCT code FROM adj_factors")]
    for code in codes:
        factors = conn.execute(
            "SELECT date, factor FROM adj_factors WHERE code = ? ORDER BY date",
            (code,),
        ).fetchall()
        fdates = [f[0] for f in factors]
        fset = set(fdates)
        missing = [
            r[0] for r in conn.execute(
                "SELECT date FROM daily_prices WHERE code = ? ORDER BY date", (code,)
            ) if r[0] not in fset
        ]
        rows = []
        for d in missing:
            i = bisect.bisect_right(fdates, d) - 1
            if i < 0:
                continue  # before first factor: leave absent (reads as 1.0)
            rows.append((code, d, factors[i][1]))
        if rows:
            conn.executemany("INSERT OR REPLACE INTO adj_factors VALUES (?, ?, ?)", rows)
            filled += len(rows)
    conn.commit()
    return filled


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


def _ifind_event_multipliers(conn: sqlite3.Connection, codes: list,
                             prev_date: str, date_iso: str) -> dict:
    """{code: multiplier} for `date_iso`, from the RATIO of iFinD's factors.

    Deliberately a ratio, not an absolute value. Our stored chains are anchored
    at 1.0 on each code's first date; iFinD anchors at listing. Writing their
    absolute af into our table would jump the base mid-series and fabricate a
    return on the splice date. Taking af[today]/af[prev] imports only the
    corporate-action event, which is the part iFinD detects more reliably than
    the retired eastmoney clist f18 probe.
    """
    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}
    series = _ifind_af_series(codes, ex_map, prev_date, date_iso)
    out = {}
    for code, by_date in series.items():
        prev_af, today_af = by_date.get(prev_date), by_date.get(date_iso)
        if prev_af and today_af and prev_af > 0:
            out[code] = today_af / prev_af
    return out


def rebuild_factors_from_ifind(conn: sqlite3.Connection, codes: list | None = None,
                               dry_run: bool = False, chunk: int = 300) -> dict:
    """Rebuild adj_factors for whole codes from iFinD's ths_af_stock.

    Rebuilds a code's ENTIRE series or none of it. Partial rebuilds are the one
    thing that must not happen here: our chains are anchored at 1.0 on each
    code's first date while iFinD anchors at listing, so splicing their absolute
    values into the middle of one of our series would fabricate a return on the
    splice date. Each series is renormalized to 1.0 at the code's first date,
    which reproduces our existing convention exactly.
    """
    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}
    bounds = {}
    for code, first, last in conn.execute(
            "SELECT code, MIN(date), MAX(date) FROM daily_prices GROUP BY code"):
        bounds[code] = (first, last)
    targets = [c for c in (codes or bounds) if c in bounds]

    stats = {"codes": len(targets), "rebuilt": 0, "rows": 0,
             "no_data": 0, "failed": 0}
    if not targets:
        return stats

    for i in range(0, len(targets), chunk):
        batch = targets[i:i + chunk]
        beg = min(bounds[c][0] for c in batch)
        end = max(bounds[c][1] for c in batch)
        try:
            series = _ifind_af_series(batch, ex_map, beg, end)
        except Exception as e:
            stats["failed"] += len(batch)
            print(f"    ⚠ batch {batch[0]}..{batch[-1]} failed: {str(e)[:70]}",
                  file=sys.stderr)
            continue

        rows = []
        for code in batch:
            by_date = series.get(code)
            if not by_date:
                stats["no_data"] += 1
                continue
            dates = sorted(d for d in by_date
                           if bounds[code][0] <= d <= bounds[code][1])
            if not dates:
                stats["no_data"] += 1
                continue
            base = by_date[dates[0]]
            if not base or base <= 0:
                stats["no_data"] += 1
                continue
            for d in dates:
                rows.append((code, d, round(by_date[d] / base, 8)))
            stats["rebuilt"] += 1

        if rows and not dry_run:
            # Replace the whole code's series atomically.
            done = {c for c, _, _ in rows}
            conn.executemany("DELETE FROM adj_factors WHERE code = ?",
                             [(c,) for c in done])
            conn.executemany(
                "INSERT OR REPLACE INTO adj_factors(code,date,factor) "
                "VALUES (?,?,?)", rows)
            conn.commit()
        stats["rows"] += len(rows)
        print(f"    [{min(i + chunk, len(targets))}/{len(targets)}] "
              f"{stats['rebuilt']} codes, {stats['rows']:,} rows", file=sys.stderr)

    if not dry_run:
        _forward_fill_factors(conn)
    return stats


def sync_adj_factors_for_today(conn: sqlite3.Connection, date_iso: str) -> str | None:
    """Incremental daily factor sync using the clist f18 detector.

    For each stock: stored_prev_raw_close / f18 == the event multiplier for
    `date_iso` (1.0 when no corporate action). New factor = prior factor × m.
    Finishes with a forward-fill so the table stays dense. Returns earliest
    changed date (for cache invalidation), or None.

    Limitation (documented): this only detects events whose ex-date is TODAY.
    After multi-day downtime, gap-day events are missed until a
    `pricedb.py factors backfill` re-derivation — same self-heal philosophy
    as the price cursor.
    """
    prev_row = conn.execute(
        "SELECT MAX(date) FROM daily_prices WHERE date < ?", (date_iso,)
    ).fetchone()
    prev_date = prev_row[0] if prev_row else None
    if not prev_date:
        return None
    prev_closes = dict(conn.execute(
        "SELECT code, close FROM daily_prices WHERE date = ?", (prev_date,)
    ))
    prev_factors = dict(conn.execute(
        "SELECT code, factor FROM adj_factors WHERE date = ?", (prev_date,)
    ))
    if prev_closes and not prev_factors:
        # Multi-day factor gap: every chain would restart at base 1.0 and
        # silently destroy the cumulative factors. Refuse; heal instead.
        raise RuntimeError(
            f"adj_factors has no rows for {prev_date} — multi-day gap; "
            f"run 'pricedb.py factors heal'"
        )

    # Primary: iFinD's own factor ratio. Fallback: the eastmoney clist f18
    # probe, which is a RETIRED provider surviving only as this helper — it
    # infers the event from prev_close/f18 and dies whenever eastmoney throttles.
    source = "ifind"
    mult_map: dict = {}
    if ifind_client.is_available():
        try:
            mult_map = _ifind_event_multipliers(
                conn, list(prev_closes), prev_date, date_iso)
        except Exception as e:
            print(f"  factors: iFinD multipliers failed ({str(e)[:80]}) — "
                  f"falling back to clist f18", file=sys.stderr)
    if not mult_map:
        source = "clist-f18"
        f18_map = _fetch_clist_prev_close_map()
        if not f18_map:
            raise RuntimeError("clist f18 snapshot returned no rows")
        for code, prev_close in prev_closes.items():
            f18 = f18_map.get(code)
            if f18 and prev_close and prev_close > 0:
                mult_map[code] = prev_close / f18

    # The noise threshold is a property of the SOURCE, not of the market.
    # clist f18 INFERS the event from prev_close/f18, so ratios within 0.5% are
    # indistinguishable from rounding noise and get snapped to 1.0. iFinD's
    # ths_af_stock is an exact published factor — applying the same 0.5% floor
    # to it discarded 4 of the 6 real dividends on 2026-08-25 (steps of
    # 1.0021–1.0039), so exact sources get only a float-noise epsilon.
    threshold = (IFIND_ADJ_EVENT_EPSILON if source == "ifind"
                 else ADJ_EVENT_THRESHOLD)

    rows = []
    events = 0
    for code, prev_close in prev_closes.items():
        m = mult_map.get(code)
        if not m or m <= 0:
            continue
        if abs(m - 1.0) <= threshold:
            m = 1.0
        else:
            events += 1
        base = prev_factors.get(code, 1.0)
        rows.append((code, date_iso, round(base * m, 8)))
    earliest = upsert_adj_factors(conn, rows)
    _forward_fill_factors(conn)
    print(f"  factors: {date_iso} synced via {source} "
          f"({events} corporate actions detected)", file=sys.stderr)
    return earliest


DATACENTER_EXDIV_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


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


def heal_adj_factor_gap(conn: sqlite3.Connection, beg_iso: str, end_iso: str) -> str | None:
    """Repair a multi-session factor gap [beg_iso, end_iso] inclusive.

    Factors only change on corporate actions, so the gap splits cleanly:
    the datacenter ex-div calendar names the codes with an event inside the
    gap — those get a full re-derivation (sina events primary, eastmoney
    return-ratio fallback), anchor-rescaled so pre-gap rows are unchanged
    (keeps rps_cache invalidation shallow); every other code is an exact
    plain forward-fill. Returns earliest changed date for cache invalidation.
    """
    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM daily_prices WHERE date >= ? AND date <= ? "
        "ORDER BY date", (beg_iso, end_iso))]
    exchanges = dict(conn.execute("SELECT code, exchange FROM stocks"))
    known = {r[0] for r in conn.execute("SELECT DISTINCT code FROM daily_prices")}

    event_codes: set = set()
    calendar_failures = 0
    for d in dates:
        codes = _fetch_ex_div_codes_datacenter(d)
        if codes is None:
            calendar_failures += 1
            print(f"  factors heal: ex-div calendar FAILED for {d} — event "
                  f"codes that day keep forward-filled factors until the next "
                  f"heal", file=sys.stderr)
            continue
        hits = set()
        for code in codes & known:
            # Skip codes whose stored factor already jumps on the event date —
            # they were derived event-aware; re-deriving is pure waste. A
            # missing row, or a factor flat across its own ex-date, is damage.
            row = conn.execute(
                "SELECT factor FROM adj_factors WHERE code = ? AND date = ?",
                (code, d)).fetchone()
            prev = conn.execute(
                "SELECT factor FROM adj_factors WHERE code = ? AND date < ? "
                "ORDER BY date DESC LIMIT 1", (code, d)).fetchone()
            prev_val = prev[0] if prev else 1.0
            if row is None or abs(row[0] - prev_val) < 1e-12:
                hits.add(code)
        print(f"  factors heal: {d} — {len(hits)} ex-div codes needing "
              f"re-derivation", file=sys.stderr)
        event_codes |= hits

    earliest: str | None = None
    failed = 0
    stale = []
    for code in sorted(event_codes):
        try:
            events = fetch_adj_factor_events_sina(code, exchanges.get(code, ""))
            if events:
                rows = _expand_events_to_code_dates(conn, code, events)
            else:
                first = conn.execute(
                    "SELECT MIN(date) FROM daily_prices WHERE code = ?", (code,)
                ).fetchone()[0]
                series = derive_factors_eastmoney(
                    code, exchanges.get(code, ""),
                    first.replace("-", ""), end_iso.replace("-", ""))
                rows = [(code, d, f) for d, f in series]
            if not rows:
                failed += 1
                continue
            # Anchor-rescale: sources use absolute (since-listing) factor
            # scale; existing rows use whatever scale backfill stored. Pin the
            # new series to the stored factor on the last pre-gap date so
            # pre-gap rows diff as unchanged and only the gap invalidates.
            anchor = conn.execute(
                "SELECT date, factor FROM adj_factors WHERE code = ? AND date < ? "
                "ORDER BY date DESC LIMIT 1", (code, beg_iso)).fetchone()
            if anchor:
                new_at_anchor = next((f for _c, d, f in reversed(rows) if d <= anchor[0]), None)
                if new_at_anchor:
                    scale = anchor[1] / new_at_anchor
                    rows = [(c, d, round(f * scale, 8)) for c, d, f in rows]
            in_gap = [f for _, d, f in rows if beg_iso <= d <= end_iso]
            pre_gap = anchor[1] if anchor else 1.0
            if in_gap and all(abs(f - pre_gap) < 1e-9 for f in in_gap):
                stale.append(code)  # calendar says event, source shows none yet
            changed = upsert_adj_factors(conn, rows)
            if changed and (earliest is None or changed < earliest):
                earliest = changed
        except Exception as e:
            failed += 1
            print(f"  factors heal: {code} FAILED ({str(e)[:80]})", file=sys.stderr)
        time.sleep(ADJ_BACKFILL_SLEEP_SEC)

    filled = _forward_fill_factors(conn)
    print(f"  factors heal: {len(event_codes)} event codes re-derived "
          f"({failed} failed), forward-filled {filled} rows", file=sys.stderr)
    if stale:
        print(f"  factors heal: WARNING — source has not yet published the "
              f"event for: {','.join(stale[:10])}"
              f"{' …' if len(stale) > 10 else ''} (re-run heal later)",
              file=sys.stderr)
    if calendar_failures == len(dates) and dates:
        print("  factors heal: WARNING — ex-div calendar unreachable for the "
              "entire gap; only forward-fill applied", file=sys.stderr)
    return earliest


def _sync_or_heal_factors(conn: sqlite3.Connection) -> str | None:
    """Keep adj_factors caught up with daily_prices, whatever the lag.

    Lag of exactly one session on today's date → fast same-day f18 sync
    (falls back to heal when clist is down). Anything more → gap heal.
    Returns earliest changed date, or None.
    """
    cov = price_adjust.factor_coverage(conn)
    mpd, mfd = cov["max_price_date"], cov["max_factor_date"]
    if not mpd or not mfd or mfd >= mpd:
        filled = _forward_fill_factors(conn)
        if filled:
            print(f"  factors: forward-filled {filled} rows", file=sys.stderr)
        return None
    prev_date = conn.execute(
        "SELECT MAX(date) FROM daily_prices WHERE date < ?", (mpd,)
    ).fetchone()[0]
    if mfd == prev_date and mpd == datetime.now().strftime("%Y-%m-%d"):
        try:
            return sync_adj_factors_for_today(conn, mpd)
        except Exception as e:
            print(f"  factors: same-day f18 sync failed ({str(e)[:80]}); "
                  f"falling back to gap heal", file=sys.stderr)
    beg = (datetime.strptime(mfd, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    return heal_adj_factor_gap(conn, beg, mpd)


def cmd_factors(args: list):
    """CLI: pricedb.py factors backfill|update|heal|verify|rebuild [--beg --end]

    backfill — codes with zero factor rows (per-code sina/eastmoney, resumable)
    update   — daily incremental (iFinD af ratio, clist f18 fallback; auto-heals)
    heal     — repair a multi-session gap (ex-div calendar + re-derivation);
               --beg/--end are ISO dates, default = the current gap
    verify   — coverage/lag audit, exit 1 on failure
    rebuild  — rebuild whole series from iFinD ths_af_stock (--code CSV to
               limit, --dry-run to preview). Destructive: it DELETEs each
               rebuilt code's rows first, so back up adj_factors beforehand.
    """
    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = None  # factor work is budget-exempt (off-hours, resumable)

    sub = args[0] if args else "verify"
    conn = get_db()
    ensure_schema(conn)

    if sub == "verify":
        cov = price_adjust.factor_coverage(conn)
        non_bj_missing, fresh_ipos = cov["non_bj_missing"], cov["fresh_ipos"]
        print(f"Factor coverage (all rows): {cov['pair_coverage_pct']:.2f}%")
        print(f"Factor coverage (factored universe): {cov['universe_coverage_pct']:.2f}%")
        print(f"Codes without factors: {cov['codes_without_factors']} "
              f"(non-BJ: {len(non_bj_missing)}{' — ' + ','.join(non_bj_missing[:5]) if non_bj_missing else ''}"
              f"{f'; 次新豁免 {len(fresh_ipos)}: ' + ','.join(fresh_ipos[:5]) if fresh_ipos else ''})")
        print(f"Latest price date:  {cov['max_price_date']}")
        print(f"Latest factor date: {cov['max_factor_date']}")
        conn.close()
        if not cov["healthy"]:
            for p in cov["problems"]:
                print(f"VERIFY FAILED: {p}", file=sys.stderr)
            sys.exit(1)
        print("VERIFY OK (BJ codes deliberately unfactored — read as 1.0)")
        return

    if sub == "rebuild":
        def _arg(flag, default=None):
            return args[args.index(flag) + 1] if flag in args else default

        if not ifind_client.is_available():
            print("iFinD not configured — cannot rebuild", file=sys.stderr)
            conn.close()
            sys.exit(1)
        dry = "--dry-run" in args
        code_arg = _arg("--code")
        codes = [c.strip() for c in code_arg.split(",")] if code_arg else None
        print(f"factors rebuild from iFinD"
              f"{' (dry run)' if dry else ''}"
              f"{f' — {len(codes)} code(s)' if codes else ' — ALL codes'}",
              file=sys.stderr)
        stats = rebuild_factors_from_ifind(conn, codes, dry_run=dry)
        try:
            print(f"\n  codes targeted : {stats['codes']}", file=sys.stderr)
            print(f"  rebuilt        : {stats['rebuilt']}", file=sys.stderr)
            print(f"  factor rows    : {stats['rows']:,}", file=sys.stderr)
            print(f"  no iFinD data  : {stats['no_data']}", file=sys.stderr)
            print(f"  failed         : {stats['failed']}", file=sys.stderr)
            if not dry:
                invalidate_rps_cache(conn)
                print("  rps_cache invalidated", file=sys.stderr)
        finally:
            conn.close()
        return

    if sub == "update":
        try:
            changed = _sync_or_heal_factors(conn)
            if changed:
                invalidate_rps_cache(conn, changed)
                print(f"  rps_cache invalidated from {changed}", file=sys.stderr)
        finally:
            conn.close()
        return

    if sub == "heal":
        def _arg(flag, default):
            return args[args.index(flag) + 1] if flag in args else default

        cov = price_adjust.factor_coverage(conn)
        mfd = cov["max_factor_date"]
        default_beg = (
            (datetime.strptime(mfd, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            if mfd else None
        )
        beg = _arg("--beg", default_beg)
        end = _arg("--end", cov["max_price_date"])
        if not beg or not end or beg > end:
            print(f"Nothing to heal (factors {mfd} vs prices {cov['max_price_date']}).",
                  file=sys.stderr)
            conn.close()
            return
        try:
            changed = heal_adj_factor_gap(conn, beg, end)
            if changed:
                invalidate_rps_cache(conn, changed)
                print(f"  rps_cache invalidated from {changed} — run "
                      f"'pricedb.py rps' to recompute.", file=sys.stderr)
        finally:
            conn.close()
        return

    if sub == "backfill":
        import akshare as ak

        def _arg(flag, default):
            return args[args.index(flag) + 1] if flag in args else default

        beg = _arg("--beg", None)
        end = _arg("--end", datetime.now().strftime("%Y%m%d"))
        if beg is None:
            first = conn.execute("SELECT MIN(date) FROM daily_prices").fetchone()[0]
            beg = first.replace("-", "") if first else "20241201"

        # Resumable: a processed code has factor rows (incl. 1.0s); remaining
        # work = codes present in daily_prices with zero factor rows.
        todo = [r[0] for r in conn.execute(
            "SELECT DISTINCT code FROM daily_prices "
            "EXCEPT SELECT DISTINCT code FROM adj_factors ORDER BY 1"
        )]
        exchanges = dict(conn.execute("SELECT code, exchange FROM stocks"))
        print(f"Backfilling factors for {len(todo)} codes ({beg} → {end})...",
              file=sys.stderr)
        earliest_changed: str | None = None
        done = failed = consecutive_failures = cooldowns = 0
        for code in todo:
            try:
                # Sina publishes hfq factors directly (1 tiny request/stock) —
                # primary source. Eastmoney return-ratio derivation and akshare
                # remain as fallbacks for codes sina doesn't carry.
                events = fetch_adj_factor_events_sina(code, exchanges.get(code, ""))
                if events is not None:
                    rows = _expand_events_to_code_dates(conn, code, events)
                else:
                    series = derive_factors_eastmoney(code, exchanges.get(code, ""), beg, end)
                    if not series:
                        series = derive_factors_from_akshare(ak, code, beg, end)
                    rows = [(code, d, f) for d, f in series]
                if rows:
                    changed = upsert_adj_factors(conn, rows)
                    if changed and (earliest_changed is None or changed < earliest_changed):
                        earliest_changed = changed
                done += 1
                consecutive_failures = 0
            except Exception as e:  # keep sweeping; rerun heals the rest
                failed += 1
                consecutive_failures += 1
                print(f"  {code}: FAILED ({str(e)[:80]})", file=sys.stderr)
                if consecutive_failures >= 10:
                    cooldowns += 1
                    if cooldowns > ADJ_BACKFILL_MAX_COOLDOWNS:
                        print(
                            "ABORT: sustained connection failures — likely an "
                            "upstream IP throttle/ban. Backfill is resumable; "
                            "retry later with the same command.",
                            file=sys.stderr,
                        )
                        break
                    print(
                        f"  circuit breaker: {consecutive_failures} consecutive "
                        f"failures — cooling down {ADJ_BACKFILL_COOLDOWN_SEC:.0f}s "
                        f"({cooldowns}/{ADJ_BACKFILL_MAX_COOLDOWNS})",
                        file=sys.stderr,
                    )
                    time.sleep(ADJ_BACKFILL_COOLDOWN_SEC)
                    consecutive_failures = 0
            if (done + failed) % 100 == 0:
                print(f"  progress: {done + failed}/{len(todo)} "
                      f"({failed} failed)", file=sys.stderr)
            time.sleep(ADJ_BACKFILL_SLEEP_SEC)
        filled = _forward_fill_factors(conn)
        print(f"Backfill done: {done} ok, {failed} failed, forward-filled {filled} rows.",
              file=sys.stderr)
        if earliest_changed:
            invalidate_rps_cache(conn, earliest_changed)
            print(f"rps_cache invalidated from {earliest_changed} — run "
                  f"'pricedb.py rps' to recompute.", file=sys.stderr)
        conn.close()
        return

    conn.close()
    print(f"Unknown factors subcommand: {sub}", file=sys.stderr)
    sys.exit(1)


def _partial_price_dates(conn: sqlite3.Connection) -> list[str]:
    """Dates whose row count is under half the median daily count — the
    signature of a provider outage that landed only a fragment of the
    universe (e.g. a clist sweep killed mid-flight)."""
    counts = conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices GROUP BY date ORDER BY date"
    ).fetchall()
    if not counts:
        return []
    ordered = sorted(c for _, c in counts)
    median = ordered[len(ordered) // 2]
    return [d for d, c in counts if c < 0.5 * median]


def db_health(conn: sqlite3.Connection, spot_check: bool = False) -> dict:
    """Data-quality health block for the daily pipeline.

    The 2026-07-30 outage lesson: every degradation path already *worked*
    (coverage floor fell back to stale data) but stayed silent for days.
    This block is the loudness layer — it rides into input/db_health.json,
    the LLM prompt, the report banner, and the phase-1 contract.

    ok=False on: screening data >1 session stale, latest day partial, or
    spot-audit price mismatches. Anything notable lands in `warnings`.
    """
    out = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "ok": True,
        "warnings": [],
    }
    latest = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()[0]
    out["latest_price_date"] = latest
    if not latest:
        out["ok"] = False
        out["warnings"].append("price DB is empty")
        return out

    counts = conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices GROUP BY date "
        "ORDER BY date DESC LIMIT 30").fetchall()
    ordered = sorted(c for _, c in counts)
    median = ordered[len(ordered) // 2] if ordered else 0
    latest_count = counts[0][1] if counts else 0
    out["latest_row_count"] = latest_count
    out["median_row_count_30d"] = median
    out["latest_partial"] = bool(median and latest_count < 0.5 * median)
    if out["latest_partial"]:
        out["ok"] = False
        out["warnings"].append(
            f"latest day {latest} is PARTIAL ({latest_count} rows vs "
            f"~{median} normal) — run 'pricedb.py repair'")

    # Staleness vs the trading calendar (falls back to weekdays offline).
    expected = last_settled_trading_day().strftime("%Y%m%d")
    out["expected_latest"] = _yyyymmdd_to_iso(expected)
    latest_compact = latest.replace("-", "")
    try:
        cal = _get_trade_calendar_cached()
    except Exception:
        cal = []
    if cal:
        lag = sum(1 for c in cal if latest_compact < c <= expected)
    else:
        lag = len(_weekday_list(latest_compact, expected)) - (
            1 if latest_compact in _weekday_list(latest_compact, expected) else 0)
    out["lag_sessions"] = lag
    if lag >= 1:
        if lag > 1:
            out["ok"] = False
        out["warnings"].append(
            f"screening data is {lag} session(s) stale "
            f"(latest {latest}, expected {out['expected_latest']})")

    cov = price_adjust.factor_coverage(conn)
    out["factor_max_date"] = cov["max_factor_date"]
    if cov["max_factor_date"] and cov["max_factor_date"] < latest:
        out["warnings"].append(
            f"adj factors lag prices ({cov['max_factor_date']} < {latest}) "
            f"— run 'pricedb.py factors heal'")

    recent_partial = [d for d in _partial_price_dates(conn)
                      if d >= (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")]
    out["partial_days_30d"] = recent_partial

    if spot_check:
        out["spot_check"] = _spot_audit(conn, latest)
        if out["spot_check"]["mismatches"]:
            out["ok"] = False
            out["warnings"].append(
                f"spot audit: {len(out['spot_check']['mismatches'])} close-price "
                f"mismatches vs sina on {latest} "
                f"({','.join(m['code'] for m in out['spot_check']['mismatches'][:5])})")
    return out


def _spot_audit(conn: sqlite3.Connection, date_iso: str, sample: int = 20) -> dict:
    """Cross-source correctness check: random codes' stored closes on
    `date_iso` vs sina. Presence checks catch missing data; this catches
    wrong-but-present data (the silent killer). Fetch failures are reported
    but never counted as mismatches."""
    import random
    codes = [r[0] for r in conn.execute(
        "SELECT d.code FROM daily_prices d JOIN stocks s ON s.code = d.code "
        "WHERE d.date = ?", (date_iso,))]
    codes = [c for c in codes if _sina_symbol(c, "")]
    picked = random.sample(codes, min(sample, len(codes)))
    checked, mismatches, failures = 0, [], 0
    for code in picked:
        stored = conn.execute(
            "SELECT close FROM daily_prices WHERE code = ? AND date = ?",
            (code, date_iso)).fetchone()[0]
        try:
            rows = _fetch_klines_sina({"code": code, "exchange": ""}, 5)
        except Exception:
            failures += 1
            continue
        ref = next((r[5] for r in rows if r[1] == date_iso), None)
        if ref is None:
            failures += 1
            continue
        checked += 1
        if abs(ref - stored) > 0.011:  # prices are 2dp; anything more is real
            mismatches.append({"code": code, "stored": stored, "sina": ref})
    return {"date": date_iso, "sampled": len(picked), "checked": checked,
            "fetch_failures": failures, "mismatches": mismatches}


def backfill_amount(conn: sqlite3.Connection, beg: str, end: str,
                    dry_run: bool = False, batch_days: int = 20) -> dict:
    """Fill NULL `daily_prices.amount` from iFinD. Returns a stats dict.

    Why this is a separate command rather than a re-fetch: `amount` is NULL
    wherever _fetch_klines_sina did the filling (sina's kline archive doesn't
    publish turnover), which in August was most sessions. Re-running `update`
    cannot repair them — every writer is INSERT OR IGNORE, and first-writer-wins
    is deliberate, so the existing rows would simply be skipped.

    This writes ONLY the amount column. OHLCV is never touched, so the
    first-writer-wins invariant holds and the command is idempotent.

    Safety gate: iFinD's close for a bar must match the stored close before we
    write. A mismatch means we are about to staple turnover onto a different
    bar — count it and skip. Those are reported, never silently dropped.
    """
    client = ifind_client.get_client()
    ex_map = {c: e for c, e in conn.execute("SELECT code, exchange FROM stocks")}

    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM daily_prices "
        "WHERE amount IS NULL AND date BETWEEN ? AND ? ORDER BY date",
        (beg, end))]
    stats = {"dates": len(dates), "candidates": 0, "filled": 0,
             "conflicted": 0, "missing": 0, "failed_batches": 0}
    if not dates:
        return stats

    print(f"  {len(dates)} session(s) with NULL amount in {beg}..{end}",
          file=sys.stderr)

    # Group into contiguous date windows so one request covers many sessions.
    for i in range(0, len(dates), batch_days):
        window = dates[i:i + batch_days]
        w_beg, w_end = window[0], window[-1]
        wanted = {}
        for code, date in conn.execute(
                "SELECT code, date FROM daily_prices WHERE amount IS NULL "
                "AND date BETWEEN ? AND ?", (w_beg, w_end)):
            wanted.setdefault(code, set()).add(date)
        if not wanted:
            continue
        stats["candidates"] += sum(len(v) for v in wanted.values())

        ths_to_code = {ifind_client.to_ths_code(c, ex_map.get(c)): c for c in wanted}
        try:
            tables = _run_with_timeout(
                "iFinD amount backfill",
                lambda: client.history_quotation(
                    list(ths_to_code), "close,amount", w_beg, w_end),
                timeout=IFIND_BATCH_TIMEOUT_SEC)
        except Exception as e:
            stats["failed_batches"] += 1
            print(f"    ⚠ {w_beg}..{w_end} failed: {str(e)[:80]}", file=sys.stderr)
            continue

        updates = []
        for table in tables:
            code = ths_to_code.get(table.get("thscode"))
            if not code:
                continue
            cols = table.get("table") or {}
            closes, amounts = cols.get("close") or [], cols.get("amount") or []
            for j, day in enumerate(table.get("time") or []):
                day = str(day)[:10]
                if day not in wanted.get(code, ()):
                    continue
                amount = amounts[j] if j < len(amounts) else None
                close = closes[j] if j < len(closes) else None
                if amount is None or close is None:
                    stats["missing"] += 1
                    continue
                stored = conn.execute(
                    "SELECT close FROM daily_prices WHERE code=? AND date=?",
                    (code, day)).fetchone()
                if not stored or stored[0] is None:
                    stats["missing"] += 1
                    continue
                if abs(stored[0] - close) > max(0.011, abs(close) * 0.0005):
                    stats["conflicted"] += 1
                    continue
                updates.append((amount, code, day))

        if updates and not dry_run:
            cur = conn.executemany(
                "UPDATE daily_prices SET amount = ? "
                "WHERE code = ? AND date = ? AND amount IS NULL", updates)
            conn.commit()
            stats["filled"] += cur.rowcount
        elif updates:
            stats["filled"] += len(updates)
        print(f"    {w_beg}..{w_end}: {len(updates)} filled, "
              f"{stats['conflicted']} conflicted so far", file=sys.stderr)

    return stats


def cmd_backfill_amount(args: list):
    """CLI: pricedb.py backfill-amount [--beg ISO] [--end ISO] [--dry-run]

    Repairs the `amount` column, which is NULL wherever the sina kline fallback
    did the filling. Writes nothing but `amount`.
    """
    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = None  # off-hours repair, budget-exempt like cmd_repair

    def _arg(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    dry = "--dry-run" in args
    conn = get_db()
    ensure_schema(conn)

    if not ifind_client.is_available():
        print("iFinD not configured (IFIND_REFRESH_TOKEN) — cannot backfill",
              file=sys.stderr)
        conn.close()
        sys.exit(1)

    first = conn.execute("SELECT MIN(date) FROM daily_prices").fetchone()[0]
    last = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()[0]
    beg = _arg("--beg", first)
    end = _arg("--end", last)

    before = conn.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE amount IS NULL "
        "AND date BETWEEN ? AND ?", (beg, end)).fetchone()[0]
    print(f"amount backfill {beg} → {end}: {before:,} NULL rows"
          f"{' (dry run)' if dry else ''}", file=sys.stderr)

    stats = backfill_amount(conn, beg, end, dry_run=dry)

    after = conn.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE amount IS NULL "
        "AND date BETWEEN ? AND ?", (beg, end)).fetchone()[0]
    conn.close()

    print(f"\n  sessions scanned : {stats['dates']}", file=sys.stderr)
    print(f"  candidates       : {stats['candidates']:,}", file=sys.stderr)
    print(f"  filled           : {stats['filled']:,}", file=sys.stderr)
    print(f"  conflicted       : {stats['conflicted']:,}  "
          f"(close mismatch — NOT written)", file=sys.stderr)
    print(f"  no iFinD amount  : {stats['missing']:,}", file=sys.stderr)
    print(f"  failed batches   : {stats['failed_batches']}", file=sys.stderr)
    print(f"  NULL amount      : {before:,} → {after:,}", file=sys.stderr)
    if stats["conflicted"]:
        print("  ⚠ conflicts mean iFinD and the stored bar disagree on close — "
              "inspect before assuming the stored bar is right", file=sys.stderr)


def cmd_repair(args: list):
    """CLI: pricedb.py repair [--beg ISO] [--end ISO] [--dry-run]

    Fill partial price days from Sina's per-code kline service (raw prices,
    one request per stock covers every gap day in the window at once).
    INSERT OR IGNORE — existing rows are never overwritten, so the primary
    eastmoney data stays canonical and the sweep is idempotent. Finishes
    with a factor-gap heal and rps_cache invalidation from the first
    repaired date.
    """
    global _UPDATE_DEADLINE
    _UPDATE_DEADLINE = None  # repair is budget-exempt (off-hours, resumable)

    def _arg(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    conn = get_db()
    ensure_schema(conn)
    partial = _partial_price_dates(conn)
    if not partial:
        print("No partial days detected — nothing to repair.", file=sys.stderr)
        conn.close()
        return
    beg = _arg("--beg", min(partial))
    end = _arg("--end", conn.execute(
        "SELECT MAX(date) FROM daily_prices").fetchone()[0])
    targets = [d for d in partial if beg <= d <= end]
    before = dict(conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices WHERE date >= ? AND date <= ? "
        "GROUP BY date", (beg, end)))
    print(f"Partial days in [{beg}, {end}]: "
          f"{', '.join(f'{d}({before.get(d, 0)})' for d in targets)}",
          file=sys.stderr)
    if "--dry-run" in args:
        conn.close()
        return

    # One sina call per code returns its last N bars — size N to reach back
    # past the earliest target date, with margin for suspensions.
    n_dates = conn.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_prices WHERE date >= ?", (beg,)
    ).fetchone()[0]
    datalen = min(1023, n_dates + 15)
    stocks = [
        {"code": r[0], "name": r[1], "exchange": r[2]}
        for r in conn.execute("SELECT code, name, exchange FROM stocks")
    ]
    print(f"Sweeping {len(stocks)} codes via sina (datalen={datalen})...",
          file=sys.stderr)

    inserted = 0
    failures: list[str] = []

    def _one(stock):
        time.sleep(SINA_REPAIR_SLEEP_SEC)
        return _fetch_klines_sina(stock, datalen)

    completed = 0
    with ThreadPoolExecutor(max_workers=SINA_REPAIR_WORKERS,
                            thread_name_prefix="pricedb-sina") as pool:
        futures = {pool.submit(_one, s): s for s in stocks}
        for future in as_completed(futures):
            stock = futures[future]
            completed += 1
            try:
                rows = [r for r in future.result() if beg <= r[1] <= end]
            except Exception as e:
                failures.append(f"{stock['code']}: {str(e)[:60]}")
                rows = []
            if rows:
                # DB writes stay on this (main) thread; workers only fetch.
                cur = conn.executemany(
                    "INSERT OR IGNORE INTO daily_prices "
                    "(code,date,open,high,low,close,volume,amount) "
                    "VALUES (?,?,?,?,?,?,?,?)", rows)
                inserted += cur.rowcount
                conn.commit()
            if completed % 250 == 0 or completed == len(stocks):
                print(f"  [sina {completed}/{len(stocks)}] "
                      f"+{inserted} rows, {len(failures)} failed",
                      file=sys.stderr)

    after = dict(conn.execute(
        "SELECT date, COUNT(*) FROM daily_prices WHERE date >= ? AND date <= ? "
        "GROUP BY date", (beg, end)))
    for d in targets:
        print(f"  {d}: {before.get(d, 0)} → {after.get(d, 0)} rows",
              file=sys.stderr)
    if failures:
        print(f"  {len(failures)} codes failed (re-run repair to retry): "
          f"{'; '.join(failures[:5])}", file=sys.stderr)

    if inserted:
        invalidate_rps_cache(conn, beg)
        print(f"rps_cache invalidated from {beg}", file=sys.stderr)
        try:
            heal_adj_factor_gap(conn, beg, end)
        except Exception as e:
            print(f"WARNING: factor heal after repair failed: {e} — run "
                  f"'pricedb.py factors heal --beg {beg}'", file=sys.stderr)
    print(f"Repair done: {inserted} rows inserted.", file=sys.stderr)
    conn.close()


def cmd_status():
    """Show DB stats."""
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}")
        print("Run 'python scripts/pricedb.py init' to create it.")
        return

    conn = get_db()
    ensure_schema(conn)

    stocks_count = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    prices_count = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    date_row = conn.execute("SELECT MIN(date), MAX(date) FROM daily_prices").fetchone()
    rps_dates = conn.execute("SELECT COUNT(DISTINCT date) FROM rps_cache").fetchone()[0]
    last_update = conn.execute("SELECT MAX(last_updated) FROM stocks").fetchone()[0]
    factor_cov = price_adjust.factor_coverage(conn)
    conn.close()

    size_mb = DB_PATH.stat().st_size / 1024 / 1024

    print(f"DB path  : {DB_PATH}")
    print(f"DB size  : {size_mb:.1f} MB")
    print(f"Stocks   : {stocks_count:,}")
    print(f"Prices   : {prices_count:,} rows")
    if date_row[0]:
        print(f"Date range: {date_row[0]} → {date_row[1]}")
    else:
        print("Date range: (no price data yet)")
    if last_update:
        print(f"Updated  : {last_update}")
    print(f"RPS cache: {rps_dates} dates computed")
    # Judge on the factored universe, never on pair_coverage_pct — the latter
    # counts unfactorable BJ codes in its denominator and so warns forever.
    unfactored = factor_cov["codes_without_factors"]
    note = f"; {unfactored} codes unfactored — BJ/次新, read as 1.0" if unfactored else ""
    print(f"Adj factors: {factor_cov['universe_coverage_pct']:.1f}% coverage "
          f"(latest {factor_cov['max_factor_date'] or 'none'}{note})")
    for problem in factor_cov["problems"]:
        print(f"WARNING: {problem}")


def cmd_rps(date: str = None):
    """Compute MA-based RPS for all stocks on DATE (default: latest)."""
    if not DB_PATH.exists():
        print("DB not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parent))
    from rps_calculator import compute_ma_rps

    if date is None:
        conn = get_db()
        row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
        date = row[0] if row and row[0] else None
        conn.close()

    if not date:
        print("No price data in DB.", file=sys.stderr)
        sys.exit(1)

    print(f"Computing MA-based RPS for {date}...", file=sys.stderr)
    t0 = time.time()
    results = compute_ma_rps(str(DB_PATH), date)
    elapsed = time.time() - t0
    print(f"  {len(results)} stocks, {elapsed:.1f}s", file=sys.stderr)

    if not results:
        print("No results.", file=sys.stderr)
        return

    top = sorted(
        [(code, data) for code, data in results.items() if data.get("rps120") is not None],
        key=lambda item: item[1]["rps120"],
        reverse=True,
    )[:20]
    print(f"\nTop 20 by RPS120 on {date}:")
    print(f"{'Code':<8} {'RPS20':>6} {'RPS60':>6} {'RPS120':>7} {'RPS250':>7} {'MA10':>10}")
    for code, data in top:
        r20 = f"{data['rps20']:.1f}" if data.get("rps20") is not None else "n/a"
        r60 = f"{data['rps60']:.1f}" if data.get("rps60") is not None else "n/a"
        r120 = f"{data['rps120']:.1f}" if data.get("rps120") is not None else "n/a"
        r250 = f"{data['rps250']:.1f}" if data.get("rps250") is not None else "n/a"
        ma10 = f"{data['ma10_today']:.2f}" if data.get("ma10_today") is not None else "n/a"
        print(f"{code:<8} {r20:>6} {r60:>6} {r120:>7} {r250:>7} {ma10:>10}")



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


def cmd_snapshot(argv: list):
    """CLI: pricedb.py snapshot [--date ISO] [--dry-run] [--force]

    Write today's settled bar from Sina's real-time quote feed (see
    snapshot_bars.py for why this exists and how it was validated).

    Refuses to run while the session is open: mid-session the feed reports an
    unsettled intraday bar, and writing that into daily_prices corrupts every
    MA and RPS downstream. --force overrides for testing only, never in a
    scheduled run.

    INSERT OR IGNORE, so existing rows are never overwritten — if the kline
    archive already delivered a day, this cannot damage it.
    """
    import snapshot_bars

    dry = "--dry-run" in argv
    force = "--force" in argv
    target = None
    if "--date" in argv:
        target = argv[argv.index("--date") + 1]

    if is_session_open() and not force:
        print("Session is still open — refusing to write an unsettled bar. "
              "(--force overrides, for testing only.)", file=sys.stderr)
        sys.exit(2)

    if target is None:
        target = most_recent_trading_day(_now().date()).isoformat()

    conn = get_db()
    ensure_schema(conn)
    stocks = [r[0] for r in conn.execute("SELECT code FROM stocks")]
    if not stocks:
        print("No stocks in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    before = conn.execute("SELECT COUNT(*) FROM daily_prices WHERE date = ?",
                          (target,)).fetchone()[0]
    print(f"Snapshot for {target}: {len(stocks)} codes, {before} rows already present",
          file=sys.stderr)

    def _progress(done, total, got):
        if done % 1000 == 0 or done == total:
            print(f"  [snapshot {done}/{total}] {got} bars parsed", file=sys.stderr)

    rows, stats = _snapshot_via_ifind(conn, stocks, target)
    if rows is None:
        rows, stats = snapshot_bars.fetch_snapshot_bars(stocks, target,
                                                        progress=_progress)
        print(f"  parsed {stats['rows']} bars "
              f"(unsupported/BJ {stats['skipped_unsupported']}, "
              f"rejected {stats['rejected']}, failed batches {stats['failed_batches']})",
              file=sys.stderr)

    if dry:
        print("  --dry-run: nothing written", file=sys.stderr)
        conn.close()
        return

    cur = conn.executemany(
        "INSERT OR IGNORE INTO daily_prices "
        "(code,date,open,high,low,close,volume,amount) VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    after = conn.execute("SELECT COUNT(*) FROM daily_prices WHERE date = ?",
                         (target,)).fetchone()[0]
    conn.close()
    print(f"  {target}: {before} → {after} rows ({cur.rowcount} inserted)", file=sys.stderr)
    if stats["failed_batches"]:
        print(f"  WARNING: {stats['failed_batches']} batch(es) failed — day may be "
              f"incomplete; re-run, or let the kline archive fill the rest tonight",
              file=sys.stderr)


def cmd_query(code: str):
    """Show a stock's recent prices and computed RPS values."""
    if not DB_PATH.exists():
        print("DB not found. Run 'init' first.", file=sys.stderr)
        sys.exit(1)

    conn = get_db()
    ensure_schema(conn)

    stock = conn.execute(
        "SELECT code, name, exchange FROM stocks WHERE code=?",
        (code,),
    ).fetchone()
    if not stock:
        print(f"Stock {code} not found in DB.")
        conn.close()
        return

    print(f"Stock: {stock[0]} ({stock[1]}) [{stock[2]}]")

    prices = conn.execute(
        "SELECT date, open, high, low, close, volume FROM daily_prices "
        "WHERE code=? ORDER BY date DESC LIMIT 20",
        (code,),
    ).fetchall()
    conn.close()

    if not prices:
        print("No price data found.")
        return

    print(f"\n{'Date':<12} {'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>12}")
    for row in prices:
        print(f"{row[0]:<12} {row[1]:>8.2f} {row[2]:>8.2f} {row[3]:>8.2f} {row[4]:>8.2f} {row[5]:>12,}")

    latest_date = prices[0][0]
    sys.path.insert(0, str(Path(__file__).parent))
    from rps_calculator import get_ma_rps_for_stocks

    rps_data = get_ma_rps_for_stocks(str(DB_PATH), [code], latest_date)
    rps = rps_data.get(code, {})
    if rps:
        print(f"\nRPS on {latest_date}:")
        for key in ["rps20", "rps60", "rps120", "rps250"]:
            value = rps.get(key)
            print(f"  {key.upper()}: {value:.1f}" if value is not None else f"  {key.upper()}: n/a")
        if rps.get("ma10_today"):
            print(f"  MA10 : {rps['ma10_today']:.2f}")
    else:
        print(f"\nNo RPS data for {latest_date} (insufficient history).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "init":
        cmd_init()
    elif command == "update":
        cmd_update()
    elif command == "status":
        cmd_status()
    elif command == "rps":
        cmd_rps(sys.argv[2] if len(sys.argv) > 2 else None)
    elif command == "factors":
        cmd_factors(sys.argv[2:])
    elif command == "repair":
        cmd_repair(sys.argv[2:])
    elif command == "backfill-amount":
        cmd_backfill_amount(sys.argv[2:])
    elif command == "snapshot":
        cmd_snapshot(sys.argv[2:])
    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: pricedb.py query CODE", file=sys.stderr)
            sys.exit(1)
        cmd_query(sys.argv[2])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)
