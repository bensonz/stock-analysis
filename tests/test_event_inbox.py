"""event_inbox — wallstreetcn candidates → AI triage / owner checklist → events.json.

Offline: the fetch and the LLM are injected (fake DataFrames, fake replies),
every path is a tmp file. A real LLM call fails the test (autouse guard).
The root conftest fingerprints tracking/ — nothing here may touch it.
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import event_calendar as ec
import event_inbox as ei
import event_triage as et
import llm_client

TODAY = date(2026, 10, 12)   # Monday

MIDTERM = {"时间": "2026-11-03 00:00:00", "地区": "美国", "事件": "美国 11 月 3 日中期选举",
           "重要性": 4, "今值": float("nan"), "预期": float("nan"), "前值": float("nan"),
           "链接": ""}
KR_CPI = {"时间": "2026-11-03 07:00:00", "地区": "韩国", "事件": "10月CPI同比",
          "重要性": 4, "今值": float("nan"), "预期": float("nan"), "前值": 2.9,
          "链接": "https://wallstreetcn.com/calendar/KR2608052/overview"}
IMP3 = {"时间": "2026-11-03 08:00:00", "地区": "日本", "事件": "9月失业率", "重要性": 3,
        "今值": float("nan"), "预期": float("nan"), "前值": float("nan"),
        "链接": "https://wallstreetcn.com/calendar/JP3/overview"}
LOW = {"时间": "2026-11-03 09:00:00", "地区": "日本", "事件": "不重要", "重要性": 2,
       "今值": float("nan"), "预期": float("nan"), "前值": float("nan"), "链接": ""}


def fake_fetch(rows_by_day=None, fail=()):
    """rows_by_day: {'YYYYMMDD': [row, ...]}; others are empty days."""
    rows_by_day = rows_by_day or {}

    def _f(day):
        if day in fail:
            raise ConnectionError("boom")
        rows = rows_by_day.get(day)
        if not rows:
            raise KeyError("public_date")   # what akshare does on an empty day
        return pd.DataFrame(rows)
    return _f


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    def _refuse(prompt):
        raise AssertionError("a unit test reached the real LLM call")
    monkeypatch.setattr(et, "call_model", _refuse)


@pytest.fixture
def paths(tmp_path):
    events = tmp_path / "events.json"
    events.write_text(json.dumps({"note": "n", "events": []}, ensure_ascii=False),
                      encoding="utf-8")
    return {"inbox_path": tmp_path / "event_inbox.md",
            "ledger_path": tmp_path / "ledger.json",
            "events_path": events}


def refresh(paths, fetch, today=TODAY, days=30, **kw):
    return ei.refresh(today, fetch_fn=fetch, days=days, **paths, **kw)


def items(paths):
    return {i.id: i for i in ei.read_inbox(paths["inbox_path"])[0]}


def set_mark(paths, item_id, mark, **edits):
    """Edit the inbox the way the owner would: change the block in place."""
    text = paths["inbox_path"].read_text(encoding="utf-8")
    blocks = text.split("\n## ")
    for n, b in enumerate(blocks):
        if f"id: {item_id}" in b:
            b = b.replace("- [ ] keep", f"- [{mark}] keep")
            for old, new in edits.items():
                b = b.replace(old, new)
            blocks[n] = b
    paths["inbox_path"].write_text("\n## ".join(blocks), encoding="utf-8")


MID_ID = "wscn-20261103-" + hashlib.sha1(
    "美国|美国 11 月 3 日中期选举".encode()).hexdigest()[:8]
KR_ID = "wscn-20261103-KR2608052"


def fake_ai(decisions, calls=None, model="fake-model"):
    """An LLM that answers `decisions` (id → judgement) and logs each prompt."""
    def _f(prompt):
        if calls is not None:
            calls.append(prompt)
        return (json.dumps({"decisions": decisions}, ensure_ascii=False),
                {"provider": "openai", "model": model, "tokens_in": 100, "tokens_out": 20})
    return _f


def judge(decision, impact="high", direction="two_sided", reason="理由"):
    return {"decision": decision, "impact": impact, "direction": direction,
            "reason": reason}


def events(paths):
    return json.loads(paths["events_path"].read_text(encoding="utf-8"))["events"]


def ledger(paths):
    return ei.load_ledger(paths["ledger_path"])["decisions"]


def flip(paths, item_id, old, new):
    """Owner edits one AI-held block in place (any text, incl. the mark)."""
    text = paths["inbox_path"].read_text(encoding="utf-8")
    blocks = text.split("\n## ")
    for n, b in enumerate(blocks):
        if f"id: {item_id}" in b:
            assert old in b, (old, b)
            blocks[n] = b.replace(old, new)
    paths["inbox_path"].write_text("\n## ".join(blocks), encoding="utf-8")


@pytest.fixture
def ai_decided(paths):
    """Midterm kept by the AI (high), KR CPI skipped by the AI."""
    refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    rec = ei.triage(TODAY, **paths, triage_fn=fake_ai({
        MID_ID: judge("keep", reason="美国中期选举决定国会控制权"),
        KR_ID: judge("skip", impact="low", reason="韩国数据非系统性")}))
    assert (rec["kept"], rec["skipped"]) == (1, 1)
    return paths


# ── mapping ──────────────────────────────────────────────────────────────────

def test_us_placeholder_midnight_keeps_listed_date_and_impacts_next_session():
    it = ei.candidate_from_row(MIDTERM)
    assert (it.tz, it.date) == ("US", "2026-11-03")
    assert it.impact_date() == date(2026, 11, 4)
    assert it.impact == "high"            # importance 4


def test_us_early_morning_beijing_is_previous_us_day():
    """FOMC 02:00 Beijing Thu = Wed US → impact Thu, not Fri."""
    row = {**MIDTERM, "时间": "2026-10-29 02:00:00", "事件": "美联储利率决议"}
    it = ei.candidate_from_row(row)
    assert it.date == "2026-10-28"
    assert it.impact_date() == date(2026, 10, 29)


def test_non_us_is_cn_same_day_and_region_prefixed():
    it = ei.candidate_from_row(KR_CPI)
    assert (it.tz, it.date, it.name) == ("CN", "2026-11-03", "韩国10月CPI同比")
    assert it.id == "wscn-20261103-KR2608052"
    assert it.kind == "macro_release" and it.impact == "high"   # importance 4


# ── refresh ──────────────────────────────────────────────────────────────────

def test_refresh_filters_importance_and_writes_inbox(paths):
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM, IMP3, LOW]}))
    assert res["new"] == 1 and res["pending"] == 1
    text = paths["inbox_path"].read_text(encoding="utf-8")
    assert "## 2026-11-04 (T-23) 美国 — 美国 11 月 3 日中期选举" in text
    assert "不重要" not in text
    assert "日本9月失业率" not in text        # imp 3 < MIN_IMPORTANCE 4


def test_refresh_drops_undecided_items_below_threshold_but_keeps_marked(paths):
    """Raising the threshold prunes old undecided items, not owner picks."""
    imp3b = {**IMP3, "事件": "9月求人倍率", "链接": "https://wallstreetcn.com/calendar/JP3b/overview"}
    refresh(paths, fake_fetch({"20261103": [MIDTERM, IMP3, imp3b]}), min_importance=3)
    a_id, b_id = "wscn-20261103-JP3", "wscn-20261103-JP3b"
    set_mark(paths, b_id, "x")
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM, IMP3, imp3b]}))
    left = items(paths)
    assert a_id not in left
    assert left[b_id].mark == "x"
    assert res["below_threshold"] == 1
    assert ei.load_ledger(paths["ledger_path"])["decisions"] == []


def test_per_date_failure_is_counted_not_fatal(paths):
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM]}, fail={"20261020"}))
    assert res["new"] == 1
    assert res["fetch_errors"] == 1
    assert res["errors"][0]["date"] == "20261020"
    assert res["empty_days"] == 29        # 31 dates - 1 with data - 1 failed


def test_round_trip_preserves_owner_marks_and_edits(paths):
    fetch = fake_fetch({"20261103": [MIDTERM, KR_CPI]})
    refresh(paths, fetch)
    set_mark(paths, MID_ID, "x", **{"impact: high": "impact: low",
                                    "  note:": "  note: 关税休战 11-10 到期"})
    set_mark(paths, "wscn-20261103-KR2608052", "-")
    before = items(paths)
    refresh(paths, fetch)                 # same candidates come back
    after = items(paths)
    assert after == before
    assert after[MID_ID].mark == "x" and after[MID_ID].impact == "low"
    assert after[MID_ID].note == "关税休战 11-10 到期"
    assert after["wscn-20261103-KR2608052"].mark == "-"


def test_render_parse_round_trip_is_exact(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    its = list(items(paths).values())
    assert ei.parse_inbox(ei.render_inbox(its, TODAY))[0] == its


def test_new_candidates_appended_without_touching_existing(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    set_mark(paths, MID_ID, "x")
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    assert res["new"] == 1 and res["already_listed"] == 1
    assert items(paths)[MID_ID].mark == "x"


def test_dedupe_by_inbox_id(paths):
    ev = ei.candidate_from_row(MIDTERM).to_event()
    paths["events_path"].write_text(json.dumps({"events": [ev]}), encoding="utf-8")
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    assert res["new"] == 0 and res["dup_id"] == 1


def test_fuzzy_dedupe_against_hand_written_entry(paths):
    """Hand entry: different wording, impact date one day off — still a dup."""
    hand = {"date": "2026-11-02", "tz": "US", "name": "美国中期选举（国会）",
            "kind": "political", "impact": "high"}
    paths["events_path"].write_text(json.dumps({"events": [hand]}, ensure_ascii=False),
                                    encoding="utf-8")
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    assert res["new"] == 0 and res["dup_fuzzy"] == 1


def test_fuzzy_needs_both_date_and_name(paths):
    far = {"date": "2026-11-20", "tz": "US", "name": "美国中期选举"}
    other = {"date": "2026-11-03", "tz": "US", "name": "非农就业"}
    paths["events_path"].write_text(json.dumps({"events": [far, other]},
                                               ensure_ascii=False), encoding="utf-8")
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    assert res["new"] == 1


def test_fuzzy_requires_same_tz(paths):
    """Real false positive from the first live refresh: 中国9月CPI was dropped
    as a duplicate of the hand-written 美国9月CPI — region stripped, "CPI" left."""
    us = {"date": "2026-10-13", "tz": "US", "name": "美国9月CPI公布（日期待BLS确认）"}
    paths["events_path"].write_text(json.dumps({"events": [us]}, ensure_ascii=False),
                                    encoding="utf-8")
    cn = {**KR_CPI, "时间": "2026-10-14 09:30:00", "地区": "中国", "事件": "中国9月CPI同比",
          "链接": ""}
    us_row = {**cn, "时间": "2026-10-14 20:30:00", "地区": "美国", "事件": "美国9月CPI同比"}
    res = refresh(paths, fake_fetch({"20261014": [cn, us_row]}))
    assert res["new"] == 1 and res["dup_fuzzy"] == 1
    assert [i.name for i in items(paths).values()] == ["中国9月CPI同比"]


def test_ledger_prevents_return(paths):
    fetch = fake_fetch({"20261103": [MIDTERM, KR_CPI]})
    refresh(paths, fetch)
    set_mark(paths, "wscn-20261103-KR2608052", "-")
    ei.promote(TODAY, **paths)
    res = refresh(paths, fetch)
    assert res["decided"] == 1
    assert "wscn-20261103-KR2608052" not in items(paths)


def test_past_items_dropped_and_recorded_expired(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    later = date(2026, 11, 5)
    res = refresh(paths, fake_fetch(), today=later)
    assert res["expired"] == 1 and items(paths) == {}
    led = json.loads(paths["ledger_path"].read_text(encoding="utf-8"))
    assert led["decisions"][0]["decision"] == "expired"


def test_past_candidates_from_source_are_not_added(paths):
    """A row whose impact date is already behind us never enters the inbox,
    even if the source hands it back for a future query date."""
    stale = {**KR_CPI, "时间": "2026-10-01 09:30:00"}
    res = refresh(paths, fake_fetch({"20261103": [stale, MIDTERM]}))
    assert res["past"] == 1 and res["new"] == 1


def test_us_listing_impacting_today_is_not_past(paths):
    """Tue 02:00 Beijing = Mon US → impact Tue = today: still actionable."""
    row = {**MIDTERM, "时间": "2026-10-13 02:00:00", "事件": "美国数据"}
    res = ei.refresh(date(2026, 10, 13), fetch_fn=fake_fetch({"20261013": [row]}),
                     days=0, **paths)
    assert res["new"] == 1 and res["past"] == 0


def test_block_without_id_is_dropped_with_warning():
    its, warns = ei.parse_inbox("## 2026-11-04 (T-1) 美国 — 手写\n- [x] keep\n")
    assert its == [] and "without an `id:`" in warns[0]


# ── promote ──────────────────────────────────────────────────────────────────

def test_promote_writes_schema_and_calendar_shows_impact_date(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    set_mark(paths, MID_ID, "x", **{"kind: other": "kind: political"})
    res = ei.promote(TODAY, **paths)
    assert (res["promoted"], res["pending"]) == (1, 1)

    doc = json.loads(paths["events_path"].read_text(encoding="utf-8"))
    ev = doc["events"][-1]
    assert set(ev) == {"date", "tz", "name", "kind", "certainty", "impact",
                       "direction", "notes", "source", "inbox_id"}
    assert ev["inbox_id"] == MID_ID and ev["kind"] == "political"
    assert ev["source"] == "华尔街见闻财经日历 imp=4"     # no link on this row
    assert doc["note"] == "n" and doc["updated"] == "2026-10-12"

    up = ec.upcoming(days=30, today=TODAY, path=paths["events_path"])
    mine = [e for e in up["dated"] if e["name"] == "美国 11 月 3 日中期选举"]
    assert mine and mine[0]["a_share_impact_date"] == "2026-11-04"
    assert mine[0]["direction"] == "two_sided"

    assert MID_ID not in items(paths)
    led = json.loads(paths["ledger_path"].read_text(encoding="utf-8"))
    assert [(d["inbox_id"], d["decision"]) for d in led["decisions"]] == [(MID_ID, "keep")]


def test_promote_uses_link_as_source(paths):
    refresh(paths, fake_fetch({"20261103": [KR_CPI]}))
    set_mark(paths, "wscn-20261103-KR2608052", "x")
    ei.promote(TODAY, **paths)
    ev = json.loads(paths["events_path"].read_text(encoding="utf-8"))["events"][0]
    assert ev["source"] == KR_CPI["链接"]


def test_invalid_edit_is_refused_and_stays_in_inbox(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    set_mark(paths, MID_ID, "x", **{"direction: two_sided": "direction: bearish"})
    res = ei.promote(TODAY, **paths)
    assert res["promoted"] == 0 and "direction 'bearish'" in res["invalid"][0]["problems"][0]
    assert items(paths)[MID_ID].mark == "x"
    assert json.loads(paths["events_path"].read_text(encoding="utf-8"))["events"] == []


def test_hyphenated_direction_is_accepted(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    set_mark(paths, MID_ID, "x", **{"direction: two_sided": "direction: two-sided"})
    assert ei.promote(TODAY, **paths)["promoted"] == 1


def test_owner_date_tz_correction_is_honoured(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    set_mark(paths, MID_ID, "x", **{"date: 2026-11-03   tz: US":
                                    "date: 2026-11-05   tz: CN"})
    ei.promote(TODAY, **paths)
    up = ec.upcoming(days=30, today=TODAY, path=paths["events_path"])
    assert [e["a_share_impact_date"] for e in up["dated"]
            if e["name"].endswith("中期选举")] == ["2026-11-05"]


def test_promote_is_idempotent_on_inbox_id(paths):
    """Crash after the events write but before the inbox write → rerun is safe."""
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    set_mark(paths, MID_ID, "x")
    saved = paths["inbox_path"].read_text(encoding="utf-8")
    ei.promote(TODAY, **paths)
    paths["inbox_path"].write_text(saved, encoding="utf-8")   # simulate the crash
    ei.promote(TODAY, **paths)
    evs = json.loads(paths["events_path"].read_text(encoding="utf-8"))["events"]
    assert len(evs) == 1


def test_promote_refuses_to_overwrite_unreadable_events(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    set_mark(paths, MID_ID, "x")
    paths["events_path"].write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        ei.promote(TODAY, **paths)
    assert paths["events_path"].read_text(encoding="utf-8") == "{not json"


# ── pipeline step + status ───────────────────────────────────────────────────

def test_pipeline_step_promotes_before_refresh_and_never_raises(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    set_mark(paths, MID_ID, "x")
    rec = ei.pipeline_step(TODAY, fetch_fn=fake_fetch({"20261103": [MIDTERM, KR_CPI]}),
                           triage_fn=fake_ai({}), **paths)
    assert rec["promote"]["promoted"] == 1
    assert rec["refresh"]["new"] == 0 and rec["refresh"]["decided"] == 1
    assert [p["id"] for p in rec["pending_items"]] == ["wscn-20261103-KR2608052"]
    assert ei.summary_line(rec).startswith("[event-inbox] new 0, pending 1, promoted 1")


def test_pipeline_step_records_failure_instead_of_raising(paths):
    paths["events_path"].write_text("{not json", encoding="utf-8")
    rec = ei.pipeline_step(TODAY, fetch_fn=fake_fetch(), triage_fn=fake_ai({}), **paths)
    assert any(e.startswith("refresh:") for e in rec["step_errors"])
    assert "FAILED" in ei.summary_line(rec)


def test_status_lists_due_soon(paths):
    soon = {**KR_CPI, "时间": "2026-10-15 09:30:00"}
    refresh(paths, fake_fetch({"20261015": [soon], "20261103": [MIDTERM]}))
    st = ei.status(TODAY, paths["inbox_path"], paths["ledger_path"])
    assert st["pending"] == 2
    assert [p["a_share_impact_date"] for p in st["due_soon"]] == ["2026-10-15"]


@pytest.mark.integration
def test_real_wallstreetcn_returns_expected_columns():
    df = ei._akshare_fetch("20261103")
    assert {"时间", "地区", "事件", "重要性", "链接"} <= set(df.columns)


# ── AI triage ────────────────────────────────────────────────────────────────

def test_triage_applies_keep_to_events_and_records_both_in_ledger(ai_decided):
    paths = ai_decided
    [ev] = events(paths)
    assert ev["inbox_id"] == MID_ID and ev["impact"] == "high"
    assert ev["decided_by"] == "ai" and ev["reason"] == "美国中期选举决定国会控制权"
    led = {d["inbox_id"]: d for d in ledger(paths)}
    assert led[MID_ID]["decided_by"] == "ai" and led[MID_ID]["model"] == "fake-model"
    assert led[KR_ID]["decision"] == "skip" and led[KR_ID]["reason"] == "韩国数据非系统性"
    assert all(d["decided"] == "2026-10-12" for d in led.values())


def test_ai_items_stay_in_inbox_with_robot_and_ai_line(ai_decided):
    its = items(ai_decided)
    assert (its[MID_ID].mark, its[KR_ID].mark) == ("x", "-")
    assert its[KR_ID].impact == "low"
    text = ai_decided["inbox_path"].read_text(encoding="utf-8")
    assert "- [x] keep 🤖   impact: high" in text
    assert "  ai: 保留 · high/two_sided · 美国中期选举决定国会控制权（fake-model，2026-10-12）" in text
    assert "待定 0 条" in text
    assert ei.pending_items(TODAY, ai_decided["inbox_path"]) == []


def test_ai_items_survive_promote_and_refresh_untouched(ai_decided):
    before = ai_decided["inbox_path"].read_text(encoding="utf-8")
    res = ei.promote(TODAY, **ai_decided)
    assert (res["promoted"], res["skipped"], res["overrides"]) == (0, 0, 0)
    refresh(ai_decided, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    assert ai_decided["inbox_path"].read_text(encoding="utf-8") == before
    assert len(events(ai_decided)) == 1


def test_render_parse_round_trip_with_ai_line(ai_decided):
    its = list(items(ai_decided).values())
    assert ei.parse_inbox(ei.render_inbox(its, TODAY))[0] == its


def test_triage_runs_once_per_item(ai_decided):
    calls = []
    rec = ei.triage(TODAY, **ai_decided, triage_fn=fake_ai({}, calls))
    assert rec["attempted"] == 0 and calls == []


def test_invalid_unknown_and_missing_outputs_stay_undecided_and_retry(paths):
    third = {**KR_CPI, "事件": "10月出口", "链接": "https://wallstreetcn.com/calendar/KR3/overview"}
    refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI, third]}))
    rec = ei.triage(TODAY, **paths, triage_fn=fake_ai({
        MID_ID: judge("keep", direction="bearish"),
        "wscn-20990101-nope": judge("keep"),
        "wscn-20261103-KR3": judge("skip", impact="low")}))
    assert rec["skipped"] == 1 and rec["kept"] == 0
    assert [x["id"] for x in rec["invalid"]] == [MID_ID]
    assert "direction 'bearish'" in rec["invalid"][0]["problem"]
    assert rec["missing"] == [KR_ID] and rec["unknown_ids"] == 1
    assert ei.triage_errors(rec) == 2
    assert {i.id: i.mark for i in items(paths).values()} == {
        MID_ID: " ", KR_ID: " ", "wscn-20261103-KR3": "-"}
    assert events(paths) == []

    calls = []
    rec2 = ei.triage(TODAY, **paths, triage_fn=fake_ai({}, calls))
    assert rec2["attempted"] == 2
    assert MID_ID in calls[0] and KR_ID in calls[0] and "KR3" not in calls[0]


@pytest.mark.parametrize("bad", [
    {"decision": "maybe", "impact": "high", "direction": "risk", "reason": "r"},
    {"decision": "keep", "impact": "huge", "direction": "risk", "reason": "r"},
    {"decision": "keep", "impact": "high", "direction": "risk", "reason": " "},
    {"decision": "keep", "impact": "high", "direction": "risk"},
    "keep",
])
def test_each_malformed_judgement_is_a_triage_error(paths, bad):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    rec = ei.triage(TODAY, **paths, triage_fn=fake_ai({MID_ID: bad}))
    assert len(rec["invalid"]) == 1 and items(paths)[MID_ID].mark == " "


def test_llm_exception_leaves_items_undecided_and_run_continues(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    before = paths["inbox_path"].read_text(encoding="utf-8")

    def boom(prompt):
        raise ConnectionError("relay down")
    rec = ei.pipeline_step(TODAY, fetch_fn=fake_fetch({"20261103": [MIDTERM]}),
                           triage_fn=boom, **paths)
    assert rec["step_errors"] == []
    assert rec["triage"]["error"] == "ConnectionError: relay down"
    assert [p["id"] for p in rec["pending_items"]] == [MID_ID]
    assert paths["inbox_path"].read_text(encoding="utf-8") == before
    line = ei.summary_line(rec)
    assert "ai kept 0/skipped 0/errors 1" in line and "AI TRIAGE FAILED: ConnectionError" in line


def test_a_call_past_the_deadline_is_a_triage_error(paths):
    """The client's own timeout does not bound a reasoning call (D19)."""
    import threading
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    release = threading.Event()

    def slow(prompt):
        release.wait(5)
        return "{}", {}
    try:
        rec = ei.triage(TODAY, **paths, triage_fn=slow, deadline_sec=0.05)
    finally:
        release.set()
    assert "exceeded" in rec["error"] and items(paths)[MID_ID].mark == " "


