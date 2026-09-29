"""run_daily.non_trading_day_reason — the scheduled run skips closed days.

launchd fires every weekday; nothing checked the exchange calendar, so the
2026-09-25 Mid-Autumn run analysed 09-24's data again and put a fake point on
the equity chart. The calendar (akshare, published ahead) lists holidays; when
it is unreachable the weekday fallback runs the pipeline anyway — failing open
costs one redundant run, failing closed would cost a real session.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import run_daily

CAL = ["20260924", "20260928", "20260929", "20260930", "20261008"]


def test_a_holiday_is_skipped_naming_the_last_session():
    reason = run_daily.non_trading_day_reason("2026-09-25", calendar=CAL)
    assert reason and "2026-09-24" in reason


def test_national_day_week_is_skipped():
    assert run_daily.non_trading_day_reason("2026-10-05", calendar=CAL)


def test_a_trading_day_runs():
    assert run_daily.non_trading_day_reason("2026-09-28", calendar=CAL) is None


def test_calendar_outage_fails_open_on_weekdays():
    # [] = calendar unavailable → weekday fallback: a Friday holiday still runs.
    assert run_daily.non_trading_day_reason("2026-09-25", calendar=[]) is None


def test_calendar_outage_still_skips_weekends():
    assert run_daily.non_trading_day_reason("2026-09-26", calendar=[])
