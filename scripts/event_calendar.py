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


def _roll_to_weekday(d: _date) -> _date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _last_day_of_month(y: int, m: int) -> _date:
    nxt = _date(y + 1, 1, 1) if m == 12 else _date(y, m + 1, 1)
    return nxt - timedelta(days=1)


# Fixed-date recurring CN events: (month, day, name, impact, notes)
_CN_FIXED = [
    (4, 30, "年报+一季报披露截止", "medium", "业绩雷集中引爆窗口；持仓个股若临近披露需单独评估"),
    (8, 31, "中报披露截止", "medium", "业绩雷集中引爆窗口；持仓个股若临近披露需单独评估"),
    (10, 31, "三季报披露截止", "medium", "业绩雷集中引爆窗口；持仓个股若临近披露需单独评估"),
]


def formulaic_events(start: _date, end: _date) -> list:
    """Derived recurring events — zero maintenance.

    US OpEx (3rd Fri), A-share option expiry (4th Wed), NBS PMI (last
    calendar day, 9:30 → same session), Caixin PMI (1st business day),
    LPR fix (20th, rolled to business day), US NFP (1st Friday),
    A-share earnings-disclosure deadlines, Golden-Week reopening session.
    """
    out = []

    def _add(d: _date, tz: str, name: str, kind: str, impact: str, notes: str):
        if start <= d <= end:
            out.append({"date": d.isoformat(), "tz": tz, "name": name,
                        "kind": kind, "certainty": "scheduled",
                        "impact": impact, "direction": "two_sided"
                        if kind in ("macro_release", "cb_rate") else "risk",
                        "notes": notes,
                        "source": "公式推算(event_calendar.py:formulaic_events)"})

    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        # Expiry-day base rates measured 2026-08-04 (index_event_study.py
        # --expiry-study, 2022-08→2026-07, n=48/leg, 中证1000, 基线+0.03%/日):
        # US OpEx次日 -0.18% (噪声内), ETF到期日 -0.01% (≈基线),
        # CFFEX交割日 -0.33% (~1.5se, 偏弱不显著). 均为提示项, 不构成缩仓依据.
        _add(_nth_weekday(y, m, 4, 3), "US", "美股月度OpEx（期权到期，GEX集中兑现）",
             "opex", "low", "复测(n=48): 次日中证1000均值-0.18% vs 基线+0.03%——"
             "无显著效应, 仅作提示（复测: scripts/index_event_study.py --expiry-study）")
        _add(_nth_weekday(y, m, 2, 4), "CN", "A股ETF期权到期日（第4周三）",
             "opex", "low", "复测(n=48): 当日中证1000均值-0.01%≈基线——无效应, 仅作日历提示"
             "（复测: scripts/index_event_study.py --expiry-study）")
        _add(_nth_weekday(y, m, 4, 3), "CN", "CFFEX股指期货/期权交割日（第3周五）",
             "opex", "low", "复测(n=48): 当日中证1000均值-0.33% vs 基线+0.03%"
             "(26/48收跌, ~1.5se)——偏弱但不显著, 观察项"
             "（复测: scripts/index_event_study.py --expiry-study）")
        _add(_last_day_of_month(y, m), "CN", "官方制造业PMI（9:30，当日盘中）",
             "macro_release", "medium", "增长脉搏读数——A股实际交易的国内数据")
        _add(_roll_to_weekday(_date(y, m, 1)), "CN", "财新制造业PMI（9:45，当日盘中）",
             "macro_release", "low", "官方PMI的民企/出口侧补充")
        _add(_roll_to_weekday(_date(y, m, 20)), "CN", "LPR报价",
             "cb_rate", "low", "通常已被MLF预告；意外调降=政策信号事件")
        _add(_nth_weekday(y, m, 4, 1), "US", "美国非农就业(NFP)",
             "macro_release", "medium", "联储路径预期的主要输入；周五盘后→影响下周一A股")
        for mm, dd, name, impact, notes in _CN_FIXED:
            if mm == m:
                _add(_date(y, mm, dd), "CN", name, "disclosure_deadline",
                     impact, notes)
        if m == 10:
            _add(_roll_to_weekday(_date(y, 10, 9)), "CN",
                 "国庆长假后首个交易日", "liquidity", "medium",
                 "一次性吸收假期内全球市场累计波动的跳空窗口")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def load_events(path: Path | None = None) -> list:
    p = path or EVENTS_FILE
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("events", [])
    except Exception:
        return []


RECENT_SETTLED_DAYS = 4  # look-back for the 已落地事件 bucket (covers a weekend)


def upcoming(days: int = 21, today: _date | None = None,
             path: Path | None = None) -> dict:
    """Events in the window + ongoing situations, sorted by A-share impact date.

    A dated event stays in `dated` until its A-SHARE IMPACT date has passed —
    not its release date (2026-08-08: NFP released Fri 8/7 evening vanished
    from Saturday's report although its A-share impact day was Monday 8/10).
    Released-but-impact-pending events carry `released: true`. Events whose
    impact date passed within RECENT_SETTLED_DAYS land in `recent` so the
    report/LLM can state their RESULT instead of silently forgetting them.
    """
    today = today or _date.today()
    horizon = today + timedelta(days=days)
    recent_floor = today - timedelta(days=RECENT_SETTLED_DAYS)
    dated, ongoing, recent = [], [], []
    for e in (load_events(path)
              + formulaic_events(recent_floor, horizon)):
        if e.get("certainty") == "ongoing" or not e.get("date"):
            ongoing.append({**{k: e.get(k) for k in
                               ("name", "kind", "impact", "notes", "source")},
                            "direction": e.get("direction", "risk")})
            continue
        try:
            d = _parse(e["date"])
        except (ValueError, TypeError):
            continue
        impact_d = a_share_impact_date(d, e.get("tz", "CN"))
        base = {**{k: e.get(k) for k in
                   ("date", "tz", "name", "kind", "certainty",
                    "impact", "notes", "source")},
                "direction": e.get("direction", "risk"),
                "a_share_impact_date": impact_d.isoformat(),
                "days_until_impact": (impact_d - today).days}
        if today <= impact_d and d <= horizon:
            if d < today:
                base["released"] = True  # data is out; A-share impact pending
            dated.append(base)
        elif recent_floor <= impact_d < today:
            recent.append(base)
    dated.sort(key=lambda x: (x["a_share_impact_date"],
                              -IMPACT_ORDER.get(x["impact"], 0)))
    recent.sort(key=lambda x: x["a_share_impact_date"], reverse=True)
    return {"as_of": today.isoformat(), "window_days": days,
            "dated": dated, "ongoing": ongoing, "recent": recent}


def risk_window(today: _date | None = None, path: Path | None = None) -> dict:
    """Compressed advisory: is a high-impact scheduled event imminent?"""
    up = upcoming(days=10, today=today, path=path)
    # supportive events inform sizing upward in the prompt but never
    # escalate the caution level
    imminent = [e for e in up["dated"]
                if e["impact"] == "high" and e["days_until_impact"] <= 3
                and e.get("direction") != "supportive"]
    ongoing_high = [e for e in up["ongoing"]
                    if e.get("impact") == "high"
                    and e.get("direction") != "supportive"]
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
            "elevated": ("存在持续性高冲击风险源（背景风险，非临近事件）：单笔规模取谨慎档。"
                         "注意：这不是停买信号——通过全部规则的标的仍应减量执行；"
                         "持续性风险不得作为长期零部署的理由"),
            "normal": "无临近高冲击既定事件：按规则正常执行，不要以泛化担忧替代规则",
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