def test_unparseable_reply_is_a_triage_error(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    rec = ei.triage(TODAY, **paths, triage_fn=lambda p: ("sorry, no JSON", {"model": "m"}))
    assert "no `decisions` object" in rec["error"] and items(paths)[MID_ID].mark == " "


def test_owner_mark_set_before_ai_ran_wins(paths):
    refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI]}))
    set_mark(paths, MID_ID, "x", **{"impact: high": "impact: low"})
    calls = []
    rec = ei.pipeline_step(TODAY, fetch_fn=fake_fetch({"20261103": [MIDTERM, KR_CPI]}),
                           triage_fn=fake_ai({MID_ID: judge("skip"), KR_ID: judge("skip")},
                                             calls), **paths)
    assert rec["promote"]["promoted"] == 1
    assert MID_ID not in calls[0] and KR_ID in calls[0]
    assert rec["triage"]["unknown_ids"] == 1     # the AI answered for it anyway: ignored
    [ev] = events(paths)
    assert ev["impact"] == "low" and "decided_by" not in ev
    assert [d["decided_by"] for d in ledger(paths) if d["inbox_id"] == MID_ID] == ["owner"]


def test_flip_ai_keep_to_skip_removes_the_event(ai_decided):
    flip(ai_decided, MID_ID, "- [x] keep", "- [-] keep")
    res = ei.promote(TODAY, **ai_decided)
    assert (res["skipped"], res["overrides"]) == (1, 1)
    assert events(ai_decided) == []
    last = ledger(ai_decided)[-1]
    assert (last["inbox_id"], last["decision"], last["decided_by"], last["overrode_ai"]) \
        == (MID_ID, "skip", "owner", "keep")
    assert MID_ID not in items(ai_decided)          # owner-decided: leaves the inbox


