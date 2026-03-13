#!/usr/bin/env python3
"""
Data Collector — All data fetching for the daily pipeline.

Functions:
- fetch_strategy_pool()      — CheeseForTune API strategy stock list
- batch_enrich(stocks)       — Enrich stocks in RPS 75-95% zone
- fetch_market_overview()    — AkShare indices + breadth + sectors
- fetch_position_prices()    — Current prices for active positions
- fetch_missed_opportunity_prices() — Prices for past recommendations

All functions return dicts, handle errors gracefully, never crash.
"""

import json
import os
import sqlite3
import sys
import time
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CRAWL_DIR = DATA_DIR / "crawl"
MARKET_DIR = DATA_DIR / "market"
PRICES_DIR = DATA_DIR / "prices"
PRICEDB_DIR = DATA_DIR / "pricedb"
DEFAULT_PRICEDB_PATH = PRICEDB_DIR / "ashare_prices.db"
WATCHLIST_DIR = PROJECT_ROOT / "watchlist"

DEFAULT_STRATEGY_ID = os.getenv("CHEESE_STRATEGY_ID", "407228")
LOCAL_STRATEGY_ID = f"{DEFAULT_STRATEGY_ID}-local-ma-rps"
LOCAL_RISK_EXCLUDE_KEYWORDS = tuple(filter(None, [
    keyword.strip() for keyword in os.getenv(
        "LOCAL_RISK_EXCLUDE_KEYWORDS",
        "ST,*ST,退市,立案,处罚,诉讼,造假,违约,减持,解禁,质押",
    ).split(",")
]))

