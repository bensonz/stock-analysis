"""Unit tests for the uniform RPS momentum gate (data_collector.passes_rps_gate).

The gate was loosened from (rps120>=85, rps250>=85, rps60>=70) to a UNIFORM
rps60/rps120/rps250 >= 80. These lock in both directions of the change:
the loosening (85->80 on the two long legs) and the tightening (rps60 70->80).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import data_collector as dc


def test_floor_is_80():
    assert dc.RPS_GATE_MIN == 80


def test_all_three_at_floor_passes():
    assert dc.passes_rps_gate(80, 80, 80) is True


def test_just_below_floor_fails_each_leg():
    assert dc.passes_rps_gate(79.9, 90, 90) is False   # rps60 leg
    assert dc.passes_rps_gate(90, 79.9, 90) is False   # rps120 leg
    assert dc.passes_rps_gate(90, 90, 79.9) is False   # rps250 leg


def test_loosening_long_leg_82_now_passes():
    # rps120=82 was REJECTED under the old >=85 gate; now it clears the 80 floor.
    assert dc.passes_rps_gate(90, 82, 82) is True


def test_tightening_rps60_75_now_fails():
    # rps60=75 was ACCEPTED under the old >=70 gate; now it fails the 80 floor.
    assert dc.passes_rps_gate(75, 95, 95) is False


def test_none_fails():
    assert dc.passes_rps_gate(None, 90, 90) is False
    assert dc.passes_rps_gate(90, None, 90) is False
    assert dc.passes_rps_gate(90, 90, None) is False


def test_real_cases_that_motivated_the_change():
    # 301345 (涛涛车业) 85.5/80.2/97.3 — failed old rps120>=85, now clears the 80 floor.
    assert dc.passes_rps_gate(85.48, 80.21, 97.28) is True
    # 002832 (比音勒芬) 91.8/85.8/67.5 — rps250 still below 80, stays excluded.
    assert dc.passes_rps_gate(91.82, 85.79, 67.48) is False


def test_gate_min_override():
    assert dc.passes_rps_gate(86, 86, 86, gate_min=85) is True
    assert dc.passes_rps_gate(84, 86, 86, gate_min=85) is False
