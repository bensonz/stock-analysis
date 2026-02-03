#!/usr/bin/env python3
"""
Stock Price Fetcher using AkShare
Usage: python fetch_price.py 600519 002721 688002
Output: JSON with current prices
"""

import sys
import json
from datetime import datetime, timedelta

try:
    import akshare as ak
except ImportError:
    print(json.dumps({"error": "akshare not installed. Run: pip install akshare"}))
    sys.exit(1)


def get_stock_price(code: str) -> dict:
    """Fetch latest price for a single stock using historical data."""
    try:
        # Normalize code (remove market suffix if present)
        code = code.split('.')[0]
        
        # Get recent data (last 5 days to ensure we have trading data)
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
        
        df = ak.stock_zh_a_hist(
            symbol=code, 
            period='daily', 
            start_date=start_date, 
            end_date=end_date
        )
        
        if df.empty:
            return {"code": code, "error": "No data found"}
        
        # Get the latest row
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
            "change_amt": float(latest['涨跌额']),
            "volume": int(latest['成交量']),
            "amount": float(latest['成交额']),
            "turnover_rate": float(latest['换手率']),
            "amplitude": float(latest['振幅']),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"code": code, "error": str(e)}


def get_stock_name(code: str) -> str:
    """Get stock name from code."""
    try:
        df = ak.stock_info_a_code_name()
        row = df[df['code'] == code]
        if not row.empty:
            return row.iloc[0]['name']
    except:
        pass
    return ""


def get_multiple_prices(codes: list) -> dict:
    """Fetch prices for multiple stocks."""
    results = {}
    for code in codes:
        result = get_stock_price(code)
        # Try to add name
        if 'error' not in result:
            result['name'] = get_stock_name(code)
        results[code] = result
    
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(codes),
        "stocks": results
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python fetch_price.py CODE1 CODE2 ..."}))
        sys.exit(1)
    
    codes = sys.argv[1:]
    
    if len(codes) == 1:
        result = get_stock_price(codes[0])
        # Add name for single stock
        if 'error' not in result:
            result['name'] = get_stock_name(codes[0])
    else:
        result = get_multiple_prices(codes)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
