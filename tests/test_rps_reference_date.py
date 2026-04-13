import sqlite3
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rps_calculator import _resolve_reference_date


def test_resolve_reference_date_skips_sparse_latest_date(tmp_path):
    db_path = tmp_path / "prices.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE daily_prices (date TEXT, code TEXT, close REAL)")
        for code in ["000001", "000002", "000003", "000004", "000005"]:
            conn.execute("INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)", ("2026-03-31", code, 10.0))
        conn.execute("INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)", ("2026-04-09", "000001", 10.5))
        conn.commit()

        resolved = _resolve_reference_date(conn, None)

    assert resolved == "2026-03-31"


def test_resolve_reference_date_respects_requested_upper_bound(tmp_path):
    db_path = tmp_path / "prices.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE daily_prices (date TEXT, code TEXT, close REAL)")
        for code in ["000001", "000002", "000003", "000004", "000005"]:
            conn.execute("INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)", ("2026-03-31", code, 10.0))
            conn.execute("INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)", ("2026-03-30", code, 9.8))
        conn.execute("INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)", ("2026-04-09", "000001", 10.5))
        conn.commit()

        resolved = _resolve_reference_date(conn, "2026-03-30")

    assert resolved == "2026-03-30"
