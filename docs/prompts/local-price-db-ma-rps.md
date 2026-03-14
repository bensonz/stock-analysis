# Local Price Database + MA-Based RPS Calculation

## Goal

Build a local price database for all A-share stocks, and compute custom MA-based RPS (Relative Price Strength) rankings using smoothed moving averages instead of raw close prices.

## Context

The current pipeline fetches a pre-filtered stock list from CheeseForTune API (strategy 352390), which provides RPS values calculated from single-day close prices. The problem: RPS changes daily based on one close, making it noisy. We want smoother RPS using MA10 (10-day moving average of close prices) as the base instead of raw close.

**Current RPS formula (CheeseForTune):**
```
RPS_N = percentile_rank( close_today / close_N_days_ago )  across all A-shares
```

**New MA-based RPS formula:**
```
RPS_N = percentile_rank( MA10_today / MA10_N_days_ago )  across all A-shares
```

Where MA10 = simple moving average of last 10 close prices. Same percentile ranking, just smoothed input.

We need this for RPS20, RPS60, RPS120, RPS250 (N = 20, 60, 120, 250 trading days).

## Requirements

### 1. Local Price Database

- **Database:** SQLite file stored in `data/pricedb/` directory (gitignored)
- **Schema:**
  - `stocks` table: `code TEXT PRIMARY KEY, name TEXT, exchange TEXT (SH/SZ/BJ), listed_date TEXT, last_updated TEXT`
  - `daily_prices` table: `code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER, amount REAL, PRIMARY KEY (code, date)`
  - Add indexes on `daily_prices(date)` and `daily_prices(code, date)`
- **Data source:** Eastmoney API (same as existing `fetch_ma_data()` in `data_collector.py`)
  - Use `https://push2his.eastmoney.com/api/qt/stock/kline/get` for historical klines (per stock)
  - Use `https://push2.eastmoney.com/api/qt/clist/get` to get full A-share stock list (bulk, paginated)
  - **IMPORTANT:** Bypass system proxy for Eastmoney requests (their push2 servers get DNS-hijacked by Surge/Clash). Use `proxies={"http": None, "https": None}` with requests, or `trust_env = False` on session.
- **Full stock list:** Fetch all A-share codes from Eastmoney's clist API (fs=`m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048` covers SZ main/创业板/SH main/科创板/北交所). Fields: f12 (code), f14 (name), f13 (exchange market id).

### 2. Bulk Download Script: `scripts/pricedb.py`

CLI interface:
```bash
python scripts/pricedb.py init          # Create DB, fetch stock list, download ALL historical data (250+ trading days back)
python scripts/pricedb.py update        # Incremental update: fetch only missing dates since last update
python scripts/pricedb.py status        # Show DB stats: total stocks, date range, last update
python scripts/pricedb.py rps [DATE]    # Compute MA-based RPS for all stocks on DATE (default: latest)
python scripts/pricedb.py query CODE    # Show a stock's recent prices + computed RPS values
```

**Bulk download strategy:**
- For `init`: fetch ~300 trading days of history for each stock (need 250 + 10 buffer for MA10 calc at 250-day lookback)
- Use ThreadPoolExecutor with 10-20 workers for parallel fetching (Eastmoney handles concurrent connections fine)
- Rate limit: no explicit delay needed per-stock with different connections, but add a small delay (0.1s) between batches
- For `update`: find the latest date in DB, fetch only days after that for each stock
- Target: full init should take ~15-30 minutes (5000 stocks × ~1s each with parallelism)
- Print progress: `[1234/5200] Fetching 600519...` every 100 stocks

### 3. RPS Calculation: `scripts/rps_calculator.py`

Core function:
```python
def compute_ma_rps(db_path: str, date: str = None, ma_period: int = 10) -> dict:
    """Compute MA-based RPS for all stocks on a given date.
    
    For each lookback period (20, 60, 120, 250 trading days):
      1. Get MA{ma_period} of close prices on `date` (avg of last 10 closes up to date)
      2. Get MA{ma_period} of close prices `lookback` trading days before `date`
      3. Compute delta = MA_today / MA_past
      4. Rank all stocks by delta → percentile (0-100)
    
    Returns:
        {code: {"rps20": float, "rps60": float, "rps120": float, "rps250": float, "ma10_today": float}}
    """
```

Additional functions:
```python
def get_ma_rps_for_stocks(db_path: str, codes: list[str], date: str = None) -> dict:
    """Get MA-based RPS for specific stocks. Calls compute_ma_rps internally (cached)."""

def compute_ma(db_path: str, code: str, date: str, period: int = 10) -> float | None:
    """Compute MA for a single stock on a date."""
```