for d in [CRAWL_DIR, MARKET_DIR, PRICES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Import CheeseForTune client (same directory)
sys.path.insert(0, str(Path(__file__).parent))
from cheesefortune_client import CheeseFortuneClient, normalize_code


def fetch_strategy_pool(strategy_id: str = DEFAULT_STRATEGY_ID) -> dict:
    """Fetch strategy stock list from CheeseForTune API.

    Tries the API endpoint first. If that fails, falls back to loading
    the most recent crawl file from data/crawl/.

    Returns:
        {
            "source": "api" | "crawl_file",
            "strategy_id": str,
            "total_stocks": int,
            "stocks": [{"code": str, "name": str, "rps120": float, ...}],
            "error": str | None
        }
    """
    # Try API endpoint for strategy stock list
    try:
        stocks = _fetch_strategy_api(strategy_id)
        if stocks:
            return {
                "source": "api",
                "strategy_id": strategy_id,
                "total_stocks": len(stocks),
                "stocks": stocks,
                "error": None,
            }
    except Exception as e:
        print(f"  Strategy API failed: {e}", file=sys.stderr)

    # Fallback: load most recent crawl file
    try:
        crawl_files = sorted(CRAWL_DIR.glob("*.json"), reverse=True)
        if crawl_files:
            data = json.loads(crawl_files[0].read_text(encoding="utf-8"))
            stocks = data.get("stocks", [])
            return {
                "source": f"crawl_file:{crawl_files[0].name}",
                "strategy_id": strategy_id,
                "total_stocks": len(stocks),
                "stocks": stocks,
                "error": None,
            }
    except Exception as e:
        print(f"  Crawl file fallback failed: {e}", file=sys.stderr)

    return {
        "source": "none",
        "strategy_id": strategy_id,
        "total_stocks": 0,
        "stocks": [],
        "error": "Could not fetch strategy pool from API or crawl files",
    }


def fetch_strategy_pool_local(db_path: str = None) -> dict:
    """Fetch strategy candidates using the local price DB + CheeseForTune filters.

    Falls back to the remote CheeseForTune strategy pool if the local DB is
    missing, stale, or local computation fails.
    """
    db_file = Path(db_path) if db_path else DEFAULT_PRICEDB_PATH
    if not db_file.exists():
        print("  Local pricedb missing — falling back to CheeseForTune strategy", file=sys.stderr)
        return fetch_strategy_pool()

    try:
        from rps_calculator import compute_ma_alignment, compute_ma_rps

        with sqlite3.connect(str(db_file)) as conn:
            latest_row = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
            latest_date = latest_row[0] if latest_row and latest_row[0] else None
            if not latest_date:
                raise RuntimeError("local pricedb has no daily_prices rows")

            latest_dt = datetime.strptime(latest_date, "%Y-%m-%d").date()
            if (datetime.now().date() - latest_dt).days > 10:
                raise RuntimeError(f"local pricedb is stale (latest date: {latest_date})")

            stock_meta = {
                row[0]: {"name": row[1], "exchange": row[2]}
                for row in conn.execute("SELECT code, name, exchange FROM stocks")
            }

        rps_by_code = compute_ma_rps(str(db_file), latest_date)
        alignment_by_code = compute_ma_alignment(str(db_file), latest_date)

        screened = []
        for code, rps in rps_by_code.items():
            rps60 = rps.get("rps60")
            rps120 = rps.get("rps120")
            rps250 = rps.get("rps250")
            alignment = alignment_by_code.get(code)
            if rps60 is None or rps120 is None or rps250 is None or not alignment:
                continue
            if rps120 < 85 or rps250 < 85 or rps60 < 70 or not alignment.get("aligned"):
                continue

            meta = stock_meta.get(code, {})
            screened.append({
                "code": code,
                "code_full": normalize_code(code),
                "name": meta.get("name", code),
                "exchange": meta.get("exchange"),
                "rps20": rps.get("rps20"),
                "rps60": rps60,
                "rps120": rps120,
                "rps250": rps250,
                "ma10": rps.get("ma10_today"),
                "ma20": round(alignment["ma20"], 4),
                "ma120": round(alignment["ma120"], 4),
                "ma250": round(alignment["ma250"], 4),
                "price_date": latest_date,
            })

        screened.sort(key=lambda item: (item["rps120"], item["rps250"], item["rps60"]), reverse=True)
        if not screened:
            return {
                "source": "local_pricedb",
                "strategy_id": LOCAL_STRATEGY_ID,
                "date": latest_date,
                "total_stocks": 0,
                "stocks": [],
                "error": None,
            }

        enriched_rows = batch_enrich(screened)
        if not enriched_rows:
            raise RuntimeError("CheeseForTune enrichment returned no results")

        snapshots = _load_price_snapshots(str(db_file), [stock["code"] for stock in screened], latest_date)
        screened_map = {stock["code"]: stock for stock in screened}
        final_stocks = []

        for summary in enriched_rows:
            if not isinstance(summary, dict) or summary.get("error"):
                continue

            code = str(summary.get("code", "")).split(".")[0]
            base = screened_map.get(code)
            if not base:
                continue

            name = summary.get("name") or base.get("name") or code
            if _is_st_stock(name):
                continue

            highlights = summary.get("highlights") or []
            risks = summary.get("risks") or []
            highlights_count = len(highlights)
            risks_count = len(risks)
            if highlights_count < 4 or risks_count > 5:
                continue
            if _has_excluded_risk(risks):
                continue

            price_snapshot = snapshots.get(code, {})
            price = price_snapshot.get("price")
            market_cap = _compute_market_cap(price, summary.get("total_shares"))
            if market_cap is None or not (20 <= market_cap <= 810):
                continue

            stock = {
                "code": code,
                "code_full": normalize_code(code),
                "name": name,
                "date": latest_date,
                "price": price,
                "change_pct": price_snapshot.get("change_pct"),
                "market_cap": round(market_cap, 2),
                "pe": summary.get("pe"),
                "pb": summary.get("pb"),
                "ps_ttm": summary.get("ps_ttm"),
                "pcf_ttm": summary.get("pcf_ttm"),
                "valuation_percentile": summary.get("valuation_percentile"),
                "score_company": summary.get("score_company"),
                "score_trend": summary.get("score_trend"),
                "score_value": summary.get("score_value"),
                "highlights_count": highlights_count,
                "risks_count": risks_count,
                "highlights": highlights,
                "risks": risks,
                "events": summary.get("events") or [],
                "industries": summary.get("industries") or [],
                "concepts": summary.get("concepts") or [],
                "revenue_yoy": summary.get("revenue_yoy"),
                "net_profit_yoy": summary.get("net_profit_yoy"),
                "gross_margin": summary.get("gross_margin"),
                "rps20": base.get("rps20"),
                "rps60": base.get("rps60"),
                "rps120": base.get("rps120"),
                "rps250": base.get("rps250"),
                "ma10": base.get("ma10"),
                "ma20": base.get("ma20"),
                "ma120": base.get("ma120"),
                "ma250": base.get("ma250"),
            }
            final_stocks.append(stock)

        final_stocks.sort(key=lambda item: (item.get("rps120", 0), item.get("rps250", 0)), reverse=True)
        return {
            "source": "local_pricedb",
            "strategy_id": LOCAL_STRATEGY_ID,
            "date": latest_date,
            "total_stocks": len(final_stocks),
            "stocks": final_stocks,
            "error": None,
        }
    except Exception as e:
        print(f"  Local pricedb strategy failed: {e}", file=sys.stderr)
        return fetch_strategy_pool()


def _load_price_snapshots(db_path: str, codes: list[str], date: str) -> dict:
    """Load latest and previous close for a set of codes on or before date."""
    if not codes:
        return {}

    placeholders = ",".join(["?"] * len(codes))
    query = f"""
        WITH ranked AS (
            SELECT
                code,
                date,
                close,
                ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
            FROM daily_prices
            WHERE date <= ? AND code IN ({placeholders})
        )
        SELECT code, date, close, rn
        FROM ranked
        WHERE rn <= 2
        ORDER BY code, rn
    """
    snapshots: dict[str, dict] = {}
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query, [date] + list(codes)).fetchall()

    for code, price_date, close, rn in rows:
        snap = snapshots.setdefault(code, {"price_date": price_date})
        if rn == 1:
            snap["price"] = float(close)
            snap["price_date"] = price_date
        elif rn == 2:
            prev_close = float(close)
            snap["prev_close"] = prev_close
            latest = snap.get("price")
            if latest not in (None, 0):
                snap["change_pct"] = round((latest - prev_close) / prev_close * 100, 2) if prev_close else None
    return snapshots