def test_flip_ai_skip_to_keep_promotes(ai_decided):
    flip(ai_decided, KR_ID, "- [-] keep", "- [x] keep")
    res = ei.promote(TODAY, **ai_decided)
    assert (res["promoted"], res["overrides"]) == (1, 1)
    ev = [e for e in events(ai_decided) if e["inbox_id"] == KR_ID][0]
    assert ev["impact"] == "low" and "decided_by" not in ev
    assert ledger(ai_decided)[-1]["overrode_ai"] == "skip"


def test_edit_impact_on_ai_keep_updates_the_entry(ai_decided):
    flip(ai_decided, MID_ID, "impact: high", "impact: medium")
    res = ei.promote(TODAY, **ai_decided)
    assert (res["promoted"], res["overrides"]) == (1, 1)
    [ev] = events(ai_decided)
    assert ev["inbox_id"] == MID_ID and ev["impact"] == "medium"
    assert "decided_by" not in ev and "reason" not in ev
    assert MID_ID not in items(ai_decided)


def test_removing_the_robot_is_not_an_override(ai_decided):
    flip(ai_decided, MID_ID, "keep 🤖", "keep")
    assert ei.promote(TODAY, **ai_decided)["overrides"] == 0
    assert events(ai_decided)[0]["decided_by"] == "ai"


