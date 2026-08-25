"""Provider-chain doctrine tests (2026-08-25).

User decision after acquiring a paid iFinD seat: the daily price chain is
iFinD primary → AkShare → Sina. iFinD leads on measured accuracy, speed and
`amount` coverage (docs/IFIND_EVAL/FINDINGS.md); the free chain is kept behind
it because iFinD is a single commercial dependency whose token can lapse, and
db_health gates the pipeline.

Supersedes the 2026-08-01 doctrine (AkShare primary → Sina) that followed the
eastmoney IP-throttle outage. eastmoney clist/direct, baostock and tushare stay
retired for price bars (kept only as internal helpers). These tests pin the
doctrine so the chain can't quietly regrow.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb

D1, D2 = "2026-07-30", "2026-07-31"


def test_chain_is_ifind_then_akshare_then_sina(monkeypatch):
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: True)
    names = [name for name, _ in pricedb.iter_providers()]
    assert names == [pricedb.PROVIDER_IFIND, pricedb.PROVIDER_AKSHARE,
                     pricedb.PROVIDER_SINA]


def test_chain_degrades_to_free_providers_without_a_token(monkeypatch):
    """A lapsed iFinD seat must fall back, not hard-stop the pipeline."""
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: False)
    names = [name for name, _ in pricedb.iter_providers()]
    assert names == [pricedb.PROVIDER_AKSHARE, pricedb.PROVIDER_SINA]


def test_retired_providers_stay_out_of_the_chain(monkeypatch):
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: True)
    names = {name for name, _ in pricedb.iter_providers()}
    assert not names & {pricedb.PROVIDER_EASTMONEY, pricedb.PROVIDER_EASTMONEY_CLIST,
                        pricedb.PROVIDER_BAOSTOCK, pricedb.PROVIDER_TUSHARE}


def _conn_with_stock():
    conn = sqlite3.connect(":memory:")
    pricedb.ensure_schema(conn)
    conn.execute("INSERT INTO stocks(code, name, exchange) "
                 "VALUES ('000001', '平安银行', 'SZ')")
    return conn


def test_bulk_fetch_sina_window_filter_and_ignore(monkeypatch):
    conn = _conn_with_stock()
    # pre-existing primary row must NOT be overwritten (amount stays)
    conn.execute("INSERT INTO daily_prices VALUES "
                 "('000001', ?, 11.28, 11.62, 11.18, 11.61, 2777707, 999.0)", (D1,))
    conn.commit()
    monkeypatch.setattr(pricedb, "SINA_REPAIR_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_klines_sina", lambda stock, datalen: [
        ("000001", "2026-07-29", 11.19, 11.36, 11.18, 11.28, 1511054, None),  # pre-window
        ("000001", D1, 11.28, 11.62, 11.18, 11.61, 2777707, None),            # exists
        ("000001", D2, 11.50, 11.63, 11.28, 11.63, 2024978, None),            # new
    ])

    pricedb._bulk_fetch_sina(conn, [{"code": "000001", "exchange": "SZ"}],
                             "20260730", "20260731", None)

    rows = conn.execute(
        "SELECT date, close, amount FROM daily_prices ORDER BY date").fetchall()
    assert rows == [(D1, 11.61, 999.0), (D2, 11.63, None)]


def _ifind_table(thscode, dates, closes, volumes, amounts):
    return {"thscode": thscode, "time": dates,
            "table": {"open": closes, "high": closes, "low": closes,
                      "close": closes, "volume": volumes, "amount": amounts}}


def test_bulk_fetch_ifind_converts_shares_to_lots_and_keeps_amount(monkeypatch):
    """iFinD volume is in SHARES; pricedb stores 手. `amount` must survive."""
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: _FakeClient([
        _ifind_table("000001.SZ", [D1, D2], [11.61, 11.63],
                     [2777707_00, 2024978_00], [1.5e9, 1.6e9])]))

    pricedb._bulk_fetch_ifind(conn, [{"code": "000001", "exchange": "SZ"}],
                              "20260730", "20260731", None)

    rows = conn.execute("SELECT date, close, volume, amount FROM daily_prices "
                        "ORDER BY date").fetchall()
    assert rows == [(D1, 11.61, 2777707, 1.5e9), (D2, 11.63, 2024978, 1.6e9)]


def test_bulk_fetch_ifind_respects_first_writer_wins(monkeypatch):
    """INSERT OR IGNORE: an existing row is never overwritten."""
    conn = _conn_with_stock()
    conn.execute("INSERT INTO daily_prices VALUES "
                 "('000001', ?, 1, 1, 1, 99.0, 111, 999.0)", (D1,))
    conn.commit()
    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: _FakeClient([
        _ifind_table("000001.SZ", [D1, D2], [11.61, 11.63],
                     [100, 200], [1.0, 2.0])]))

    pricedb._bulk_fetch_ifind(conn, [{"code": "000001", "exchange": "SZ"}],
                              "20260730", "20260731", None)

    rows = conn.execute("SELECT date, close, amount FROM daily_prices "
                        "ORDER BY date").fetchall()
    assert rows == [(D1, 99.0, 999.0), (D2, 11.63, 2.0)]


def test_bulk_fetch_ifind_filters_window_and_skips_suspended(monkeypatch):
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: _FakeClient([
        _ifind_table("000001.SZ", ["2026-07-29", D1, D2],
                     [11.28, None, 11.63],       # D1 suspended → no bar
                     [100, None, 200], [1.0, None, 2.0])]))

    pricedb._bulk_fetch_ifind(conn, [{"code": "000001", "exchange": "SZ"}],
                              "20260730", "20260731", None)

    dates = [r[0] for r in conn.execute("SELECT date FROM daily_prices ORDER BY date")]
    assert dates == [D2], "pre-window and suspended rows must both be dropped"


def test_bulk_fetch_ifind_raises_on_empty_weekday_window(monkeypatch):
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: _FakeClient([]))
    with pytest.raises(RuntimeError, match="no rows"):
        pricedb._bulk_fetch_ifind(conn, [{"code": "000001", "exchange": "SZ"}],
                                  "20260730", "20260731", None)


class _FakeClient:
    def __init__(self, tables):
        self._tables = tables
        self.data_vol = 0

    def history_quotation(self, codes, indicators, beg, end, **kwargs):
        return self._tables

    def real_time(self, codes, indicators, **kwargs):
        return self._tables


# ---------------------------------------------------------------------------
# iFinD snapshot — same guards as snapshot_bars.parse_quote_line
# ---------------------------------------------------------------------------

TARGET = "2026-08-25"


def _rt_table(stamp="2026-08-25 16:01:08", o=11.5, h=11.7, low=11.4,
              latest=11.6, volume=994881, amount=1.15e9):
    return {"thscode": "000001.SZ", "time": [stamp],
            "table": {"open": [o], "high": [h], "low": [low], "latest": [latest],
                      "volume": [volume], "amount": [amount]}}


def _snapshot(monkeypatch, tables):
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: True)
    monkeypatch.setattr(pricedb.ifind_client, "get_client",
                        lambda: _FakeClient(tables))
    return pricedb._snapshot_via_ifind(conn, ["000001"], TARGET)


def test_snapshot_keeps_realtime_volume_in_lots(monkeypatch):
    """real_time returns 手 already — dividing by 100 here would be a 100x bug."""
    rows, stats = _snapshot(monkeypatch, [_rt_table(volume=994881)])
    assert rows == [("000001", TARGET, 11.5, 11.7, 11.4, 11.6, 994881, 1.15e9)]
    assert stats["rejected"] == 0


def test_snapshot_rejects_stale_session(monkeypatch):
    """A suspended name keeps reporting its last session; never stamp it today."""
    rows, _ = _snapshot(monkeypatch, [_rt_table(stamp="2026-08-24 15:30:00")])
    assert rows is None


def test_snapshot_rejects_pre_close_timestamp(monkeypatch):
    """Before 15:00 the 'close' is really an intraday print."""
    rows, _ = _snapshot(monkeypatch, [_rt_table(stamp="2026-08-25 11:30:00")])
    assert rows is None


def test_snapshot_rejects_zero_volume(monkeypatch):
    rows, _ = _snapshot(monkeypatch, [_rt_table(volume=0)])
    assert rows is None


def test_snapshot_rejects_incoherent_bar(monkeypatch):
    """close above high — do not trust any of it."""
    rows, _ = _snapshot(monkeypatch, [_rt_table(h=11.7, latest=99.0)])
    assert rows is None


def test_snapshot_returns_none_when_ifind_unavailable(monkeypatch):
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: False)
    assert pricedb._snapshot_via_ifind(conn, ["000001"], TARGET) == (None, None)


def test_snapshot_falls_back_when_client_raises(monkeypatch):
    """A snapshot is best-effort: errors must degrade to sina, not kill the run."""
    conn = _conn_with_stock()

    class _Boom:
        data_vol = 0

        def real_time(self, *a, **k):
            raise RuntimeError("network down")

    monkeypatch.setattr(pricedb.ifind_client, "is_available", lambda: True)
    monkeypatch.setattr(pricedb.ifind_client, "get_client", lambda: _Boom())
    assert pricedb._snapshot_via_ifind(conn, ["000001"], TARGET) == (None, None)


def test_bulk_fetch_sina_raises_on_empty_weekday_window(monkeypatch):
    conn = _conn_with_stock()
    monkeypatch.setattr(pricedb, "SINA_REPAIR_SLEEP_SEC", 0.0)
    monkeypatch.setattr(pricedb, "_fetch_klines_sina", lambda stock, datalen: [])
    with pytest.raises(RuntimeError, match="no rows"):
        pricedb._bulk_fetch_sina(conn, [{"code": "000001", "exchange": "SZ"}],
                                 "20260730", "20260731", None)


def test_fetch_stock_list_akshare_derives_exchange(monkeypatch):
    import pandas as pd
    fake = pd.DataFrame({"code": ["600000", "000001", "300750", "920001"],
                         "name": ["浦发银行", "平安银行", "宁德时代", "某北交所"]})

    class _AK:
        @staticmethod
        def stock_info_a_code_name():
            return fake

    out = pricedb.fetch_stock_list_akshare(_AK)
    assert {s["code"]: s["exchange"] for s in out} == {
        "600000": "SH", "000001": "SZ", "300750": "SZ", "920001": "BJ"}
