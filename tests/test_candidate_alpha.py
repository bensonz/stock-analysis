"""The methodology choices are the finding — pin them, not the numbers.

Every number this script prints will drift as runs accumulate. What must not
drift is *how* they are computed, because three separate decisions are what
separate a real answer from a flattering one:

1. Excess of index. The market was roughly flat over the sample while the screen
   was not; without subtracting the benchmark a bad screen and a bad tape are
   the same picture.
2. Fixed horizons, never "to exit". Measuring to exit folds our own sell rule
   into the answer and reports on the exit machinery instead of the pick. This
   is exactly the error that made an earlier pass of this analysis read as
   "reliably negative" when it was not.
3. Clustering by code. A name sits on the list a median of 16 sessions (max
   117), so 7266 rows are ~294 stocks counted repeatedly. Row-level n is the
   right description of a random pick on a random day; it is the wrong
   denominator for a confidence claim, and quoting it as one overstates
   certainty by more than an order of magnitude.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import candidate_alpha as ca


PANEL = {
    # rises 10% over 5 sessions
    "000001": [("2026-01-01", 100.0), ("2026-01-02", 102.0), ("2026-01-05", 104.0),
               ("2026-01-06", 106.0), ("2026-01-07", 108.0), ("2026-01-08", 110.0)],
    # flat
    "000002": [("2026-01-01", 50.0), ("2026-01-02", 50.0), ("2026-01-05", 50.0),
               ("2026-01-06", 50.0), ("2026-01-07", 50.0), ("2026-01-08", 50.0)],
}
# index also rises 10% — so 000001 has ZERO alpha and 000002 has -10%
INDEX = {"2026-01-01": 1000.0, "2026-01-02": 1020.0, "2026-01-05": 1040.0,
         "2026-01-06": 1060.0, "2026-01-07": 1080.0, "2026-01-08": 1100.0}
IDATES = sorted(INDEX)


def test_a_stock_that_merely_matched_the_index_shows_no_alpha():
    """+10% in a +10% market is not skill. Reporting raw returns would credit it."""
    got = ca.excess(PANEL, INDEX, IDATES, [("2026-01-01", "000001")], 5)
    assert abs(got[0]) < 1e-9


def test_a_flat_stock_in_a_rising_market_is_a_loss():
    got = ca.excess(PANEL, INDEX, IDATES, [("2026-01-01", "000002")], 5)
    assert abs(got[0] - (-10.0)) < 1e-9


def test_the_horizon_is_fixed_not_read_from_any_exit():
    """forward() takes h sessions and knows nothing about trades or sell rules."""
    assert abs(ca.forward(PANEL, "000001", "2026-01-01", 5) - 10.0) < 1e-9
    assert abs(ca.forward(PANEL, "000001", "2026-01-01", 2) - 4.0) < 1e-9


def test_a_window_running_past_the_data_is_dropped_not_truncated():
    """Silently shortening the window would quietly mix horizons together."""
    assert ca.forward(PANEL, "000001", "2026-01-06", 5) is None


def test_clustering_collapses_repeat_appearances_to_one_observation():
    """The same stock listed on four days is one stock, not four data points."""
    items = [("2026-01-01", "000002"), ("2026-01-02", "000002"),
             ("2026-01-05", "000002"), ("2026-01-01", "000001")]
    rows = ca.excess(PANEL, INDEX, IDATES, items, 2)
    clustered = ca.cluster_by_code(PANEL, INDEX, IDATES, items, 2)
    assert len(rows) == 4
    assert len(clustered) == 2


def test_welch_is_used_because_the_samples_are_wildly_unequal():
    """~50 LLM picks against ~1000 blind rows. A pooled-variance test would
    understate the standard error and manufacture significance."""
    small = [1.0, 2.0, 3.0, 2.5, 1.5]
    large = [1.0, 2.0, 3.0, 2.5, 1.5] * 40
    w = ca.welch(small, large)
    assert w is not None and not w["significant"]
    assert abs(w["diff"]) < 1e-9


def test_status_classes_are_read_from_the_first_glyph(tmp_path):
    """Status text varies ('❌ MA5,MA10,MA20', '❌ MA20'); only the class matters."""
    run = tmp_path / "2026-01-02" / "noon" / "output"
    run.mkdir(parents=True)
    (run / "candidates.md").write_text(
        "| Code | Name | RPS120 | RPS60 | MA5% | MA10% | MA20% | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 000001 | a | 90 | 88 | +1.0 | +2.0 | +3.0 | ✅ PASS |\n"
        "| 000002 | b | 99 | 97 | +1.0 | +2.0 | +3.0 | ⏳ >95 |\n"
        "| 000003 | c | 80 | 78 | -9.0 | -9.0 | -9.0 | ❌ MA5,MA10,MA20 |\n",
        encoding="utf-8")
    rows = ca.parse_candidates(runs_dir=tmp_path)
    assert [r[5] for r in rows] == ["✅", "⏳", "❌"]
    assert [r[0] for r in rows] == ["2026-01-02"] * 3
    assert rows[0][2] == 90.0 and rows[2][4] == -9.0


def test_columns_come_from_each_files_own_header(tmp_path):
    """candidates.md has had two shapes — the pre-2026-05 table carried extra
    Trend and Co columns before the MA block:

        | Code | Name | RPS120 | RPS60 | Trend | Co | MA5% | MA10% | MA20% | Status |
        | Code | Name | RPS120 | RPS60 | MA5% | MA10% | MA20% | Status |

    Positional parsing reads MA5% as MA20% for every row of the older format —
    about 80% of the archive — and produced a published distance-bucket table
    that silently mixed the two measurements. Both eras must yield identical
    values for the same stock.
    """
    old = tmp_path / "2026-04-28" / "output"
    new = tmp_path / "2026-08-27" / "afternoon" / "output"
    old.mkdir(parents=True)
    new.mkdir(parents=True)
    (old / "candidates.md").write_text(
        "| Code | Name | RPS120 | RPS60 | Trend | Co | MA5% | MA10% | MA20% | Status |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        "| 000001 | a | 90 | 88 | - | - | +1.5 | +2.5 | +3.5 | ✅ PASS |\n",
        encoding="utf-8")
    (new / "candidates.md").write_text(
        "| Code | Name | RPS120 | RPS60 | MA5% | MA10% | MA20% | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 000001 | a | 90 | 88 | +1.5 | +2.5 | +3.5 | ✅ PASS |\n",
        encoding="utf-8")

    rows = ca.parse_candidates(runs_dir=tmp_path)
    assert len(rows) == 2
    old_row = next(r for r in rows if r[0] == "2026-04-28")
    new_row = next(r for r in rows if r[0] == "2026-08-27")
    # (rps120, dist_ma5, dist_ma20, status) must agree across the format change
    assert old_row[2:] == new_row[2:] == (90.0, 1.5, 3.5, "✅")


def test_thin_samples_are_flagged_rather_than_reported():
    """A mean over three observations is not a result; describe() must say so
    instead of printing a confident-looking number."""
    assert ca.describe([1.0, 2.0, 3.0])["thin"] is True
    assert ca.describe([1.0] * 20)["thin"] is False
