#!/usr/bin/env python3
"""
margin_flow.py — Per-stock margin financing (融资融券) trend from Eastmoney direct.

融资余额 (financing balance) is the total borrowed money sitting in leveraged long
positions on a stock. A steadily *falling* balance means leveraged holders are net
closing positions — a positioning/sentiment risk flag (speculative support draining),
NOT a price predictor. Use it as corroboration alongside sector/IV/extension, never as
a standalone buy/sell driver.

Free & daily from Eastmoney's datacenter (no token / no points). Kept dependency-light
(plain urllib/json, proxy-stripped like pricedb's Eastmoney fetch) so it stays a simple
fetcher and is unit-testable via the _fetch_json seam.

Usage:
    python3 scripts/margin_flow.py --human 601958   # trend table + summary
    python3 scripts/margin_flow.py 601958           # JSON summary
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

# Eastmoney datacenter reportName RPTA_WEB_RZRQ_GGMX = per-stock 融资融券明细.
EASTMONEY_MARGIN_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
MARGIN_TIMEOUT_SEC = float(os.getenv("MARGIN_TIMEOUT", "15"))


def _normalize_scode(code: str) -> str:
    """Eastmoney's SCODE filter uses the bare 6-digit code (no exchange suffix)."""
    return str(code or "").split(".")[0].strip()


def _margin_url(code: str, page_size: int = 10) -> str:
    scode = _normalize_scode(code)
    params = {
        "reportName": "RPTA_WEB_RZRQ_GGMX",
        "columns": "DATE,SCODE,SECNAME,RZYE,RZYEZB,RZJME",
        "filter": f'(SCODE="{scode}")',
        "sortColumns": "DATE",
        "sortTypes": "-1",  # newest first
        "pageSize": str(page_size),
        "pageNumber": "1",
    }
    # safe="," keeps the literal commas Eastmoney expects in `columns`.
    return f"{EASTMONEY_MARGIN_URL}?{urllib.parse.urlencode(params, safe=',')}"


def _fetch_json_urllib(url: str) -> str:
    # Strip proxy: Surge/local proxies hijack *.eastmoney.com DNS to 198.18.x.x.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "close",
            "User-Agent": "Mozilla/5.0 margin-flow-eastmoney-direct",
        },
    )
    with opener.open(request, timeout=MARGIN_TIMEOUT_SEC) as response:
        return response.read().decode("utf-8")


def _fetch_json_curl(url: str) -> str:
    completed = subprocess.run(
        ["curl", "-sS", "--max-time", str(max(1, int(MARGIN_TIMEOUT_SEC))), "-x", "", url],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=MARGIN_TIMEOUT_SEC + 2,
    )
    return completed.stdout


def _fetch_json(url: str) -> dict:
    """Proxy-stripped urllib with a curl fallback. Raises on total failure."""
    try:
        raw = _fetch_json_urllib(url)
    except Exception as urllib_error:
        try:
            raw = _fetch_json_curl(url)
        except Exception as curl_error:
            raise RuntimeError(f"urllib failed: {urllib_error}; curl failed: {curl_error}") from curl_error
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"invalid Eastmoney JSON: {e}") from e


def _parse_margin_rows(payload: dict) -> list[dict]:
    """Extract the newest-first row list from the Eastmoney envelope, defensively."""
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    data = result.get("data")
    if not isinstance(data, list):
        return []
    return [r for r in data if isinstance(r, dict)]


def _to_float(value) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize_margin(rows: list[dict], window: int = 5) -> dict | None:
    """Compact prompt block from newest-first margin rows.

    Returns ~5 fields: latest 融资余额 (亿), 占流通市值 %, N-session % change, count of
    net-repayment sessions in the window, and a coarse signal. None if no usable data.
    """
    if not rows:
        return None
    latest = rows[0]
    rzye = _to_float(latest.get("RZYE"))
    if rzye is None:
        return None

    recent = rows[:window]
    net_days = [_to_float(r.get("RZJME")) for r in recent]
    net5_repay_days = sum(1 for v in net_days if v is not None and v < 0)

    # % change in 融资余额 across the window (oldest-in-window -> latest).
    chg5_pct = None
    older = _to_float(recent[-1].get("RZYE")) if len(recent) > 1 else None
    if older not in (None, 0):
        chg5_pct = round((rzye - older) / older * 100, 2)

    if chg5_pct is not None and chg5_pct <= -1 and net5_repay_days >= 3:
        signal = "deleveraging"
    elif chg5_pct is not None and chg5_pct >= 1:
        signal = "adding"
    else:
        signal = "neutral"

    pct_float = _to_float(latest.get("RZYEZB"))
    return {
        "rzye_yi": round(rzye / 1e8, 2),
        "pct_float": round(pct_float, 2) if pct_float is not None else None,
        "chg5_pct": chg5_pct,
        "net5_repay_days": net5_repay_days,
        "signal": signal,
    }


def fetch_margin_flow(code: str) -> dict | None:
    """Fetch + summarize per-stock margin flow. Returns None on any failure (never raises)."""
    try:
        payload = _fetch_json(_margin_url(code))
        return summarize_margin(_parse_margin_rows(payload))
    except Exception as e:  # graceful-degrade, like the IV/price fetchers
        print(f"  Warning: margin fetch failed for {code}: {e}", file=sys.stderr)
        return None


def main():
    args = [a for a in sys.argv[1:] if a != "--human"]
    human = "--human" in sys.argv
    code = args[0] if args else "601958"

    if human:
        payload = _fetch_json(_margin_url(code))
        rows = _parse_margin_rows(payload)
        print(f"📊 融资融券趋势 {code}")
        print("=" * 46)
        print("date       | 融资余额(亿) | 占流通% | 融资净买入(万)")
        for r in rows:
            rzye = _to_float(r.get("RZYE")) or 0
            zb = _to_float(r.get("RZYEZB"))
            jme = _to_float(r.get("RZJME")) or 0
            zb_str = f"{zb:>5.2f}" if zb is not None else "   ?"
            print(f"{str(r.get('DATE',''))[:10]} | {rzye/1e8:>9.2f} | {zb_str} | {jme/1e4:>10.1f}")
        print("-" * 46)
        print(json.dumps(summarize_margin(rows), ensure_ascii=False))
    else:
        print(json.dumps(fetch_margin_flow(code), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
