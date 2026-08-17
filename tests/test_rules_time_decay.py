"""Rule 5 time stop — pins check_time_decay.py to agents/ANALYST.md.

Threshold is 15 sessions / <3% (ANALYST.md Rule 5). It got there the hard way:
the rule sat at V1's 20d/<5% long after the spec said 10d/<3%, was reconciled to
10d on 2026-08-16, and 10d was then measured as the worst of five variants
(docs/audits/EXIT_ABLATION.md) and corrected to 15d on 08-17. These tests exist
so the spec and the code cannot drift apart again.

Driven through the real stdin/stdout contract (subprocess), not by import — that
contract is what run_rules.py depends on.
"""
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

RULE = Path(__file__).resolve().parent.parent / "scripts" / "rules" / "check_time_decay.py"


def weekdays_between(entry: date, today: date) -> int:
    """Mirror of the rule's own counter: weekdays in (entry, today]."""
    days, d = 0, entry
    while d < today:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def entry_n_weekdays_ago(n: int) -> str:
    """Weekday D with exactly n sessions elapsed by the rule's reckoning.

    Searched rather than derived: `today` counts only when it is itself a
    weekday, so any closed-form offset is off by one on weekends — which is
    exactly how this test first failed.
    """
    today = date.today()
    d = today
    while d.weekday() >= 5 or weekdays_between(d, today) != n:
        d -= timedelta(days=1)
        assert (today - d).days < 60, f"no entry date yields {n} sessions"
    return d.isoformat()


def run(positions):
    p = subprocess.run([sys.executable, str(RULE)], input=json.dumps(
        {"activePositions": positions}), capture_output=True, text=True)
    return json.loads(p.stdout)


def pos(days_ago, pnl, sector="半导体", code="600000", name="测试"):
    return {"code": code, "name": name, "sector": sector, "pnl_pct": pnl,
            "entryDate": entry_n_weekdays_ago(days_ago)}


def only(result):
    assert len(result["violations"]) == 1, result
    return result["violations"][0]


def test_fires_at_fifteen_days_under_three_percent():
    v = only(run([pos(15, 2.9)]))
    assert v["severity"] == "SELL"
    assert v["threshold"] == 15
    assert v["trading_days"] >= 15
    # 10 sessions was the 08-16 value; measured harmful, must not fire there —
    # and at 15d, day 10 is outside the warn window too, so it is fully silent
    assert run([pos(10, 2.9)])["violations"] == []


def test_three_percent_rides_at_any_age():
    # the spec's floor is a floor: >=3% never time-stops, however long it's held
    assert run([pos(15, 3.0)])["violations"] == []
    assert run([pos(40, 3.1)])["violations"] == []


def test_warns_before_the_threshold_but_does_not_sell():
    v = only(run([pos(14, 2.0)]))
    assert v["severity"] == "INFO"
    assert "APPROACHING" in v["suggestion"]
    assert run([pos(11, 2.0)])["violations"] == []     # outside the warn window


def test_commodity_grace_is_gone():
    """ANALYST.md Rule 5: "No 'event-driven exceptions' to time stops."

    LEARNINGS #19 gave 化工/黄金/有色/... a 30-day threshold, which under a
    15-day spec means commodity names would be exempt for an extra fortnight.
    """
    v = only(run([pos(15, 1.0, sector="黄金")]))
    assert v["severity"] in ("SELL", "REVIEW")
    assert v["threshold"] == 15
    assert v["is_commodity"] is True     # still reported, no longer load-bearing


def test_exit_code_and_clean_book():
    p = subprocess.run([sys.executable, str(RULE)], input=json.dumps(
        {"activePositions": [pos(2, -1.0)]}), capture_output=True, text=True)
    assert p.returncode == 0 and json.loads(p.stdout)["status"] == "ok"
    p = subprocess.run([sys.executable, str(RULE)], input=json.dumps(
        {"activePositions": [pos(17, -4.0)]}), capture_output=True, text=True)
    assert p.returncode == 1 and json.loads(p.stdout)["status"] == "violations"
