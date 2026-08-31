#!/usr/bin/env python3
"""fetch_gex.py — A-share ETF options gamma exposure (GEX) snapshot.

Source: the 期权实验室 backend (same /api/history/* family as the IV feed):

    GET {GEX_BACKEND_URL}/api/history/gex?underlying=510050
      → spot, flip_point, call_wall, put_wall, total_net_gex, levels[...]

State reading per underlying (dealer-hedging mechanics):
    regime = sign of total_net_gex (the DIRECT measurement):
        > 0 → 净正gamma: hedging DAMPENS moves (压制/钉住倾向)
        < 0 → 净负gamma: hedging AMPLIFIES moves (追涨杀跌)
    flip_point in this backend is the strike-profile zero-crossing (below
    it the OI profile is put-gamma-dominated) — a landmark, NOT the
    current-regime boundary. 2026-08-04 lesson: spot can sit below flip
    while net GEX is positive; labeling that "负gamma" (the SpotGamma
    convention) contradicted the backend's own numbers. Report both
    dimensions separately, never derive one from the other.

Tier-2 advisory context only (read-only): it rides into the prompt and the
report; NO mechanical rule consumes it. Graduation to anything more requires
a measured audition first (three-tier doctrine, docs/backtest/RESULTS.md).

Degrades gracefully: backend down → {"error": ...} and the pipeline carries
on, same contract as iv_sentiment.

Env: GEX_BACKEND_URL overrides the backend (default: the deployed lab).
"""
import json
import os
import sys
from datetime import datetime

import requests

GEX_BACKEND_URL = (os.getenv("GEX_BACKEND_URL")
                   or "http://47.94.238.128:8080").rstrip("/")
API = f"{GEX_BACKEND_URL}/api/history/gex"

UNDERLYINGS = [
    {"code": "510050", "name": "50ETF"},
    {"code": "510300", "name": "300ETF"},
    {"code": "510500", "name": "500ETF"},
    {"code": "588000", "name": "科创50ETF"},
    {"code": "159915", "name": "创业板ETF"},
]

TIMEOUT = 10


