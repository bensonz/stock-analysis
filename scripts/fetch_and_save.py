#!/usr/bin/env python3
"""
Stock Price Fetcher + Historical Data Saver
Usage:
  python fetch_and_save.py prices 600519 002721 688002   # Fetch & save prices
  python fetch_and_save.py market                         # Save market snapshot
  python fetch_and_save.py history 600519 --days 30       # Save historical OHLCV

All data saved to ../data/ relative to this script.
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

try:
    import akshare as ak
except ImportError:
    print(json.dumps({"error": "akshare not installed. Run: pip install akshare"}))
    sys.exit(1)

DATA_DIR = Path(__file__).parent.parent / "data"
PRICES_DIR = DATA_DIR / "prices"
MARKET_DIR = DATA_DIR / "market"

for d in [PRICES_DIR, MARKET_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def get_stock_price(code: str) -> dict:
    """Fetch latest price for a single stock."""
    try:
        code = code.split('.')[0]
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date)
        if df.empty:
            return {"code": code, "error": "No data found"}
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        return {
            "code": code,
            "date": str(latest['日期']),
            "price": float(latest['收盘']),
            "open": float(latest['开盘']),
            "high": float(latest['最高']),
            "low": float(latest['最低']),
            "prev_close": float(prev['收盘']),
            "change_pct": float(latest['涨跌幅']),
            "volume": int(latest['成交量']),
            "amount": float(latest['成交额']),
            "turnover_rate": float(latest['换手率']),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"code": code, "error": str(e)}


def save_prices(codes: list):
    """Fetch prices and append to daily price file."""
    today = datetime.now().strftime('%Y-%m-%d')
    price_file = PRICES_DIR / f"{today}.json"

    existing = {}
    if price_file.exists():
        existing = json.loads(price_file.read_text())

    for code in codes:
        result = get_stock_price(code)
        existing[code] = result

    price_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    print(json.dumps({"saved": str(price_file), "count": len(codes), "stocks": existing}, ensure_ascii=False, indent=2))


def save_market_snapshot():
    """Save market indices, breadth, and sector data."""
    today = datetime.now().strftime('%Y-%m-%d')
    snapshot = {"date": today, "timestamp": datetime.now().isoformat()}

    # Major indices
    try:
        indices = {}
        for name, code in [("上证指数", "000001"), ("深证成指", "399001"), ("创业板指", "399006"), ("科创50", "000688")]:
            df = ak.stock_zh_index_daily(symbol=f"sh{code}" if code.startswith("000") and code != "000688" else f"sz{code}")
            if not df.empty:
                latest = df.iloc[-1]
                indices[name] = {
                    "code": code,
                    "close": float(latest['close']),
                    "date": str(latest['date']),
                }
        snapshot["indices"] = indices
    except Exception as e:
        snapshot["indices_error"] = str(e)

    # Market breadth (advance/decline)
    try:
        df = ak.stock_zh_a_spot_em()
        if not df.empty:
            up = len(df[df['涨跌幅'] > 0])
            down = len(df[df['涨跌幅'] < 0])
            flat = len(df[df['涨跌幅'] == 0])
            snapshot["breadth"] = {"up": up, "down": down, "flat": flat, "total": len(df)}
    except Exception as e:
        snapshot["breadth_error"] = str(e)

    # Top sectors
    try:
        df = ak.stock_board_industry_name_em()
        if not df.empty and '涨跌幅' in df.columns:
            top5 = df.nlargest(5, '涨跌幅')[['板块名称', '涨跌幅']].to_dict('records')
            bot5 = df.nsmallest(5, '涨跌幅')[['板块名称', '涨跌幅']].to_dict('records')
            snapshot["sectors"] = {"top5": top5, "bottom5": bot5}
    except Exception as e:
        snapshot["sectors_error"] = str(e)

    market_file = MARKET_DIR / f"{today}.json"
    market_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(json.dumps({"saved": str(market_file), "snapshot": snapshot}, ensure_ascii=False, indent=2))


def save_history(code: str, days: int = 60):
    """Save historical OHLCV for a stock."""
    code = code.split('.')[0]
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

    try:
        df = ak.stock_zh_a_hist(symbol=code, period='daily', start_date=start_date, end_date=end_date)
        if df.empty:
            print(json.dumps({"code": code, "error": "No data"}))
            return

        records = []
        for _, row in df.iterrows():
            records.append({
                "date": str(row['日期']),
                "open": float(row['开盘']),
                "high": float(row['最高']),
                "low": float(row['最低']),
                "close": float(row['收盘']),
                "volume": int(row['成交量']),
                "amount": float(row['成交额']),
                "change_pct": float(row['涨跌幅']),
                "turnover": float(row['换手率']),
            })

        hist_file = PRICES_DIR / f"{code}_history.json"
        hist_file.write_text(json.dumps({
            "code": code, "days": days, "count": len(records),
            "from": records[0]["date"], "to": records[-1]["date"],
            "updated": datetime.now().isoformat(),
            "data": records
        }, ensure_ascii=False, indent=2))
        print(json.dumps({"saved": str(hist_file), "code": code, "records": len(records)}))
    except Exception as e:
        print(json.dumps({"code": code, "error": str(e)}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_and_save.py prices CODE1 CODE2 ...  # Daily prices")
        print("  python fetch_and_save.py market                   # Market snapshot")
        print("  python fetch_and_save.py history CODE [--days N]  # Historical OHLCV")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "prices":
        save_prices(sys.argv[2:])
    elif cmd == "market":
        save_market_snapshot()
    elif cmd == "history":
        days = 60
        code = sys.argv[2] if len(sys.argv) > 2 else None
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            days = int(sys.argv[idx + 1])
        if code:
            save_history(code, days)
        else:
            print(json.dumps({"error": "Need a stock code"}))
    else:
        print(json.dumps({"error": f"Unknown command: {cmd}"}))
