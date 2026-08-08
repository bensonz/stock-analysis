"""event_calendar — foreseeable-event risk window. Offline; no DB, no network."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import event_calendar as ec


def _write(tmp_path, events):
    p = tmp_path / "events.json"
    p.write_text(json.dumps({"events": events}, ensure_ascii=False), encoding="utf-8")
    return p


def test_us_event_impacts_next_a_share_session():
    # FOMC decision Wed 2026-09-16 (US) -> announced Beijing Thu 2:00 -> hits 9/17
    assert ec.a_share_impact_date(date(2026, 9, 16), "US") == date(2026, 9, 17)
    # US Friday event -> next session is Monday
    assert ec.a_share_impact_date(date(2026, 9, 11), "US") == date(2026, 9, 14)
    # CN-dated deadline lands same day (if a weekday)
    assert ec.a_share_impact_date(date(2026, 11, 10), "CN") == date(2026, 11, 10)


def test_formulaic_opex_dates():
    evs = ec.formulaic_events(date(2026, 8, 1), date(2026, 8, 31))
    by_name = {e["name"]: e["date"] for e in evs}
    assert by_name["美股月度OpEx（期权到期，GEX集中兑现）"] == "2026-08-21"  # 3rd Fri
    assert by_name["A股ETF期权到期日（第4周三）"] == "2026-08-26"            # 4th Wed
    assert by_name["CFFEX股指期货/期权交割日（第3周五）"] == "2026-08-21"    # 3rd Fri (CN)
    # measured-base-rate discipline: every opex note must cite the rerunnable study
    for e in evs:
        if e["kind"] == "opex":
            assert "index_event_study" in e["notes"]


def test_formulaic_recurring_cn_and_us_events():
    evs = ec.formulaic_events(date(2026, 8, 1), date(2026, 10, 12))
    by = {}
    for e in evs:
        by.setdefault(e["name"], []).append(e["date"])
    assert "2026-08-31" in by["官方制造业PMI（9:30，当日盘中）"]     # last cal day
    assert "2026-09-01" in by["财新制造业PMI（9:45，当日盘中）"]     # 1st biz day
    assert "2026-09-21" in by["LPR报价"]                            # 20th=Sun → Mon
    assert "2026-09-04" in by["美国非农就业(NFP)"]                   # 1st Friday
    assert by["中报披露截止"] == ["2026-08-31"]
    assert by["国庆长假后首个交易日"] == ["2026-10-09"]              # Fri, no roll
    # NFP is US-timed: Friday release impacts the next Monday session
    nfp = [e for e in evs if e["name"] == "美国非农就业(NFP)"][0]
    assert ec.a_share_impact_date(date(2026, 9, 4), nfp["tz"]) == date(2026, 9, 7)


def test_supportive_events_never_escalate_risk(tmp_path):
    sup = {"date": "2026-08-03", "tz": "CN", "name": "政策利好窗口",
           "kind": "policy_meeting", "certainty": "scheduled",
           "impact": "high", "direction": "supportive"}
    ongoing_sup = {"date": None, "name": "宽松定调窗口", "kind": "policy_meeting",
                   "certainty": "ongoing", "impact": "high",
                   "direction": "supportive"}
    rw = ec.risk_window(today=date(2026, 8, 3),
                        path=_write(tmp_path, [sup, ongoing_sup]))
    assert rw["level"] == "normal"              # supportive high-impact ≠ caution
    up = ec.upcoming(days=7, today=date(2026, 8, 3),
                     path=_write(tmp_path, [sup, ongoing_sup]))
    assert up["dated"][0]["direction"] == "supportive"   # but it IS surfaced
    assert up["ongoing"][0]["direction"] == "supportive"


def test_report_md_renders_event_window(tmp_path):
    import report_generator
    data = {"market": {}, "events": {
        "dated": [{"a_share_impact_date": "2026-09-17", "days_until_impact": 2,
                   "impact": "high", "direction": "risk", "certainty": "scheduled",
                   "name": "FOMC利率决议", "notes": "点阵图"}],
        "ongoing": [{"impact": "medium", "direction": "supportive",
                     "name": "政策宽松窗口", "notes": "小盘占优"}],
        "risk_window": {"level": "event_imminent", "advice": "新开仓减半"},
        "fomc_next_session_stats": {"n": 12, "sessions_negative": 9,
                                    "mean_ew_ret_pct": -0.45, "note": "小样本"},
    }}
    out = report_generator.generate_report_md("2026-08-01", data, {}, output_dir=tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "## 未来事件窗口" in text
    assert "event_imminent" in text and "新开仓减半" in text
    assert "🔴 **2026-09-17**" in text and "FOMC利率决议" in text
    assert "🟢 **持续中**" in text and "政策宽松窗口" in text
    assert "9次收跌" in text


def test_upcoming_window_and_ordering(tmp_path):
    p = _write(tmp_path, [
        {"date": "2026-08-12", "tz": "US", "name": "CPI", "kind": "macro_release",
         "certainty": "scheduled", "impact": "medium"},
        {"date": "2026-10-28", "tz": "US", "name": "FOMC", "kind": "cb_decision",
         "certainty": "scheduled", "impact": "high"},          # outside 21d window
        {"date": None, "name": "Hormuz", "kind": "geopolitical",
         "certainty": "ongoing", "impact": "high"},
    ])
    up = ec.upcoming(days=21, today=date(2026, 7, 31), path=p)
    names = [e["name"] for e in up["dated"]]
    assert "CPI" in names and "FOMC" not in names
    cpi = up["dated"][names.index("CPI")]
    assert cpi["a_share_impact_date"] == "2026-08-13"
    assert cpi["days_until_impact"] == 13
    assert [o["name"] for o in up["ongoing"]] == ["Hormuz"]


def test_risk_window_levels(tmp_path):
    fomc = {"date": "2026-09-16", "tz": "US", "name": "FOMC",
            "kind": "cb_decision", "certainty": "scheduled", "impact": "high"}
    hormuz = {"date": None, "name": "Hormuz", "kind": "geopolitical",
              "certainty": "ongoing", "impact": "high"}

    # decision impact 9/17; on 9/15 it is 2 days out -> event_imminent
    rw = ec.risk_window(today=date(2026, 9, 15), path=_write(tmp_path, [fomc]))
    assert rw["level"] == "event_imminent"
    assert rw["imminent"][0]["a_share_impact_date"] == "2026-09-17"

    # far from any dated event but an ongoing high-impact crisis -> elevated
    rw2 = ec.risk_window(today=date(2026, 8, 3),
                         path=_write(tmp_path, [fomc, hormuz]))
    assert rw2["level"] == "elevated"

    # nothing at all -> normal
    rw3 = ec.risk_window(today=date(2026, 8, 3), path=_write(tmp_path, []))
    assert rw3["level"] == "normal"


def test_malformed_calendar_degrades_to_empty(tmp_path):
    p = tmp_path / "events.json"
    p.write_text("{not json", encoding="utf-8")
    up = ec.upcoming(days=7, today=date(2026, 7, 31), path=p)
    assert up["ongoing"] == []
    # only formulaic (derived) events remain — none from the broken file
    assert up["dated"] and all(e["certainty"] == "scheduled" for e in up["dated"])


def test_prompt_section_renders_events():
    import llm_client
    phase1 = {
        "events": {
            "dated": [{"a_share_impact_date": "2026-09-17", "days_until_impact": 2,
                       "impact": "high", "name": "FOMC利率决议", "notes": "点阵图"}],
            "ongoing": [{"impact": "high", "name": "霍尔木兹海峡危机", "notes": "断航"}],
            "risk_window": {"level": "event_imminent", "advice": "新开仓减半"},
            "fomc_next_session_stats": {"n": 12, "sessions_negative": 9,
                                        "mean_ew_ret_pct": -0.45, "note": "小样本"},
        },
    }
    text = llm_client.build_summary(phase1)
    assert "未来事件窗口" in text
    assert "FOMC利率决议" in text and "霍尔木兹海峡危机" in text
    assert "event_imminent" in text and "新开仓减半" in text
    assert "9 次收跌" in text


def test_released_event_stays_until_impact_date(tmp_path):
    # 2026-08-08: NFP released Fri 8/7 evening vanished from Saturday's report
    # although its A-share impact day was Monday 8/10. A dated event must stay
    # until IMPACT passes, flagged released once its own date is behind us.
    nfp = {"date": "2026-08-07", "tz": "US", "name": "NFP",
           "kind": "macro_release", "certainty": "scheduled", "impact": "medium"}
    p = _write(tmp_path, [nfp])
    # Saturday: released, impact Monday still ahead → stays in dated
    up = ec.upcoming(days=21, today=date(2026, 8, 8), path=p)
    names = [e["name"] for e in up["dated"]]
    assert "NFP" in names
    e = up["dated"][names.index("NFP")]
    assert e["released"] is True
    assert e["a_share_impact_date"] == "2026-08-10"
    # before release: present, NOT flagged
    up0 = ec.upcoming(days=21, today=date(2026, 8, 6), path=p)
    e0 = next(x for x in up0["dated"] if x["name"] == "NFP")
    assert "released" not in e0
    # after the impact day passes: moves to recent (result bucket)
    up2 = ec.upcoming(days=21, today=date(2026, 8, 11), path=p)
    assert "NFP" not in [e["name"] for e in up2["dated"]]
    assert "NFP" in [e["name"] for e in up2["recent"]]
    # beyond the look-back: forgotten entirely (formulaic events may still
    # populate the window — only NFP must be gone)
    up3 = ec.upcoming(days=21, today=date(2026, 8, 20), path=p)
    assert "NFP" not in [e["name"] for e in up3["recent"] + up3["dated"]]
