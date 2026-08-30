#!/usr/bin/env python3
"""index_event_study.py — forward index returns after a list of event dates.

The tool behind every "会后N日指数平均±X%" claim in tracking/events.json:
numbers in the calendar must be re-runnable, and this is the re-run
(traceability rule, 2026-08-04 — after the unmeasured "+2% 小盘占优"
politburo folklore was caught by the user and refuted).

Data: sina index daily klines (sh000852 = 中证1000, sh000300 = 沪深300),
close-to-close from the last close <= event date to N sessions later.
Coverage: sina serves ~1023 bars ≈ back to mid-2022.

Usage:
  python3 scripts/index_event_study.py                      # politburo default
  python3 scripts/index_event_study.py --sessions 10 --dates 2024-09-26,2025-07-30
"""
import json
import statistics
import sys

import requests

# Economic-work Politburo meetings (dates from 新华社 wire copy; 2025-12-08
# and 2026-04-28 verified via people.cn / news.cn on 2026-08-04).
POLITBURO_DATES = [
    "2022-04-29", "2022-07-28", "2022-12-06",
    "2023-04-28", "2023-07-24", "2023-12-08",
    "2024-04-30", "2024-07-30", "2024-09-26", "2024-12-09",
    "2025-04-25", "2025-07-30", "2025-12-08",
    "2026-04-28", "2026-07-30",
]

SINA_KLINE = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/x=/"
              "CN_MarketDataService.getKLineData")


def fetch_index(symbol: str, datalen: int = 1023) -> dict:
    """{iso_date: close} for an index, ascending coverage of ~4 years."""
    resp = requests.get(
        SINA_KLINE,
        params={"symbol": symbol, "scale": "240", "ma": "no",
                "datalen": str(datalen)},
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0",
                 "Referer": "https://finance.sina.com.cn"})
    text = resp.text
    data = json.loads(text[text.index("(") + 1: text.rindex(")")])
    return {d["day"]: float(d["close"]) for d in data}


def forward_return(closes: dict, event_date: str, sessions: int) -> float | None:
    """Close-to-close % from last close <= event_date to `sessions` later.
    None when the event or the full forward window is outside coverage."""
    dates = sorted(closes)
    base = [d for d in dates if d <= event_date]
    if not base or base[-1] < dates[0]:
        return None
    i = dates.index(base[-1])
    if i + sessions >= len(dates):
        return None
    return (closes[dates[i + sessions]] / closes[base[-1]] - 1) * 100


def study(event_dates: list, sessions: int = 10,
          small: str = "sh000852", large: str = "sh000300") -> dict:
    s_closes, l_closes = fetch_index(small), fetch_index(large)
    rows, skipped = [], []
    for d in sorted(event_dates):
        rs = forward_return(s_closes, d, sessions)
        rl = forward_return(l_closes, d, sessions)
        if rs is None or rl is None:
            skipped.append(d)
            continue
        rows.append({"event": d, small: round(rs, 2), large: round(rl, 2),
                     "spread_pp": round(rs - rl, 2)})
    small_rets = [r[small] for r in rows]
    spreads = [r["spread_pp"] for r in rows]
    return {
        "sessions": sessions, "n": len(rows), "skipped": skipped,
        "rows": rows,
        "summary": {
            f"{small}_mean_pct": round(statistics.mean(small_rets), 2) if rows else None,
            f"{small}_median_pct": round(statistics.median(small_rets), 2) if rows else None,
            f"{small}_positive": f"{sum(1 for x in small_rets if x > 0)}/{len(rows)}",
            "spread_mean_pp": round(statistics.mean(spreads), 2) if rows else None,
            "spread_positive": f"{sum(1 for x in spreads if x > 0)}/{len(rows)}",
        },
    }


def expiry_study(beg_ym=(2022, 8), end_ym=(2026, 7)) -> None:
    """Derivative-expiry base rates behind the calendar's opex notes.

    Three legs vs the all-sample daily baseline (中证1000):
    US monthly OpEx (3rd Fri, effect = next A-share session), A-share ETF
    option expiry (4th Wed, same-day), CFFEX index futures/options
    settlement (3rd Fri, same-day). Same-day legs pass the previous
    calendar day so forward_return's +1 session lands on the event day.
    """
    import statistics
    from datetime import date, timedelta

    def nth_weekday(y, m, weekday, n):
        d = date(y, m, 1)
        d += timedelta(days=(weekday - d.weekday()) % 7)
        return d + timedelta(weeks=n - 1)

    months = [(y, m) for y in range(beg_ym[0], end_ym[0] + 1)
              for m in range(1, 13)
              if beg_ym <= (y, m) <= end_ym]
    closes = fetch_index("sh000852")
    dates = sorted(closes)
    daily = [(closes[dates[i + 1]] / closes[dates[i]] - 1) * 100
             for i in range(len(dates) - 1)]
    print(f"基线(中证1000全样本日收益): mean {statistics.mean(daily):+.2f}% "
          f"sd {statistics.stdev(daily):.2f} n={len(daily)}")

    legs = [
        ("美股OpEx次日", [nth_weekday(y, m, 4, 3) for y, m in months], 0),
        ("A股ETF期权到期日当天", [nth_weekday(y, m, 2, 4) for y, m in months], -1),
        ("CFFEX交割日当天", [nth_weekday(y, m, 4, 3) for y, m in months], -1),
    ]
    for label, evs, off in legs:
        rets = [r for d in evs
                if (r := forward_return(
                    closes, (d + timedelta(days=off)).isoformat(), 1)) is not None]
        print(f"{label}: n={len(rets)} mean {statistics.mean(rets):+.2f}% "
              f"sd {statistics.stdev(rets):.2f} "
              f"neg {sum(1 for x in rets if x < 0)}/{len(rets)}")


if __name__ == "__main__":
    args = sys.argv[1:]

    def _arg(flag, default):
        return args[args.index(flag) + 1] if flag in args else default

    if "--expiry-study" in args:
        expiry_study()
        sys.exit(0)

    dates = _arg("--dates", None)
    dates = dates.split(",") if dates else POLITBURO_DATES
    result = study(dates, sessions=int(_arg("--sessions", "10")))
    for r in result["rows"]:
        print(f"{r['event']}: 中证1000 {r['sh000852']:+6.2f}%  "
              f"沪深300 {r['sh000300']:+6.2f}%  价差 {r['spread_pp']:+6.2f}pp")
    if result["skipped"]:
        print(f"(跳过—数据范围外或窗口未完成: {', '.join(result['skipped'])})")
    print(json.dumps(result["summary"], ensure_ascii=False))