def _compute_market_cap(price: float | None, total_shares: float | None) -> float | None:
    """Compute market cap in 亿元 from latest price and total shares."""
    if price in (None, 0) or total_shares in (None, 0):
        return None
    try:
        return float(price) * float(total_shares) / 100_000_000
    except (TypeError, ValueError):
        return None


def _has_excluded_risk(risks: list[dict]) -> bool:
    """Return True when a risk tag/text contains a configured exclude keyword."""
    for risk in risks:
        tag = str(risk.get("tag", "")).strip().lower()
        text = str(risk.get("text", "")).strip().lower()
        for keyword in LOCAL_RISK_EXCLUDE_KEYWORDS:
            needle = keyword.lower()
            if needle and (needle in tag or needle in text):
                return True
    return False


def _is_st_stock(name: str) -> bool:
    """Detect ST / *ST names conservatively."""
    if not name:
        return False
    normalized = str(name).strip().upper()
    return normalized.startswith("ST") or normalized.startswith("*ST") or " ST" in normalized


def _fetch_strategy_api(strategy_id: str) -> Optional[list[dict]]:
    """Try to fetch strategy stock list from CheeseForTune API.

    Uses /api/v2/userSelectStrategy/info/{strategyId}.
    Returns array of arrays: [code.exchange, name, date, highlights, mcap, pe, risks, rps120, rps250, rps20, rps60]
    """
    client = CheeseFortuneClient()
    url = f"{client.BASE_URL}/api/v2/userSelectStrategy/info/{strategy_id}"
    try:
        result = client._request(url)
        if result.get("code") == "000" and result.get("datas"):
            datas = result["datas"]
            raw_list = datas.get("list", []) if isinstance(datas, dict) else datas
            if isinstance(raw_list, list) and len(raw_list) > 0:
                # Each item is an array: [code.exchange, name, date, highlights, mcap, pe, risks, rps120, rps250, rps20, rps60]
                return _parse_strategy_array(raw_list)
    except Exception:
        pass

    return None


def _parse_strategy_array(raw: list) -> list[dict]:
    """Parse strategy API response (array of arrays) into normalized stock dicts.
    
    Each item: [code.exchange, name, date, highlights, mcap, pe, risks, rps120, rps250, rps20, rps60]
    Example: ["002270.SZ", "华明装备", "2026/03/02", 7, 320.22, 10.1, 1, 93.96, 91.02, 72.81, 86.31]
    """
    stocks = []
    for item in raw:
        if not isinstance(item, list) or len(item) < 2:
            continue
        code_full = str(item[0])  # e.g. "002270.SZ"
        code = code_full.split(".")[0]
        stock: dict = {
            "code": code,
            "code_full": code_full,
            "name": item[1] if len(item) > 1 else "",
            "date": item[2] if len(item) > 2 else "",
            "highlights_count": item[3] if len(item) > 3 else 0,
            "market_cap": item[4] if len(item) > 4 else None,
            "pe": item[5] if len(item) > 5 else None,
            "risks_count": item[6] if len(item) > 6 else 0,
        }
        # RPS values (indices 7-10)
        if len(item) > 7 and item[7] is not None:
            stock["rps120"] = float(item[7])
        if len(item) > 8 and item[8] is not None:
            stock["rps250"] = float(item[8])
        if len(item) > 9 and item[9] is not None:
            stock["rps20"] = float(item[9])
        if len(item) > 10 and item[10] is not None:
            stock["rps60"] = float(item[10])
        stocks.append(stock)
    return stocks


