#!/usr/bin/env python3
"""
pricedb.py — Local A-share price database management.

SQLite-backed price history for all A-share stocks.
Data sources:
- Primary: Tushare Pro (requires `TUSHARE_TOKEN` / `TUSHARE_PRO_TOKEN`)
- Fallback: BaoStock

Usage:
    python scripts/pricedb.py init          # Create DB, fetch stock list, download ALL historical data
    python scripts/pricedb.py update        # Incremental update: fetch missing dates since last update
    python scripts/pricedb.py status        # Show DB stats: total stocks, date range, last update
    python scripts/pricedb.py rps [DATE]    # Compute MA-based RPS for all stocks on DATE (default: latest)
    python scripts/pricedb.py query CODE    # Show a stock's recent prices + computed RPS values
"""

import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "data" / "pricedb"
DB_PATH = DB_DIR / "ashare_prices.db"
ENV_FILE = PROJECT_ROOT / ".env"

PROVIDER_TUSHARE = "tushare"
PROVIDER_BAOSTOCK = "baostock"
TUSHARE_TOKEN_ENV_NAMES = ("TUSHARE_TOKEN", "TUSHARE_PRO_TOKEN", "TS_TOKEN")

# History needed: 250-day RPS + 10-day MA buffer → use extra holiday margin
INIT_HISTORY_DAYS = 450
TUSHARE_RETRY_DELAY = 0.5
TUSHARE_RETRIES = 3


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
    """Yield available providers in preferred order: Tushare, then BaoStock."""
    token = get_tushare_token()
    if token:
        try:
            import tushare as ts

            yield PROVIDER_TUSHARE, ts.pro_api(token=token, timeout=30)
        except Exception as e:
            print(f"  Could not initialize Tushare: {e}", file=sys.stderr)
    else:
        print("  Tushare token not found; will try BaoStock fallback.", file=sys.stderr)

    try:
        import baostock as bs

        login_result = bs.login()
        if getattr(login_result, "error_code", "0") != "0":
            raise RuntimeError(getattr(login_result, "error_msg", "BaoStock login failed"))
        yield PROVIDER_BAOSTOCK, bs
    except Exception as e:
        print(f"  Could not initialize BaoStock: {e}", file=sys.stderr)


def close_provider(provider_name: str, provider: object):
    """Close provider resources if needed."""
    if provider_name == PROVIDER_BAOSTOCK:
        try:
            provider.logout()
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
# Tushare provider
# ---------------------------------------------------------------------------


def _call_tushare(label: str, func):
    """Call a Tushare API with retries."""
    last_error = None
    for attempt in range(TUSHARE_RETRIES):
        try:
            return func()
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
    trade_dates = fetch_trade_dates_tushare(pro, beg, end)
    if not trade_dates:
        raise RuntimeError(f"No trading dates returned for {beg} → {end}")

    valid_codes = {stock["code"] for stock in stocks}
    total_inserted = 0

    for index, trade_date in enumerate(trade_dates, start=1):
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
        rows = _baostock_rows(bs.query_all_stock(day=day))
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
    result = bs.query_history_k_data_plus(
        code_full,
        "date,code,open,high,low,close,volume,amount",
        start_date=_yyyymmdd_to_iso(beg),
        end_date=_yyyymmdd_to_iso(end),
        frequency="d",
        adjustflag="3",
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

    for index, stock in enumerate(stocks, start=1):
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

        if index % 100 == 0 or index == len(stocks):
            print(
                f"  [BaoStock {index}/{len(stocks)}] last: {stock['code']} → {len(rows)} rows",
                file=sys.stderr,
            )

    print(f"  Total: {total_inserted:,} rows inserted", file=sys.stderr)


# ---------------------------------------------------------------------------
# Unified provider API
# ---------------------------------------------------------------------------


def fetch_stock_list(provider_name: str, provider: object) -> list[dict]:
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
    if provider_name == PROVIDER_TUSHARE:
        return _bulk_fetch_tushare(conn, stocks, beg, end, provider)
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

    conn = get_db()
    ensure_schema(conn)

    row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
    latest = row[0] if row and row[0] else None
    if not latest:
        print("No price data in DB. Run 'init' first.", file=sys.stderr)
        conn.close()
        sys.exit(1)

    beg = (datetime.strptime(latest, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    provider_errors = []

    for provider_name, provider in iter_providers():
        try:
            print(f"Refreshing stock list via {provider_name}...", file=sys.stderr)
            latest_stocks = fetch_stock_list(provider_name, provider)
            if not latest_stocks:
                raise RuntimeError(f"{provider_name} returned no stock list")
            upsert_stocks(conn, latest_stocks)
            print(f"  {len(latest_stocks)} stocks in universe", file=sys.stderr)

            stocks = [
                {"code": row[0], "name": row[1], "exchange": row[2]}
                for row in conn.execute("SELECT code, name, exchange FROM stocks")
            ]
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
            conn.close()
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
    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: pricedb.py query CODE", file=sys.stderr)
            sys.exit(1)
        cmd_query(sys.argv[2])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)
