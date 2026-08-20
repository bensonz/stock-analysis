"""Rule 2b extension must be measured against a LIVE price, or not at all.

2026-08-20 noon: 成都先导 688222 gapped +8% at the open and was +13% by 11:35.
`fetch_ma_data` measured extension from the DB's newest *settled* close — the
previous session's — so it reported dist_ma20 = +8.1%, inside Rule 2b's 12%
cap, and the model wrote "MA距离全部合规" in good faith. Against the real price
it was +19.6%: a 7.6-point violation. Screening and execution were reading two
different prices; only an unrelated limit-band bug prevented the buy.

Design: MAs stay from settled bars (an unsettled bar must never enter an
average); the distance numerator is the live price. On live-fetch failure the
candidate is rejected with the reason logged — never screened on a stale close.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_collector as dc


class _FakeConn:
    """Minimal sqlite stand-in: 20 flat settled closes at 32.00."""

    def __init__(self, closes):
        self._closes = closes

    def execute(self, sql, params=()):
        rows = [(c, 1.0, f"2026-08-{i + 1:02d}") for i, c in enumerate(self._closes)]
        return _FakeCursor(rows)

    def close(self):
        pass


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def _patch(monkeypatch, live_result, closes=None):
    closes = closes or [32.0] * 20
    monkeypatch.setattr(dc, "DEFAULT_PRICEDB_PATH", Path(__file__))   # any existing file
    monkeypatch.setattr(dc.sqlite3, "connect", lambda *a, **k: _FakeConn(closes))
    if isinstance(live_result, Exception):
        def _boom(_stocks):
            raise live_result
        monkeypatch.setattr(dc, "_fetch_position_prices_sina", _boom)
    else:
        monkeypatch.setattr(dc, "_fetch_position_prices_sina", lambda _s: live_result)


def test_distance_is_measured_from_the_live_price(monkeypatch):
    # settled closes flat at 32.00 → MA20 = 32.00; live price 38.40 = +20%
    _patch(monkeypatch, {"688222": {"price": 38.40}})
    out = dc.fetch_ma_data([{"code": "688222"}])["688222"]
    assert out["price_source"] == "live" and out["screenable"] is True
    assert out["price"] == 38.40
    assert out["prev_close"] == 32.0
    assert out["dist_ma20_pct"] == 20.0        # NOT 0.0, which the stale close gives


def test_moving_averages_still_come_from_settled_bars(monkeypatch):
    """The live price must not contaminate the average itself."""
    _patch(monkeypatch, {"688222": {"price": 38.40}})
    out = dc.fetch_ma_data([{"code": "688222"}])["688222"]
    assert out["ma5"] == 32.0 and out["ma20"] == 32.0


def test_live_failure_rejects_and_logs_the_reason(monkeypatch):
    _patch(monkeypatch, {})            # quote service returned nothing for it
    out = dc.fetch_ma_data([{"code": "688222"}])["688222"]
    assert out["screenable"] is False
    assert out["price_source"] == "prev_close"
    assert out["screen_error"]                       # a reason, not silence
    assert "candidate rejected" in out["dist_basis_note"]
    assert out["prev_close"] == 32.0                 # kept for forensics


def test_live_fetch_exception_is_captured_not_swallowed(monkeypatch):
    _patch(monkeypatch, RuntimeError("sina timeout"))
    out = dc.fetch_ma_data([{"code": "688222"}])["688222"]
    assert out["screenable"] is False
    assert "sina timeout" in out["screen_error"]


def test_a_zero_or_negative_live_price_is_not_trusted(monkeypatch):
    for bad in (0, -1.0, None, "38.40"):
        _patch(monkeypatch, {"688222": {"price": bad}})
        out = dc.fetch_ma_data([{"code": "688222"}])["688222"]
        assert out["screenable"] is False, f"{bad!r} must not pass as a price"