def _parse_strategy_stocks(raw: list) -> list[dict]:
    """Parse raw API response (dict items) into normalized stock dicts."""
    stocks = []
    for item in raw:
        stock = {
            "code": str(item.get("code", item.get("stockCode", ""))).split(".")[0],
            "name": item.get("name", item.get("stockName", "")),
        }
        # RPS fields (try various key names)
        for rps_key in ["rps120", "rps_120", "RPS120"]:
            if rps_key in item:
                stock["rps120"] = float(item[rps_key])
                break
        for rps_key in ["rps250", "rps_250", "RPS250"]:
            if rps_key in item:
                stock["rps250"] = float(item[rps_key])
                break
        for rps_key in ["rps20", "rps_20", "RPS20"]:
            if rps_key in item:
                stock["rps20"] = float(item[rps_key])
                break
        for rps_key in ["rps60", "rps_60", "RPS60"]:
            if rps_key in item:
                stock["rps60"] = float(item[rps_key])
                break

        # Price / change
        if "price" in item:
            stock["price"] = float(item["price"])
        if "change_pct" in item or "changePct" in item:
            stock["change_pct"] = float(item.get("change_pct", item.get("changePct", 0)))
        if "mcap" in item or "market_cap" in item:
            stock["market_cap"] = item.get("mcap", item.get("market_cap"))
        if "added" in item:
            stock["added"] = item["added"]
        if "highlights" in item:
            stock["highlights"] = item["highlights"]
        if "risks" in item:
            stock["risks"] = item["risks"]

        stocks.append(stock)
    return stocks


def batch_enrich(stocks: list[dict], max_workers: int = 8) -> list[dict]:
    """Enrich stocks in RPS 75-95% zone using CheeseForTune API.

    Runs concurrent workers (each with its own client instance) to
    parallelize fetching. The server handles concurrent connections fine;
    rate limiting only triggers on rapid sequential calls from one client.

    Args:
        stocks: List of stock dicts with at least "code" key.
        max_workers: Number of concurrent fetchers (default 8).

    Returns:
        List of enriched stock summary dicts.
    """
    if not stocks:
        return []

    codes = [normalize_code(s["code"]) for s in stocks]

    def _fetch_one(i_code):
        i, code = i_code
        print(f"  [{i+1}/{len(codes)}] Fetching {code}...", file=sys.stderr)
        try:
            client = CheeseFortuneClient()
            client.MIN_REQUEST_INTERVAL = 0.3
            return client.get_stock_summary(code)
        except Exception as e:
            return {"code": code, "error": str(e)}

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_fetch_one, enumerate(codes)))
        return results
    except Exception as e:
        print(f"  Batch enrich error: {e}", file=sys.stderr)
        return [{"code": c, "error": str(e)} for c in codes]


def fetch_ma_data(stocks: list[dict]) -> dict:
    """Fetch MA5/MA10/MA20 data for stocks via Eastmoney kline API.

    Bypasses proxy (Eastmoney push2 gets DNS-hijacked by Surge/Clash).

    Args:
        stocks: List of stock dicts with "code" or "code_full" keys.

    Returns:
        Dict of {code: {price, ma5, ma10, ma20, dist_ma5_pct, dist_ma10_pct, dist_ma20_pct}}
    """
    import requests as _req
    from concurrent.futures import ThreadPoolExecutor

    results = {}

    def _fetch_one(stock):
        code = str(stock.get("code", "")).split(".")[0]
        code_full = stock.get("code_full", "")
        if not code:
            return None

        # Determine secid (1=SH, 0=SZ)
        if code_full.endswith(".SH") or code.startswith("6"):
            secid = f"1.{code}"
        else:
            secid = f"0.{code}"

        try:
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "klt": "101", "fqt": "0",
                "secid": secid, "beg": "20260101", "end": "20261231",
            }
            r = _req.get(url, params=params, timeout=10, proxies={"http": None, "https": None})
            klines = r.json().get("data", {}).get("klines", [])
            closes = [float(k.split(",")[2]) for k in klines]

            if len(closes) < 5:
                return None

            latest = closes[-1]
            ma5 = sum(closes[-5:]) / 5
            ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else None
            ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None

            return {
                "code": code,
                "price": latest,
                "ma5": round(ma5, 2),
                "ma10": round(ma10, 2) if ma10 else None,
                "ma20": round(ma20, 2) if ma20 else None,
                "dist_ma5_pct": round((latest - ma5) / ma5 * 100, 1),
                "dist_ma10_pct": round((latest - ma10) / ma10 * 100, 1) if ma10 else None,
                "dist_ma20_pct": round((latest - ma20) / ma20 * 100, 1) if ma20 else None,
            }
        except Exception:
            return None

    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            fetched = list(executor.map(_fetch_one, stocks))

        for item in fetched:
            if item:
                results[item["code"]] = item
    except Exception as e:
        print(f"  MA data fetch error: {e}", file=sys.stderr)

    return results


