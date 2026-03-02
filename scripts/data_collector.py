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
import sys
import time
import urllib.request
import ssl
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

    Uses the strategy detail API endpoint (reverse-engineered).
    Returns list of stock dicts or None if endpoint doesn't work.
    """
    client = CheeseFortuneClient()
    # Try the strategy stock list endpoint
    url = f"{client.BASE_URL}/api/v3/stockP/strategyStockList?strategyId={strategy_id}"
    try:
        result = client._request(url)
        if result.get("code") == "000" and result.get("datas"):
            raw_stocks = result["datas"]
            if isinstance(raw_stocks, list):
                return _parse_strategy_stocks(raw_stocks)
            # Sometimes datas is a dict with a stocks key
            if isinstance(raw_stocks, dict) and "stocks" in raw_stocks:
                return _parse_strategy_stocks(raw_stocks["stocks"])
    except Exception:
        pass

    # Try alternative endpoint
    url = f"{client.BASE_URL}/api/v2/strategy/stockList?strategyId={strategy_id}"
    try:
        result = client._request(url)
        if result.get("code") == "000" and result.get("datas"):
            raw_stocks = result["datas"]
            if isinstance(raw_stocks, list):
                return _parse_strategy_stocks(raw_stocks)
    except Exception:
        pass

    return None


def _parse_strategy_stocks(raw: list) -> list[dict]:
    """Parse raw API response into normalized stock dicts."""
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


def batch_enrich(stocks: list[dict]) -> list[dict]:
    """Enrich stocks in RPS 75-95% zone using CheeseForTune batch API.

    Args:
        stocks: List of stock dicts with at least "code" key.

    Returns:
        List of enriched stock summary dicts.
    """
    if not stocks:
        return []

    codes = [normalize_code(s["code"]) for s in stocks]
    try:
        client = CheeseFortuneClient()
        results = client.get_batch_summaries(codes)
        return results
    except Exception as e:
        print(f"  Batch enrich error: {e}", file=sys.stderr)
        return [{"code": c, "error": str(e)} for c in codes]


def fetch_market_overview() -> dict:
    """Fetch market indices, breadth, and sector data via AkShare.

    Returns partial data on failure — never crashes.
    """
    try:
        import akshare as ak
    except ImportError:
        return {"error": "akshare not installed"}

    result = {"timestamp": datetime.now().isoformat()}

    # Major indices
    try:
        indices = {}
        for name, code in [
            ("上证指数", "sh000001"),
            ("深证成指", "sz399001"),
            ("创业板指", "sz399006"),
            ("科创50", "sh000688"),
        ]:
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
    except Exception as e:
        result["indices_error"] = str(e)

    # Market breadth
    try:
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            up = int(len(df[df["涨跌幅"] > 0]))
            down = int(len(df[df["涨跌幅"] < 0]))
            flat = int(len(df[df["涨跌幅"] == 0]))
            result["breadth"] = {"up": up, "down": down, "flat": flat, "total": len(df)}
    except Exception as e:
        result["breadth_error"] = str(e)

    # Top/bottom sectors
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
    """Fetch current prices for active positions using AkShare.

    Args:
        positions: List of position dicts with "code" key.

    Returns:
        Dict keyed by code with price data.
    """
    if not positions:
        return {}

    try:
        import akshare as ak
    except ImportError:
        return {p["code"]: {"error": "akshare not installed"} for p in positions}

    prices = {}
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
                }
            else:
                prices[code] = {"code": code, "error": "No data"}
        except Exception as e:
            prices[code] = {"code": code, "error": str(e)}

    return prices


def fetch_missed_opportunity_prices(recent_watchlists: list[dict]) -> list[dict]:
    """Get current prices for past recommendations to check missed opportunities.

    Args:
        recent_watchlists: List of watchlist dicts (loaded from watchlist/*.json)

    Returns:
        List of dicts with code, recommended_date, recommended_price, current_price, return_pct.
    """
    try:
        import akshare as ak
    except ImportError:
        return []

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

    # Fetch current prices
    results = []
    for c in candidates:
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(
                symbol=c["code"], period="daily",
                start_date=start_date, end_date=end_date,
            )
            if df is not None and not df.empty:
                current_price = float(df.iloc[-1]["收盘"])
                rec_price = c["recommended_price"]
                return_pct = round((current_price - rec_price) / rec_price * 100, 2) if rec_price else 0
                results.append({
                    **c,
                    "current_price": current_price,
                    "return_pct": return_pct,
                })
            else:
                results.append({**c, "current_price": None, "return_pct": None})
        except Exception as e:
            results.append({**c, "current_price": None, "return_pct": None, "error": str(e)})

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
