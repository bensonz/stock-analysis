#!/usr/bin/env python3
"""fetch_gex.py — A-share ETF options gamma exposure (GEX) snapshot.

Source: the 期权实验室 backend (same /api/history/* family as the IV feed):

    GET {GEX_BACKEND_URL}/api/history/gex?underlying=510050
      → spot, flip_point, call_wall, put_wall, total_net_gex, levels[...]

State reading per underlying (dealer-hedging mechanics):
    spot < flip_point → 负gamma侧: hedging AMPLIFIES moves (追涨杀跌区)
    spot > flip_point → 正gamma侧: hedging DAMPENS moves (钉住/压制区)

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
    below = spot < flip
    return {
        "underlying": raw.get("underlying"),
        "spot": spot,
        "flip_point": round(flip, 3),
        "dist_to_flip_pct": round(dist_pct, 2),
        "regime": "负gamma放大区" if below else "正gamma压制区",
        "total_net_gex": raw.get("total_net_gex"),
        "call_wall": raw.get("call_wall"),
        "put_wall": raw.get("put_wall"),
        "expiry_month": raw.get("expiry_month"),
        "captured_at": raw.get("captured_at"),
    }


def overall_reading(states: list) -> dict:
    """Aggregate: how much of the ETF complex sits below its flip point."""
    n = len(states)
    below = sum(1 for s in states if s["regime"] == "负gamma放大区")
    if n == 0:
        return {"signal": "无数据", "below_flip": "0/0", "implication": ""}
    if below == n:
        signal = "全面负gamma"
        implication = ("全部标的现价低于零gamma翻转点——做市对冲放大双向波动，"
                       "大涨大跌都更容易过冲；止损纪律照常，追高风险加倍。")
    elif below >= (n + 1) // 2:
        signal = "偏负gamma"
        implication = "多数标的在负gamma侧，波动放大环境为主。"
    elif below == 0:
        signal = "全面正gamma"
        implication = "全部标的在正gamma侧——对冲盘压制波动，倾向钉住/横盘。"
    else:
        signal = "偏正gamma"
        implication = "多数标的在正gamma侧，波动趋于收敛。"
    return {"signal": signal, "below_flip": f"{below}/{n}",
            "implication": implication}


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
            print(f"  现价 {s['spot']}  零gamma翻转点 {s['flip_point']} "
                  f"({s['dist_to_flip_pct']:+.2f}%) → {s['regime']}")
            print(f"  净GEX {s['total_net_gex']:.3g}  "
                  f"put墙 {s['put_wall']} / call墙 {s['call_wall']}")
        o = data["overall"]
        print(f"\n{'=' * 50}")
        print(f"综合: {o['signal']} (低于翻转点 {o['below_flip']})")
        if o.get("implication"):
            print(o["implication"])
        if data.get("error"):
            print(f"⚠️ {data['error']}")
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
