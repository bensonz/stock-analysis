import sqlite3
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from rps_calculator import _resolve_reference_date, compute_ma_rps


def _seed_rps_db_with_sparse_head_dates(db_path: Path) -> str:
    codes = ["000001", "000002", "000003", "000004", "000005"]
    older_full_dates = [f"2026-03-{day:02d}" for day in range(1, 21)]
    sparse_dates = [f"2026-03-{day:02d}" for day in range(21, 30)]
    latest_full_date = "2026-03-30"

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE daily_prices (date TEXT, code TEXT, close REAL)")
        conn.execute(
            "CREATE TABLE rps_cache (date TEXT, code TEXT, rps20 REAL, rps60 REAL, rps120 REAL, rps250 REAL, ma10 REAL)"
        )

        for date_index, date_str in enumerate(older_full_dates, start=1):
            for code_index, code in enumerate(codes, start=1):
                conn.execute(
                    "INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)",
                    (date_str, code, 10.0 + date_index + code_index / 100),
                )

        for date_index, date_str in enumerate(sparse_dates, start=1):
            conn.execute(
                "INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)",
                (date_str, "000001", 30.0 + date_index),
            )

        for code_index, code in enumerate(codes, start=1):
            conn.execute(
                "INSERT INTO daily_prices(date, code, close) VALUES (?, ?, ?)",
                (latest_full_date, code, 50.0 + code_index / 10),
            )

        conn.commit()

    return latest_full_date


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


def test_compute_ma_rps_skips_sparse_dates_inside_ma_windows(tmp_path):
    db_path = tmp_path / "prices.db"
    _seed_rps_db_with_sparse_head_dates(db_path)

    results = compute_ma_rps(str(db_path), force_recompute=True)

    assert len(results) == 5
    assert set(results) == {"000001", "000002", "000003", "000004", "000005"}


def test_compute_ma_rps_recomputes_when_cache_is_undersized(tmp_path):
    db_path = tmp_path / "prices.db"
    latest_full_date = _seed_rps_db_with_sparse_head_dates(db_path)

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO rps_cache(date, code, rps20, rps60, rps120, rps250, ma10) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (latest_full_date, "000001", 10.0, 20.0, 30.0, 40.0, 11.1),
        )
        conn.commit()

    results = compute_ma_rps(str(db_path))

    assert len(results) == 5

    with sqlite3.connect(str(db_path)) as conn:
        cached_count = conn.execute("SELECT COUNT(*) FROM rps_cache WHERE date=?", (latest_full_date,)).fetchone()[0]

    assert cached_count == 5
