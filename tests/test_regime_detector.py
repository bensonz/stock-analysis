"""Tests for the read-only regime detector v1.1 (2026-08-04).

Synthetic-panel tests — no DB. Pins the 2-D label semantics that came out
of the v1 retro failure: stop-rate = pool danger (level), rank-IC =
ranking efficacy (ordering); the two are independent dimensions.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import regime_detector as rd

N_CODES = 40
DATES = pd.date_range("2026-06-01", periods=14, freq="B")
CODES = [f"{600000 + i:06d}" for i in range(N_CODES)]


def _panel(closes: pd.DataFrame) -> dict:
    # everyone passes the gate; rps60 strictly increasing across codes
    rps = pd.DataFrame(
        [[80 + i * 0.45 for i in range(len(closes.columns))]] * len(closes),
        index=closes.index, columns=closes.columns)
    return {"closes": closes, "rps60": rps, "rps120": rps, "rps250": rps}


def test_label_matrix():
    assert rd.label_for(0.05, 0.20) == rd.LABEL_TREND
    assert rd.label_for(0.05, 0.55) == rd.LABEL_REVERSAL   # danger overrides
    assert rd.label_for(-0.10, 0.20) == rd.LABEL_REVERSAL  # deep inversion
    assert rd.label_for(0.00, 0.20) == rd.LABEL_NEUTRAL    # safe, no edge
    assert rd.label_for(None, 0.20) == rd.LABEL_NEUTRAL


def test_ic_positive_when_ranking_pays():
    # higher rps60 code → higher daily growth → forward returns align: IC ≈ +1
    closes = pd.DataFrame(
        {c: [100 * (1 + i * 0.002) ** t for t in range(len(DATES))]
         for i, c in enumerate(CODES)}, index=DATES)
    ic = rd.compute_ic_series(_panel(closes))
    assert len(ic) > 0
    assert ic.min() > 0.95


def test_ic_negative_when_ranking_inverted():
    closes = pd.DataFrame(
        {c: [100 * (1 + (N_CODES - i) * 0.002) ** t for t in range(len(DATES))]
         for i, c in enumerate(CODES)}, index=DATES)
    ic = rd.compute_ic_series(_panel(closes))
    assert ic.max() < -0.95


def test_stop_rate_counts_breaches():
    # 12 of 40 codes crash 10% right after the first date → rate 0.30 there
    data = {c: [100.0] * len(DATES) for c in CODES}
    for i, c in enumerate(CODES[:12]):
        for t in range(1, len(DATES)):
            data[c][t] = 90.0
    closes = pd.DataFrame(data, index=DATES)
    stops = rd.compute_stop_rate_series(_panel(closes))
    assert abs(stops.iloc[0] - 0.30) < 1e-9
    assert stops.iloc[-1] == 0.0 if len(stops) > 1 else True


def test_small_pool_skipped():
    closes = pd.DataFrame(
        {c: [100.0] * len(DATES) for c in CODES[:10]}, index=DATES)
    panel = _panel(closes)
    assert len(rd.compute_ic_series(panel)) == 0
    assert len(rd.compute_stop_rate_series(panel)) == 0
