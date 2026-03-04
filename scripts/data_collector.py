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
WATCHLIST_DIR = PROJECT_ROOT / "watchlist"

for d in [CRAWL_DIR, MARKET_DIR, PRICES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Import CheeseForTune client (same directory)
sys.path.insert(0, str(Path(__file__).parent))
from cheesefortune_client import CheeseFortuneClient, normalize_code


def fetch_strategy_pool(strategy_id: str = "352390") -> dict:
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


def fetch_market_overview() -> dict:
    """Fetch market indices, breadth, and sector data.

    Primary: Sina Finance API (reliable, not blocked by Surge/Clash).
    Fallback: AkShare historical daily for indices.
    Breadth/sectors still use AkShare with Eastmoney (may fail under proxy).

    Returns partial data on failure — never crashes.
    """
    try:
        import akshare as ak
    except ImportError:
        ak = None

    result = {"timestamp": datetime.now().isoformat()}

    # --- Major indices (Sina real-time, then AkShare historical fallback) ---
    indices = _fetch_indices_sina()

    # Fall back to AkShare historical daily for any missing indices
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

    # --- Market breadth (Sina first, AkShare fallback) ---
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

    # --- Top/bottom sectors (Sina first, AkShare fallback) ---
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
                start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
                df = ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date,
                )
                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    prev = df.iloc[-2] if len(df) > 1 else latest
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
                        "volume": int(latest["成交量"]),
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
                    kline = client.get_kline(cf_code, days=5)
                    if kline and len(kline) > 0:
                        # kline data: list of [date, close, volume, amount, time, null]
                        latest = kline[-1]
                        prev = kline[-2] if len(kline) > 1 else latest
                        price = float(latest[1]) if len(latest) > 1 else 0
                        prev_price = float(prev[1]) if len(prev) > 1 else price
                        change_pct = round((price - prev_price) / prev_price * 100, 2) if prev_price else 0
                        prices[code] = {
                            "code": code,
                            "name": pos.get("name", ""),
                            "date": str(latest[0]) if latest[0] else "",
                            "price": price,
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
    """Load recent watchlist JSON files.

    Args:
        days: Number of days back to look.

    Returns:
        List of watchlist dicts, newest first.
    """
    watchlists = []
    files = sorted(WATCHLIST_DIR.glob("*.json"), reverse=True)
    for f in files[:days]:
        try:
            watchlists.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, IOError) as e:
            print(f"  Warning: skipping watchlist {f.name}: {e}", file=sys.stderr)
    return watchlists


def save_crawl_data(date: str, data: dict) -> Path:
    """Save strategy pool crawl data to data/crawl/YYYY-MM-DD.json."""
    out = CRAWL_DIR / f"{date}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def save_market_data(date: str, data: dict) -> Path:
    """Save market overview to data/market/YYYY-MM-DD.json."""
    out = MARKET_DIR / f"{date}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def save_price_data(date: str, data: dict) -> Path:
    """Save price snapshots to data/prices/YYYY-MM-DD.json."""
    out = PRICES_DIR / f"{date}.json"
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
