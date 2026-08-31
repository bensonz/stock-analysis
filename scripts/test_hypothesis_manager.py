#!/usr/bin/env python3
"""Tests for the hypothesis-based learning system."""

import json
import sys
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import hypothesis_manager as hm

def _recent(day_offset: int) -> str:
    """Evidence date `day_offset` days into a window ending yesterday.

    These tests hardcoded 2026-03-XX dates; RETIRE_STALE_DAYS(30) compares
    lastTested to date.today(), so every hypothesis was auto-retired before the
    promotion chain could run once the calendar moved on — the suite rotted
    silently around 2026-04-06 and stayed red for five months. Relative dates
    keep the fixture inside the freshness window forever. Offsets preserve the
    original ordering (old 2026-03-01 == offset 1).
    """
    from datetime import date, timedelta
    base = date.today() - timedelta(days=15)
    return (base + timedelta(days=day_offset - 1)).isoformat()



def _fresh_data():
    """Return empty hypothesis data."""
    return {"version": 2, "lastUpdated": str(date.today()), "hypotheses": []}


def _make_hypothesis(data, text="Test hypothesis", h_type="heuristic", tags=None, status=None, **kwargs):
    """Helper to create a hypothesis with defaults."""
    return hm.create_hypothesis(data, text=text, h_type=h_type, tags=tags or ["test"], status=status, **kwargs)


# ─── Unit Tests ──────────────────────────────────────────────────────────────

