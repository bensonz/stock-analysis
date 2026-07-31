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
    dates = {e["name"][:2]: e["date"] for e in evs}
    assert dates["美股"] == "2026-08-21"        # 3rd Friday
    assert dates["A股"] == "2026-08-26"         # 4th Wednesday


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
    assert all(e["kind"] == "opex" for e in up["dated"])   # formulaic still works


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
