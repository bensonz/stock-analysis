#!/usr/bin/env python3
"""
Stock Price Fetcher using AkShare
Usage: python fetch_price.py 600519 002721 688002
Output: JSON with current prices
"""

import sys
import json
from datetime import datetime

try:
    import akshare as ak
except ImportError:
    print(json.dumps({"error": "akshare not installed. Run: pip install akshare"}))
    sys.exit(1)


def get_stock_price(code: str) -> dict:
    """Fetch real-time price for a single stock."""
    try:
        # Normalize code (remove market suffix if present)
        code = code.split('.')[0]
        
        # Determine market prefix
        if code.startswith('6'):
            symbol = f"sh{code}"
        elif code.startswith(('0', '3')):
            symbol = f"sz{code}"
        elif code.startswith('4') or code.startswith('8'):
            symbol = f"bj{code}"  # Beijing Stock Exchange
        else:
            symbol = f"sz{code}"  # Default to Shenzhen
        
        # Fetch real-time quote
        df = ak.stock_zh_a_spot_em()
        
        # Find the stock
        row = df[df['代码'] == code]
        
        if row.empty:
            return {"code": code, "error": "Stock not found"}
        
        row = row.iloc[0]
        
        return {
            "code": code,
            "name": row.get('名称', ''),
            "price": float(row.get('最新价', 0)),
            "change_pct": float(row.get('涨跌幅', 0)),
            "change_amt": float(row.get('涨跌额', 0)),
            "open": float(row.get('今开', 0)),
            "high": float(row.get('最高', 0)),
            "low": float(row.get('最低', 0)),
            "prev_close": float(row.get('昨收', 0)),
            "volume": float(row.get('成交量', 0)),
            "amount": float(row.get('成交额', 0)),
            "turnover_rate": float(row.get('换手率', 0)),
            "pe_ratio": float(row.get('市盈率-动态', 0)) if row.get('市盈率-动态') else None,
            "pb_ratio": float(row.get('市净率', 0)) if row.get('市净率') else None,
            "market_cap": float(row.get('总市值', 0)),
            "float_cap": float(row.get('流通市值', 0)),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"code": code, "error": str(e)}


def get_multiple_prices(codes: list) -> dict:
    """Fetch prices for multiple stocks efficiently."""
    try:
        # Fetch all A-share real-time data once
        df = ak.stock_zh_a_spot_em()
        
        results = {}
        for code in codes:
            code = code.split('.')[0]
            row = df[df['代码'] == code]
            
            if row.empty:
                results[code] = {"code": code, "error": "Stock not found"}
                continue
            
            row = row.iloc[0]
            results[code] = {
                "code": code,
                "name": row.get('名称', ''),
                "price": float(row.get('最新价', 0)),
                "change_pct": float(row.get('涨跌幅', 0)),
                "prev_close": float(row.get('昨收', 0)),
                "volume": float(row.get('成交量', 0)),
                "turnover_rate": float(row.get('换手率', 0)),
                "market_cap": float(row.get('总市值', 0)),
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "stocks": results
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python fetch_price.py CODE1 CODE2 ..."}))
        sys.exit(1)
    
    codes = sys.argv[1:]
    
    if len(codes) == 1:
        result = get_stock_price(codes[0])
    else:
        result = get_multiple_prices(codes)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
