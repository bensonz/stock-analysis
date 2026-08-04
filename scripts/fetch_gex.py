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
    spot, flip = raw.get("spot"), raw.get("flip_point")
    if not spot or not flip:
        return None
    dist_pct = (spot / flip - 1) * 100
    net = raw.get("total_net_gex")
    if net is None:
        return None
    return {
        "underlying": raw.get("underlying"),
        "spot": spot,
        "flip_point": round(flip, 3),
        "dist_to_flip_pct": round(dist_pct, 2),
        "regime": "净正gamma(压制倾向)" if net > 0 else "净负gamma(放大倾向)",
        "spot_vs_flip": ("剖面零轴下方(put-gamma主导区)" if spot < flip
                         else "剖面零轴上方(call-gamma主导区)"),
        "total_net_gex": net,
        "call_wall": raw.get("call_wall"),
        "put_wall": raw.get("put_wall"),
        "expiry_month": raw.get("expiry_month"),
        "captured_at": raw.get("captured_at"),
    }


def overall_reading(states: list) -> dict:
    """Aggregate the two dimensions separately: net-GEX sign (regime) and
    spot-vs-profile-zero position (where hedging pressure concentrates)."""
    n = len(states)
    if n == 0:
        return {"signal": "无数据", "net_negative": "0/0",
                "below_flip": "0/0", "implication": ""}
    neg = sum(1 for s in states if s["total_net_gex"] < 0)
    below = sum(1 for s in states if "下方" in s["spot_vs_flip"])
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
    if below == n and neg == 0:
        implication += ("注意：现价虽均处行权价剖面put-gamma主导区（零轴下方），"
                        "但整体净gamma为正——剖面位置是结构参考，不改变当前压制判读。")
    return {"signal": signal, "net_negative": f"{neg}/{n}",
            "below_flip": f"{below}/{n}", "implication": implication}


def fetch_all() -> dict:
    states = []
    for u in UNDERLYINGS:
        raw = fetch_gex(u["code"])
        state = read_state(raw) if raw else None
        if state:
            state["name"] = u["name"]
            states.append(state)
    out = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": f"期权实验室 {API} (自建后端, 每标的可复查)",
        "etf_gex_data": states,
        "overall": overall_reading(states),
    }
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