**Implementation notes:**
- Use pure SQL for efficiency: compute MAs using window functions or subqueries
- Cache the full RPS computation per date (it's the same ranking for all stocks)
- Save computed RPS to a `rps_cache` table: `date TEXT, code TEXT, rps20 REAL, rps60 REAL, rps120 REAL, rps250 REAL, ma10 REAL, PRIMARY KEY (date, code)`
- Stocks with insufficient history for a given lookback should get `None` for that RPS period

### 4. Integration with Pipeline: Update `data_collector.py`

Add a new function:
```python
def fetch_strategy_pool_local(db_path: str = None) -> dict:
    """Fetch strategy candidates using local price DB + CheeseForTune fundamental filters.
    
    1. Compute MA-based RPS for all stocks from local DB
    2. Apply filters locally:
       - RPS120 >= 85 (MA-based)
       - RPS250 >= 85 (MA-based)  
       - RPS60 >= 70 (MA-based)
       - MA alignment: MA20 > MA120 > MA250 (compute from local DB)
    3. For stocks passing RPS + MA filters, batch query CheeseForTune for:
       - Market cap (20-810亿 filter)
       - Highlights count (>= 4)
       - Risk count (<= 5)
       - Risk tag exclusions
       - ST exclusion
    4. Return final filtered list in same format as fetch_strategy_pool()
    
    Falls back to fetch_strategy_pool() (CheeseForTune API) if local DB not available.
    """
```

Modify `phase1_collect()` in `run_daily.py`:
- Try `fetch_strategy_pool_local()` first
- Fall back to `fetch_strategy_pool()` if DB missing or error
- The rest of the pipeline stays the same (enrichment, market data, etc.)
- Add `pricedb update` call at the start of Phase 1 (incremental update before computing RPS)

### 5. Docker Setup

Create `Dockerfile` and `docker-compose.yml` for optional containerized usage:

```dockerfile
# Dockerfile — for running the price DB update as a service
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ scripts/
COPY agents/ agents/
# DB is mounted, not baked in
VOLUME /app/data/pricedb
CMD ["python", "scripts/pricedb.py", "update"]
```

```yaml
# docker-compose.yml
services:
  pricedb:
    build: .
    volumes:
      - ./data/pricedb:/app/data/pricedb
    # Run daily update
    command: python scripts/pricedb.py update
```

### 6. .gitignore Update

Add to `.gitignore`:
```
data/pricedb/
```

### 7. Requirements

Add `sqlite3` is stdlib, no new deps needed. But ensure `requests` is available (already in the venv).

Create a `requirements.txt` if one doesn't exist:
```
akshare>=1.18
anthropic>=0.84
httpx>=0.28
openai>=2.26
pycryptodome>=3.21
requests>=2.32
```

## File Structure After Implementation

```
scripts/
  pricedb.py           # NEW — DB management CLI (init/update/status/rps/query)
  rps_calculator.py    # NEW — MA-based RPS computation
  data_collector.py    # MODIFIED — add fetch_strategy_pool_local()
  run_daily.py         # MODIFIED — use local DB when available, run pricedb update in Phase 1
data/
  pricedb/             # NEW — gitignored, contains SQLite DB
    ashare_prices.db   # ~500MB-1GB for full A-share history
Dockerfile             # NEW
docker-compose.yml     # NEW
.gitignore             # MODIFIED — add data/pricedb/
```

## Testing

After implementation:
1. `python scripts/pricedb.py init` — should complete in 15-30 min, DB should have ~5000 stocks × 300 days
2. `python scripts/pricedb.py status` — verify counts
3. `python scripts/pricedb.py rps` — compute today's RPS, verify output looks reasonable (values 0-100, distributed)
4. `python scripts/pricedb.py query 600519` — show 贵州茅台's data as sanity check
5. Compare: run `fetch_strategy_pool()` (CheeseForTune) and `fetch_strategy_pool_local()` side by side — the stock lists won't be identical (different RPS algo) but should have significant overlap
6. Run the full pipeline: `python scripts/run_daily.py --phase1` — should use local DB automatically

## Important Notes

- The Eastmoney push2 servers get DNS-hijacked by Surge/Clash proxies. **Always bypass proxy** for these requests.
- SQLite is fine for this use case — single writer (update script), single reader (pipeline). No need for Postgres.
- The Docker setup is optional — primary usage is running scripts directly on macOS with the venv.
- Keep the CheeseForTune strategy API as fallback — if local DB is stale or missing, fall back gracefully.
- The MA period (10) should be configurable but default to 10.
- When computing "MA10 N days ago", be careful: you need the 10 closes *ending on* the date that is N trading days before today. Not calendar days — trading days (skip weekends/holidays).
