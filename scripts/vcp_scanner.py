#!/usr/bin/env python3
"""
vcp_scanner.py — Minervini VCP (Volatility Contraction Pattern) Scanner v2

Detects actual swing highs/lows to find real contractions,
not fixed time segments. Requires at least 2 distinct pullbacks
with each successive one shallower than the prior.

Swing detection: a swing high is a local max with lower highs on both sides
(using a window of `swing_lookback` days). Same logic inverted for swing lows.
"""

import sqlite3
import sys
import os
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import price_adjust


def find_swings(highs: list, lows: list, lookback: int = 5) -> tuple:
    """Find swing highs and swing lows using a rolling window.
    
    Returns (swing_highs, swing_lows) as lists of (index, price).
    """
    n = len(highs)
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, n - lookback):
        # Swing high: highest in the window
        window_highs = highs[i - lookback : i + lookback + 1]
        if highs[i] == max(window_highs):
            # Avoid duplicates near each other
            if not swing_highs or i - swing_highs[-1][0] >= lookback:
                swing_highs.append((i, highs[i]))
        
        # Swing low: lowest in the window
        window_lows = lows[i - lookback : i + lookback + 1]
        if lows[i] == min(window_lows):
            if not swing_lows or i - swing_lows[-1][0] >= lookback:
                swing_lows.append((i, lows[i]))
    
    return swing_highs, swing_lows


def find_contractions(swing_highs: list, swing_lows: list, volumes: list = None) -> list:
    """Find pullback contractions from swing data.
    
    A contraction = from a swing high down to the next swing low.
    Returns list of (high_idx, high_price, low_idx, low_price, depth_pct, avg_vol).
    avg_vol is the average volume during the contraction period (if volumes provided).
    """
    contractions = []
    
    for hi_idx, hi_price in swing_highs:
        # Find the next swing low AFTER this swing high
        next_low = None
        for lo_idx, lo_price in swing_lows:
            if lo_idx > hi_idx:
                next_low = (lo_idx, lo_price)
                break
        
        if next_low and hi_price > 0:
            lo_idx, lo_price = next_low
            depth = (hi_price - lo_price) / hi_price * 100
            if depth > 3:  # ignore tiny wiggles (<3%)
                # Calculate average volume during this contraction
                avg_vol = 0
                if volumes and lo_idx < len(volumes) and hi_idx < len(volumes):
                    seg_vols = volumes[hi_idx:lo_idx + 1]
                    avg_vol = sum(seg_vols) / len(seg_vols) if seg_vols else 0
                contractions.append((hi_idx, hi_price, lo_idx, lo_price, depth, avg_vol))
    
    return contractions


