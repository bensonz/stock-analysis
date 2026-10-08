"""Corporate actions (cash dividends + 送转) in the simulated book.

Owner ask 2026-10-08: 普洛药业 000739 went ex-dividend (10派1.39) and the book
took the price drop with no cash credit. See docs/corporate_actions/.

Every test here runs on a tmp book. The module-scoped guard below hashes the
repo's tracking/ before and after: a leaked path global (CLOSED_DIR is bound
at import, separately from TRACKING_DIR — the 2026-08-19 incident) fails the
run instead of silently writing into the real book.
"""
import hashlib
import json
from pathlib import Path

import pytest

import corporate_actions as ca
import position_manager as pm

ROOT = Path(__file__).resolve().parent.parent
LIVE_TRACKING = ROOT / "tracking"


def _fingerprint(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return "absent"
    for f in sorted(root.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(root)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


@pytest.fixture(scope="module", autouse=True)
def _live_book_untouched():
    before = _fingerprint(LIVE_TRACKING)
    yield
    assert _fingerprint(LIVE_TRACKING) == before, \
        "a corporate-actions test mutated the LIVE tracking/ directory"


@pytest.fixture
def book(tmp_path, monkeypatch):
    """A tmp book with every position_manager path global rebound."""
    closed = tmp_path / "closed"
    closed.mkdir()
    daily = tmp_path / "daily"
    daily.mkdir()
    monkeypatch.setattr(pm, "TRACKING_DIR", tmp_path)
    monkeypatch.setattr(pm, "CLOSED_DIR", closed)
    monkeypatch.setattr(pm, "DAILY_DIR", daily)
    monkeypatch.setattr(pm, "POSITIONS_FILE", tmp_path / "positions.json")
    monkeypatch.setattr(pm, "PORTFOLIO_CONFIG_FILE", tmp_path / "portfolio_config.json")
    (tmp_path / "portfolio_config.json").write_text(json.dumps({
        "starting_capital": 1000000, "max_position_pct": 10,
        "max_positions": 10, "min_cash_pct": 20}), encoding="utf-8")
    # no price DB lookups from close_position
    monkeypatch.setattr(pm, "_trading_days_held", lambda *a, **k: 10)
    return tmp_path


def _put(book, code="000739", entry_date="2026-09-22", entry=24.21, shares=1700,
         stop=23.0, **extra):
    pos = {"code": code, "name": "普洛药业", "status": "active",
           "entryDate": entry_date, "entryPrice": entry, "shares": shares,
           "allocatedCapital": round(entry * shares, 2),
           "stopLoss": stop, "currentStop": stop, "targetPrice": 30.0,
           "history": [{"date": entry_date, "action": "OPEN", "price": entry,
                        "shares": shares}], **extra}
    (book / f"{code}.json").write_text(json.dumps(pos, ensure_ascii=False),
                                       encoding="utf-8")
    return pos


def _read(book, code="000739"):
    return json.loads((book / f"{code}.json").read_text(encoding="utf-8"))


def _ev(ex="2026-10-08", cash=1.39, bonus=0.0):
    return {"exDate": ex, "cashPer10": cash, "bonusPer10": bonus,
            "plan": "test"}


def _fetcher(events_by_code):
    calls = []

    def f(code):
        calls.append(code)
        return events_by_code.get(code, [])
    f.calls = calls
    return f


# ── tax brackets (A-share holding-period rule, judged at the ex-date) ──

@pytest.mark.parametrize("entry,ex,rate", [
    ("2026-09-22", "2026-10-08", 0.20),   # the 000739 case: 16 days
    ("2026-09-22", "2026-10-22", 0.20),   # exactly 1 calendar month → still ≤1m
    ("2026-09-22", "2026-10-23", 0.10),   # 1 month + 1 day
    ("2026-01-31", "2026-02-28", 0.20),   # month-end clamp: 01-31 + 1m = 02-28
    ("2026-01-31", "2026-03-01", 0.10),
    ("2025-10-08", "2026-10-08", 0.10),   # exactly 1 year → still ≤1y
    ("2025-10-08", "2026-10-09", 0.00),   # 1 year + 1 day
    ("2024-02-29", "2025-02-28", 0.10),   # leap-day clamp
    ("2024-02-29", "2025-03-01", 0.00),
])
def test_tax_rate_brackets(entry, ex, rate):
    assert ca.tax_rate(entry, ex) == rate


# ── parsing the eastmoney rows ──

def _row(ex="2026-10-08 00:00:00", cash=1.39, it=None, progress="实施分配"):
    return {"SECURITY_CODE": "000739", "EX_DIVIDEND_DATE": ex,
            "PRETAX_BONUS_RMB": cash, "BONUS_IT_RATIO": it,
            "ASSIGN_PROGRESS": progress, "IMPL_PLAN_PROFILE": "10派1.39元"}


def test_parse_keeps_implemented_cash_and_bonus():
    evs = ca.parse_events([
        _row(),
        _row(ex="2014-05-30 00:00:00", cash=0.1, it=3),
        _row(ex="2013-06-21 00:00:00", cash=None, it=10),
    ])
    by = {e["exDate"]: e for e in evs}
    assert by["2026-10-08"]["cashPer10"] == 1.39
    assert by["2026-10-08"]["bonusPer10"] == 0.0
    assert by["2014-05-30"]["bonusPer10"] == 3.0
    assert by["2013-06-21"]["cashPer10"] == 0.0
    assert [e["exDate"] for e in evs] == sorted(by)   # oldest first


def test_parse_skips_unimplemented_plans_and_empty_rows():
    evs = ca.parse_events([
        _row(progress="董事会预案"),
        _row(progress="股东大会预案"),
        _row(ex=None),
        _row(cash=None, it=None),
        _row(cash=0, it=0),
    ])
    assert evs == []


def test_fetch_failure_returns_none(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(requests, "get", boom)
    assert ca.fetch_events("000739") is None


def test_fetch_unsuccessful_payload_returns_none(monkeypatch):
    import requests

    class R:
        def json(self):
            return {"success": False, "message": "throttled", "result": None}
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    assert ca.fetch_events("000739") is None


def test_fetch_no_rows_is_empty_list_not_none(monkeypatch):
    import requests

    class R:
        def json(self):
            return {"success": False, "message": "返回数据为空", "code": 9201,
                    "result": None}
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    assert ca.fetch_events("000739") == []


# ── applying to the book ──

def test_cash_dividend_credits_net_cash(book):
    _put(book)
    before = pm.build_positions_snapshot()["portfolio"]
    res = ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [_ev()]}))
    pos = _read(book)
    [rec] = pos["corporateActions"]
    assert rec["exDate"] == "2026-10-08"
    assert rec["grossCash"] == 236.30          # 1700 × 0.139
    assert rec["taxRate"] == 0.20
    assert rec["tax"] == 47.26
    assert rec["netCash"] == 189.04
    assert rec["sharesBefore"] == rec["sharesAfter"] == 1700
    assert pos["history"][-1]["action"] == "DIVIDEND"
    after = pm.build_positions_snapshot()["portfolio"]
    assert round(after["cash"] - before["cash"], 2) == 189.04
    assert after["dividendCash"] == 189.04
    assert round(after["realizedPnl"] - before["realizedPnl"], 2) == 189.04
    assert res["status"] == "ok"
    assert [a["code"] for a in res["applied"]] == ["000739"]