def _fetch_indices_sina() -> dict:
    """Fetch real-time index data from Sina Finance API.

    Sina's hq.sinajs.cn is reliable and not blocked by Surge/Clash proxies
    (unlike Eastmoney push2 servers whose DNS gets hijacked to 198.18.x.x).

    Returns dict of {name: {code, close, change_pct, date}} or empty on failure.
    """
    import requests as _req
    import re

    sina_codes = {
        "s_sh000001": ("上证指数", "sh000001"),
        "s_sz399001": ("深证成指", "sz399001"),
        "s_sz399006": ("创业板指", "sz399006"),
        "s_sh000688": ("科创50", "sh000688"),
    }

    try:
        codes_str = ",".join(sina_codes.keys())
        url = f"https://hq.sinajs.cn/list={codes_str}"
        s = _req.Session()
        s.trust_env = False  # Skip system proxy
        r = s.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=10)
        r.raise_for_status()

        indices = {}
        today_str = datetime.now().strftime("%Y-%m-%d")
        # Parse: var hq_str_s_sh000001="上证指数,4082.4740,-40.2020,-0.98,7651695,111308199";
        for line in r.text.strip().split("\n"):
            m = re.match(r'var hq_str_(\w+)="(.+?)";', line)
            if not m:
                continue
            sina_code = m.group(1)
            parts = m.group(2).split(",")
            if len(parts) < 4 or sina_code not in sina_codes:
                continue
            name, our_code = sina_codes[sina_code]
            indices[name] = {
                "code": our_code,
                "close": round(float(parts[1]), 3),
                "change_pct": round(float(parts[3]), 2),
                "date": today_str,
            }
        return indices
    except Exception as e:
        print(f"  Sina index fetch failed: {e}", file=sys.stderr)
        return {}


def _fetch_breadth_sina() -> dict | None:
    """Fetch market breadth (up/down/flat counts) from Sina Finance.

    Paginates through Sina's A-share real-time list (80 per page, ~65 pages).
    Returns dict with up/down/flat/total or None on failure.
    """
    import requests as _req

    PAGE_SIZE = 80  # Sina max per page
    MAX_PAGES = 80  # Safety cap (~6400 stocks)
    url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

    try:
        s = _req.Session()
        s.trust_env = False

        all_stocks = []
        for page in range(1, MAX_PAGES + 1):
            params = {
                "page": page,
                "num": PAGE_SIZE,
                "sort": "symbol",
                "asc": 1,
                "node": "hs_a",
                "symbol": "",
                "_s_r_a": "page",
            }
            r = s.get(url, params=params, timeout=15)
            r.raise_for_status()

            data = json.loads(r.text)
            if not data:
                break
            all_stocks.extend(data)
            if len(data) < PAGE_SIZE:
                break  # Last page

        if not all_stocks:
            return None

        up = sum(1 for st in all_stocks if float(st.get("changepercent", 0)) > 0)
        down = sum(1 for st in all_stocks if float(st.get("changepercent", 0)) < 0)
        flat = sum(1 for st in all_stocks if float(st.get("changepercent", 0)) == 0)
        return {"up": up, "down": down, "flat": flat, "total": len(all_stocks)}
    except Exception as e:
        print(f"  Sina breadth fetch failed: {e}", file=sys.stderr)
        return None


def _fetch_sectors_sina() -> dict | None:
    """Fetch top/bottom sector rankings from Sina Finance.

    Parses Sina's sinaindustry endpoint for sector change percentages.
    Returns dict with top5/bottom5 lists or None on failure.
    """
    import requests as _req
    import re

    try:
        s = _req.Session()
        s.trust_env = False
        r = s.get(
            "http://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php",
            timeout=10,
        )
        r.raise_for_status()

        m = re.search(r'var\s+\w+\s*=\s*({.+})', r.text)
        if not m:
            return None

        sectors = []
        for _key, val in re.findall(r'"(\w+)":"([^"]+)"', m.group(1)):
            parts = val.split(",")
            if len(parts) >= 6 and parts[5]:
                sectors.append({
                    "板块名称": parts[1],
                    "涨跌幅": round(float(parts[5]), 2),
                })

        if not sectors:
            return None

        sectors.sort(key=lambda x: x["涨跌幅"], reverse=True)
        return {
            "top5": sectors[:5],
            "bottom5": sectors[-5:][::-1],  # worst first
        }
    except Exception as e:
        print(f"  Sina sectors fetch failed: {e}", file=sys.stderr)
        return None


