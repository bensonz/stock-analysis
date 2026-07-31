#!/usr/bin/env python3
"""
event_calendar.py — foreseeable-event risk window for the daily pipeline.

Motivation (2026-07 post-mortem): the July drawdown clustered around events
that were on PUBLIC calendars — Hormuz re-escalation week (7/7-7/10), the hot
June CPI print (7/14), and the FOMC decision the system bought straight into
(entries 7/29, decision Beijing-time 7/30 = the panic day). The pipeline had
no representation of "what is scheduled to happen next"; this module gives
it one.

Three layers, honest about what each knows:
  1. Curated calendar (tracking/events.json) — scheduled macro events,
     policy deadlines, ongoing crises. Hand-maintained; dates verified
     against primary sources when added.
  2. Formulaic events — US monthly OpEx (3rd Friday, GEX unwind) and
     A-share index-option expiry (4th Wednesday), derived, no maintenance.
  3. Measured base rates — for recurring event types with history inside
     our price DB (FOMC decisions), the realized next-session A-share stats.
     Small n; reported with n, never as a bare probability.

Timezone rule: a `tz: US` event lands in A-share terms on the FIRST trading
day strictly AFTER its US date (FOMC 2pm ET = 2:00 Beijing next morning;
CPI 8:30 ET = 20:30 Beijing same evening — both hit the next session).
Trading days approximated as weekdays (CN holidays not modeled — this is an
advisory risk window, not settlement logic).

Read-only everywhere; degrades to an empty payload on any failure.
"""
import json
import sys
from datetime import date as _date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE = PROJECT_ROOT / "tracking" / "events.json"

# FOMC decision days (2nd meeting day, US date), published Fed calendars.
# Used for the measured next-session base rate — extend as meetings occur.
FOMC_DECISION_DATES = [
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30",
    "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
]

IMPACT_ORDER = {"high": 2, "medium": 1, "low": 0}


def _parse(d: str) -> _date:
    return _date.fromisoformat(d)


def _next_weekday_after(d: _date) -> _date:
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def a_share_impact_date(event_date: _date, tz: str) -> _date:
    """First A-share session bearing the event's impact (see module doc)."""
    if tz == "US":
        return _next_weekday_after(event_date)
    return event_date if event_date.weekday() < 5 else _next_weekday_after(event_date)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> _date:
    d = _date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def formulaic_events(start: _date, end: _date) -> list:
    """US OpEx (3rd Friday) + A-share index-option expiry (4th Wednesday)."""
    out = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        for d, tz, name in (
            (_nth_weekday(y, m, 4, 3), "US",
             "美股月度OpEx（期权到期，GEX集中兑现）"),
            (_nth_weekday(y, m, 2, 4), "CN",
             "A股股指/ETF期权到期日"),
        ):
            if start <= d <= end:
                out.append({"date": d.isoformat(), "tz": tz, "name": name,
                            "kind": "opex", "certainty": "scheduled",
                            "impact": "low", "notes": "机械性波动放大窗口"})
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def load_events(path: Path | None = None) -> list:
    p = path or EVENTS_FILE
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("events", [])
    except Exception:
        return []


def upcoming(days: int = 21, today: _date | None = None,
             path: Path | None = None) -> dict:
    """Events in the window + ongoing situations, sorted by A-share impact date."""
    today = today or _date.today()
    horizon = today + timedelta(days=days)
    dated, ongoing = [], []
    for e in load_events(path) + formulaic_events(today, horizon):
        if e.get("certainty") == "ongoing" or not e.get("date"):
            ongoing.append({k: e.get(k) for k in
                            ("name", "kind", "impact", "notes")})
            continue
        try:
            d = _parse(e["date"])
        except (ValueError, TypeError):
            continue
        if not (today <= d <= horizon):
            continue
        impact_d = a_share_impact_date(d, e.get("tz", "CN"))
        dated.append({**{k: e.get(k) for k in
                         ("date", "tz", "name", "kind", "certainty",
                          "impact", "notes")},
                      "a_share_impact_date": impact_d.isoformat(),
                      "days_until_impact": (impact_d - today).days})
    dated.sort(key=lambda x: (x["a_share_impact_date"],
                              -IMPACT_ORDER.get(x["impact"], 0)))
    return {"as_of": today.isoformat(), "window_days": days,
            "dated": dated, "ongoing": ongoing}