def test_equity_identity_holds_with_dividends(book):
    _put(book)
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [_ev()]}))
    pf = pm.build_positions_snapshot()["portfolio"]
    assert round(pf["totalEquity"] - pf["startingCapital"], 2) == pf["totalPnl"]


def test_rerun_is_idempotent(book):
    _put(book)
    f = _fetcher({"000739": [_ev()]})
    ca.apply_due("2026-10-08", fetcher=f)
    cash1 = pm.build_positions_snapshot()["portfolio"]["cash"]
    res = ca.apply_due("2026-10-08", fetcher=f)
    pos = _read(book)
    assert len(pos["corporateActions"]) == 1
    assert [h["action"] for h in pos["history"]].count("DIVIDEND") == 1
    assert pm.build_positions_snapshot()["portfolio"]["cash"] == cash1
    assert res["applied"] == []


def test_event_on_or_before_entry_date_is_ignored(book):
    _put(book, entry_date="2026-10-08")
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [
        _ev("2026-10-08"), _ev("2026-04-29", cash=2.38)]}))
    assert "corporateActions" not in _read(book)


def test_future_event_is_not_applied_yet(book):
    _put(book)
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [_ev("2026-10-09")]}))
    assert "corporateActions" not in _read(book)


def test_back_credit_of_a_missed_event(book):
    """Run date after the ex-date still credits it (entryDate < exDate <= date)."""
    _put(book)
    ca.apply_due("2026-10-12", fetcher=_fetcher({"000739": [_ev()]}))
    assert _read(book)["corporateActions"][0]["netCash"] == 189.04