def test_unticking_an_ai_keep_reopens_it_for_the_owner(ai_decided):
    flip(ai_decided, MID_ID, "- [x] keep", "- [ ] keep")
    res = ei.promote(TODAY, **ai_decided)
    assert (res["reopened"], res["overrides"]) == (1, 1)
    assert events(ai_decided) == []
    it = items(ai_decided)[MID_ID]
    assert it.mark == " " and it.ai == ""
    assert [p["id"] for p in ei.pending_items(TODAY, ai_decided["inbox_path"])] == [MID_ID]
    assert ei.triage(TODAY, **ai_decided, triage_fn=fake_ai({}))["attempted"] == 0
    set_mark(ai_decided, MID_ID, "x")          # owner decides later: plain promote
    assert ei.promote(TODAY, **ai_decided)["promoted"] == 1


def test_invalid_owner_edit_of_ai_keep_leaves_ai_entry_in_place(ai_decided):
    flip(ai_decided, MID_ID, "direction: two_sided", "direction: bearish")
    res = ei.promote(TODAY, **ai_decided)
    assert res["invalid"] and res["overrides"] == 0
    assert events(ai_decided)[0]["decided_by"] == "ai"


def test_ai_item_leaves_inbox_after_its_impact_date(ai_decided):
    n = len(ledger(ai_decided))
    res = refresh(ai_decided, fake_fetch({"20261103": [MIDTERM, KR_CPI]}),
                  today=date(2026, 11, 5))
    assert res["ai_retired"] == 2 and res["new"] == 0
    assert items(ai_decided) == {}
    assert len(ledger(ai_decided)) == n          # no expiry record: it was decided
    assert len(events(ai_decided)) == 1