def _fetch_market_cheesefortune() -> dict | None:
    """Fetch market overview from CheeseForTune API.

    Returns dict with breadth and sectors, or None on failure.
    Uses v4/marketSummary for breadth and v3/plateStatPc for sectors.
    """
    try:
        from scripts.cheesefortune_client import CheeseFortuneClient
    except ImportError:
        try:
            from cheesefortune_client import CheeseFortuneClient
        except ImportError:
            return None

    try:
        c = CheeseFortuneClient()
        result = {}

        # --- Breadth from marketSummary ---
        try:
            r = c._request(
                f"{c.BASE_URL}/api/v4/market/marketSummary?isCN=true"
            )
            if r.get("code") == "000" and r.get("datas"):
                d = r["datas"]
                rfs = d.get("rise_fall_stat", {})
                if rfs:
                    result["breadth"] = {
                        "up": rfs.get("r", 0),
                        "down": rfs.get("f", 0),
                        "flat": rfs.get("p", 0),
                        "total": rfs.get("r", 0) + rfs.get("f", 0) + rfs.get("p", 0),
                        "distribution": dict(zip(
                            rfs.get("temp", []),
                            rfs.get("list", []),
                        )),
                    }
        except Exception as e:
            print(f"  CheeseForTune breadth failed: {e}", file=sys.stderr)

        # --- Sectors from plateStatPc ---
        try:
            r_top = c._request(
                f"{c.BASE_URL}/api/v3/market/plateStatPc"
                "?ascOrDesc=1&step=1&type=13&isCN=true"
            )
            r_bot = c._request(
                f"{c.BASE_URL}/api/v3/market/plateStatPc"
                "?ascOrDesc=-1&step=1&type=13&isCN=true"
            )

            top5, bot5 = [], []
            if r_top.get("code") == "000":
                for s in r_top["datas"].get("data", [])[:5]:
                    top5.append({
                        "板块名称": s.get("name", s.get("code", "")),
                        "涨跌幅": round(float(s.get("chg", 0)), 2),
                    })
            if r_bot.get("code") == "000":
                for s in r_bot["datas"].get("data", [])[:5]:
                    bot5.append({
                        "板块名称": s.get("name", s.get("code", "")),
                        "涨跌幅": round(float(s.get("chg", 0)), 2),
                    })

            if top5 or bot5:
                result["sectors"] = {"top5": top5, "bottom5": bot5}
        except Exception as e:
            print(f"  CheeseForTune sectors failed: {e}", file=sys.stderr)

        return result if result else None
    except Exception as e:
        print(f"  CheeseForTune market overview failed: {e}", file=sys.stderr)
        return None


def fetch_market_overview() -> dict:
    """Fetch market indices, breadth, and sector data.

    Data sources (in priority order):
    - Indices: Sina Finance real-time → AkShare historical daily
    - Breadth: CheeseForTune marketSummary → Sina paginated → AkShare
    - Sectors: CheeseForTune plateStatPc → Sina sinaindustry → AkShare

    Returns partial data on failure — never crashes.
    """
    try:
        import akshare as ak
    except ImportError:
        ak = None

    result = {"timestamp": datetime.now().isoformat()}

    # --- Major indices (Sina real-time, then AkShare historical fallback) ---
    indices = _fetch_indices_sina()

    missing = {"上证指数", "深证成指", "创业板指", "科创50"} - set(indices.keys())
    if missing and ak:
        fallback_map = {
            "上证指数": "sh000001",
            "深证成指": "sz399001",
            "创业板指": "sz399006",
            "科创50": "sh000688",
        }
        for name in missing:
            code = fallback_map[name]
            try:
                df = ak.stock_zh_index_daily(symbol=code)
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    close_val = float(latest["close"])
                    prev_val = float(prev["close"])
                    change_pct = round((close_val - prev_val) / prev_val * 100, 2) if prev_val else 0
                    indices[name] = {
                        "code": code,
                        "close": close_val,
                        "change_pct": change_pct,
                        "date": str(latest["date"]),
                    }
            except Exception as e:
                indices[name] = {"error": str(e)}

    result["indices"] = indices

    # --- Breadth + Sectors (CheeseForTune primary) ---
    cf = _fetch_market_cheesefortune()

    if cf and "breadth" in cf:
        result["breadth"] = cf["breadth"]
    else:
        # Sina fallback for breadth
        breadth = _fetch_breadth_sina()
        if breadth:
            result["breadth"] = breadth
        elif ak:
            try:
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    up = int(len(df[df["涨跌幅"] > 0]))
                    down = int(len(df[df["涨跌幅"] < 0]))
                    flat = int(len(df[df["涨跌幅"] == 0]))
                    result["breadth"] = {"up": up, "down": down, "flat": flat, "total": len(df)}
            except Exception as e:
                result["breadth_error"] = str(e)

    if cf and "sectors" in cf:
        result["sectors"] = cf["sectors"]
    else:
        # Sina fallback for sectors
        sectors = _fetch_sectors_sina()
        if sectors:
            result["sectors"] = sectors
        elif ak:
            try:
                df = ak.stock_board_industry_name_em()
                if df is not None and not df.empty and "涨跌幅" in df.columns:
                    top5 = df.nlargest(5, "涨跌幅")[["板块名称", "涨跌幅"]].to_dict("records")
                    bot5 = df.nsmallest(5, "涨跌幅")[["板块名称", "涨跌幅"]].to_dict("records")
                    result["sectors"] = {"top5": top5, "bottom5": bot5}
            except Exception as e:
                result["sectors_error"] = str(e)

    return result


