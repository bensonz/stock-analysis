"""Tests for the pricedb timeout helpers."""
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import pricedb  # noqa: E402
from pricedb import _TimeoutError, _run_with_timeout  # noqa: E402


def test_run_with_timeout_returns_value():
    assert _run_with_timeout("fast", lambda: 42, timeout=1.0) == 42


def test_run_with_timeout_propagates_exception():
    def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        _run_with_timeout("raises", boom, timeout=1.0)


def test_run_with_timeout_raises_on_hang():
    start = time.monotonic()
    with pytest.raises(_TimeoutError) as excinfo:
        _run_with_timeout("hang", lambda: time.sleep(5), timeout=0.5)
    elapsed = time.monotonic() - start

    assert "hang" in str(excinfo.value)
    assert "0s timeout" in str(excinfo.value) or "1s timeout" in str(excinfo.value)
    assert elapsed < 1.0  # ~0.5s + thread overhead


def test_call_tushare_retries_on_timeout(monkeypatch):
    monkeypatch.setattr(pricedb, "PRICEDB_CALL_TIMEOUT_SEC", 0.3)
    monkeypatch.setattr(pricedb, "TUSHARE_RETRY_DELAY", 0.01)

    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            time.sleep(1.0)  # exceeds 0.3s timeout
        return "ok"

    start = time.monotonic()
    result = pricedb._call_tushare("flaky", flaky)
    elapsed = time.monotonic() - start

    assert result == "ok"
    assert calls["n"] >= 2
    # 1st call: ~0.3s timeout. 2nd call: immediate. Bound generously.
    assert elapsed < pricedb.PRICEDB_CALL_TIMEOUT_SEC * 2 + 0.5


def test_call_tushare_eventually_raises(monkeypatch):
    monkeypatch.setattr(pricedb, "PRICEDB_CALL_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(pricedb, "TUSHARE_RETRY_DELAY", 0.01)

    def always_hangs():
        time.sleep(5)

    start = time.monotonic()
    with pytest.raises(RuntimeError) as excinfo:
        pricedb._call_tushare("hangs", always_hangs)
    elapsed = time.monotonic() - start

    assert "hangs" in str(excinfo.value)
    # 3 retries × 0.2s timeout + small slack. No retry sleeps on _TimeoutError.
    assert elapsed < pricedb.PRICEDB_CALL_TIMEOUT_SEC * pricedb.TUSHARE_RETRIES + 0.5


def test_budget_exceeded_when_deadline_passed(monkeypatch):
    monkeypatch.setattr(pricedb, "_UPDATE_DEADLINE", time.monotonic() - 1)
    assert pricedb._budget_exceeded() is True


def test_budget_not_exceeded_with_no_deadline(monkeypatch):
    monkeypatch.setattr(pricedb, "_UPDATE_DEADLINE", None)
    assert pricedb._budget_exceeded() is False


def test_budget_not_exceeded_within_window(monkeypatch):
    monkeypatch.setattr(pricedb, "_UPDATE_DEADLINE", time.monotonic() + 60)
    assert pricedb._budget_exceeded() is False
