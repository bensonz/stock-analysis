"""The pure bar/code transforms — tested with no mocking whatsoever.

That property is the whole reason `pricedb_bars.py` was split out of the
3,649-line `pricedb.py` on 2026-08-30. Before the split, exercising a 7-line
date converter meant importing a module that pulls in ifind_client, akshare and
the sqlite schema, so tests reached for private network names
(`_fetch_klines_sina`, `_fetch_clist_page`, `_ifind_af_series`) to get anywhere
near the logic. Not one line below patches anything.

These functions are the boundary between a provider's wire format and our row
tuple. They are where an off-by-one column or a silently-swallowed None becomes
a wrong price in the database, which makes them exactly the code that should be
cheapest to test.

If anything here ever needs a `conn` or a socket, it does not belong in
pricedb_bars — that is the boundary worth defending.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pricedb.bars as bars


# --- date / code normalisation ---------------------------------------------

def test_yyyymmdd_becomes_iso():
    assert bars._yyyymmdd_to_iso("20260828") == "2026-08-28"


def test_a_value_already_iso_is_left_alone():
    """Called on both shapes; converting twice must not corrupt."""
    assert bars._yyyymmdd_to_iso("2026-08-28") == "2026-08-28"


def test_none_survives_normalisation():
    assert bars._yyyymmdd_to_iso(None) is None


def test_iso_to_yyyymmdd_round_trips():
    assert bars._iso_to_yyyymmdd(bars._yyyymmdd_to_iso("20260828")) == "20260828"


def test_exchange_is_inferred_from_the_code_prefix():
    assert bars._exchange_from_code("600000") == "SH"
    assert bars._exchange_from_code("000001") == "SZ"
    assert bars._exchange_from_code("300750") == "SZ"


def test_sina_symbol_prefixes_the_exchange_in_lower_case():
    assert bars._sina_symbol("600000", "SH") == "sh600000"
    assert bars._sina_symbol("000001", "SZ") == "sz000001"


# --- numeric coercion -------------------------------------------------------

def test_safe_float_turns_junk_into_none_not_zero():
    """Zero is a real price; None is 'we do not know'. Collapsing the second
    into the first is how a missing bar becomes a limit-down."""
    assert bars._safe_float("12.34") == 12.34
    assert bars._safe_float("-") is None
    assert bars._safe_float("") is None
    assert bars._safe_float(None) is None


def test_safe_float_keeps_a_genuine_zero():
    assert bars._safe_float("0") == 0.0
    assert bars._safe_float(0) == 0.0


def test_safe_int_behaves_the_same_way():
    assert bars._safe_int("100") == 100
    assert bars._safe_int("-") is None
    assert bars._safe_int(None) is None


# --- weekday windows --------------------------------------------------------

def test_weekday_list_excludes_the_weekend():
    """2026-08-28 is a Friday; the 29th and 30th are the weekend."""
    got = bars._weekday_list("20260828", "20260831")
    assert got == ["20260828", "20260831"]


def test_a_window_entirely_inside_a_weekend_is_empty():
    """This emptiness is load-bearing: _bulk_fetch_* uses it to tell 'the
    provider returned nothing on a trading day' (a real failure) from 'we asked
    about a Saturday' (not a failure)."""
    assert bars._weekday_list("20260829", "20260830") == []


def test_a_reversed_window_yields_nothing_rather_than_raising():
    assert bars._weekday_list("20260831", "20260828") == []


# --- provider payload → row tuple ------------------------------------------

def test_eastmoney_kline_string_maps_onto_a_row():
    stock = {"code": "600000", "exchange": "SH"}
    row = bars._eastmoney_kline_to_tuple(
        stock, "2026-08-28,10.00,10.50,10.80,9.90,123456,7890123.0,1.0,2.0,0.5,1.5")
    assert row[0] == "600000"
    assert row[1] == "2026-08-28"
    assert 9.0 < row[4] < 11.0          # close sits in the OHLC band


def test_a_malformed_kline_is_dropped_not_guessed():
    """A short row must not silently shift columns — that would write a volume
    into a price."""
    assert bars._eastmoney_kline_to_tuple({"code": "600000"}, "2026-08-28,10.00") is None


def test_akshare_row_maps_onto_the_same_tuple_shape():
    stock = {"code": "600000", "exchange": "SH"}
    row = bars._akshare_hist_row_to_tuple(stock, {
        "日期": "2026-08-28", "开盘": 10.0, "最高": 10.8,
        "最低": 9.9, "收盘": 10.5, "成交量": 123456, "成交额": 7890123.0})
    assert row is not None
    assert row[0] == "600000" and row[1] == "2026-08-28"
    assert len(row) == len(bars._eastmoney_kline_to_tuple(
        stock, "2026-08-28,10.00,10.50,10.80,9.90,123456,7890123.0,1.0,2.0,0.5,1.5")), (
        "providers must agree on row shape or the INSERT silently misaligns")


def test_secid_encodes_the_exchange_eastmoney_expects():
    assert bars._eastmoney_secid({"code": "600000", "exchange": "SH"}) == "1.600000"
    assert bars._eastmoney_secid({"code": "000001", "exchange": "SZ"}) == "0.000001"


def test_a_share_equity_filter_rejects_non_equities():
    assert bars._is_a_share_equity("600000", "SH") is True
    assert bars._is_a_share_equity("000001", "SZ") is True
    assert bars._is_a_share_equity("900001", "SH") is False   # B-share