def fetch_position_prices(positions: list[dict]) -> dict:
    """Fetch current prices for active positions.

    Tries AkShare (Eastmoney) first; falls back to CheeseForTune kline API
    for any stocks that fail (Eastmoney push2 servers are unreliable).

    Args:
        positions: List of position dicts with "code" key.

    Returns:
        Dict keyed by code with price data.
    """
    if not positions:
        return {}

    prices = {}
    failed_codes = []

    # Try AkShare first
    try:
        import akshare as ak
        for pos in positions:
            code = pos["code"].split(".")[0]
            try:
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
                df = ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date,
                )
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
                    volumes = [int(v) for v in df["成交量"].tail(30).tolist() if v is not None]
                    mavol30 = round(sum(volumes) / len(volumes), 2) if volumes else None
                    latest_volume = int(latest["成交量"])
                    prices[code] = {
                        "code": code,
                        "name": pos.get("name", ""),
                        "date": str(latest["日期"]),
                        "price": float(latest["收盘"]),
                        "open": float(latest["开盘"]),
                        "high": float(latest["最高"]),
                        "low": float(latest["最低"]),
                        "prev_close": float(prev["收盘"]),
                        "change_pct": float(latest["涨跌幅"]),
                        "volume": latest_volume,
                        "mavol30": mavol30,
                        "volume_below_mavol30": bool(mavol30 and latest_volume < mavol30),
                        "amount": float(latest["成交额"]),
                        "turnover_rate": float(latest["换手率"]),
                        "source": "akshare",
                    }
                else:
                    failed_codes.append(pos)
            except Exception:
                failed_codes.append(pos)
    except ImportError:
        failed_codes = list(positions)

    # Fallback: CheeseForTune kline API for failures
    if failed_codes:
        print(f"  AkShare failed for {len(failed_codes)} stocks, trying CheeseForTune kline...", file=sys.stderr)
        try:
            client = CheeseFortuneClient()
            for pos in failed_codes:
                code = pos["code"].split(".")[0]
                cf_code = normalize_code(code)
                try:
                    kline = client.get_kline(cf_code, days=35)
                    if kline and len(kline) > 0:
                        # kline data: list of [date, close, volume, amount, time, null]
                        latest = kline[-1]
                        prev = kline[-2] if len(kline) > 1 else latest
                        price = float(latest[1]) if len(latest) > 1 else 0
                        prev_price = float(prev[1]) if len(prev) > 1 else price
                        latest_volume = int(latest[2]) if len(latest) > 2 and latest[2] is not None else 0
                        volumes = [int(row[2]) for row in kline[-30:] if len(row) > 2 and row[2] is not None]
                        mavol30 = round(sum(volumes) / len(volumes), 2) if volumes else None
                        change_pct = round((price - prev_price) / prev_price * 100, 2) if prev_price else 0
                        prices[code] = {
                            "code": code,
                            "name": pos.get("name", ""),
                            "date": str(latest[0]) if latest[0] else "",
                            "price": price,
                            "volume": latest_volume,
                            "mavol30": mavol30,
                            "volume_below_mavol30": bool(mavol30 and latest_volume < mavol30),
                            "change_pct": change_pct,
                            "source": "cheesefortune_kline",
                        }
                    else:
                        prices[code] = {"code": code, "error": "No kline data"}
                except Exception as e:
                    prices[code] = {"code": code, "error": f"kline fallback: {e}"}
        except Exception as e:
            for pos in failed_codes:
                code = pos["code"].split(".")[0]
                prices[code] = {"code": code, "error": f"all sources failed: {e}"}

    return prices