def scan_vcp(
    db_path: str,
    rps_data: dict = None,
    min_rps120: float = 85,
    date: str = None,
    base_days: int = 120,
    min_contractions: int = 2,
    swing_lookback: int = 5,
    top_n: int = 30,
) -> list:
    """Scan for VCP setups using swing-based contraction detection."""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    if not date:
        date = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()[0]
    
    names = {}
    for row in conn.execute("SELECT code, name FROM stocks"):
        names[row["code"]] = row["name"]
    
    stocks = conn.execute(
        "SELECT DISTINCT code FROM daily_prices GROUP BY code HAVING COUNT(*) >= 250"
    ).fetchall()
    stock_codes = [r["code"] for r in stocks]
    
    if rps_data:
        stock_codes = [c for c in stock_codes 
                       if c in rps_data and isinstance(rps_data[c], dict)
                       and (rps_data[c].get("rps60", 0) or 0) >= min_rps120
                       and (rps_data[c].get("rps120", 0) or 0) >= min_rps120
                       and (rps_data[c].get("rps250", 0) or 0) >= min_rps120]
    
    results = []
    
    price_adjust.ensure_adj_schema(conn)
    for code in stock_codes:
        rows = conn.execute(
            f"SELECT d.date, d.open, d.high, d.low, d.close, d.volume, d.amount, "
            f"{price_adjust.factor_sql()} AS factor FROM daily_prices d"
            f"{price_adjust.adj_join_sql()} "
            "WHERE d.code = ? AND d.date <= ? ORDER BY d.date ASC",
            (code, date)
        ).fetchall()

        # Today-scale adjustment (x_i × f_i / f_last): dividend/split gaps no
        # longer fake contractions, while current/pivot prices stay in real
        # tradeable scale. Volume is NOT adjusted — across a split date volume
        # ratios are distorted (rare within the 250d window; known caveat).
        f_last = (float(rows[-1]["factor"]) or 1.0) if rows else 1.0
        closes = [r["close"] * r["factor"] / f_last for r in rows if r["close"] is not None]
        highs = [r["high"] * r["factor"] / f_last for r in rows if r["high"] is not None]
        lows = [r["low"] * r["factor"] / f_last for r in rows if r["low"] is not None]
        volumes = [r["volume"] for r in rows if r["volume"] is not None and r["volume"] > 0]
        
        n = len(closes)
        if n < 250 or len(highs) < 250 or len(volumes) < 50:
            continue
        
        current = closes[-1]
        
        # --- Stage 2 Check ---
        ma50 = sum(closes[-50:]) / 50
        ma200 = sum(closes[-200:]) / 200
        
        if not (current > ma50 > ma200):
            continue
        
        # 50MA rising
        ma50_prev = sum(closes[-60:-10]) / 50 if n >= 60 else ma50
        if ma50 <= ma50_prev:
            continue
        
        # Max advance filter (reject 3x+ runners)
        low_250 = min(lows[-250:])
        advance = (current - low_250) / low_250 * 100 if low_250 > 0 else 999
        if advance > 200:
            continue
        
        # Reject parabolic recent moves: if stock ran >40% in the last 20 days
        # that's a breakout already in progress, not a setup forming
        if n >= 20:
            low_20 = min(lows[-20:])
            recent_run = (current - low_20) / low_20 * 100 if low_20 > 0 else 0
            if recent_run > 40:
                continue
        
        # --- Find VCP in the base window ---
        base_n = min(base_days, n - 50)
        base_highs = highs[-base_n:]
        base_lows = lows[-base_n:]
        base_closes = closes[-base_n:]
        base_vols = volumes[-min(base_n, len(volumes)):]
        
        # Find swings
        sh, sl = find_swings(base_highs, base_lows, lookback=swing_lookback)
        
        if len(sh) < 2 or len(sl) < 1:
            continue
        
        # Find contractions (pullback depths from each swing high)
        contractions = find_contractions(sh, sl, volumes=base_vols)
        
        if len(contractions) < min_contractions:
            continue
        
        # Check if contractions are tightening
        depths = [c[4] for c in contractions]
        
        # Count how many successive contractions get tighter
        tightening_count = 0
        for i in range(1, len(depths)):
            if depths[i] < depths[i - 1]:
                tightening_count += 1
        
        # Need at least one tightening pair, and last must be < first
        if depths[-1] >= depths[0]:
            continue
        
        contraction_ratio = depths[-1] / depths[0] if depths[0] > 0 else 1.0
        
        # --- Distance from peak ---
        # The OVERALL peak (including any breakout move) 
        peak = max(base_highs)
        
        # The peak WITHIN the contraction zone (before the last swing low)
        # This is what Minervini calls the pivot point
        if contractions:
            last_contraction_end = contractions[-1][2]  # index of last swing low
            # The pivot = highest high after the last contraction low
            post_last_low = base_highs[last_contraction_end:]
            pivot = max(post_last_low) if post_last_low else peak
        else:
            pivot = peak
        
        # Reject if stock already broke out and ran far past the pivot
        # (i.e., the peak is way above the pivot = breakout already happened)
        if peak > 0 and pivot > 0:
            breakout_run = (peak - pivot) / pivot * 100
            if breakout_run > 10:
                continue  # already broke out and ran 10%+, we missed it
        
        dist_from_peak = (peak - current) / peak * 100
        if dist_from_peak > 20 or dist_from_peak < -1:
            continue
        
        # Also check: current should be near the PIVOT, not far below after a failed breakout
        dist_from_pivot = (pivot - current) / pivot * 100 if pivot > 0 else 0
        
        # --- Volume dry-up (recent vs average) ---
        vol_10 = sum(base_vols[-10:]) / min(10, len(base_vols[-10:]))
        vol_50 = sum(volumes[-50:]) / 50
        vol_ratio = vol_10 / vol_50 if vol_50 > 0 else 1.0
        
        # --- Volume declining across contractions ---
        contraction_vols = [c[5] for c in contractions if c[5] > 0]
        vol_declining = False
        vol_decline_count = 0
        if len(contraction_vols) >= 2:
            for i in range(1, len(contraction_vols)):
                if contraction_vols[i] < contraction_vols[i - 1]:
                    vol_decline_count += 1
            # At least half the pairs should show declining volume
            vol_declining = vol_decline_count >= len(contraction_vols) // 2
            # And last should be lower than first
            if contraction_vols[-1] >= contraction_vols[0]:
                vol_declining = False
        
        # --- MA proximity: is current price near a key MA? ---
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if n >= 60 else ma20
        
        dist_ma10 = abs(current - ma10) / ma10 * 100 if ma10 > 0 else 99
        dist_ma20 = abs(current - ma20) / ma20 * 100 if ma20 > 0 else 99
        dist_ma60 = abs(current - ma60) / ma60 * 100 if ma60 > 0 else 99
        
        # Best (nearest) MA distance
        nearest_ma_dist = min(dist_ma10, dist_ma20, dist_ma60)
        nearest_ma = "MA10" if dist_ma10 <= dist_ma20 and dist_ma10 <= dist_ma60 else \
                     "MA20" if dist_ma20 <= dist_ma60 else "MA60"
        
        # Price should be AT or ABOVE the MA (pullback to support, not breakdown)
        on_ma_support = (current >= ma10 * 0.97 or current >= ma20 * 0.97 or current >= ma60 * 0.97)
        
        # --- Last contraction tightness ---
        last_depth = depths[-1]
        
        # --- Scoring v4 (tuned from 280-trade backtest, Jan-Feb 2026) ---
        # Backtest findings (n=280):
        #   - Contraction ratio < 0.4: 55% WR, +7.7% avg 10d (THE alpha signal)
        #   - MA dist < 3%: necessary gate (0% WR when > 3%)
        #   - Near peak: mild positive
        #   - Volume declining: no meaningful edge
        #   - Hold 10d optimal, 20d loses money
        score = 0
        
        # Hard gates (reject if failed)
        if nearest_ma_dist > 5:
            continue  # too far from all MAs
        
        # Contraction ratio — THE alpha signal (0-35)
        if contraction_ratio < 0.3:
            score += 35
        elif contraction_ratio < 0.4:
            score += 30
        elif contraction_ratio < 0.5:
            score += 20
        elif contraction_ratio < 0.7:
            score += 10
        else:
            score += 5
        
        # MA proximity — gate + bonus (0-20)
        if on_ma_support and nearest_ma_dist < 1:
            score += 20
        elif on_ma_support and nearest_ma_dist < 2:
            score += 15
        elif on_ma_support and nearest_ma_dist < 3:
            score += 10
        elif nearest_ma_dist < 5:
            score += 3
        
        # Near breakout / distance from peak (0-15)
        if dist_from_peak < 3:
            score += 15
        elif dist_from_peak < 5:
            score += 12
        elif dist_from_peak < 8:
            score += 8
        elif dist_from_peak < 12:
            score += 4
        
        # Base structure — number of contractions (0-10)
        if len(contractions) >= 4:
            score += 10
        elif len(contractions) >= 3:
            score += 7
        else:
            score += 3
        
        # Last contraction depth — tighter = closer to breakout (0-10)
        if last_depth < 6:
            score += 10
        elif last_depth < 10:
            score += 7
        elif last_depth < 14:
            score += 4
        
        # Recent volume dry-up (0-5)
        if vol_ratio < 0.6:
            score += 5
        elif vol_ratio < 0.8:
            score += 3
        
        # Volume declining across contractions (0-5)
        if vol_declining:
            score += 5
        
        if score < 30:
            continue
        
        r120 = rps_data.get(code, {}).get("rps120", 0) if rps_data else 0
        r60 = rps_data.get(code, {}).get("rps60", 0) if rps_data else 0
        r250 = rps_data.get(code, {}).get("rps250", 0) if rps_data else 0
        
        # Format contractions for display
        depth_strs = [f"{d:.0f}%" for d in depths]
        
        # Days the base has been forming
        first_swing_idx = contractions[0][0]
        base_duration = base_n - first_swing_idx
        
        results.append({
            "code": code,
            "name": names.get(code, "?"),
            "score": score,
            "close": current,
            "peak": peak,
            "dist_from_peak_pct": round(dist_from_peak, 1),
            "num_contractions": len(contractions),
            "depths": [round(d, 1) for d in depths],
            "depth_strs": depth_strs,
            "last_depth": round(last_depth, 1),
            "contraction_ratio": round(contraction_ratio, 2),
            "vol_ratio": round(vol_ratio, 2),
            "vol_declining": vol_declining,
            "nearest_ma": nearest_ma,
            "nearest_ma_dist": round(nearest_ma_dist, 1),
            "ma10": round(ma10, 2),
            "ma20": round(ma20, 2),
            "ma60": round(ma60, 2),
            "base_days": base_duration,
            "advance_pct": round(advance, 0),
            "rps120": round(r120, 1) if r120 else 0,
            "rps60": round(r60, 1) if r60 else 0,
            "rps250": round(r250, 1) if r250 else 0,
        })
    
    conn.close()
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "pricedb", "ashare_prices.db")
    
    from rps_calculator import compute_ma_rps
    rps = compute_ma_rps(db_path)
    
    min_rps = float(sys.argv[1]) if len(sys.argv) > 1 else 85
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    base = int(sys.argv[3]) if len(sys.argv) > 3 else 120
    
    results = scan_vcp(db_path, rps_data=rps, min_rps120=min_rps, top_n=top, base_days=base)
    
    print(f"VCP Scan v2 (swing-based): {len(results)} setups (RPS120>={min_rps}, base={base}d)")
    print()
    print(f"{'Code':<8} {'Name':<10} {'Sc':>3} {'Close':>8} {'%Pk':>5} "
          f"{'#C':>2} {'Contractions':<24} {'Last':>5} {'VolR':>5} {'VD':>3} "
          f"{'MA':>5} {'%MA':>5} {'R250':>5} {'R120':>5} {'R60':>5}")
    print("-" * 115)
    for r in results:
        cs = "→".join(r["depth_strs"])
        name = r["name"] or "?"
        vd = " ✓" if r.get("vol_declining") else "  "
        print(f"{r['code']:<8} {name[:8]:<10} {r['score']:>3} {r['close']:>8.2f} "
              f"{r['dist_from_peak_pct']:>4.1f}% {r['num_contractions']:>2} "
              f"{cs:<24} {r['last_depth']:>4.1f}% {r['vol_ratio']:>5.2f} {vd:>3} "
              f"{r.get('nearest_ma','?'):>5} {r.get('nearest_ma_dist',0):>4.1f}% "
              f"{r['rps250']:>5.1f} {r['rps120']:>5.1f} {r['rps60']:>5.1f}")