def fetch_gex(code: str) -> dict | None:
    try:
        resp = requests.get(API, params={"underlying": code}, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def read_state(raw: dict) -> dict | None:
    """Distill one underlying's payload into the advisory state block."""
    net = raw.get("total_net_gex")
    if net is None:
        # Regime is the one thing that cannot be inferred from anything else.
        # Without it the row says nothing and must not pad a denominator.
        return None
    spot, flip = raw.get("spot"), raw.get("flip_point")

    # `flip_point` is DESCRIPTIVE — it feeds dist_to_flip_pct and spot_vs_flip
    # and nothing else. Requiring it here used to discard the whole row, net GEX
    # included, and on 2026-08-31 that inverted the published signal: three of
    # five underlyings came back with flip_point=None and net GEX of -74.8M,
    # -2.8M and -18.8M, leaving only the two positive ones. The report then said
    # 全面净正gamma (0/2 negative) when the truth was 偏净负gamma (3/5).
    #
    # The bias is not random. flip_point is a zero-crossing of the gamma
    # profile, and the backend cannot locate one when the profile never crosses
    # zero inside the strike range — far likelier under strongly NEGATIVE net
    # gamma. The absent field correlates with the signal, so dropping on it
    # discarded the amplifying half and called the remainder unanimous.
    has_profile = bool(spot) and bool(flip)
    return {
        "underlying": raw.get("underlying"),
        "spot": spot,
        "flip_point": round(flip, 3) if has_profile else None,
        "dist_to_flip_pct": round((spot / flip - 1) * 100, 2) if has_profile else None,
        "regime": "净正gamma(压制倾向)" if net > 0 else "净负gamma(放大倾向)",
        "spot_vs_flip": (("剖面零轴下方(put-gamma主导区)" if spot < flip
                          else "剖面零轴上方(call-gamma主导区)") if has_profile else None),
        "total_net_gex": net,
        "call_wall": raw.get("call_wall"),
        "put_wall": raw.get("put_wall"),
        "expiry_month": raw.get("expiry_month"),
        "captured_at": raw.get("captured_at"),
    }


NO_PROFILE = "无"          # backend gave no zero-crossing for this underlying


def fmt_flip(state: dict) -> str:
    """The profile zero-axis, or 无 when the backend could not locate one."""
    v = state.get("flip_point")
    return NO_PROFILE if v is None else f"{v}"


def fmt_dist(state: dict) -> str:
    """Distance to the zero axis as a signed percent, or 无.

    Exists so the three places that render GEX — report_generator, llm_client
    and this module's --human output — share one definition. When read_state
    stopped discarding profile-less rows on 2026-08-31, every one of those sites
    was formatting the field with `:+.2f`, and the first to run took down the
    pipeline at Gate 3 with NoneType.__format__. Three hand-rolled null checks
    would just have invited a fourth site to forget.
    """
    v = state.get("dist_to_flip_pct")
    return NO_PROFILE if v is None else f"{v:+.2f}%"


def overall_reading(states: list) -> dict:
    """Aggregate the two dimensions separately: net-GEX sign (regime) and
    spot-vs-profile-zero position (where hedging pressure concentrates)."""
    n = len(states)
    if n == 0:
        return {"signal": "无数据", "net_negative": "0/0",
                "below_flip": "0/0", "implication": ""}
    neg = sum(1 for s in states if s["total_net_gex"] < 0)
    # Count the profile dimension over rows that HAVE a profile. Borrowing the
    # regime denominator would understate a real concentration, and — worse —
    # would let `below == n` fire below on a subset (see the caveat guard).
    profiled = [s for s in states if s.get("spot_vs_flip")]
    n_prof = len(profiled)
    below = sum(1 for s in profiled if "下方" in s["spot_vs_flip"])
    if neg == n:
        signal = "全面净负gamma"
        implication = ("全部标的做市净空gamma——对冲盘放大双向波动，"
                       "大涨大跌都更容易过冲；止损纪律照常，追高风险加倍。")
    elif neg > n // 2:
        signal = "偏净负gamma"
        implication = "多数标的净负gamma，波动放大环境为主。"
    elif neg == 0:
        signal = "全面净正gamma"
        implication = "全部标的做市净多gamma——对冲盘压制波动，倾向收敛/钉住。"
    else:
        signal = "偏净正gamma"
        implication = "多数标的净正gamma，波动趋于收敛。"
    # This caveat asserts something structural about EVERY underlying, so it may
    # only fire when every underlying actually has a profile. n_prof == n is the
    # guard: on a partial read it stays silent rather than generalising from the
    # subset that happened to parse.
    if n_prof == n and below == n and neg == 0:
        implication += ("注意：现价虽均处行权价剖面put-gamma主导区（零轴下方），"
                        "但整体净gamma为正——剖面位置是结构参考，不改变当前压制判读。")
    return {"signal": signal, "net_negative": f"{neg}/{n}",
            "below_flip": f"{below}/{n_prof}", "implication": implication}


def fetch_all() -> dict:
    """Read every underlying, and say plainly how many actually made it.

    The old version dropped failures silently and only complained when ALL of
    them failed. Two of five therefore rendered as "全面净正gamma" — across the
    board — with nothing anywhere saying the board was 60% missing. Partial
    coverage is now recorded per underlying and carried into the artifact.
    """
    states, missing = [], []
    for u in UNDERLYINGS:
        raw = fetch_gex(u["code"])
        state = read_state(raw) if raw else None
        if state:
            state["name"] = u["name"]
            states.append(state)
        else:
            missing.append(u["code"])
            print(f"  GEX: no usable reading for {u['code']} ({u['name']})",
                  file=sys.stderr)
    out = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": f"期权实验室 {API} (自建后端, 每标的可复查)",
        "etf_gex_data": states,
        "coverage": {
            "expected": len(UNDERLYINGS),
            "fetched": len(states),
            "missing": missing,
            "partial": bool(missing),
        },
        "overall": overall_reading(states),
    }
    if missing and states:
        out["overall"]["implication"] += (
            f"（覆盖不全：{len(states)}/{len(UNDERLYINGS)} 个标的有读数，"
            f"缺 {', '.join(missing)}——以下比例仅就已读到的标的而言。）")
        print(f"  GEX: PARTIAL coverage {len(states)}/{len(UNDERLYINGS)}",
              file=sys.stderr)
    if not states:
        out["error"] = f"GEX backend unreachable at {GEX_BACKEND_URL}"
    return out


def main():
    data = fetch_all()
    if "--human" in sys.argv:
        print(f"📐 A股ETF期权Gamma敞口 ({data['date']})")
        print("=" * 50)
        for s in data["etf_gex_data"]:
            print(f"\n{s['name']} ({s['underlying']}) 到期月{s['expiry_month']}:")
            print(f"  净GEX {s['total_net_gex']:.3g} → {s['regime']}")
            # A row may now carry a regime without a profile (flip_point=None).
            # Formatting None crashed here the moment the parser stopped
            # discarding those rows — the same NoneType.__format__ break that
            # took out candidates.md on 2026-08-25. The degraded path has to be
            # printable, or the fix that surfaces it takes the report down.
            if s.get("dist_to_flip_pct") is None:
                print(f"  现价 {s['spot']} vs 剖面零轴 无（后端未给出零轴，"
                      f"剖面在行权区间内未穿零）  "
                      f"put墙 {s['put_wall']} / call墙 {s['call_wall']}")
            else:
                print(f"  现价 {s['spot']} vs 剖面零轴 {s['flip_point']} "
                      f"({s['dist_to_flip_pct']:+.2f}%, {s['spot_vs_flip']})  "
                      f"put墙 {s['put_wall']} / call墙 {s['call_wall']}")
        o = data["overall"]
        print(f"\n{'=' * 50}")
        print(f"综合: {o['signal']} (净负gamma {o['net_negative']}, "
              f"现价处剖面零轴下方 {o['below_flip']})")
        if o.get("implication"):
            print(o["implication"])
        if data.get("error"):
            print(f"⚠️ {data['error']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