def fetch_missed_opportunity_prices(recent_watchlists: list[dict]) -> list[dict]:
    """Get current prices for past recommendations to check missed opportunities.

    Tries AkShare first, falls back to CheeseForTune kline for failures.

    Args:
        recent_watchlists: List of watchlist dicts (loaded from watchlist/*.json)

    Returns:
        List of dicts with code, recommended_date, recommended_price, current_price, return_pct.
    """
    # Collect unique codes from recommendations (excluding AVOID)
    seen = set()
    candidates = []
    for wl in recent_watchlists:
        date = wl.get("date", "")
        for rec in wl.get("recommendations", []):
            recommendation = rec.get("recommendation", rec.get("action", ""))
            if recommendation == "AVOID":
                continue
            code = str(rec.get("code", "")).split(".")[0]
            if not code or code in seen:
                continue
            seen.add(code)
            candidates.append({
                "code": code,
                "name": rec.get("name", ""),
                "recommended_date": date,
                "recommended_price": rec.get("price", 0),
                "recommendation": recommendation,
            })

    if not candidates:
        return []

    # Fetch current prices — use fetch_position_prices which has fallback
    price_data = fetch_position_prices(
        [{"code": c["code"], "name": c.get("name", "")} for c in candidates]
    )

    results = []
    for c in candidates:
        code = c["code"]
        pd = price_data.get(code, {})
        current_price = pd.get("price")
        rec_price = c["recommended_price"]
        return_pct = None
        if current_price and rec_price:
            return_pct = round((current_price - rec_price) / rec_price * 100, 2)
        results.append({
            **c,
            "current_price": current_price,
            "return_pct": return_pct,
        })

    return results


def load_recent_watchlists(days: int = 5) -> list[dict]:
    """Load recent watchlist JSON files from runs/ and legacy watchlist/ dir.

    Args:
        days: Number of days back to look.

    Returns:
        List of watchlist dicts, newest first.
    """
    watchlists = []

    # New location: runs/*/output/watchlist.json
    runs_dir = PROJECT_ROOT / "runs"
    if runs_dir.exists():
        for d in sorted(runs_dir.iterdir(), reverse=True):
            if len(watchlists) >= days:
                break
            wl_file = d / "output" / "watchlist.json"
            if wl_file.exists():
                try:
                    watchlists.append(json.loads(wl_file.read_text(encoding="utf-8")))
                except (json.JSONDecodeError, IOError):
                    pass

    # Legacy fallback: watchlist/*.json
    if len(watchlists) < days:
        files = sorted(WATCHLIST_DIR.glob("*.json"), reverse=True)
        for f in files:
            if len(watchlists) >= days:
                break
            try:
                wl = json.loads(f.read_text(encoding="utf-8"))
                # Avoid duplicates by date
                existing_dates = {w.get("date") for w in watchlists}
                if wl.get("date") not in existing_dates:
                    watchlists.append(wl)
            except (json.JSONDecodeError, IOError) as e:
                print(f"  Warning: skipping watchlist {f.name}: {e}", file=sys.stderr)

    return watchlists


def save_crawl_data(date: str, data: dict, output_dir: Path | None = None) -> Path:
    """Save strategy pool crawl data."""
    if output_dir:
        out = output_dir / "crawl.json"
    else:
        out = CRAWL_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def save_market_data(date: str, data: dict, output_dir: Path | None = None) -> Path:
    """Save market overview data."""
    if output_dir:
        out = output_dir / "market.json"
    else:
        out = MARKET_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def save_price_data(date: str, data: dict, output_dir: Path | None = None) -> Path:
    """Save price snapshots."""
    if output_dir:
        out = output_dir / "prices.json"
    else:
        out = PRICES_DIR / f"{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python data_collector.py strategy     # Fetch strategy pool")
        print("  python data_collector.py market        # Fetch market overview")
        print("  python data_collector.py positions     # Fetch position prices")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "strategy":
        result = fetch_strategy_pool()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == "market":
        result = fetch_market_overview()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif cmd == "positions":
        from position_manager import load_active_positions
        positions = load_active_positions()
        result = fetch_position_prices(positions)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Unknown command: {cmd}")
