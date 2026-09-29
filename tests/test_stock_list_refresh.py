"""pricedb.refresh_stock_list — the universe refresh as its own step.

Until 2026-09-29 the stock list was refreshed only inside the akshare branch
of `update`, i.e. only when every provider ahead of akshare failed. iFinD
answered first from 08-25 and the close-slot snapshot has pre-empted `update`
since 09-25, so the list sat at 2026-08-24 for five weeks and 20 new listings
never entered the DB. Nothing reported it.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb


def _conn(codes):
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    conn.executemany(
        "INSERT INTO stocks(code, name, exchange, last_updated) VALUES (?,?,?,?)",
        [(c, c, "SH", "2026-08-24 15:05:21") for c in codes])
    conn.commit()
    return conn


def _listing(*codes):
    return lambda: [{"code": c, "name": f"n{c}", "exchange": "SH"} for c in codes]


def test_new_listings_are_added_and_reported():
    conn = _conn(["600000"])
    out = pricedb.refresh_stock_list(conn, fetch=_listing("600000", "601091"))
    assert out == {"total": 2, "added": ["601091"]}
    assert conn.execute("SELECT name FROM stocks WHERE code='601091'").fetchone() == ("n601091",)


def test_refresh_stamps_last_updated_on_every_listed_code():
    conn = _conn(["600000"])
    pricedb.refresh_stock_list(conn, fetch=_listing("600000"))
    stamp = conn.execute("SELECT last_updated FROM stocks").fetchone()[0]
    assert not stamp.startswith("2026-08-24")


def test_delisted_codes_are_kept():
    # History still references them; the refresh adds, it never prunes.
    conn = _conn(["600000", "600001"])
    pricedb.refresh_stock_list(conn, fetch=_listing("600000"))
    assert conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0] == 2


def test_empty_listing_fails_loudly_and_writes_nothing():
    conn = _conn(["600000"])
    with pytest.raises(RuntimeError, match="empty"):
        pricedb.refresh_stock_list(conn, fetch=lambda: [])
    stamp = conn.execute("SELECT last_updated FROM stocks").fetchone()[0]
    assert stamp.startswith("2026-08-24")