def risk_window(today: _date | None = None, path: Path | None = None) -> dict:
    """Compressed advisory: is a high-impact scheduled event imminent?"""
    up = upcoming(days=10, today=today, path=path)
    imminent = [e for e in up["dated"]
                if e["impact"] == "high" and e["days_until_impact"] <= 3]
    ongoing_high = [e for e in up["ongoing"] if e.get("impact") == "high"]
    level = ("event_imminent" if imminent
             else "elevated" if ongoing_high else "normal")
    return {
        "level": level,
        "imminent": [{"name": e["name"],
                      "a_share_impact_date": e["a_share_impact_date"]}
                     for e in imminent],
        "ongoing_high_impact": [e["name"] for e in ongoing_high],
        "advice": {
            "event_imminent": "高冲击既定事件落地在即：新开仓减半或推迟至事件后一个交易日",
            "elevated": "存在持续性高冲击风险源：仓位与止损按谨慎档执行",
            "normal": "无临近高冲击既定事件",
        }[level],
    }


def fomc_next_session_stats(db_path: str | None = None) -> dict | None:
    """Measured base rate: A-share session following past FOMC decisions.

    Equal-weight mean return and up-ratio of the covered session bearing
    each decision's impact, from our own panel. n is small — the number is
    context, not a forecast.
    """
    try:
        import base_rates
        if db_path is None:
            import pricedb
            db_path = str(pricedb.DB_PATH)
        closes = base_rates.get_panel(db_path)["closes"]
        rets = closes.pct_change().mean(axis=1) * 100
        ups = (closes.pct_change() > 0).mean(axis=1) * 100
        rows = []
        for ds in FOMC_DECISION_DATES:
            target = a_share_impact_date(_parse(ds), "US").isoformat()
            sessions = [d for d in closes.index if d >= target]
            if not sessions:
                continue
            d = sessions[0]
            rows.append({"decision": ds, "session": d,
                         "ew_ret_pct": round(float(rets.loc[d]), 2),
                         "up_ratio_pct": round(float(ups.loc[d]), 1)})
        if not rows:
            return None
        neg = sum(1 for r in rows if r["ew_ret_pct"] < 0)
        return {
            "n": len(rows),
            "sessions_negative": neg,
            "mean_ew_ret_pct": round(sum(r["ew_ret_pct"] for r in rows) / len(rows), 2),
            "worst": min(rows, key=lambda r: r["ew_ret_pct"]),
            "note": f"样本仅{len(rows)}次（本地价格库范围），供参考不构成概率",
            "sessions": rows,
        }
    except Exception:
        return None


def phase1_payload(today: _date | None = None, db_path: str | None = None,
                   path: Path | None = None) -> dict:
    """Everything the daily pipeline attaches as the `events` artifact."""
    payload = upcoming(days=21, today=today, path=path)
    payload["risk_window"] = risk_window(today=today, path=path)
    stats = fomc_next_session_stats(db_path)
    if stats:
        payload["fomc_next_session_stats"] = {
            k: stats[k] for k in ("n", "sessions_negative", "mean_ew_ret_pct",
                                  "worst", "note")}
    return payload


if __name__ == "__main__":
    if "--human" in sys.argv:
        p = phase1_payload()
        rw = p["risk_window"]
        print(f"事件风险窗口 [{rw['level']}] — {rw['advice']}")
        for e in p["dated"]:
            print(f"  {e['a_share_impact_date']} (T-{e['days_until_impact']:>2}) "
                  f"[{e['impact']:>6}] {e['name']}")
        for e in p["ongoing"]:
            print(f"  ── 持续中 [{e['impact']:>6}] {e['name']}")
        st = p.get("fomc_next_session_stats")
        if st:
            print(f"  FOMC次日A股（n={st['n']}）: 平均EW {st['mean_ew_ret_pct']:+.2f}%, "
                  f"{st['sessions_negative']}/{st['n']}次收跌, "
                  f"最差 {st['worst']['session']} {st['worst']['ew_ret_pct']:+.2f}%")
    else:
        print(json.dumps(phase1_payload(), ensure_ascii=False, indent=1))
