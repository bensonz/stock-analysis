"""event_inbox — wallstreetcn candidates → owner checklist → events.json.

Offline: the fetch is injected (fake DataFrames), every path is a tmp file.
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

TODAY = date(2026, 10, 12)   # Monday

MIDTERM = {"时间": "2026-11-03 00:00:00", "地区": "美国", "事件": "美国 11 月 3 日中期选举",
           "重要性": 4, "今值": float("nan"), "预期": float("nan"), "前值": float("nan"),
           "链接": ""}
KR_CPI = {"时间": "2026-11-03 07:00:00", "地区": "韩国", "事件": "10月CPI同比",
          "重要性": 3, "今值": float("nan"), "预期": float("nan"), "前值": 2.9,
          "链接": "https://wallstreetcn.com/calendar/KR2608052/overview"}
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


@pytest.fixture
def paths(tmp_path):
    events = tmp_path / "events.json"
    events.write_text(json.dumps({"note": "n", "events": []}, ensure_ascii=False),
                      encoding="utf-8")
    return {"inbox_path": tmp_path / "event_inbox.md",
            "ledger_path": tmp_path / "ledger.json",
            "events_path": events}


def refresh(paths, fetch, today=TODAY, days=30):
    return ei.refresh(today, fetch_fn=fetch, days=days, **paths)


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
    assert it.kind == "macro_release" and it.impact == "medium"


# ── refresh ──────────────────────────────────────────────────────────────────

def test_refresh_filters_importance_and_writes_inbox(paths):
    res = refresh(paths, fake_fetch({"20261103": [MIDTERM, KR_CPI, LOW]}))
    assert res["new"] == 2 and res["pending"] == 2
    text = paths["inbox_path"].read_text(encoding="utf-8")
    assert "## 2026-11-04 (T-23) 美国 — 美国 11 月 3 日中期选举" in text
    assert "不重要" not in text


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
                           **paths)
    assert rec["promote"]["promoted"] == 1
    assert rec["refresh"]["new"] == 0 and rec["refresh"]["decided"] == 1
    assert [p["id"] for p in rec["pending_items"]] == ["wscn-20261103-KR2608052"]
    assert ei.summary_line(rec).startswith("[event-inbox] new 0, pending 1, promoted 1")


def test_pipeline_step_records_failure_instead_of_raising(paths):
    paths["events_path"].write_text("{not json", encoding="utf-8")
    rec = ei.pipeline_step(TODAY, fetch_fn=fake_fetch(), **paths)
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
