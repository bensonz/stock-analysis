"""Schema and row persistence, driven against `:memory:` — no network, no mocks.

`pricedb_storage.py` was split out of pricedb.py on 2026-08-30. Every function
takes an explicit `conn`, which is what makes these tests possible at all: before
the split the same logic sat in a module whose import pulls in ifind_client and
akshare, so touching it from a test meant standing up the world.

`get_db()` and DB_PATH deliberately did NOT move. Two tests monkeypatch
`pricedb.DB_PATH`; had the factory moved it would read
`pricedb_storage.DB_PATH` and those patches would silently stop working. A test
that still passes while testing nothing is worse than no test. Hence the rule:
storage takes a connection, it does not create one.

The `write_bars` cases matter more than they look. That INSERT existed in TEN
hand-written copies across the provider functions, each repeating
`(code,date,open,high,low,close,volume,amount)` — ten chances to transpose two
columns and write a volume into a price, with nothing to catch it but a strange
chart weeks later.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb.storage as storage

BAR = ("600000", "2026-08-28", 10.0, 10.8, 9.9, 10.5, 123456, 7890123.0)


def fresh():
    conn = sqlite3.connect(":memory:")
    storage.ensure_schema(conn)
    return conn


def test_schema_is_created_from_nothing():
    conn = fresh()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"stocks", "daily_prices"} <= tables


def test_ensure_schema_is_idempotent():
    """It runs on every command; a second call must not throw or wipe data."""
    conn = fresh()
    storage.write_bars(conn, [BAR])
    storage.ensure_schema(conn)
    assert conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0] == 1


def test_write_bars_persists_columns_in_the_declared_order():
    """The whole point of one shared INSERT: close must land in close, not in
    volume. Read the row back by NAME, not by position."""
    conn = fresh()
    assert storage.write_bars(conn, [BAR]) == 1
    row = conn.execute(
        "SELECT code, date, open, high, low, close, volume, amount "
        "FROM daily_prices").fetchone()
    assert row == BAR


def test_write_bars_on_empty_input_is_a_no_op():
    """Providers call it with whatever they got, including nothing."""
    conn = fresh()
    assert storage.write_bars(conn, []) == 0


def test_replace_mode_lets_the_primary_provider_win():
    conn = fresh()
    storage.write_bars(conn, [BAR])
    richer = ("600000", "2026-08-28", 1.0, 1.0, 1.0, 99.0, 1, 2.0)
    storage.write_bars(conn, [richer], replace=True)
    assert conn.execute("SELECT close FROM daily_prices").fetchone()[0] == 99.0


def test_ignore_mode_protects_a_richer_row_from_a_thinner_one():
    """Sina bars carry NULL amount. Letting one overwrite an iFinD row would
    lose data no later pass restores — which is why the repair paths use
    IGNORE, and why the mode is an explicit argument rather than a default."""
    conn = fresh()
    storage.write_bars(conn, [BAR])
    thin = ("600000", "2026-08-28", 1.0, 1.0, 1.0, 1.0, 1, None)
    assert storage.write_bars(conn, [thin], replace=False) == 0
    code, close, amount = conn.execute(
        "SELECT code, close, amount FROM daily_prices").fetchone()
    assert (close, amount) == (10.5, 7890123.0)


def test_upsert_stocks_adds_then_updates_without_duplicating():
    conn = fresh()
    storage.upsert_stocks(conn, [{"code": "600000", "name": "浦发银行", "exchange": "SH"}])
    storage.upsert_stocks(conn, [{"code": "600000", "name": "浦发银行A", "exchange": "SH"}])
    rows = conn.execute("SELECT code, name FROM stocks").fetchall()
    assert len(rows) == 1 and rows[0][1] == "浦发银行A"


def test_partial_days_are_identified_against_the_universe():
    """A day fetched only halfway must be visible as partial — that is the
    signal db_health and the coverage cursor both key off."""
    conn = fresh()
    storage.upsert_stocks(conn, [
        {"code": f"{600000+i:06d}", "name": "x", "exchange": "SH"} for i in range(100)])
    full = [(f"{600000+i:06d}", "2026-08-27", 1, 1, 1, 1, 1, 1.0) for i in range(100)]
    part = [(f"{600000+i:06d}", "2026-08-28", 1, 1, 1, 1, 1, 1.0) for i in range(10)]
    storage.write_bars(conn, full + part)
    assert storage._last_fully_covered_date(conn) == "2026-08-27"


def test_the_coverage_cursor_is_none_on_an_empty_db():
    """Must not invent a date — callers use this to decide what to fetch."""
    assert storage._last_fully_covered_date(fresh()) is None