class TestCreateHypothesis:
    def test_basic_creation(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "ST stocks underperform")
        assert h["id"] == "h001"
        assert h["text"] == "ST stocks underperform"
        assert h["status"] == "observation"
        assert h["sampleSize"] == 0
        assert h["hitRate"] == 0.5
        assert h["confidence"] == 0.5
        assert h["type"] == "heuristic"
        print("✅ test_basic_creation")

    def test_with_initial_evidence(self):
        data = _fresh_data()
        h = hm.create_hypothesis(
            data, "Avoid ST stocks", h_type="heuristic",
            initial_evidence={"type": "supporting", "detail": "ST某某 dropped 12%"},
        )
        assert h["sampleSize"] == 1
        assert h["hitRate"] == 1.0
        assert h["confidence"] == 0.6  # (1 + 1) / (1 + 2) = 0.667 → but initial is 0.6 in code
        assert len(h["evidence"]["supporting"]) == 1
        assert len(h["evidence"]["contradicting"]) == 0
        print("✅ test_with_initial_evidence")

    def test_with_contradicting_initial_evidence(self):
        data = _fresh_data()
        h = hm.create_hypothesis(
            data, "Avoid ST stocks", h_type="heuristic",
            initial_evidence={"type": "contradicting", "detail": "ST某某 rallied 8%"},
        )
        assert h["hitRate"] == 0.0
        assert h["confidence"] == 0.4
        print("✅ test_with_contradicting_initial_evidence")

    def test_sequential_ids(self):
        data = _fresh_data()
        h1 = _make_hypothesis(data, "First")
        h2 = _make_hypothesis(data, "Second")
        h3 = _make_hypothesis(data, "Third")
        assert h1["id"] == "h001"
        assert h2["id"] == "h002"
        assert h3["id"] == "h003"
        print("✅ test_sequential_ids")

    def test_invalid_type_raises(self):
        data = _fresh_data()
        try:
            hm.create_hypothesis(data, "Bad", h_type="invalid_type")
            assert False, "Should have raised"
        except ValueError:
            pass
        print("✅ test_invalid_type_raises")

    def test_explicit_status(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Pre-validated rule", status="validated")
        assert h["status"] == "validated"
        print("✅ test_explicit_status")


class TestAddEvidence:
    def test_supporting_evidence(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        hm.add_evidence(data, h["id"], "supporting", "It worked")
        assert h["sampleSize"] == 1
        assert h["hitRate"] == 1.0
        assert len(h["evidence"]["supporting"]) == 1
        print("✅ test_supporting_evidence")

    def test_contradicting_evidence(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        hm.add_evidence(data, h["id"], "contradicting", "It failed")
        assert h["sampleSize"] == 1
        assert h["hitRate"] == 0.0
        assert len(h["evidence"]["contradicting"]) == 1
        print("✅ test_contradicting_evidence")

    def test_mixed_evidence_hitrate(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        hm.add_evidence(data, h["id"], "supporting", "Win 1")
        hm.add_evidence(data, h["id"], "supporting", "Win 2")
        hm.add_evidence(data, h["id"], "contradicting", "Loss 1")
        assert h["sampleSize"] == 3
        assert abs(h["hitRate"] - 0.667) < 0.01  # 2/3
        print("✅ test_mixed_evidence_hitrate")

    def test_confidence_increases_with_supporting(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        prev_conf = h["confidence"]
        for i in range(5):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}")
        assert h["confidence"] > prev_conf
        assert h["confidence"] < 1.0  # Never reaches 1.0 due to prior
        print("✅ test_confidence_increases_with_supporting")

    def test_confidence_decreases_with_contradicting(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        prev_conf = h["confidence"]
        for i in range(5):
            hm.add_evidence(data, h["id"], "contradicting", f"Loss {i}")
        assert h["confidence"] < prev_conf
        assert h["confidence"] > 0.0  # Never reaches 0.0 due to prior
        print("✅ test_confidence_decreases_with_contradicting")

    def test_confidence_bounds(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        # Add 100 supporting
        for i in range(100):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}", ev_date=f"2026-01-{(i%28)+1:02d}")
        assert 0 <= h["confidence"] <= 1
        # Reset and add 100 contradicting
        data2 = _fresh_data()
        h2 = _make_hypothesis(data2, "Test2")
        for i in range(100):
            hm.add_evidence(data2, h2["id"], "contradicting", f"Loss {i}", ev_date=f"2026-02-{(i%28)+1:02d}")
        assert 0 <= h2["confidence"] <= 1
        print("✅ test_confidence_bounds")

    def test_duplicate_evidence_ignored(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        today = str(date.today())
        hm.add_evidence(data, h["id"], "supporting", "Same detail", ev_date=today)
        hm.add_evidence(data, h["id"], "supporting", "Same detail", ev_date=today)
        assert h["sampleSize"] == 1  # Duplicate ignored
        assert len(h["evidence"]["supporting"]) == 1
        print("✅ test_duplicate_evidence_ignored")

    def test_similar_evidence_ignored(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        today = str(date.today())
        hm.add_evidence(data, h["id"], "supporting", "ST stock dropped 12%", ev_date=today)
        hm.add_evidence(data, h["id"], "supporting", "ST stock dropped 12% today", ev_date=today)
        assert h["sampleSize"] == 1  # Similar enough to be duplicate
        print("✅ test_similar_evidence_ignored")

    def test_different_date_not_duplicate(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        hm.add_evidence(data, h["id"], "supporting", "Same detail", ev_date=_recent(1))
        hm.add_evidence(data, h["id"], "supporting", "Same detail", ev_date=_recent(2))
        assert h["sampleSize"] == 2  # Different dates = different evidence
        print("✅ test_different_date_not_duplicate")

    def test_nonexistent_id_raises(self):
        data = _fresh_data()
        try:
            hm.add_evidence(data, "h999", "supporting", "Ghost")
            assert False, "Should have raised"
        except ValueError:
            pass
        print("✅ test_nonexistent_id_raises")

    def test_invalid_evidence_type_raises(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Test")
        try:
            hm.add_evidence(data, h["id"], "neutral", "Meh")
            assert False, "Should have raised"
        except ValueError:
            pass
        print("✅ test_invalid_evidence_type_raises")


class TestAutoLifecycle:
    def test_promote_observation_to_hypothesis(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Pattern spotted")
        assert h["status"] == "observation"
        hm.add_evidence(data, h["id"], "supporting", "Case 1")
        hm.add_evidence(data, h["id"], "supporting", "Case 2")
        assert h["status"] == "hypothesis"  # 2+ evidence
        print("✅ test_promote_observation_to_hypothesis")

    def test_promote_hypothesis_to_validated(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Seems to work", status="hypothesis")
        # Need 5+ evidence with hitRate >= 0.65
        for i in range(4):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}", ev_date=_recent(i+1))
        assert h["status"] == "hypothesis"  # Only 4, not enough
        hm.add_evidence(data, h["id"], "supporting", "Win 4", ev_date=_recent(5))
        assert h["status"] == "validated"  # 5 supporting, hitRate=1.0
        print("✅ test_promote_hypothesis_to_validated")

    def test_no_promote_with_low_hitrate(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Shaky pattern", status="hypothesis")
        # 3 supporting, 3 contradicting = 50% hitRate < 65%
        for i in range(3):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}", ev_date=_recent(i+1))
        for i in range(3):
            hm.add_evidence(data, h["id"], "contradicting", f"Loss {i}", ev_date=_recent(i+4))
        assert h["status"] == "hypothesis"  # 6 samples but 50% < 65%
        print("✅ test_no_promote_with_low_hitrate")

    def test_promote_validated_to_rule(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Rock solid", status="validated")
        # Need 10+ evidence with hitRate >= 0.75
        for i in range(8):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}", ev_date=_recent(i+1))
        assert h["status"] == "validated"  # 8, not enough
        hm.add_evidence(data, h["id"], "supporting", "Win 8", ev_date=_recent(9))
        hm.add_evidence(data, h["id"], "supporting", "Win 9", ev_date=_recent(10))
        assert h["status"] == "rule"  # 10 supporting, hitRate=1.0
        print("✅ test_promote_validated_to_rule")

    def test_demote_rule_to_validated(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Was a rule", status="rule")
        # Start with 8 supporting to be a rule
        for i in range(8):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}", ev_date=f"2026-02-{i+1:02d}")
        assert h["status"] == "rule"
        # Add contradicting to drop hitRate below 75%
        for i in range(4):
            hm.add_evidence(data, h["id"], "contradicting", f"Loss {i}", ev_date=_recent(i+1))
        # 8/12 = 66.7% < 75% → demote
        assert h["status"] == "validated"
        print("✅ test_demote_rule_to_validated")

    def test_demote_validated_to_hypothesis(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Slipping", status="validated")
        for i in range(3):
            hm.add_evidence(data, h["id"], "supporting", f"Win {i}", ev_date=f"2026-02-{i+1:02d}")
        for i in range(4):
            hm.add_evidence(data, h["id"], "contradicting", f"Loss {i}", ev_date=_recent(i+1))
        # 3/7 = 42.9% < 65% → demote
        assert h["status"] == "hypothesis"
        print("✅ test_demote_validated_to_hypothesis")

    def test_auto_retire_low_hitrate(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Bad idea", status="hypothesis")
        hm.add_evidence(data, h["id"], "supporting", "Win once", ev_date=_recent(1))
        for i in range(4):
            hm.add_evidence(data, h["id"], "contradicting", f"Loss {i}", ev_date=_recent(i+2))
        # 1/5 = 20% < 40% threshold → retired
        assert h["status"] == "retired"
        assert h["retiredReason"] is not None
        assert "hitRate" in h["retiredReason"]
        print("✅ test_auto_retire_low_hitrate")

    def test_auto_retire_stale(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Old news")
        stale_date = str(date.today() - timedelta(days=35))
        h["lastTested"] = stale_date
        # Trigger lifecycle check via add_evidence... but actually _auto_lifecycle
        # is called after add_evidence. Let's simulate by calling it directly.
        hm._auto_lifecycle(h)
        assert h["status"] == "retired"
        assert "days" in h["retiredReason"]
        print("✅ test_auto_retire_stale")

    def test_retired_stays_retired(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Dead hypothesis")
        h["status"] = "retired"
        h["retiredDate"] = str(date.today())
        h["retiredReason"] = "Manual"
        hm._auto_lifecycle(h)
        assert h["status"] == "retired"  # Should not un-retire
        print("✅ test_retired_stays_retired")


class TestFuzzyMatch:
    def test_exact_match(self):
        data = _fresh_data()
        _make_hypothesis(data, "Avoid ST stocks because they underperform", tags=["entry-filter"])
        match = hm.find_matching(data, "Avoid ST stocks because they underperform", ["entry-filter"])
        assert match is not None
        assert match["id"] == "h001"
        print("✅ test_exact_match")

    def test_similar_text_match(self):
        data = _fresh_data()
        _make_hypothesis(data, "ST stocks tend to underperform the market", tags=["entry-filter", "stock-selection"])
        match = hm.find_matching(data, "avoid ST stocks they usually underperform", ["entry-filter"])
        assert match is not None
        print("✅ test_similar_text_match")

    def test_no_false_match(self):
        data = _fresh_data()
        _make_hypothesis(data, "Breadth below 0.5:1 is a no-entry signal", tags=["market-regime"])
        match = hm.find_matching(data, "IV Rank below 15% means reduce position size", ["iv-sentiment"])
        assert match is None
        print("✅ test_no_false_match")

    def test_retired_not_matched(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Dead rule about something specific")
        h["status"] = "retired"
        match = hm.find_matching(data, "Dead rule about something specific")
        assert match is None
        print("✅ test_retired_not_matched")

    def test_best_match_wins(self):
        data = _fresh_data()
        _make_hypothesis(data, "IV Rank matters for timing", tags=["iv"])
        _make_hypothesis(data, "IV Rank below 15% means reduce new position sizing by 50%", tags=["iv", "position-sizing"])
        match = hm.find_matching(data, "When IV Rank is under 15%, cut new position size in half", ["iv", "position-sizing"])
        assert match is not None
        assert match["id"] == "h002"  # More specific match
        print("✅ test_best_match_wins")


class TestGetActiveForPrompt:
    def test_empty_data(self):
        data = _fresh_data()
        result = hm.get_active_for_prompt(data)
        assert "bootstrapping" in result
        print("✅ test_empty_data")

    def test_only_shows_validated_and_rule(self):
        data = _fresh_data()
        _make_hypothesis(data, "Just an observation", status="observation")
        _make_hypothesis(data, "Just a hypothesis", status="hypothesis")
        _make_hypothesis(data, "Validated finding", status="validated")
        _make_hypothesis(data, "Proven rule", status="rule")
        result = hm.get_active_for_prompt(data)
        assert "Validated finding" in result
        assert "Proven rule" in result
        assert "Just an observation" not in result
        assert "Just a hypothesis" not in result
        print("✅ test_only_shows_validated_and_rule")

    def test_format_includes_stats(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Good rule", status="rule")
        h["hitRate"] = 0.85
        h["sampleSize"] = 12
        h["confidence"] = 0.82
        result = hm.get_active_for_prompt(data)
        assert "85%" in result
        assert "n=12" in result
        print("✅ test_format_includes_stats")


class TestProcessLearnings:
    def test_string_format_backward_compat(self):
        data = _fresh_data()
        actions = hm.process_learnings(data, [
            "New observation about market behavior",
            "Another learning from today",
        ])
        assert len(actions) == 2
        assert len(data["hypotheses"]) == 2
        assert all(h["status"] == "observation" for h in data["hypotheses"])
        print("✅ test_string_format_backward_compat")

    def test_dict_format_new(self):
        data = _fresh_data()
        actions = hm.process_learnings(data, [{
            "text": "IV below 15% means caution",
            "type": "signal",
            "tags": ["iv", "entry-filter"],
            "mechanism": "Low IV = complacency, vol expansion imminent",
        }])
        assert len(actions) == 1
        h = data["hypotheses"][0]
        assert h["type"] == "signal"
        assert h["tags"] == ["iv", "entry-filter"]
        assert h["mechanism"] == "Low IV = complacency, vol expansion imminent"
        print("✅ test_dict_format_new")

    def test_invalid_evidence_type_is_coerced_not_fatal(self):
        # 2026-08-14: the model wrote evidence_type:"observation" (a `type`
        # value), which KeyError'd on evidence["observation"], aborted the
        # whole learnings step and hard-failed an otherwise clean run at
        # Gate 3 — no commit, no site rebuild, trades already applied.
        data = _fresh_data()
        actions = hm.process_learnings(data, [{
            "text": "板块轮动加速=存量资金博弈",
            "type": "signal",
            "evidence_type": "observation",   # invalid
            "tags": ["sector"],
        }])
        h = data["hypotheses"][0]
        assert len(h["evidence"]["supporting"]) == 1
        assert h["evidence"]["contradicting"] == []
        assert any("coerced" in a for a in actions)   # degradation stays loud

    def test_one_bad_learning_does_not_discard_the_batch(self):
        # The three learnings from that run: two valid, one malformed. All
        # three were lost. Now a bad entry costs only itself.
        data = _fresh_data()
        actions = hm.process_learnings(data, [
            {"text": "Breadth below 0.5 blocks new entries", "type": "rule",
             "tags": ["entry-filter"]},
            12345,                        # neither dict nor str — raises
            {"text": "Medical sector rotated out of the top five", "type": "signal",
             "tags": ["sector"]},
        ])
        texts = [h["text"] for h in data["hypotheses"]]
        assert "Breadth below 0.5 blocks new entries" in texts
        assert "Medical sector rotated out of the top five" in texts
        assert any("skipped malformed" in a for a in actions)   # and stays loud

    def test_create_hypothesis_rejects_bad_initial_evidence_bucket(self):
        # Backstop for any caller that bypasses process_learnings.
        data = _fresh_data()
        h = hm.create_hypothesis(
            data, text="直接建仓的假设", h_type="observation", tags=[],
            initial_evidence={"type": "nonsense", "detail": "d", "date": "2026-08-14"})
        assert len(h["evidence"]["supporting"]) == 1
        assert set(h["evidence"].keys()) == {"supporting", "contradicting"}

    def test_matches_existing(self):
        data = _fresh_data()
        # Create existing hypothesis
        _make_hypothesis(data, "Breadth below 0.5 is a no-entry signal", tags=["market-regime", "entry-filter", "breadth"])
        # Process a related learning (dict format with tags for better matching)
        actions = hm.process_learnings(data, [{
            "text": "Breadth 0.35:1 confirmed as strong no-entry signal today",
            "tags": ["market-regime", "breadth"],
        }])
        assert len(data["hypotheses"]) == 1  # No new hypothesis created
        assert data["hypotheses"][0]["sampleSize"] == 1  # Evidence added
        assert "Updated" in actions[0]
        print("✅ test_matches_existing")

    def test_explicit_related_hypothesis(self):
        data = _fresh_data()
        h = _make_hypothesis(data, "Cut at -5%", tags=["exit-rule"])
        actions = hm.process_learnings(data, [{
            "text": "中石科技 -5% stop saved further losses today",
            "related_hypothesis": h["id"],
            "evidence_type": "supporting",
        }])
        assert len(data["hypotheses"]) == 1
        assert h["sampleSize"] == 1
        print("✅ test_explicit_related_hypothesis")

    def test_empty_text_skipped(self):
        data = _fresh_data()
        actions = hm.process_learnings(data, [{"text": ""}, {"text": None}])
        assert len(actions) == 0
        assert len(data["hypotheses"]) == 0
        print("✅ test_empty_text_skipped")


class TestFullLifecycle:
    def test_observation_to_rule(self):
        """Full lifecycle: observation → hypothesis → validated → rule.
        
        Uses the structured learning format with related_hypothesis references,
        which is how the system works in practice after the first observation.
        """
        data = _fresh_data()

        # Day 1: First observation (string format, creates new)
        hm.process_learnings(data, [{
            "text": "Sector gravity always wins — cold sector stock fell",
            "type": "heuristic",
            "tags": ["sector", "exit-rule"],
        }], run_date=_recent(1))
        h = data["hypotheses"][0]
        assert h["status"] == "observation"

        # Day 2+: Subsequent evidence references the hypothesis explicitly
        hm.process_learnings(data, [{
            "text": "Sector gravity confirmed — another cold sector stock fell despite good fundamentals",
            "related_hypothesis": h["id"],
            "evidence_type": "supporting",
        }], run_date=_recent(2))
        assert h["status"] == "hypothesis"
        assert h["sampleSize"] == 2

        # Days 3-6: More supporting evidence → promotes to validated
        for i in range(3, 7):
            hm.process_learnings(data, [{
                "text": f"Sector gravity case day {i}: wrong-sector stock dragged down",
                "related_hypothesis": h["id"],
                "evidence_type": "supporting",
            }], run_date=_recent(i))
        assert h["status"] == "validated"
        assert h["sampleSize"] == 6

        # Days 7-12: Even more → promotes to rule
        for i in range(7, 13):
            hm.process_learnings(data, [{
                "text": f"Yet another sector gravity case day {i}",
                "related_hypothesis": h["id"],
                "evidence_type": "supporting",
            }], run_date=_recent(i))
        assert h["status"] == "rule"
        assert h["sampleSize"] == 12
        assert h["hitRate"] == 1.0

        # Now add contradicting evidence → demotes
        for i in range(13, 17):
            hm.process_learnings(data, [{
                "text": f"Exception: stock in cold sector rallied despite sector gravity (day {i})",
                "related_hypothesis": h["id"],
                "evidence_type": "contradicting",
            }], run_date=_recent(i))

        # 12/16 = 75% → still rule (at boundary)
        assert h["hitRate"] == 0.75
        assert h["status"] == "rule"

        # One more contradicting → 12/17 = 70.6% < 75% → demote to validated
        hm.process_learnings(data, [{
            "text": "Another cold-sector exception",
            "related_hypothesis": h["id"],
            "evidence_type": "contradicting",
        }], run_date=_recent(17))
        assert h["hitRate"] < 0.75
        assert h["status"] == "validated"

        print("✅ test_observation_to_rule (full lifecycle)")


class TestPersistence:
    def test_save_and_load(self):
        """Test that save/load round-trips correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "hypotheses.json"
            # Monkey-patch the file path
            original = hm.HYPOTHESES_FILE
            hm.HYPOTHESES_FILE = tmp_file
            try:
                data = _fresh_data()
                _make_hypothesis(data, "Persistent rule", tags=["test"])
                hm.add_evidence(data, "h001", "supporting", "It worked")
                hm.save_hypotheses(data)

                loaded = hm.load_hypotheses()
                assert len(loaded["hypotheses"]) == 1
                assert loaded["hypotheses"][0]["text"] == "Persistent rule"
                assert loaded["hypotheses"][0]["sampleSize"] == 1
            finally:
                hm.HYPOTHESES_FILE = original
        print("✅ test_save_and_load")


# TestHistoricalReplay::test_replay_existing_runs deleted 2026-09-01 (repo
# audit): it iterated runs/*/response.json — a GIT-IGNORED artifact — so its
# inputs were untracked local state and it could never pass on a clean clone.
# Production already guards the list-shaped response it tripped on
# (run_daily._extract_json). A replay harness belongs in scripts/research/
# against tracked fixtures, not in the unit suite against local debris.


# ─── Run all tests ───────────────────────────────────────────────────────────

def run_all():
    test_classes = [
        TestCreateHypothesis,
        TestAddEvidence,
        TestAutoLifecycle,
        TestFuzzyMatch,
        TestGetActiveForPrompt,
        TestProcessLearnings,
        TestFullLifecycle,
        TestPersistence,
        TestHistoricalReplay,
    ]

    total = 0
    passed = 0
    failed = 0

    for cls in test_classes:
        print(f"\n{'='*60}")
        print(f"  {cls.__name__}")
        print(f"{'='*60}")
        instance = cls()
        for name in sorted(dir(instance)):
            if name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, name)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    print(f"❌ {name}: {e}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())