def test_prompt_carries_spec_today_calendar_and_candidates(paths):
    hand = {"date": "2026-11-10", "tz": "CN", "name": "中美关税休战到期",
            "certainty": "scheduled", "impact": "high"}
    paths["events_path"].write_text(json.dumps({"events": [hand]}, ensure_ascii=False),
                                    encoding="utf-8")
    refresh(paths, fake_fetch({"20261103": [MIDTERM]}))
    calls = []
    ei.triage(TODAY, **paths, triage_fn=fake_ai({}, calls))
    prompt = calls[0]
    assert prompt.startswith("# 🗓️ 事件分拣员")
    assert "2026-10-12 (星期一)" in prompt
    assert "- 2026-11-10 · 中美关税休战到期 · high" in prompt
    assert "美国非农就业(NFP)" in prompt          # formulaic events count as on-calendar
    assert f"| {MID_ID} | 2026-11-04 | 美国 | 美国 11 月 3 日中期选举 | 4 | 2026-11-03 00:00 |" \
        in prompt


def test_triage_caps_items_per_call(paths):
    rows = [{**KR_CPI, "事件": f"数据{n}", "链接": f"https://wallstreetcn.com/calendar/K{n}/x"}
            for n in range(5)]
    refresh(paths, fake_fetch({"20261103": rows}))
    rec = ei.triage(TODAY, **paths, triage_fn=fake_ai({}), max_items=3)
    assert rec["attempted"] == 3


