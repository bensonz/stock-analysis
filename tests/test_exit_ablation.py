"""Exit-policy settlement — the mechanics the ablation's conclusions rest on.

`settle()` decides, for one real entry and one candidate exit policy, where the
trade would have come out. Every conclusion in docs/audits/EXIT_ABLATION.md is a
mean over this function, so its edge cases (gap-through fills, intraday triggers,
T+1, rule precedence) are what actually need pinning.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import exit_ablation as ea


def bar(date, o, h, low, c):
    return (date, o, h, low, c)


def test_hard_stop_triggers_on_intraday_low_not_close():
    """A stock that dips to the stop and closes green still stopped out."""
    bars = [bar("d1", 10.0, 10.1, 9.4, 10.05)]        # low 9.4 < 9.5 stop
    gross, why, held = ea.settle(bars, 10.0, -5.0, None, 0, None, None)
    assert why == "hard_stop" and held == 1
    assert abs(gross - (-5.0)) < 1e-9                  # filled at the stop level


def test_gap_through_fills_at_the_open_not_the_stop():
    """The difference between honest and flattering: a -12% gap fills at -12%."""
    bars = [bar("d1", 8.8, 8.9, 8.5, 8.6)]             # opened below the 9.5 stop
    gross, why, _ = ea.settle(bars, 10.0, -5.0, None, 0, None, None)
    assert why == "hard_stop"
    assert abs(gross - (-12.0)) < 1e-9                 # open, not -5%


def test_early_stop_only_inside_its_window():
    falling = [bar(f"d{i}", 10.0, 10.0, 9.8, 9.6) for i in range(1, 6)]
    # -4% on close, within the 3-day window → early stop on session 1
    gross, why, held = ea.settle(falling, 10.0, -5.0, -3.0, 3, None, None)
    assert why == "early_stop" and held == 1 and abs(gross - (-4.0)) < 1e-9
    # same path, window closed → rides to the horizon instead
    _g, why2, _h = ea.settle(falling, 10.0, -5.0, -3.0, 0, None, None)
    assert why2 == "horizon"


def test_time_stop_fires_at_the_threshold_and_respects_the_gain_bar():
    flat = [bar(f"d{i}", 10.0, 10.2, 9.9, 10.1) for i in range(1, 13)]   # +1%
    _g, why, held = ea.settle(flat, 10.0, -5.0, None, 0, 10, 3.0)
    assert why == "time_stop" and held == 10          # ON day 10, not 11
    # a position above the bar is never time-stopped
    winner = [bar(f"d{i}", 10.0, 10.6, 10.0, 10.5) for i in range(1, 13)]  # +5%
    _g2, why2, _h2 = ea.settle(winner, 10.0, -5.0, None, 0, 10, 3.0)
    assert why2 == "horizon"


def test_hard_stop_takes_precedence_over_a_same_session_time_stop():
    """Both could fire on session 10; the hard stop is the one that happened."""
    bars = [bar(f"d{i}", 10.0, 10.1, 9.95, 10.0) for i in range(1, 10)]
    bars.append(bar("d10", 10.0, 10.0, 9.0, 9.2))     # breaches -5% intraday
    _g, why, held = ea.settle(bars, 10.0, -5.0, None, 0, 10, 3.0)
    assert why == "hard_stop" and held == 10


def test_close_fill_ignores_intraday_dips_and_fills_worse():
    """The twice-a-day problem: we don't hold a resting stop, we sample.

    Measured on 21 real stop exits: mean -2.56pp past the stop level, 14 of 21
    filling below it. `fill="close"` is the pessimistic bound on that.
    """
    # dips to -6% intraday, closes at -1%: a resting order fills, we never see it
    dip = [bar("d1", 10.0, 10.0, 9.4, 9.9), bar("d2", 9.9, 10.2, 9.9, 10.2)]
    assert ea.settle(dip, 10.0, -5.0, None, 0, None, None, fill="stop")[1] == "hard_stop"
    assert ea.settle(dip, 10.0, -5.0, None, 0, None, None, fill="close")[1] == "horizon"

    # closes at -8%: both see it, but close-fill takes the worse price
    through = [bar("d1", 9.9, 9.9, 9.1, 9.2)]
    opt = ea.settle(through, 10.0, -5.0, None, 0, None, None, fill="stop")
    pess = ea.settle(through, 10.0, -5.0, None, 0, None, None, fill="close")
    assert opt[1] == pess[1] == "hard_stop"
    assert abs(opt[0] - (-5.0)) < 1e-9 and abs(pess[0] - (-8.0)) < 1e-9
    assert pess[0] < opt[0]


def test_date_triggered_rules_are_identical_under_both_fills():
    """Only the hard stop is price-triggered; the time stop must not move."""
    flat = [bar(f"d{i}", 10.0, 10.2, 9.9, 10.1) for i in range(1, 13)]
    a = ea.settle(flat, 10.0, -5.0, None, 0, 10, 3.0, fill="stop")
    b = ea.settle(flat, 10.0, -5.0, None, 0, 10, 3.0, fill="close")
    assert a == b and a[1] == "time_stop"


def test_no_rules_rides_to_the_horizon():
    bars = [bar(f"d{i}", 10.0, 10.0, 5.0, 6.0) for i in range(1, 4)]   # -40%
    gross, why, held = ea.settle(bars, 10.0, None, None, 0, None, None)
    assert why == "horizon" and held == 3
    assert abs(gross - (-40.0)) < 1e-9                # no stop = full damage


def test_empty_bars_settle_to_nothing():
    assert ea.settle([], 10.0, -5.0, None, 0, None, None) == (None, None, 0)
