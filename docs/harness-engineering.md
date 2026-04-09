# Harness Engineering — Stock Analysis Pipeline

## The Problem

The pipeline "completes successfully" while silently degraded. Today's run:
- `prices.json`: both holdings returned `{"error": "No kline data"}` — **LLM had no prices**
- `crawl.json`: 0 stocks, dated yesterday — **LLM had no candidates**
- Pipeline exit code: 0, status: "complete", duration: 69.7s

This happens because:
1. **Every data fetch swallows errors** → returns partial/empty dicts instead of failing
2. **Validator produces WARNING strings** → nobody reads them, pipeline continues
3. **No contracts between phases** → Phase 2 runs regardless of Phase 1 quality
4. **No freshness checks** → yesterday's data passes as today's
5. **Fallback chains are incomplete** → AkShare (proxy-blocked) → CheeseForTune kline (no OHLC) → give up. Sina (which works) isn't wired in for positions.

The pipeline is a series of best-effort fetches wrapped in try/except that pass garbage forward.

---

## Architecture: Contract-Based Pipeline

Every step has an **input contract** (what it needs) and an **output contract** (what it guarantees). If a contract is violated, the step **fails loudly** — no silent degradation.

### Pipeline Phases

```
Phase 1: COLLECT    →  contracts validate  →  Phase 2: LLM PROMPT
Phase 2: LLM CALL   →  contracts validate  →  Phase 3: APPLY
Phase 3: APPLY       →  contracts validate  →  Phase 4: COMMIT
```

Each `→` is a **gate**. Gate fails = pipeline stops with a clear error, not a "warning."

---

## Phase 1: Data Collection — Input/Output Contracts

### 1.1 Strategy Pool

**Output contract:**
```python
{
    "source": str,           # REQUIRED — which source produced this
    "date": str,             # REQUIRED — must equal today's date (YYYY-MM-DD)
    "total_stocks": int,     # REQUIRED — can be 0 (legitimate on bad days)
    "stocks": list,          # REQUIRED — each stock has: code, name, rps120, price
    "error": None            # MUST be None — any error = contract violation
}
```

**Validation gate:**
- `date` must be today. Yesterday's data = FAIL.
- If `total_stocks == 0`: WARN but allow (can be legitimate). Log reason.
- Each stock in `stocks` must have `code` (6 digits), `name` (non-empty), `rps120` (numeric, 0-100), `price` (numeric, > 0).

**Current problem:** Returns `"date": "2026-04-08"` (yesterday) with 0 stocks, no validation catches it.

### 1.2 Position Prices (for active holdings)

**Output contract (per position):**
```python
{
    "code": str,              # REQUIRED
    "price": float,           # REQUIRED — > 0
    "date": str,              # REQUIRED — must be today or last trading day
    "open": float,            # REQUIRED for OHLC validation
    "high": float,            # REQUIRED
    "low": float,             # REQUIRED
    "volume": int,            # REQUIRED — >= 0
    "mavol30": float | None,  # OPTIONAL but expected
    "source": str,            # REQUIRED — which provider
    "error": None             # MUST be None
}
```

