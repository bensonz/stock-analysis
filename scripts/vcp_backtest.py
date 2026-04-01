#!/usr/bin/env python3
"""
vcp_backtest.py — Backtest the VCP scanner

For each historical scan date:
1. Run VCP scanner
2. Simulate buying the top N picks at next day's open
3. Track returns at +5d, +10d, +20d
4. Compare vs index (上证)

Usage: python vcp_backtest.py [min_rps] [base_days] [scan_interval_days]
"""

import sqlite3
import sys
import os
import json
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rps_calculator import compute_ma_rps
from vcp_scanner import scan_vcp


def get_trading_dates(conn, min_date=None, max_date=None):
    """Get all trading dates in the DB."""
    q = "SELECT DISTINCT date FROM daily_prices"
    conditions = []
    if min_date:
        conditions.append(f"date >= '{min_date}'")
    if max_date:
        conditions.append(f"date <= '{max_date}'")
    if conditions:
        q += " WHERE " + " AND ".join(conditions)
    q += " ORDER BY date"
    return [r[0] for r in conn.execute(q).fetchall()]


def get_price_on_date(conn, code, date, field="open"):
    """Get a stock's price on a specific date. Returns None if not found."""
    row = conn.execute(
        f"SELECT {field} FROM daily_prices WHERE code=? AND date=?",
        (code, date)
    ).fetchone()
    return row[0] if row and row[0] else None


def get_index_return(conn, date_from, date_to):
    """Get 上证指数 return between two dates (using 000001 proxy or similar)."""
    # We might not have index data, use a large-cap ETF or just skip
    return None


