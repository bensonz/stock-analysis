"""iFinD client tests.

Pins the payload shapes and traps documented in docs/IFIND_EVAL/IFIND_API_GUIDE.md
— particularly the ones that fail SILENTLY rather than loudly:

  * `date_sequence` takes `indipara`, not `indicators`
  * ths_the_sw_industry_stock params are [level, date], level first
  * errorcode -4001 ("no data") is an empty result, not a fault
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import ifind_client


# ---------------------------------------------------------------------------
# Code conversion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,expected", [
    ("600519", "600519.SH"),
    ("688169", "688169.SH"),   # STAR board is SH — the '6' test must beat '8'/BJ
    ("000001", "000001.SZ"),
    ("300750", "300750.SZ"),
    ("830799", "830799.BJ"),
    ("871981", "871981.BJ"),
    ("600519.SH", "600519.SH"),  # already suffixed, passed through
])
def test_to_ths_code_by_prefix(code, expected):
    assert ifind_client.to_ths_code(code) == expected


def test_explicit_exchange_wins_over_prefix():
    # pricedb's stocks.exchange is authoritative when present
    assert ifind_client.to_ths_code("000001", "SH") == "000001.SH"
    assert ifind_client.to_ths_code("600519", "SZ") == "600519.SZ"


def test_from_ths_code():
    assert ifind_client.from_ths_code("600519.SH") == "600519"


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def _client(tmp_path, token="tok"):
    c = ifind_client.IFindClient(refresh_token="refresh",
                                 token_cache=tmp_path / "t.json")
    c._access = token
    c._expires = datetime.now() + timedelta(days=5)
    return c


def test_post_returns_body_and_accumulates_datavol(tmp_path, monkeypatch):
    c = _client(tmp_path)
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _Resp({"errorcode": 0, "tables": [1], "dataVol": 42}))
    body = c.post("cmd_history_quotation", {})
    assert body["tables"] == [1]
    assert c.data_vol == 42
    c.post("cmd_history_quotation", {})
    assert c.data_vol == 84


def test_no_data_errorcode_is_empty_not_error(tmp_path, monkeypatch):
    """-4001 means the query legitimately matched nothing (e.g. empty data_pool)."""
    c = _client(tmp_path)
    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: _Resp({"errorcode": -4001, "errmsg": "no data."}))
    assert c.post("data_pool", {}) == {"tables": [], "dataVol": 0}


def test_bad_params_raises_loudly(tmp_path, monkeypatch):
    """-4210 is a wrong indicator name or param order — never degrade silently."""
    c = _client(tmp_path)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(
        {"errorcode": -4210, "errmsg": "error happen with input parameters"}))
    with pytest.raises(ifind_client.IFindError) as ei:
        c.post("basic_data_service", {})
    assert ei.value.errorcode == -4210


def test_missing_endpoint_raises(tmp_path, monkeypatch):
    c = _client(tmp_path)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp({}, status=404))
    with pytest.raises(ifind_client.IFindError):
        c.post("data_statistics", {})


def test_unconfigured_client_raises_rather_than_hanging(monkeypatch):
    """With no token in env or .env, callers get a clear signal to fall back.

    An empty `refresh_token` argument deliberately falls through to the
    environment, so absence has to be simulated at that layer.
    """
    monkeypatch.setattr(ifind_client, "_env", lambda name: None)
    c = ifind_client.IFindClient(refresh_token="")
    assert not c.configured
    with pytest.raises(ifind_client.IFindNotConfigured):
        c.access_token()


# ---------------------------------------------------------------------------
# Token lifecycle
# ---------------------------------------------------------------------------


def test_token_cached_to_disk_and_reused(tmp_path, monkeypatch):
    cache = tmp_path / "t.json"
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return _Resp({"errorcode": 0, "data": {
            "access_token": "AT1", "expired_time": "2099-01-01 00:00:00"}})

    monkeypatch.setattr(requests, "post", fake_post)
    c1 = ifind_client.IFindClient(refresh_token="r", token_cache=cache)
    assert c1.access_token() == "AT1"
    assert len(calls) == 1

    # a fresh client (i.e. a new CLI invocation) reads the cache, no round trip
    c2 = ifind_client.IFindClient(refresh_token="r", token_cache=cache)
    assert c2.access_token() == "AT1"
    assert len(calls) == 1


def test_expiring_token_is_refreshed(tmp_path, monkeypatch):
    """A token inside the refresh margin must not be handed out mid-run."""
    cache = tmp_path / "t.json"
    cache.write_text(json.dumps({
        "access_token": "STALE",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()}))
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(
        {"errorcode": 0, "data": {"access_token": "FRESH",
                                  "expired_time": "2099-01-01 00:00:00"}}))
    c = ifind_client.IFindClient(refresh_token="r", token_cache=cache)
    assert c.access_token() == "FRESH"


def test_token_file_is_owner_only(tmp_path, monkeypatch):
    cache = tmp_path / "t.json"
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(
        {"errorcode": 0, "data": {"access_token": "AT",
                                  "expired_time": "2099-01-01 00:00:00"}}))
    ifind_client.IFindClient(refresh_token="r", token_cache=cache).access_token()
    assert (cache.stat().st_mode & 0o077) == 0, "token file must not be group/world readable"


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------


def test_batching_splits_and_concatenates(tmp_path, monkeypatch):
    c = _client(tmp_path)
    monkeypatch.setattr(ifind_client, "MAX_CODES_PER_REQUEST", 2)
    seen = []

    def fake_post(url, json=None, **kwargs):
        codes = json["codes"].split(",")
        seen.append(codes)
        return _Resp({"errorcode": 0, "dataVol": len(codes),
                      "tables": [{"thscode": x} for x in codes]})

    monkeypatch.setattr(requests, "post", fake_post)
    tables = c.history_quotation(["a", "b", "c", "d", "e"], "close",
                                 "2026-08-25", "2026-08-25")
    assert [t["thscode"] for t in tables] == ["a", "b", "c", "d", "e"]
    assert sorted(len(s) for s in seen) == [1, 2, 2]


def test_empty_code_list_makes_no_request(tmp_path, monkeypatch):
    c = _client(tmp_path)
    monkeypatch.setattr(requests, "post", lambda *a, **k: pytest.fail("no request expected"))
    assert c.history_quotation([], "close", "2026-08-25", "2026-08-25") == []


# ---------------------------------------------------------------------------
# Payload shapes (the traps)
# ---------------------------------------------------------------------------


def _capture(monkeypatch):
    sent = {}

    def fake_post(url, json=None, **kwargs):
        sent["url"], sent["payload"] = url, json
        return _Resp({"errorcode": 0, "tables": []})

    monkeypatch.setattr(requests, "post", fake_post)
    return sent


def test_date_sequence_uses_indipara_not_indicators(tmp_path, monkeypatch):
    sent = _capture(monkeypatch)
    _client(tmp_path).date_sequence(
        ["600519.SH"], [{"indicator": "ths_af_stock", "indiparams": [""]}],
        "2026-08-14", "2026-08-25")
    assert "indipara" in sent["payload"]
    assert "indicators" not in sent["payload"], \
        "date_sequence rejects `indicators` with -4210"


def test_history_quotation_cps_selects_adjustment(tmp_path, monkeypatch):
    sent = _capture(monkeypatch)
    c = _client(tmp_path)
    c.history_quotation(["600519.SH"], "close", "2026-08-21", "2026-08-25")
    assert "CPS" not in sent["payload"]["functionpara"], "default must be raw prices"
    c.history_quotation(["600519.SH"], "close", "2026-08-21", "2026-08-25", cps="2")
    assert sent["payload"]["functionpara"]["CPS"] == "2"


# ---------------------------------------------------------------------------
# Integration (live API)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_live_bars_match_known_values():
    c = ifind_client.get_client()
    if not c.configured:
        pytest.skip("IFIND_REFRESH_TOKEN not configured")
    tables = c.history_quotation(["600519.SH"], "open,high,low,close,volume,amount",
                                 "2026-08-25", "2026-08-25")
    assert len(tables) == 1
    t = tables[0]["table"]
    assert t["close"][0] == pytest.approx(1304.0, abs=0.01)
    assert t["amount"][0] is not None, "iFinD must carry turnover amount"


@pytest.mark.integration
def test_live_sw_industry_param_order():
    """[level, date] works; [date, level] silently returns an empty string."""
    c = ifind_client.get_client()
    if not c.configured:
        pytest.skip("IFIND_REFRESH_TOKEN not configured")
    ok = c.basic_data(["600519.SH"], [
        {"indicator": "ths_the_sw_industry_stock", "indiparams": ["1", "2026-08-25"]}])
    assert ok[0]["table"]["ths_the_sw_industry_stock"][0] == "食品饮料"

    reversed_ = c.basic_data(["600519.SH"], [
        {"indicator": "ths_the_sw_industry_stock", "indiparams": ["2026-08-25", "1"]}])
    assert reversed_[0]["table"]["ths_the_sw_industry_stock"][0] == "", \
        "documented trap: reversed params return empty, not an error"