**Validation gate:**
- **Every active position MUST have a valid price.** No exceptions.
- `{"error": "No kline data"}` = contract violation = FAIL.
- If primary source fails, fallback chain must resolve it. If ALL sources fail for ANY position, pipeline FAILS.
- Price must be within reasonable range (not 0, not negative, not 100x yesterday's close).

**Fallback chain (ordered):**
1. **Sina real-time** (`hq.sinajs.cn`) — works through proxy, has OHLC ✅
2. AkShare (Eastmoney) — blocked by proxy, but works without proxy
3. CheeseForTune kline — close only, no OHLC (last resort)

**Current problem:** AkShare fails (proxy) → CheeseForTune fails ("No kline data") → returns error dict → pipeline continues with no prices.

### 1.3 Market Overview

**Output contract:**
```python
{
    "indices": {
        "上证指数": {"close": float, "change_pct": float, "date": str},
        "深证成指": {"close": float, "change_pct": float, "date": str},
        "创业板指": {"close": float, "change_pct": float, "date": str},
    },
    "breadth": {
        "up": int,       # > 0 during trading hours
        "down": int,     # > 0 during trading hours
        "total": int,    # > 1000 (sanity: A-share has ~5000 stocks)
    },
    "sectors": {...}     # top/bottom sectors
}
```

**Validation gate:**
- All 3 major indices MUST have valid `close` and `change_pct`.
- Breadth `total` must be > 1000 (sanity check — A-share has ~5000 stocks).
- Index dates must be today or last trading day.

### 1.4 IV Sentiment

**Output contract:**
```python
{
    "overall_sentiment": {
        "signal": str,        # one of: 偏乐观, 中性, 偏悲观
        "avg_iv_rank": float, # 0.0 - 1.0
        "based_on": list,     # >= 1 proxy
    },
    "error": None
}
```

**Validation gate:**
- Must have at least 1 proxy with data. If all proxies fail, WARN but don't block (IV is supplementary).

### 1.5 Enrichment (CheeseForTune detail)

**Output contract (per stock):**
```python
{
    "code": str,
    "pe": float | None,
    "pb": float | None,
    "market_cap": float,     # REQUIRED — needed for sizing
    "ai_score": float | None,
    # ... other CheeseForTune fields
}
```

**Validation gate:**
- At least 50% of candidates must enrich successfully. If > 50% fail, WARN.
- `market_cap` must be present and > 0 for each enriched stock.

---

## Phase 1 → Phase 2 Gate

Before building the LLM prompt, validate the **complete Phase 1 bundle:**

```python
def validate_phase1_gate(data: dict) -> tuple[bool, list[str]]:
    """Returns (pass, errors). If pass=False, pipeline MUST stop."""
    errors = []
    
    # HARD GATES — any failure = stop
    
    # 1. Position prices: ALL active positions must have prices
    for code, pdata in data["position_prices"].items():
        if pdata.get("error") or not pdata.get("price"):
            errors.append(f"HARD FAIL: no price for active position {code}")
    
    # 2. Market indices: at least 2 of 3 major indices must have data
    indices = data.get("market", {}).get("indices", {})
    valid_indices = sum(1 for k in ["上证指数", "深证成指", "创业板指"] 
                       if k in indices and "error" not in indices[k])
    if valid_indices < 2:
        errors.append(f"HARD FAIL: only {valid_indices}/3 indices have data")
    
    # 3. Breadth: must exist with total > 1000
    breadth = data.get("market", {}).get("breadth", {})
    if breadth.get("total", 0) < 1000:
        errors.append(f"HARD FAIL: breadth total={breadth.get('total', 0)} (need >1000)")
    
    # 4. Strategy pool date must be today (if non-empty)
    pool = data.get("strategy_pool", {})
    if pool.get("total_stocks", 0) > 0 and pool.get("date") != data["date"]:
        errors.append(f"HARD FAIL: pool date={pool.get('date')} != today={data['date']}")
    
    # SOFT GATES — warn but allow
    
    if pool.get("total_stocks", 0) == 0:
        errors.append(f"SOFT WARN: strategy pool empty (may be legitimate)")
    
    iv = data.get("iv_sentiment", {})
    if iv.get("error"):
        errors.append(f"SOFT WARN: IV sentiment failed: {iv['error']}")
    
    hard_fails = [e for e in errors if e.startswith("HARD")]
    return (len(hard_fails) == 0, errors)
```

---

## Phase 2: LLM Call — Output Contract

**Input:** Well-formed prompt with validated data (guaranteed by Phase 1 gate).

**Output contract (LLM response JSON):**
```python
{
    "market_summary": str,        # REQUIRED — non-empty
    "position_decisions": [       # REQUIRED — one per active position
        {
            "code": str,          # must match an active position
            "action": str,        # one of: HOLD, SELL, RAISE_STOP
            "reason": str,        # non-empty
            # if SELL:
            "exit_price": float,  # required
            "lesson": str,        # required
            # if RAISE_STOP:
            "new_stop": float,    # required, > current stop
        }
    ],
    "new_positions": list,        # can be empty
    "skip_list": list,            # REQUIRED — one per pool candidate not selected
    "new_learnings": list,        # can be empty
    "watchlist": list,            # REQUIRED
}
```

**Validation gate (Phase 2 → Phase 3):**
```python
def validate_llm_output(decisions: dict, data: dict) -> tuple[bool, list[str]]:
    errors = []
    
    # 1. Every active position must have a decision
    active_codes = {p["code"] for p in data["positions"]}
    decision_codes = {d["code"] for d in decisions.get("position_decisions", [])}
    missing = active_codes - decision_codes
    if missing:
        errors.append(f"HARD FAIL: no decision for positions: {missing}")
    
    # 2. Actions must be valid
    for d in decisions.get("position_decisions", []):
        if d["action"] not in ("HOLD", "SELL", "RAISE_STOP"):
            errors.append(f"HARD FAIL: invalid action '{d['action']}' for {d['code']}")
        if d["action"] == "SELL" and not d.get("exit_price"):
            errors.append(f"HARD FAIL: SELL {d['code']} missing exit_price")
        if d["action"] == "RAISE_STOP" and not d.get("new_stop"):
            errors.append(f"HARD FAIL: RAISE_STOP {d['code']} missing new_stop")
    
    # 3. New positions must have required fields
    for p in decisions.get("new_positions", []):
        for field in ("code", "name", "entry_price", "stop", "target", "thesis"):
            if not p.get(field):
                errors.append(f"HARD FAIL: new position {p.get('code','?')} missing {field}")
    
    # 4. market_summary must exist
    if not decisions.get("market_summary"):
        errors.append("SOFT WARN: missing market_summary")
    
    hard_fails = [e for e in errors if e.startswith("HARD")]
    return (len(hard_fails) == 0, errors)
```

---

## Phase 3: Apply — Output Contract

**Input:** Validated LLM decisions + original Phase 1 data.

**Output contract:**
- Every SELL action results in a closed position file in `tracking/closed/`
- Every OPEN action results in an active position file in `tracking/`
- `positions.json` is regenerated and matches tracking files exactly
- Post-run snapshot is written to `runs/<date>/output/positions_snapshot.json`
- Daily summary, report, and watchlist are written

**Validation gate (Phase 3 → Phase 4):**
- `positions.json` active codes == tracking/*.json active codes (already exists, but currently just warns)
- Every new position has entry price within today's OHLC (already partially implemented)
- Portfolio cash% is within 0-100% (sanity)
- No position has negative shares or zero entry price

---

## Features to Build

### F1: Typed Data Contracts (dataclasses or Pydantic)

Replace loose dicts with typed structures. Every field has a type, required/optional, and valid range.

```python
@dataclass
class PositionPrice:
    code: str
    price: float          # > 0
    date: str             # today or last trading day
    open: float           # > 0
    high: float           # >= open, >= close
    low: float            # <= open, <= close
    volume: int           # >= 0
    mavol30: float | None
    source: str
    
    def validate(self) -> list[str]:
        errors = []
        if self.price <= 0:
            errors.append(f"{self.code}: price={self.price} <= 0")
        if self.high < self.low:
            errors.append(f"{self.code}: high={self.high} < low={self.low}")
        if self.high < self.price or self.low > self.price:
            errors.append(f"{self.code}: price={self.price} outside [{self.low}, {self.high}]")
        return errors
```

### F2: Hard Gates Between Phases

```python
class PipelineGate:
    """Gate between pipeline phases. Fails loudly on contract violations."""
    
    def __init__(self, name: str):
        self.name = name
        self.hard_fails = []
        self.soft_warns = []
    
    def hard(self, condition: bool, msg: str):
        if not condition:
            self.hard_fails.append(msg)
    
    def soft(self, condition: bool, msg: str):
        if not condition:
            self.soft_warns.append(msg)
    
    def check(self) -> bool:
        """Returns True if gate passes. Raises on hard failures."""
        if self.hard_fails:
            raise PipelineHardFail(
                f"Gate '{self.name}' FAILED with {len(self.hard_fails)} hard failures:\n" +
                "\n".join(f"  ✗ {f}" for f in self.hard_fails)
            )
        return True
```

### F3: Sina as Primary Price Source

Wire `hq.sinajs.cn` into `fetch_position_prices()` as the **first** source, not a fallback. It works through the proxy, returns OHLC, and is fast.

```python
# Fallback chain (new order):
# 1. Sina real-time (hq.sinajs.cn) — OHLC, works through proxy
# 2. AkShare (Eastmoney push2) — OHLC, may be proxy-blocked  
# 3. CheeseForTune kline — close only, last resort
# 4. Local pricedb — stale but better than nothing
```

### F4: Data Freshness Enforcement

```python
def assert_fresh(date_str: str, label: str, max_age_days: int = 0):
    """Ensure data is from today (or within max_age_days)."""
    from datetime import datetime, timedelta
    data_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    age = (today - data_date).days
    if age > max_age_days:
        raise StaleDataError(f"{label} is {age} days old (date={date_str}, today={today})")
```

### F5: Pipeline Status Codes

Replace the current "always succeed" model with explicit status codes:

```python
class PipelineResult:
    SUCCESS = "success"           # All phases passed, all gates clear
    DEGRADED = "degraded"         # Soft warnings but no hard failures
    FAILED = "failed"             # Hard gate failure, pipeline stopped
    PARTIAL = "partial"           # Some phases completed before failure
    
    def __init__(self, status, phases_completed, errors, warnings):
        self.status = status
        self.exit_code = 0 if status in (self.SUCCESS, self.DEGRADED) else 1
```

The cron message should reflect the ACTUAL status, not "completed successfully" when prices are missing.

### F6: Structured Run Manifest

Each run produces a machine-readable manifest:

```python
# runs/2026-04-09/manifest.json
{
    "date": "2026-04-09",
    "status": "failed",           # not "success"
    "exit_code": 1,
    "phases": {
        "collect": {
            "status": "degraded",
            "duration_sec": 13.8,
            "data_quality": {
                "strategy_pool": {"status": "stale", "date": "2026-04-08", "stocks": 0},
                "position_prices": {"status": "failed", "missing": ["605167", "688037"]},
                "market": {"status": "ok"},
                "iv_sentiment": {"status": "ok"}
            }
        },
        "gate_phase1": {
            "status": "failed",
            "hard_fails": [
                "no price for active position 605167",
                "no price for active position 688037"
            ]
        }
        // phases 2-4 never ran
    }
}
```

### F7: Source Health Pre-Check

Before the main pipeline, probe each data source:

```python
def health_check() -> dict:
    """Quick probe of all data sources. Run before pipeline."""
    results = {}
    
    # Sina
    try:
        resp = urllib.request.urlopen("https://hq.sinajs.cn/list=sh000001", timeout=5)
        results["sina"] = {"status": "ok", "latency_ms": ...}
    except:
        results["sina"] = {"status": "down"}
    
    # CheeseForTune
    try:
        client = CheeseFortuneClient()
        client.get_market_summary()
        results["cheesefortune"] = {"status": "ok"}
    except:
        results["cheesefortune"] = {"status": "down"}
    
    # AkShare/Eastmoney
    try:
        resp = urllib.request.urlopen("https://push2his.eastmoney.com/...", timeout=5)
        results["eastmoney"] = {"status": "ok"}
    except:
        results["eastmoney"] = {"status": "down"}
    
    return results
```

If critical sources are down, fail fast before wasting 70 seconds.

### F8: Retry with Backoff (Per-Source)

Current behavior: try once, catch exception, move to fallback.
Better: retry 2-3 times with exponential backoff before declaring failure.

```python
def fetch_with_retry(fn, retries=3, backoff_base=2):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(backoff_base ** attempt)
```

---

## Implementation Priority

| # | Feature | Impact | Effort | Why |
|---|---------|--------|--------|-----|
| 1 | **F3: Sina primary** | HIGH | LOW | Fixes the immediate price fetch failures. 30 min. |
| 2 | **F2: Hard gates** | HIGH | MED | Stops garbage-in-garbage-out. Pipeline fails instead of lying. |
| 3 | **F4: Freshness checks** | HIGH | LOW | Catches stale pool data. 15 min. |
| 4 | **F5: Status codes** | MED | LOW | Cron reports truth instead of "success". |
| 5 | **F6: Run manifest** | MED | LOW | Machine-readable run status for debugging. |
| 6 | **F7: Health pre-check** | MED | LOW | Fail fast when sources are down. |
| 7 | **F1: Typed contracts** | MED | HIGH | Prevents drift long-term. Biggest refactor. |
| 8 | **F8: Retry with backoff** | LOW | LOW | Nice-to-have, most failures are source-level not transient. |

---

## What This Changes Day-to-Day

**Before (today):**
```
Pipeline completed successfully in 70s.
[hidden: prices missing, pool stale, LLM guessing]
→ HOLD both positions (correct by accident)
```

**After:**
```
Pipeline FAILED at Phase 1 gate: 
  ✗ no price for active position 605167
  ✗ no price for active position 688037
  ✗ strategy pool date=2026-04-08 != today=2026-04-09
Pipeline stopped. No LLM call made. No positions modified.
→ Alert sent with failure reason.
```

The LLM should never run on incomplete data. If it does, we've already lost.