def run_backtest(
    db_path: str,
    min_rps: float = 85,
    base_days: int = 120,
    scan_interval: int = 10,
    top_n_per_scan: int = 10,
    hold_periods: list = None,
    min_score: int = 40,
):
    if hold_periods is None:
        hold_periods = [5, 10, 20]
    
    conn = sqlite3.connect(db_path)
    all_dates = get_trading_dates(conn)
    
    # Need enough history for the scanner (250d for RPS + base_days)
    # Start scanning from index 260 onwards
    start_idx = 260
    if start_idx >= len(all_dates):
        print("Not enough data for backtest")
        return
    
    # Pick scan dates at intervals
    scan_dates = []
    idx = start_idx
    while idx < len(all_dates) - max(hold_periods) - 1:
        scan_dates.append((idx, all_dates[idx]))
        idx += scan_interval
    
    print(f"Backtest config:")
    print(f"  Min RPS (60/120/250): {min_rps}")
    print(f"  Base window: {base_days}d")
    print(f"  Min score: {min_score}")
    print(f"  Scan dates: {len(scan_dates)} ({scan_dates[0][1]} to {scan_dates[-1][1]})")
    print(f"  Hold periods: {hold_periods}")
    print(f"  Top picks per scan: {top_n_per_scan}")
    print()
    
    all_trades = []
    
    for scan_num, (date_idx, scan_date) in enumerate(scan_dates):
        # Compute RPS as of scan_date
        rps = compute_ma_rps(db_path, date=scan_date)
        
        # Run VCP scanner
        picks = scan_vcp(
            db_path, rps_data=rps, min_rps120=min_rps,
            date=scan_date, base_days=base_days, top_n=top_n_per_scan
        )
        
        # Filter by min score
        picks = [p for p in picks if p["score"] >= min_score]
        
        if not picks:
            continue
        
        # For each pick, get entry price (next day open) and exit prices
        entry_date_idx = date_idx + 1
        if entry_date_idx >= len(all_dates):
            continue
        entry_date = all_dates[entry_date_idx]
        
        for pick in picks:
            code = pick["code"]
            entry_price = get_price_on_date(conn, code, entry_date, "open")
            if not entry_price or entry_price <= 0:
                continue
            
            trade = {
                "scan_date": scan_date,
                "entry_date": entry_date,
                "code": code,
                "name": pick["name"],
                "score": pick["score"],
                "entry_price": entry_price,
                "num_contractions": pick["num_contractions"],
                "last_depth": pick["last_depth"],
                "contraction_ratio": pick["contraction_ratio"],
                "vol_ratio": pick["vol_ratio"],
                "vol_declining": pick.get("vol_declining", False),
                "nearest_ma": pick.get("nearest_ma", "?"),
                "nearest_ma_dist": pick.get("nearest_ma_dist", 99),
                "dist_from_peak": pick["dist_from_peak_pct"],
            }
            
            for period in hold_periods:
                exit_idx = entry_date_idx + period
                if exit_idx < len(all_dates):
                    exit_date = all_dates[exit_idx]
                    exit_price = get_price_on_date(conn, code, exit_date, "close")
                    if exit_price and exit_price > 0:
                        ret = (exit_price - entry_price) / entry_price * 100
                        trade[f"ret_{period}d"] = round(ret, 2)
                    else:
                        trade[f"ret_{period}d"] = None
                else:
                    trade[f"ret_{period}d"] = None
            
            # Max drawdown during holding period (worst close in first 20 days)
            max_dd = 0
            for d in range(1, min(21, len(all_dates) - entry_date_idx)):
                dd_date = all_dates[entry_date_idx + d]
                dd_price = get_price_on_date(conn, code, dd_date, "low")
                if dd_price and dd_price > 0:
                    dd = (dd_price - entry_price) / entry_price * 100
                    max_dd = min(max_dd, dd)
            trade["max_dd_20d"] = round(max_dd, 2)
            
            all_trades.append(trade)
        
        if (scan_num + 1) % 5 == 0:
            print(f"  Scanned {scan_num + 1}/{len(scan_dates)} dates, {len(all_trades)} trades so far")
    
    conn.close()
    
    # --- Results ---
    print(f"\n{'='*70}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*70}")
    print(f"Total trades: {len(all_trades)}")
    
    if not all_trades:
        print("No trades found.")
        return
    
    for period in hold_periods:
        key = f"ret_{period}d"
        returns = [t[key] for t in all_trades if t[key] is not None]
        if not returns:
            continue
        
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r <= 0]
        
        avg = sum(returns) / len(returns)
        win_rate = len(winners) / len(returns) * 100
        avg_win = sum(winners) / len(winners) if winners else 0
        avg_loss = sum(losers) / len(losers) if losers else 0
        median = sorted(returns)[len(returns) // 2]
        best = max(returns)
        worst = min(returns)
        
        print(f"\n--- {period}-day returns ---")
        print(f"  Trades:   {len(returns)}")
        print(f"  Win rate: {win_rate:.1f}%")
        print(f"  Avg ret:  {avg:+.2f}%")
        print(f"  Median:   {median:+.2f}%")
        print(f"  Avg win:  {avg_win:+.2f}%")
        print(f"  Avg loss: {avg_loss:+.2f}%")
        print(f"  Best:     {best:+.2f}%")
        print(f"  Worst:    {worst:+.2f}%")
    
    # Max drawdown stats
    dds = [t["max_dd_20d"] for t in all_trades]
    print(f"\n--- Max drawdown (20d) ---")
    print(f"  Avg:    {sum(dds)/len(dds):.2f}%")
    print(f"  Worst:  {min(dds):.2f}%")
    
    # --- Breakdown by score ---
    print(f"\n--- By score bucket ---")
    buckets = [(60, 999, "60+"), (50, 59, "50-59"), (40, 49, "40-49"), (30, 39, "30-39")]
    for lo, hi, label in buckets:
        bucket_trades = [t for t in all_trades if lo <= t["score"] <= hi]
        if not bucket_trades:
            continue
        rets_10 = [t["ret_10d"] for t in bucket_trades if t.get("ret_10d") is not None]
        if rets_10:
            wr = len([r for r in rets_10 if r > 0]) / len(rets_10) * 100
            avg = sum(rets_10) / len(rets_10)
            print(f"  Score {label}: {len(rets_10)} trades, WR={wr:.0f}%, avg={avg:+.2f}%")
    
    # --- Breakdown by vol_declining ---
    print(f"\n--- Volume declining across contractions ---")
    for vd_val, label in [(True, "Vol declining ✓"), (False, "Vol NOT declining")]:
        subset = [t for t in all_trades if t.get("vol_declining") == vd_val]
        rets = [t["ret_10d"] for t in subset if t.get("ret_10d") is not None]
        if rets:
            wr = len([r for r in rets if r > 0]) / len(rets) * 100
            avg = sum(rets) / len(rets)
            print(f"  {label}: {len(rets)} trades, WR={wr:.0f}%, avg 10d={avg:+.2f}%")
    
    # --- Breakdown by MA proximity ---
    print(f"\n--- MA proximity (entry near MA) ---")
    for threshold, label in [(3, "< 3%"), (6, "3-6%"), (99, "> 6%")]:
        if threshold == 3:
            subset = [t for t in all_trades if t.get("nearest_ma_dist", 99) < 3]
        elif threshold == 6:
            subset = [t for t in all_trades if 3 <= t.get("nearest_ma_dist", 99) < 6]
        else:
            subset = [t for t in all_trades if t.get("nearest_ma_dist", 99) >= 6]
        rets = [t["ret_10d"] for t in subset if t.get("ret_10d") is not None]
        if rets:
            wr = len([r for r in rets if r > 0]) / len(rets) * 100
            avg = sum(rets) / len(rets)
            print(f"  MA dist {label}: {len(rets)} trades, WR={wr:.0f}%, avg 10d={avg:+.2f}%")
    
    # --- Breakdown by contraction ratio ---
    print(f"\n--- Contraction ratio (last/first depth) ---")
    for threshold, label in [(0.4, "< 0.4 (tight)"), (0.7, "0.4-0.7 (ok)"), (1.0, "0.7+ (loose)")]:
        if threshold == 0.4:
            subset = [t for t in all_trades if t.get("contraction_ratio", 1) < 0.4]
        elif threshold == 0.7:
            subset = [t for t in all_trades if 0.4 <= t.get("contraction_ratio", 1) < 0.7]
        else:
            subset = [t for t in all_trades if t.get("contraction_ratio", 1) >= 0.7]
        rets = [t["ret_10d"] for t in subset if t.get("ret_10d") is not None]
        if rets:
            wr = len([r for r in rets if r > 0]) / len(rets) * 100
            avg = sum(rets) / len(rets)
            print(f"  Ratio {label}: {len(rets)} trades, WR={wr:.0f}%, avg 10d={avg:+.2f}%")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "pricedb", "ashare_prices.db")
    
    min_rps = float(sys.argv[1]) if len(sys.argv) > 1 else 85
    base_days = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    run_backtest(db_path, min_rps=min_rps, base_days=base_days, scan_interval=interval)
