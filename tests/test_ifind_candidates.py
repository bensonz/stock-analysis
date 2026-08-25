"""iwencai screens as a display-only artifact.

Scope discipline: this must stay a *second opinion* read alongside the
CheeseForTune pool. It does not touch the hard RPS/MA gate in
fetch_strategy_pool_local, and a failure must cost nothing but the artifact.
That mirrors regime.json, which is deliberately display-only until there is
out-of-sample evidence to graduate it.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_collector as dc
import ifind_client


class _FakeClient:
    def __init__(self, tables_by_query=None, raises=False):
        self.tables_by_query = tables_by_query or {}
        self.raises = raises
        self.data_vol = 0

    def iwencai(self, query, domain="stock"):
        if self.raises:
            raise RuntimeError("iwencai down")
        return self.tables_by_query.get(query, {})


def _install(monkeypatch, client):
    monkeypatch.setattr(ifind_client, "is_available", lambda: True)
    monkeypatch.setattr(ifind_client, "get_client", lambda: client)


# ---------------------------------------------------------------------------
# Column normalization
# ---------------------------------------------------------------------------


def test_rows_strip_the_embedded_query_date():
    """iwencai names columns `涨跌幅:前复权[20260825]` — keys must be stable."""
    rows = dc._iwencai_rows({
        "股票代码": ["600519.SH", "000001.SZ"],
        "涨跌幅:前复权[20260825]": [1.5, -2.0],
    })

    assert rows == [{"股票代码": "600519.SH", "涨跌幅:前复权": 1.5},
                    {"股票代码": "000001.SZ", "涨跌幅:前复权": -2.0}]


def test_rows_drop_entries_without_a_code():
    rows = dc._iwencai_rows({"股票代码": ["600519.SH", ""], "x": [1, 2]})
    assert len(rows) == 1


def test_rows_handle_empty_table():
    assert dc._iwencai_rows({}) == []


@pytest.mark.parametrize("column", ["上市天数", "上市交易日天数"])
def test_listed_days_found_under_either_column_name(column):
    """iwencai names the column after the query phrasing; a literal match
    would silently disable the new-listing filter."""
    assert dc._listed_days({"股票代码": "x", column: 42}) == 42


def test_listed_days_absent_is_none():
    assert dc._listed_days({"股票代码": "x"}) is None


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------


def test_debut_listings_are_dropped(monkeypatch):
    """A debut session printed +282% on 2026-08-25 and has no momentum history."""
    query = dc.IWENCAI_SCREENS[0][1]
    _install(monkeypatch, _FakeClient({query: {
        "股票代码": ["600519.SH", "301999.SZ"],
        "上市天数": [2624, 1],
        "涨跌幅[20260825]": [3.0, 282.98],
    }}))

    out = dc.fetch_ifind_candidates()
    screen = out["screens"][0]

    assert screen["count"] == 1
    assert screen["dropped_new_listings"] == 1
    assert screen["stocks"][0]["股票代码"] == "600519.SH"


def test_one_failing_screen_does_not_kill_the_rest(monkeypatch):
    class _Partial(_FakeClient):
        def iwencai(self, query, domain="stock"):
            if query == dc.IWENCAI_SCREENS[0][1]:
                raise RuntimeError("boom")
            return {"股票代码": ["600519.SH"], "上市天数": [2624]}

    _install(monkeypatch, _Partial())

    out = dc.fetch_ifind_candidates()

    assert "error" in out["screens"][0]
    assert out["screens"][1]["count"] == 1, "later screens still run"


def test_unconfigured_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(ifind_client, "is_available", lambda: False)

    out = dc.fetch_ifind_candidates()

    assert out["available"] is False and out["reason"]


def test_artifact_carries_its_display_only_caveat(monkeypatch):
    _install(monkeypatch, _FakeClient())

    out = dc.fetch_ifind_candidates()

    assert "does NOT feed the RPS/MA gate" in out["note"]


def test_save_writes_named_artifact(monkeypatch, tmp_path):
    path = dc.save_ifind_candidates("2026-08-25", {"available": True},
                                    output_dir=tmp_path)
    assert path.name == "ifind_candidates.json" and path.exists()


def test_screens_do_not_touch_the_rps_gate():
    """Structural guard: the gate constant is unchanged by this feature."""
    assert dc.RPS_GATE_MIN == 80
    assert dc.passes_rps_gate(85, 85, 85) is True
    assert dc.passes_rps_gate(85, 85, 79) is False