def test_summary_line_reports_ai_counts_and_overrides(ai_decided):
    flip(ai_decided, MID_ID, "- [x] keep", "- [-] keep")
    rec = ei.pipeline_step(TODAY, fetch_fn=fake_fetch({"20261103": [MIDTERM, KR_CPI]}),
                           triage_fn=fake_ai({}), **ai_decided)
    assert "ai kept 0/skipped 0/errors 0, overrides 1" in ei.summary_line(rec)


# ── event_triage.call_model: provider plumbing (fake clients, no network) ────

class _FakeOpenAI:
    def __init__(self, text, finish="stop"):
        self.kw = None
        msg = type("M", (), {"content": text})()
        choice = type("C", (), {"message": msg, "finish_reason": finish})()
        usage = type("U", (), {"prompt_tokens": 7, "completion_tokens": 3})()
        resp = type("R", (), {"choices": [choice], "usage": usage})()
        outer = self

        class _Completions:
            def create(self, **kw):
                outer.kw = kw
                return resp
        self.chat = type("Chat", (), {"completions": _Completions()})()


@pytest.fixture
def real_call_model(monkeypatch):
    monkeypatch.undo()                     # lift the autouse refusal for this test
    monkeypatch.setattr(llm_client, "normalize_llm_provider", lambda p=None: "openai")
    monkeypatch.setattr(llm_client, "OPENAI_MODEL", "deepseek-test")
    return monkeypatch