def test_bonus_shares_rescale_shares_and_entry_but_not_stop(book):
    _put(book, stop=23.0)
    before = pm.build_positions_snapshot()["portfolio"]
    res = ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [
        _ev(cash=0.0, bonus=4.0)]}))   # 10转4
    pos = _read(book)
    [rec] = pos["corporateActions"]
    assert pos["shares"] == 2380 == rec["sharesAfter"]
    assert rec["sharesBefore"] == 1700
    assert abs(pos["entryPrice"] - 24.21 / 1.4) < 1e-6
    assert pos["allocatedCapital"] == round(24.21 * 1700, 2)   # unchanged
    assert pos["stopLoss"] == 23.0 and pos["currentStop"] == 23.0
    assert rec["grossCash"] == 0 and rec["netCash"] == 0
    assert pos["history"][-1]["action"] == "BONUS_SHARES"
    after = pm.build_positions_snapshot()["portfolio"]
    assert abs(after["cash"] - before["cash"]) <= 0.01      # cost basis preserved
    assert any("stop" in w.lower() for w in res["warnings"])


def test_bonus_shares_floor_to_whole_shares(book):
    _put(book, shares=155)
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [
        _ev(cash=0.0, bonus=3.0)]}))
    assert _read(book)["shares"] == 201          # 201.5 floored


def test_cash_plus_bonus_pays_cash_on_pre_bonus_shares(book):
    _put(book)
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [
        _ev(cash=1.0, bonus=3.0)]}))
    pos = _read(book)
    [rec] = pos["corporateActions"]
    assert rec["grossCash"] == 170.0             # 1700 × 0.1, not 2210 × 0.1
    assert pos["shares"] == 2210
    actions = [h["action"] for h in pos["history"]]
    assert "DIVIDEND" in actions and "BONUS_SHARES" in actions


def test_fetch_failure_leaves_book_untouched_and_is_loud(book):
    _put(book)
    snap = (book / "000739.json").read_bytes()
    res = ca.apply_due("2026-10-08", fetcher=lambda code: None)
    assert (book / "000739.json").read_bytes() == snap
    assert res["status"] == "degraded"
    assert res["fetch_failed"] == ["000739"]
    assert res["warnings"]


def test_fetcher_exception_is_a_degradation_not_a_crash(book):
    _put(book)

    def boom(code):
        raise RuntimeError("parse exploded")
    res = ca.apply_due("2026-10-08", fetcher=boom)
    assert res["status"] == "degraded" and res["fetch_failed"] == ["000739"]
    assert "corporateActions" not in _read(book)


def test_no_open_positions_makes_no_fetches(book):
    f = _fetcher({})
    res = ca.apply_due("2026-10-08", fetcher=f)
    assert f.calls == [] and res["status"] == "ok"


def test_closed_trades_are_never_restated(book):
    """apply_due only reads active positions — a closed record with a
    historical ex-date in its window gets nothing."""
    closed = {"code": "000739", "name": "普洛药业", "status": "closed",
              "entryDate": "2026-04-01", "exitDate": "2026-05-10",
              "entryPrice": 20.0, "exitPrice": 21.0, "shares": 1000,
              "returnPct": 5.0}
    p = pm.CLOSED_DIR / "000739_2026-05-10.json"
    p.write_text(json.dumps(closed, ensure_ascii=False), encoding="utf-8")
    raw = p.read_bytes()
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [_ev("2026-04-29", 2.38)]}))
    assert p.read_bytes() == raw
    assert pm.compute_realized_pnl() == 1000.0


# ── closing a position carries its dividends ──

def test_close_carries_dividends_into_realized_and_return(book):
    _put(book)
    ca.apply_due("2026-10-08", fetcher=_fetcher({"000739": [_ev()]}))
    pf_open = pm.build_positions_snapshot()["portfolio"]
    closed = pm.close_position("000739", reason="test", exit_price=26.0,
                               date="2026-10-09")
    assert closed["corporateActions"][0]["netCash"] == 189.04
    trading = (26.0 - 24.21) * 1700
    assert pm.compute_realized_pnl() == round(trading + 189.04, 2)
    expected_ret = round((trading + 189.04) / (24.21 * 1700) * 100, 2)
    assert closed["returnPct"] == expected_ret
    pf = pm.build_positions_snapshot()["portfolio"]
    # dividend counted once: moved from the open term into closed realized
    assert pf["dividendCash"] == 0
    assert pf["cash"] == round(pf_open["cash"] + 26.0 * 1700, 2)


def test_close_without_dividends_keeps_old_return_formula(book):
    _put(book)
    closed = pm.close_position("000739", reason="test", exit_price=26.0,
                               date="2026-10-09")
    assert closed["returnPct"] == round((26.0 - 24.21) / 24.21 * 100, 2)