def test_call_model_uses_the_pipeline_openai_model_without_tools(real_call_model):
    fake = _FakeOpenAI('{"decisions": {}}')
    real_call_model.setattr(llm_client, "_build_openai_client", lambda: fake)
    text, meta = et.call_model("PROMPT")
    assert text == '{"decisions": {}}'
    assert meta == {"provider": "openai", "model": "deepseek-test",
                    "tokens_in": 7, "tokens_out": 3}
    assert fake.kw["model"] == "deepseek-test" and "tools" not in fake.kw
    assert fake.kw["messages"] == [{"role": "user", "content": "PROMPT"}]


def test_call_model_refuses_a_truncated_reply(real_call_model):
    real_call_model.setattr(llm_client, "_build_openai_client",
                            lambda: _FakeOpenAI('{"decisions": {', finish="length"))
    with pytest.raises(RuntimeError, match="truncated"):
        et.call_model("PROMPT")


def test_status_reports_ai_stats_and_override_rate(ai_decided):
    flip(ai_decided, KR_ID, "- [-] keep", "- [x] keep")
    ei.promote(TODAY, **ai_decided)
    a = ei.status(TODAY, ai_decided["inbox_path"], ai_decided["ledger_path"])["ai"]
    assert (a["kept"], a["skipped"], a["kept_high"]) == (1, 1, 1)
    assert a["overrides"] == 1 and a["overrides_by_ai_decision"] == {"keep": 0, "skip": 1}
    assert a["override_rate"] == 0.5 and a["flippable_in_inbox"] == 1


def test_status_cli_prints_ai_line(ai_decided, monkeypatch, capsys):
    # status()'s path defaults are bound at def time; point them at tmp
    monkeypatch.setattr(ei.status, "__defaults__",
                        (None, ai_decided["inbox_path"], ai_decided["ledger_path"]))
    assert ei.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "ai: kept 1 (impact=high 1), skipped 1, owner overrides 0 (rate 0%" in out

