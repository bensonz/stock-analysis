# Worker Prompt: Harness Engineering — Contract-Based Pipeline

## Context

The stock analysis pipeline at `/Users/bz/Work/Personal/stock-analysis/` runs daily via cron. It collects market data, calls an LLM for analysis, and applies trading decisions. The problem: **it "succeeds" while feeding garbage to the LLM.** Errors are swallowed as warnings, phases run regardless of data quality, and the pipeline reports "completed successfully" even when core data (prices, candidates) is missing.

**Today's example:** Both active positions returned `{"error": "No kline data"}` in `prices.json`. Strategy pool returned 0 stocks dated yesterday. Pipeline exit code: 0. Status: "complete." The LLM made decisions with no price data.

## Goal

Transform the pipeline from "best-effort with silent degradation" to "contract-based with hard gates." Every phase has input/output contracts. If a contract is violated, the pipeline **fails loudly** — no silent degradation.

## Architecture

Reference design doc: `/Users/bz/Work/Personal/stock-analysis/docs/harness-engineering.md`

```
Phase 1: COLLECT  →  [Gate 1]  →  Phase 2: LLM  →  [Gate 2]  →  Phase 3: APPLY  →  [Gate 3]  →  Phase 4: COMMIT
```

Each gate validates contracts. Hard failures = pipeline stops. Soft warnings = pipeline continues with warnings logged.

---

## Changes Required

### 1. New File: `scripts/contracts.py`

Create a new module for all pipeline contracts, gates, and validation logic.

```python
"""
contracts.py — Pipeline data contracts and phase gates.

Every pipeline phase has input/output contracts. Gates between phases
validate contracts and fail loudly on violations.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class PipelineStatus(Enum):
    SUCCESS = "success"        # All phases passed, all gates clear, no warnings
    DEGRADED = "degraded"      # Soft warnings but no hard failures
    FAILED = "failed"          # Hard gate failure, pipeline stopped
    PARTIAL = "partial"        # Some phases completed before failure


class Severity(Enum):
    HARD = "hard"    # Pipeline must stop
    SOFT = "soft"    # Warning, pipeline continues


@dataclass
class GateResult:
    name: str
    passed: bool
    hard_fails: list[str] = field(default_factory=list)
    soft_warns: list[str] = field(default_factory=list)


class PipelineGate:
    """Gate between pipeline phases. Accumulates checks, fails loudly on hard violations."""

    def __init__(self, name: str):
        self.name = name
        self.hard_fails: list[str] = []
        self.soft_warns: list[str] = []

    def hard(self, condition: bool, msg: str):
        """Add a hard requirement. If condition is False, pipeline must stop."""
        if not condition:
            self.hard_fails.append(msg)

    def soft(self, condition: bool, msg: str):
        """Add a soft check. If condition is False, log warning but continue."""
        if not condition:
            self.soft_warns.append(msg)

    def check(self) -> GateResult:
        """Evaluate the gate. Returns GateResult with pass/fail and messages."""
        passed = len(self.hard_fails) == 0
        return GateResult(
            name=self.name,
            passed=passed,
            hard_fails=list(self.hard_fails),
            soft_warns=list(self.soft_warns),
        )


class PipelineHardFail(Exception):
    """Raised when a pipeline gate has hard failures."""

    def __init__(self, gate_result: GateResult):
        self.gate_result = gate_result
        fails = "\n".join(f"  ✗ {f}" for f in gate_result.hard_fails)
        warns = "\n".join(f"  ⚠ {w}" for w in gate_result.soft_warns)
        parts = [f"Gate '{gate_result.name}' FAILED with {len(gate_result.hard_fails)} hard failure(s):"]
        parts.append(fails)
        if warns:
            parts.append(f"Additionally {len(gate_result.soft_warns)} warning(s):")
            parts.append(warns)
        super().__init__("\n".join(parts))


def _is_trading_day_recent(date_str: str, max_age_calendar_days: int = 4) -> bool:
    """Check if a date string is recent enough to be valid market data.
    
    Weekends and holidays can cause gaps of up to 3-4 calendar days,
    so we allow max_age_calendar_days gap (default 4 covers long weekends).
    """
    if not date_str:
        return False
    try:
        # Handle various date formats
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                data_date = datetime.strptime(date_str[:10], fmt).date()
                break
            except ValueError:
                continue
        else:
            return False
        today = datetime.now().date()
        return (today - data_date).days <= max_age_calendar_days
    except Exception:
        return False


def _is_today(date_str: str) -> bool:
    """Check if date string matches today."""
    if not date_str:
        return False
    today = datetime.now().strftime("%Y-%m-%d")
    return date_str[:10] == today


# ─── Gate 1: Phase 1 → Phase 2 (Data Collection → LLM Prompt) ───

def validate_phase1_gate(data: dict) -> GateResult:
    """Validate Phase 1 output before building the LLM prompt.
    
    Hard failures (pipeline stops):
    - Any active position missing a valid price
    - Fewer than 2 of 3 major indices have data  
    - Breadth data missing or clearly broken (total < 1000)
    - Strategy pool has stocks but date is stale (not today or last trading day)
    
    Soft warnings (pipeline continues):
    - Strategy pool is empty (can be legitimate on weak days)
    - IV sentiment failed
    - Some enrichment failures
    """
    gate = PipelineGate("phase1_to_phase2")
    
    # ── Position prices: EVERY active position MUST have a valid price ──
    positions = data.get("positions", [])
    position_prices = data.get("position_prices", {})
    
    if positions and not position_prices:
        gate.hard(False, f"position_prices is empty but have {len(positions)} active position(s)")
    
    for pos in positions:
        code = pos.get("code", "unknown")
        name = pos.get("name", code)
        pdata = position_prices.get(code, {})
        
        if not isinstance(pdata, dict):
            gate.hard(False, f"position {code} ({name}): price data is not a dict")
            continue
        
        if pdata.get("error"):
            gate.hard(False, f"position {code} ({name}): price fetch error: {pdata['error']}")
            continue
        
        price = pdata.get("price")
        if price is None or price <= 0:
            gate.hard(False, f"position {code} ({name}): invalid price={price}")
            continue
        
        # Price date must be recent (today or last trading day)
        price_date = pdata.get("date", "")
        gate.soft(
            _is_trading_day_recent(price_date),
            f"position {code} ({name}): price date '{price_date}' may be stale"
        )
    
    # ── Market indices: at least 2 of 3 major indices must have valid data ──
    market = data.get("market", {})
    indices = market.get("indices", {})
    major_indices = ["上证指数", "深证成指", "创业板指"]
    valid_indices = 0
    for idx_name in major_indices:
        idx_data = indices.get(idx_name, {})
        if isinstance(idx_data, dict) and "error" not in idx_data and idx_data.get("close"):
            valid_indices += 1
    
    gate.hard(valid_indices >= 2, f"only {valid_indices}/3 major indices have valid data")
    
    # ── Breadth: must exist with reasonable total ──
    breadth = market.get("breadth", {})
    breadth_total = breadth.get("total", 0)
    # A-share market has ~5000+ stocks. Anything below 1000 is broken data.
    gate.hard(
        breadth_total >= 1000,
        f"breadth total={breadth_total} (expected >=1000 for A-share market)"
    )
    
    # ── Strategy pool date freshness ──
    pool = data.get("strategy_pool", {})
    pool_stocks = pool.get("stocks", [])
    pool_date = pool.get("date", "")
    
    if pool.get("error"):
        gate.soft(False, f"strategy pool error: {pool['error']}")
    elif len(pool_stocks) > 0 and pool_date:
        # If pool has stocks, date must be today or last trading day
        gate.hard(
            _is_trading_day_recent(pool_date, max_age_calendar_days=4),
            f"strategy pool date '{pool_date}' is stale (stocks={len(pool_stocks)})"
        )
        gate.soft(
            _is_today(pool_date),
            f"strategy pool date '{pool_date}' is not today (may be using last trading day data)"
        )
    elif len(pool_stocks) == 0:
        gate.soft(False, "strategy pool is empty (may be legitimate on weak days)")
    
    # ── IV sentiment (supplementary — soft only) ──
    iv = data.get("iv_sentiment", {})
    gate.soft(not iv.get("error"), f"IV sentiment failed: {iv.get('error', 'unknown')}")
    
    # ── Enrichment quality ──
    enriched = data.get("enriched", [])
    if enriched:
        error_count = sum(1 for e in enriched if isinstance(e, dict) and e.get("error"))
        error_pct = error_count / len(enriched) * 100 if enriched else 0
        gate.soft(error_pct < 50, f"enrichment: {error_count}/{len(enriched)} failed ({error_pct:.0f}%)")
    
    return gate.check()


# ─── Gate 2: Phase 2 → Phase 3 (LLM Response → Apply) ───

def validate_llm_output_gate(decisions: dict, data: dict) -> GateResult:
    """Validate LLM response before applying decisions.
    
    Hard failures:
    - decisions is empty or unparseable
    - Active positions missing from position_decisions
    - Invalid action types
    - SELL without exit_price
    - RAISE_STOP without new_stop
    - New position missing required fields
    
    Soft warnings:
    - Missing market_summary
    - Missing skip_list entries
    """
    gate = PipelineGate("phase2_to_phase3")
    
    # ── Decisions must exist and be a dict ──
    gate.hard(isinstance(decisions, dict) and len(decisions) > 0, "LLM response is empty or not a dict")
    if not isinstance(decisions, dict) or not decisions:
        return gate.check()
    
    # ── Every active position must have exactly one decision ──
    active_codes = {p["code"] for p in data.get("positions", [])}
    position_decisions = decisions.get("position_decisions", [])
    decision_codes = set()
    
    for d in position_decisions:
        code = str(d.get("code", "")).split(".")[0]
        decision_codes.add(code)
        action = d.get("action", "")
        
        # Valid action types
        gate.hard(
            action in ("HOLD", "SELL", "RAISE_STOP"),
            f"position {code}: invalid action '{action}' (must be HOLD/SELL/RAISE_STOP)"
        )
        
        # SELL requires exit_price
        if action == "SELL":
            gate.hard(
                d.get("exit_price") not in (None, "", 0),
                f"position {code}: SELL missing exit_price"
            )
        
        # RAISE_STOP requires new_stop
        if action == "RAISE_STOP":
            new_stop = d.get("new_stop")
            gate.hard(
                new_stop is not None and new_stop > 0,
                f"position {code}: RAISE_STOP missing or invalid new_stop={new_stop}"
            )
        
        # Reason should be present
        gate.soft(bool(d.get("reason")), f"position {code}: {action} has no reason")
    
    # Check for missing decisions
    missing = active_codes - decision_codes
    gate.hard(len(missing) == 0, f"no decision for active position(s): {missing}")
    
    # ── New positions must have required fields ──
    for p in decisions.get("new_positions", []) or []:
        code = str(p.get("code", "?")).split(".")[0]
        required_fields = {
            "code": p.get("code"),
            "name": p.get("name"),
            "entry_price": p.get("entry_price"),
            "stop": p.get("stop"),
            "target": p.get("target"),
            "thesis": p.get("thesis"),
        }
        for fname, fval in required_fields.items():
            gate.hard(
                fval not in (None, "", 0),
                f"new position {code}: missing required field '{fname}'"
            )
        
        # Entry price sanity: must be positive and reasonable
        ep = p.get("entry_price")
        if ep is not None and isinstance(ep, (int, float)):
            gate.hard(ep > 0, f"new position {code}: entry_price={ep} must be > 0")
            # Stop must be below entry
            stop = p.get("stop")
            if stop is not None and isinstance(stop, (int, float)):
                gate.hard(stop < ep, f"new position {code}: stop={stop} >= entry_price={ep}")
    
    # ── Soft checks ──
    gate.soft(bool(decisions.get("market_summary")), "missing market_summary")
    gate.soft("watchlist" in decisions, "missing watchlist")
    
    return gate.check()


# ─── Gate 3: Phase 3 → Phase 4 (Apply → Commit) ───

def validate_phase3_gate(date: str, apply_log: dict, data: dict) -> GateResult:
    """Validate Phase 3 output before committing.
    
    Hard failures:
    - Actions contain ERROR entries
    - Position file inconsistency (positions.json vs tracking/*.json)
    
    Soft warnings:
    - Price corrections applied
    - Fallback prices used
    """
    gate = PipelineGate("phase3_to_phase4")
    
    actions = apply_log.get("actions", [])
    
    # Check for error actions
    error_actions = [a for a in actions if isinstance(a, str) and a.startswith("ERROR")]
    gate.hard(len(error_actions) == 0, f"apply phase had errors: {error_actions}")
    
    # Check for price corrections / fallback warnings
    corrections = [a for a in actions if isinstance(a, str) and "PRICE_CORRECTED" in a]
    fallbacks = [a for a in actions if isinstance(a, str) and "WARN" in a and "fallback" in a.lower()]
    
    for c in corrections:
        gate.soft(False, c)
    for f in fallbacks:
        gate.soft(False, f)
    
    # Post-apply rule violations
    rule_violations = apply_log.get("post_apply_rule_violations", {})
    if rule_violations.get("status") == "violations":
        for rule in rule_violations.get("rules", []):
            if rule.get("status") == "violations":
                for v in rule.get("violations", []):
                    gate.soft(False, f"rule {rule['rule']}: {v.get('suggestion', v.get('code', '?'))}")
    
    return gate.check()


# ─── Run Manifest ───

@dataclass
class RunManifest:
    """Machine-readable summary of a pipeline run."""
    date: str
    status: PipelineStatus
    phases: dict = field(default_factory=dict)  
    gates: dict = field(default_factory=dict)
    total_duration_sec: float = 0.0
    exit_code: int = 0
    
    def add_phase(self, name: str, status: str, duration_sec: float = 0.0, details: dict = None):
        self.phases[name] = {
            "status": status,
            "duration_sec": round(duration_sec, 1),
            **(details or {}),
        }
    
    def add_gate(self, result: GateResult):
        self.gates[result.name] = {
            "passed": result.passed,
            "hard_fails": result.hard_fails,
            "soft_warns": result.soft_warns,
        }
    
    def finalize(self):
        """Set overall status from gate results."""
        any_hard_fail = any(not g["passed"] for g in self.gates.values())
        any_soft_warn = any(len(g["soft_warns"]) > 0 for g in self.gates.values())
        
        if any_hard_fail:
            self.status = PipelineStatus.FAILED
            self.exit_code = 1
        elif any_soft_warn:
            self.status = PipelineStatus.DEGRADED
            self.exit_code = 0
        else:
            self.status = PipelineStatus.SUCCESS
            self.exit_code = 0
    
    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "total_duration_sec": round(self.total_duration_sec, 1),
            "phases": self.phases,
            "gates": self.gates,
        }


# ─── Source Health Check ───

def check_source_health(timeout: float = 5.0) -> dict:
    """Quick probe of all data sources before starting the pipeline.
    
    Returns dict of {source_name: {"status": "ok"|"down", "latency_ms": float, "error": str}}.
    """
    import time
    import urllib.request
    
    results = {}
    
    # 1. Sina Finance (primary for indices + position prices)
    try:
        import requests
        start = time.time()
        s = requests.Session()
        s.trust_env = False
        r = s.get(
            "https://hq.sinajs.cn/list=s_sh000001",
            headers={"Referer": "https://finance.sina.com.cn"},
            timeout=timeout,
        )
        latency = (time.time() - start) * 1000
        # Check we got actual data (not empty/error page)
        ok = r.status_code == 200 and "上证指数" in r.text
        results["sina"] = {"status": "ok" if ok else "bad_response", "latency_ms": round(latency, 1)}
    except Exception as e:
        results["sina"] = {"status": "down", "error": str(e)}
    
    # 2. CheeseForTune API
    try:
        start = time.time()
        from cheesefortune_client import CheeseFortuneClient
        client = CheeseFortuneClient()
        # Quick probe — market summary is a lightweight endpoint
        r = client._request(f"{client.BASE_URL}/api/v4/market/marketSummary?isCN=true")
        latency = (time.time() - start) * 1000
        ok = r.get("code") == "000"
        results["cheesefortune"] = {"status": "ok" if ok else "bad_response", "latency_ms": round(latency, 1)}
    except Exception as e:
        results["cheesefortune"] = {"status": "down", "error": str(e)}
    
    # 3. AkShare / Eastmoney
    try:
        start = time.time()
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1&fields2=f51&klt=101&fqt=1&beg=20260101&end=20260101&lmt=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        latency = (time.time() - start) * 1000
        results["eastmoney"] = {"status": "ok", "latency_ms": round(latency, 1)}
    except Exception as e:
        err_str = str(e)
        # Detect proxy block (Surge/Clash DNS hijack)
        if "198.18" in err_str or "timed out" in err_str.lower():
            results["eastmoney"] = {"status": "proxy_blocked", "error": err_str}
        else:
            results["eastmoney"] = {"status": "down", "error": err_str}
    
    # 4. Local pricedb
    from pathlib import Path
    db_path = Path(__file__).parent.parent / "data" / "pricedb" / "ashare_prices.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            latest = conn.execute("SELECT MAX(date) FROM daily_prices").fetchone()
            conn.close()
            latest_date = latest[0] if latest and latest[0] else None
            results["pricedb"] = {
                "status": "ok" if latest_date else "empty",
                "latest_date": latest_date,
                "stale": not _is_trading_day_recent(latest_date) if latest_date else True,
            }
        except Exception as e:
            results["pricedb"] = {"status": "error", "error": str(e)}
    else:
        results["pricedb"] = {"status": "missing"}
    
    return results
```

### 2. Modify: `scripts/data_collector.py` — Add Sina as primary price source

**In `fetch_position_prices()`**, add Sina real-time as the FIRST source, before AkShare. Sina works through the proxy and returns full OHLC data.

Add this new function **before** `fetch_position_prices()` (around line 845):

```python
def _fetch_position_prices_sina(positions: list[dict]) -> dict:
    """Fetch real-time stock prices from Sina Finance.
    
    Sina hq.sinajs.cn returns full quote data including OHLC, volume, etc.
    Format for individual stocks: sh600000 (Shanghai) or sz000001 (Shenzhen).
    
    Response format per stock (comma-separated):
    0: name, 1: open, 2: prev_close, 3: price, 4: high, 5: low,
    6: bid, 7: ask, 8: volume (shares), 9: amount (元),
    ... (bid/ask depth)
    30: date, 31: time
    
    Returns dict keyed by code with price data, only for stocks that succeeded.
    """
    import requests as _req
    import re
    
    if not positions:
        return {}
    
    # Build Sina code list: sh + 6-digit code for Shanghai, sz for Shenzhen
    code_map = {}  # sina_code -> original_code
    for pos in positions:
        code = str(pos.get("code", "")).split(".")[0]
        if not code or len(code) != 6:
            continue
        # Shanghai: starts with 6, 9, or 5 (for ETFs); Shenzhen: starts with 0, 3, or 1
        # 科创板 (688xxx) is Shanghai
        if code.startswith(("6", "9", "5")):
            sina_code = f"sh{code}"
        elif code.startswith(("0", "3", "1", "2")):
            sina_code = f"sz{code}"
        else:
            continue
        code_map[sina_code] = code
    
    if not code_map:
        return {}
    
    prices = {}
    try:
        codes_str = ",".join(code_map.keys())
        url = f"https://hq.sinajs.cn/list={codes_str}"
        s = _req.Session()
        s.trust_env = False  # Skip system proxy
        r = s.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=10)
        r.raise_for_status()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        name_map = {pos.get("code", "").split(".")[0]: pos.get("name", "") for pos in positions}
        
        for line in r.text.strip().split("\n"):
            m = re.match(r'var hq_str_(\w+)="(.+?)";', line)
            if not m:
                continue
            
            sina_code = m.group(1)
            parts = m.group(2).split(",")
            
            if sina_code not in code_map or len(parts) < 32:
                continue
            
            code = code_map[sina_code]
            
            try:
                price = float(parts[3])
                open_price = float(parts[1])
                high = float(parts[4])
                low = float(parts[5])
                prev_close = float(parts[2])
                volume_shares = int(float(parts[8]))
                amount = float(parts[9])
                date_str = parts[30]  # YYYY-MM-DD
                
                # Skip if price is 0 (suspended/not trading)
                if price <= 0:
                    continue
                
                # Volume in lots (手) for compatibility — Sina returns shares
                volume = volume_shares // 100
                
                change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0
                
                prices[code] = {
                    "code": code,
                    "name": name_map.get(code, parts[0]),
                    "date": date_str or today_str,
                    "price": price,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "prev_close": prev_close,
                    "change_pct": change_pct,
                    "volume": volume,
                    "amount": amount,
                    "source": "sina",
                }
            except (ValueError, IndexError):
                continue
    except Exception as e:
        print(f"  Sina position price fetch failed: {e}", file=sys.stderr)
    
    return prices
```

**Then modify `fetch_position_prices()`** to use Sina first:

Replace the current `fetch_position_prices()` function body with this flow:

```python
def fetch_position_prices(positions: list[dict]) -> dict:
    """Fetch current prices for active positions.

    Fallback chain (in order):
    1. Sina real-time (hq.sinajs.cn) — works through proxy, returns OHLC ✅
    2. AkShare (Eastmoney push2) — may be proxy-blocked
    3. CheeseForTune kline — close only, no OHLC (last resort)

    Args:
        positions: List of position dicts with "code" key.

    Returns:
        Dict keyed by code with price data.
    """
    if not positions:
        return {}

    prices = {}
    failed_positions = []

    # === Source 1: Sina real-time (primary) ===
    try:
        sina_prices = _fetch_position_prices_sina(positions)
        for pos in positions:
            code = pos["code"].split(".")[0]
            if code in sina_prices:
                prices[code] = sina_prices[code]
            else:
                failed_positions.append(pos)
    except Exception as e:
        print(f"  Sina price fetch failed entirely: {e}", file=sys.stderr)
        failed_positions = list(positions)

    if not failed_positions:
        # Add MAVOL30 from pricedb if available (Sina doesn't have it)
        _enrich_with_mavol30(prices)
        return prices

    # === Source 2: AkShare (fallback) ===
    still_failed = []
    try:
        import akshare as ak
        for pos in failed_positions:
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
                    still_failed.append(pos)
            except Exception:
                still_failed.append(pos)
    except ImportError:
        still_failed = list(failed_positions)

    if not still_failed:
        _enrich_with_mavol30(prices)
        return prices

    # === Source 3: CheeseForTune kline (last resort) ===
    print(f"  Sources 1+2 failed for {len(still_failed)} stocks, trying CheeseForTune kline...", file=sys.stderr)
    try:
        client = CheeseFortuneClient()
        for pos in still_failed:
            code = pos["code"].split(".")[0]
            cf_code = normalize_code(code)
            try:
                kline = client.get_kline(cf_code, days=35)
                if kline and len(kline) > 0:
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
                    prices[code] = {"code": code, "error": "No kline data from any source"}
            except Exception as e:
                prices[code] = {"code": code, "error": f"all 3 sources failed: {e}"}
    except Exception as e:
        for pos in still_failed:
            code = pos["code"].split(".")[0]
            prices[code] = {"code": code, "error": f"all sources failed: {e}"}

    _enrich_with_mavol30(prices)
    return prices


def _enrich_with_mavol30(prices: dict):
    """Add MAVOL30 from local pricedb for prices that don't have it (e.g., Sina source)."""
    need_mavol = [code for code, p in prices.items() 
                  if isinstance(p, dict) and not p.get("error") and p.get("mavol30") is None]
    if not need_mavol or not DEFAULT_PRICEDB_PATH.exists():
        return
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(DEFAULT_PRICEDB_PATH))
        for code in need_mavol:
            rows = conn.execute(
                "SELECT volume FROM daily_prices WHERE code = ? ORDER BY date DESC LIMIT 30",
                (code,),
            ).fetchall()
            if rows:
                volumes = [int(r[0]) for r in rows if r[0] is not None]
                if volumes:
                    mavol30 = round(sum(volumes) / len(volumes), 2)
                    prices[code]["mavol30"] = mavol30
                    current_vol = prices[code].get("volume", 0)
                    prices[code]["volume_below_mavol30"] = bool(current_vol < mavol30)
        conn.close()
    except Exception as e:
        print(f"  MAVOL30 enrichment failed: {e}", file=sys.stderr)
```

### 3. Modify: `scripts/run_daily.py` — Wire in gates and manifest

**Import contracts at the top** (add after existing imports):

```python
from contracts import (
    PipelineStatus,
    PipelineHardFail,
    RunManifest,
    validate_phase1_gate,
    validate_llm_output_gate,
    validate_phase3_gate,
    check_source_health,
)
```

**In `main()`, modify the `--run` branch.** The key changes are:

#### A. Add health check before Phase 1

After the `print` header and before `data = phase1_collect(date)`, add:

```python
        # Pre-flight: Source health check
        print("Pre-flight: Checking data sources...", file=sys.stderr)
        health = check_source_health()
        for source, status in health.items():
            icon = "✓" if status.get("status") == "ok" else "✗" if status.get("status") in ("down", "proxy_blocked") else "⚠"
            latency = f" ({status['latency_ms']:.0f}ms)" if "latency_ms" in status else ""
            extra = f" — {status.get('error', '')}" if status.get("error") else ""
            if source == "pricedb" and status.get("latest_date"):
                extra = f" (latest: {status['latest_date']}, stale: {status.get('stale')})"
            print(f"  {icon} {source}: {status['status']}{latency}{extra}", file=sys.stderr)
        
        manifest = RunManifest(date=date, status=PipelineStatus.SUCCESS)
        manifest.add_phase("health_check", "ok", details={"sources": health})
        
        # Warn if critical sources are all down
        sina_down = health.get("sina", {}).get("status") != "ok"
        cf_down = health.get("cheesefortune", {}).get("status") != "ok"
        em_down = health.get("eastmoney", {}).get("status") not in ("ok",)
        if sina_down and cf_down and em_down:
            print("  ✗ ALL external data sources are down — pipeline will likely fail", file=sys.stderr)
```

#### B. Add Gate 1 after Phase 1

After `phase1_file.write_text(...)`, add:

```python
        # Gate 1: Validate Phase 1 output
        print(f"\nGate 1: Validating Phase 1 data...", file=sys.stderr)
        gate1 = validate_phase1_gate(data)
        manifest.add_gate(gate1)
        manifest.add_phase("collect", "ok" if gate1.passed else "failed",
                           duration_sec=data.get("_log_phase1", {}).get("duration_sec", 0),
                           details={"errors": data.get("_log_phase1", {}).get("errors", [])})
        
        if gate1.soft_warns:
            for w in gate1.soft_warns:
                print(f"  ⚠ {w}", file=sys.stderr)
        
        if not gate1.passed:
            for f in gate1.hard_fails:
                print(f"  ✗ {f}", file=sys.stderr)
            manifest.finalize()
            # Save manifest
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Pipeline FAILED at Gate 1 with {len(gate1.hard_fails)} hard failure(s)", file=sys.stderr)
            print(f"No LLM call made. No positions modified.", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            # Print machine-readable failure to stdout for cron
            print(json.dumps({
                "date": date,
                "status": "failed",
                "failed_at": "gate1_phase1_validation",
                "hard_fails": gate1.hard_fails,
                "soft_warns": gate1.soft_warns,
            }, ensure_ascii=False))
            sys.exit(1)
        
        print(f"  ✓ Gate 1 passed", file=sys.stderr)
```

#### C. Add Gate 2 after LLM response parsing

After the LLM response is parsed and `decisions` is set, add:

```python
        # Gate 2: Validate LLM output
        print(f"\nGate 2: Validating LLM response...", file=sys.stderr)
        gate2 = validate_llm_output_gate(decisions, data)
        manifest.add_gate(gate2)
        manifest.add_phase("llm_analysis", "ok" if gate2.passed else "failed",
                           duration_sec=llm_result["duration_sec"])
        
        if gate2.soft_warns:
            for w in gate2.soft_warns:
                print(f"  ⚠ {w}", file=sys.stderr)
        
        if not gate2.passed:
            for f in gate2.hard_fails:
                print(f"  ✗ {f}", file=sys.stderr)
            manifest.finalize()
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Pipeline FAILED at Gate 2 with {len(gate2.hard_fails)} hard failure(s)", file=sys.stderr)
            print(f"LLM ran but response is invalid. No positions modified.", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            print(json.dumps({
                "date": date,
                "status": "failed",
                "failed_at": "gate2_llm_validation",
                "hard_fails": gate2.hard_fails,
                "soft_warns": gate2.soft_warns,
            }, ensure_ascii=False))
            sys.exit(1)
        
        print(f"  ✓ Gate 2 passed", file=sys.stderr)
```

#### D. Add Gate 3 after Phase 3

After `log3 = phase3_apply(...)`, add:

```python
        # Gate 3: Validate Phase 3 output
        print(f"\nGate 3: Validating apply results...", file=sys.stderr)
        gate3 = validate_phase3_gate(date, log3, data)
        manifest.add_gate(gate3)
        manifest.add_phase("apply", "ok" if gate3.passed else "failed",
                           duration_sec=log3.get("duration_sec", 0))
        
        if gate3.soft_warns:
            for w in gate3.soft_warns:
                print(f"  ⚠ {w}", file=sys.stderr)
        
        if not gate3.passed:
            for f in gate3.hard_fails:
                print(f"  ✗ {f}", file=sys.stderr)
            manifest.finalize()
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Pipeline FAILED at Gate 3. Apply had errors. Review tracking state.", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            print(json.dumps({
                "date": date,
                "status": "failed",
                "failed_at": "gate3_apply_validation",
                "hard_fails": gate3.hard_fails,
            }, ensure_ascii=False))
            sys.exit(1)
        
        print(f"  ✓ Gate 3 passed", file=sys.stderr)
```

#### E. Save manifest at end of successful run

Before or after the existing Phase 4/5 code, add:

```python
        # Finalize manifest
        manifest.add_phase("validate", "ok" if not errors else "warnings",
                           details={"errors": errors})
        manifest.total_duration_sec = total_sec
        manifest.finalize()
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
```

#### F. Update stdout summary to include status

Change the final `print(json.dumps({...}))` to include the real status:

```python
        print(json.dumps({
            "date": date,
            "status": manifest.status.value,
            "sells": len(sells),
            "opens": len(new_pos),
            "holds": len(holds),
            "tool_calls": len(llm_result["tool_calls"]),
            "tokens": llm_result["input_tokens"] + llm_result["output_tokens"],
            "duration_sec": total_sec,
            "validation_errors": len(errors),
            "gate_warnings": sum(len(g["soft_warns"]) for g in manifest.gates.values()),
        }, ensure_ascii=False))
```

### 4. Modify: `scripts/validator.py` — Upgrade `validate_data()`

The existing `validate_data()` function should be updated to use the new severity model. It currently produces string lists that nobody acts on. It should be kept for backward compat but the real validation now happens in `contracts.py` gates. 

**No changes needed** — `validate_data()` can stay as-is for the `collection_errors` field in the data dict. The gates in `contracts.py` are the enforcement layer.

---

## Test Plan

Create `/Users/bz/Work/Personal/stock-analysis/tests/test_contracts.py`:

```python
"""
Tests for pipeline contracts and gates.

Run: python -m pytest tests/test_contracts.py -v
Or:  python tests/test_contracts.py
"""

import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest
from contracts import (
    PipelineGate,
    PipelineStatus,
    RunManifest,
    validate_phase1_gate,
    validate_llm_output_gate,
    validate_phase3_gate,
    _is_trading_day_recent,
    _is_today,
)
from datetime import datetime, timedelta


# ─── Helpers ───

def make_position_prices(*codes, source="sina", error=None):
    """Build a position_prices dict for testing."""
    prices = {}
    today = datetime.now().strftime("%Y-%m-%d")
    for code in codes:
        if error:
            prices[code] = {"code": code, "error": error}
        else:
            prices[code] = {
                "code": code,
                "name": f"Test_{code}",
                "date": today,
                "price": 100.0,
                "open": 99.0,
                "high": 101.0,
                "low": 98.0,
                "prev_close": 99.5,
                "change_pct": 0.5,
                "volume": 50000,
                "mavol30": 60000.0,
                "source": source,
            }
    return prices


def make_positions(*codes):
    """Build a positions list for testing."""
    return [{"code": code, "name": f"Test_{code}"} for code in codes]


def make_market(indices_ok=True, breadth_ok=True, breadth_total=5000):
    """Build a market dict for testing."""
    today = datetime.now().strftime("%Y-%m-%d")
    market = {}
    if indices_ok:
        market["indices"] = {
            "上证指数": {"code": "sh000001", "close": 3200.0, "change_pct": -0.5, "date": today},
            "深证成指": {"code": "sz399001", "close": 11000.0, "change_pct": 0.3, "date": today},
            "创业板指": {"code": "sz399006", "close": 2300.0, "change_pct": -0.2, "date": today},
        }
    else:
        market["indices"] = {
            "上证指数": {"error": "fetch failed"},
        }
    if breadth_ok:
        market["breadth"] = {"up": 2000, "down": 2500, "flat": 100, "total": breadth_total}
    else:
        market["breadth"] = {}
    return market


def make_pool(total=10, date=None, error=None):
    """Build a strategy_pool dict for testing."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    stocks = [{"code": f"{600000+i}", "name": f"Stock_{i}", "rps120": 85.0, "price": 50.0}
              for i in range(total)]
    return {
        "source": "test",
        "strategy_id": "test",
        "date": date,
        "total_stocks": total,
        "stocks": stocks,
        "error": error,
    }


def make_phase1_data(
    position_codes=None,
    price_error=None,
    indices_ok=True,
    breadth_ok=True,
    breadth_total=5000,
    pool_total=10,
    pool_date=None,
    pool_error=None,
    iv_error=None,
):
    """Build a complete Phase 1 data dict for testing."""
    codes = position_codes or []
    data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "positions": make_positions(*codes),
        "position_prices": make_position_prices(*codes, error=price_error) if codes else {},
        "market": make_market(indices_ok=indices_ok, breadth_ok=breadth_ok, breadth_total=breadth_total),
        "strategy_pool": make_pool(total=pool_total, date=pool_date, error=pool_error),
        "enriched": [],
        "iv_sentiment": {"error": iv_error} if iv_error else {"overall_sentiment": {"signal": "中性"}},
    }
    return data


# ━━━ PipelineGate unit tests ━━━

class TestPipelineGate:
    def test_empty_gate_passes(self):
        gate = PipelineGate("test")
        result = gate.check()
        assert result.passed is True
        assert result.hard_fails == []
        assert result.soft_warns == []

    def test_soft_warn_still_passes(self):
        gate = PipelineGate("test")
        gate.soft(False, "this is a warning")
        result = gate.check()
        assert result.passed is True
        assert len(result.soft_warns) == 1

    def test_hard_fail_blocks(self):
        gate = PipelineGate("test")
        gate.hard(False, "critical failure")
        result = gate.check()
        assert result.passed is False
        assert len(result.hard_fails) == 1

    def test_hard_pass_when_true(self):
        gate = PipelineGate("test")
        gate.hard(True, "should not appear")
        result = gate.check()
        assert result.passed is True
        assert result.hard_fails == []

    def test_multiple_failures(self):
        gate = PipelineGate("test")
        gate.hard(False, "fail 1")
        gate.hard(False, "fail 2")
        gate.soft(False, "warn 1")
        result = gate.check()
        assert result.passed is False
        assert len(result.hard_fails) == 2
        assert len(result.soft_warns) == 1


# ━━━ Date freshness tests ━━━

class TestDateFreshness:
    def test_today_is_fresh(self):
        today = datetime.now().strftime("%Y-%m-%d")
        assert _is_trading_day_recent(today) is True

    def test_yesterday_is_fresh(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert _is_trading_day_recent(yesterday) is True

    def test_4_days_ago_is_fresh(self):
        """Long weekends can cause 3-4 day gaps."""
        four_ago = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d")
        assert _is_trading_day_recent(four_ago) is True

    def test_5_days_ago_is_stale(self):
        five_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        assert _is_trading_day_recent(five_ago) is False

    def test_empty_string_is_not_fresh(self):
        assert _is_trading_day_recent("") is False

    def test_none_is_not_fresh(self):
        assert _is_trading_day_recent(None) is False

    def test_slash_format(self):
        today = datetime.now().strftime("%Y/%m/%d")
        assert _is_trading_day_recent(today) is True

    def test_is_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        assert _is_today(today) is True

    def test_yesterday_is_not_today(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        assert _is_today(yesterday) is False


# ━━━ Gate 1: Phase 1 → Phase 2 ━━━

class TestPhase1Gate:
    """Gate 1 validates Phase 1 data collection output."""

    def test_clean_data_passes(self):
        """Perfect data → gate passes with no warnings."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert result.hard_fails == []

    def test_no_positions_passes(self):
        """No active positions → gate passes (nothing to price)."""
        data = make_phase1_data(position_codes=[])
        result = validate_phase1_gate(data)
        assert result.passed is True

    def test_position_price_error_hard_fails(self):
        """Position with price error → hard failure."""
        data = make_phase1_data(position_codes=["605167"], price_error="No kline data")
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("605167" in f and "No kline data" in f for f in result.hard_fails)

    def test_position_price_zero_hard_fails(self):
        """Position with price=0 → hard failure."""
        data = make_phase1_data(position_codes=["605167"])
        data["position_prices"]["605167"]["price"] = 0
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("invalid price=0" in f for f in result.hard_fails)

    def test_position_price_none_hard_fails(self):
        """Position with price=None → hard failure."""
        data = make_phase1_data(position_codes=["605167"])
        data["position_prices"]["605167"]["price"] = None
        result = validate_phase1_gate(data)
        assert result.passed is False

    def test_position_prices_empty_with_positions_hard_fails(self):
        """Active positions but empty price dict → hard failure."""
        data = make_phase1_data(position_codes=["605167"])
        data["position_prices"] = {}
        result = validate_phase1_gate(data)
        assert result.passed is False

    def test_two_of_three_indices_ok(self):
        """2/3 indices valid → passes."""
        data = make_phase1_data()
        del data["market"]["indices"]["创业板指"]
        result = validate_phase1_gate(data)
        assert result.passed is True

    def test_one_of_three_indices_hard_fails(self):
        """Only 1/3 indices valid → hard failure."""
        data = make_phase1_data(indices_ok=False)
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("indices" in f.lower() for f in result.hard_fails)

    def test_breadth_too_low_hard_fails(self):
        """Breadth total < 1000 → hard failure (broken data)."""
        data = make_phase1_data(breadth_total=500)
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("breadth" in f.lower() for f in result.hard_fails)

    def test_breadth_missing_hard_fails(self):
        """No breadth data → hard failure."""
        data = make_phase1_data(breadth_ok=False)
        result = validate_phase1_gate(data)
        assert result.passed is False

    def test_pool_stale_date_hard_fails(self):
        """Pool has stocks but date is 10 days old → hard failure."""
        stale = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        data = make_phase1_data(pool_date=stale, pool_total=5)
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert any("stale" in f.lower() for f in result.hard_fails)

    def test_pool_yesterday_soft_warns(self):
        """Pool date is yesterday (not today) → soft warning, not hard fail.
        This is common when pricedb hasn't updated yet."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        data = make_phase1_data(pool_date=yesterday, pool_total=5)
        result = validate_phase1_gate(data)
        assert result.passed is True  # Soft warn, not hard fail
        assert any("not today" in w.lower() for w in result.soft_warns)

    def test_pool_empty_soft_warns(self):
        """Empty pool → soft warning (can be legitimate on weak days)."""
        data = make_phase1_data(pool_total=0)
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert any("empty" in w.lower() for w in result.soft_warns)

    def test_pool_error_soft_warns(self):
        """Pool with error → soft warning."""
        data = make_phase1_data(pool_error="API timeout")
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert any("API timeout" in w for w in result.soft_warns)

    def test_iv_error_soft_warns(self):
        """IV sentiment failure → soft warning (supplementary data)."""
        data = make_phase1_data(iv_error="timeout")
        result = validate_phase1_gate(data)
        assert result.passed is True
        assert any("IV" in w for w in result.soft_warns)

    def test_multiple_position_failures(self):
        """Multiple positions failing → all reported."""
        data = make_phase1_data(position_codes=["605167", "688037"], price_error="No kline data")
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert len(result.hard_fails) >= 2

    def test_real_failure_scenario_20260409(self):
        """Reproduce today's actual failure: both prices missing, pool stale."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        # Simulate real failure
        data["position_prices"]["605167"] = {"code": "605167", "error": "No kline data"}
        data["position_prices"]["688037"] = {"code": "688037", "error": "No kline data"}
        data["strategy_pool"]["date"] = "2026-04-08"
        data["strategy_pool"]["total_stocks"] = 0
        data["strategy_pool"]["stocks"] = []
        data["date"] = "2026-04-09"
        
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert len(result.hard_fails) >= 2  # Both prices
        # Pool is empty (0 stocks) → soft warn about empty, NOT hard fail about stale
        # (stale date check only applies when pool has stocks)


# ━━━ Gate 2: Phase 2 → Phase 3 ━━━

class TestLLMOutputGate:
    """Gate 2 validates LLM response before applying decisions."""

    def _make_decisions(self, position_codes=None, new_positions=None, extra=None):
        """Build a valid decisions dict."""
        decisions = {
            "market_summary": "Test summary",
            "position_decisions": [
                {"code": code, "action": "HOLD", "reason": "Above stop"}
                for code in (position_codes or [])
            ],
            "new_positions": new_positions or [],
            "skip_list": [],
            "watchlist": [],
            "new_learnings": [],
            **(extra or {}),
        }
        return decisions

    def test_valid_decisions_pass(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions(position_codes=["605167"])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_empty_decisions_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        result = validate_llm_output_gate({}, data)
        assert result.passed is False

    def test_missing_position_decision_hard_fails(self):
        """Active position not in decisions → hard fail."""
        data = make_phase1_data(position_codes=["605167", "688037"])
        decisions = self._make_decisions(position_codes=["605167"])  # Missing 688037
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("688037" in f for f in result.hard_fails)

    def test_invalid_action_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "BUY_MORE", "reason": "YOLO"}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("BUY_MORE" in f for f in result.hard_fails)

    def test_sell_without_exit_price_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "SELL", "reason": "Stop hit"}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("exit_price" in f for f in result.hard_fails)

    def test_sell_with_exit_price_passes(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "SELL", "reason": "Stop hit", "exit_price": 15.5}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_raise_stop_without_new_stop_hard_fails(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "RAISE_STOP", "reason": "Trailing"}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("new_stop" in f for f in result.hard_fails)

    def test_raise_stop_with_valid_stop_passes(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions()
        decisions["position_decisions"] = [
            {"code": "605167", "action": "RAISE_STOP", "reason": "Trailing", "new_stop": 16.0}
        ]
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_new_position_missing_fields_hard_fails(self):
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test"}  # Missing entry_price, stop, target, thesis
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert len(result.hard_fails) >= 3  # At least entry_price, stop, target

    def test_new_position_stop_above_entry_hard_fails(self):
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": 50.0,
             "stop": 55.0, "target": 60.0, "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is False
        assert any("stop" in f and "entry_price" in f for f in result.hard_fails)

    def test_valid_new_position_passes(self):
        data = make_phase1_data()
        decisions = self._make_decisions(new_positions=[
            {"code": "600000", "name": "Test", "entry_price": 50.0,
             "stop": 45.0, "target": 60.0, "thesis": "Breakout"}
        ])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True

    def test_missing_market_summary_soft_warns(self):
        data = make_phase1_data(position_codes=["605167"])
        decisions = self._make_decisions(position_codes=["605167"])
        decisions["market_summary"] = ""
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True
        assert any("market_summary" in w for w in result.soft_warns)

    def test_no_positions_empty_decisions_passes(self):
        """No active positions + empty position_decisions → passes."""
        data = make_phase1_data(position_codes=[])
        decisions = self._make_decisions(position_codes=[])
        result = validate_llm_output_gate(decisions, data)
        assert result.passed is True


# ━━━ Gate 3: Phase 3 → Phase 4 ━━━

class TestPhase3Gate:
    def test_clean_apply_passes(self):
        log = {"actions": ["HOLD 605167", "Generated report"]}
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is True

    def test_error_action_hard_fails(self):
        log = {"actions": ["ERROR SELL 605167: file not found"]}
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is False

    def test_price_correction_soft_warns(self):
        log = {"actions": ["PRICE_CORRECTED 605167: LLM=29.79 outside [28,31], using market=30.5"]}
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is True
        assert len(result.soft_warns) == 1

    def test_volume_rule_violation_soft_warns(self):
        log = {
            "actions": ["HOLD 605167"],
            "post_apply_rule_violations": {
                "status": "violations",
                "rules": [{
                    "rule": "check_volume_below_mavol30",
                    "status": "violations",
                    "violations": [{"code": "605167", "suggestion": "Volume 21K below MAVOL30 67K"}],
                }],
            },
        }
        result = validate_phase3_gate("2026-04-09", log, {})
        assert result.passed is True
        assert len(result.soft_warns) >= 1


# ━━━ RunManifest tests ━━━

class TestRunManifest:
    def test_successful_run(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        m.add_phase("collect", "ok", 13.5)
        g = PipelineGate("test")
        m.add_gate(g.check())
        m.finalize()
        assert m.status == PipelineStatus.SUCCESS
        assert m.exit_code == 0

    def test_degraded_run(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        g = PipelineGate("test")
        g.soft(False, "IV failed")
        m.add_gate(g.check())
        m.finalize()
        assert m.status == PipelineStatus.DEGRADED
        assert m.exit_code == 0

    def test_failed_run(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        g = PipelineGate("test")
        g.hard(False, "no prices")
        m.add_gate(g.check())
        m.finalize()
        assert m.status == PipelineStatus.FAILED
        assert m.exit_code == 1

    def test_to_dict_serializable(self):
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        m.finalize()
        d = m.to_dict()
        # Must be JSON-serializable
        json_str = json.dumps(d)
        assert '"success"' in json_str


# ━━━ Sina price fetch tests (integration) ━━━

class TestSinaPriceFetch:
    """Integration tests for Sina price fetching.
    
    These tests hit the real Sina API. Skip with -m "not integration" if needed.
    They verify the Sina fallback chain actually works on this machine.
    """

    @pytest.mark.integration
    def test_fetch_shanghai_stock(self):
        """Fetch a Shanghai stock (6xxxxx) via Sina."""
        from data_collector import _fetch_position_prices_sina
        positions = [{"code": "601398", "name": "工商银行"}]  # ICBC — always available
        result = _fetch_position_prices_sina(positions)
        assert "601398" in result
        p = result["601398"]
        assert p["source"] == "sina"
        assert p["price"] > 0
        assert p["open"] > 0
        assert p["high"] >= p["low"]
        assert p["volume"] >= 0

    @pytest.mark.integration
    def test_fetch_shenzhen_stock(self):
        """Fetch a Shenzhen stock (0xxxxx) via Sina."""
        from data_collector import _fetch_position_prices_sina
        positions = [{"code": "000001", "name": "平安银行"}]
        result = _fetch_position_prices_sina(positions)
        assert "000001" in result
        assert result["000001"]["price"] > 0

    @pytest.mark.integration
    def test_fetch_star_market_stock(self):
        """Fetch a 科创板 stock (688xxx) via Sina."""
        from data_collector import _fetch_position_prices_sina
        positions = [{"code": "688037", "name": "芯源微"}]
        result = _fetch_position_prices_sina(positions)
        assert "688037" in result
        assert result["688037"]["price"] > 0

    @pytest.mark.integration
    def test_fetch_multiple_stocks(self):
        """Fetch multiple stocks in one call."""
        from data_collector import _fetch_position_prices_sina
        positions = [
            {"code": "605167", "name": "利柏特"},
            {"code": "688037", "name": "芯源微"},
        ]
        result = _fetch_position_prices_sina(positions)
        assert len(result) == 2
        for code in ["605167", "688037"]:
            assert code in result
            assert result[code]["price"] > 0

    @pytest.mark.integration
    def test_full_fallback_chain(self):
        """Test full fetch_position_prices with Sina as primary."""
        from data_collector import fetch_position_prices
        positions = [
            {"code": "601398", "name": "工商银行"},
            {"code": "605167", "name": "利柏特"},
        ]
        result = fetch_position_prices(positions)
        for code in ["601398", "605167"]:
            assert code in result
            p = result[code]
            assert not p.get("error"), f"{code} has error: {p.get('error')}"
            assert p["price"] > 0
            # Should come from Sina (primary) unless something is wrong
            # Don't assert source=sina because AkShare might succeed too


# ━━━ End-to-end pipeline gate tests ━━━

class TestEndToEnd:
    """Tests that simulate real pipeline scenarios."""

    def test_20260409_scenario_would_fail(self):
        """Today's real scenario: both positions have no prices.
        With gates, the pipeline would have stopped at Gate 1."""
        data = {
            "date": "2026-04-09",
            "positions": [
                {"code": "605167", "name": "利柏特"},
                {"code": "688037", "name": "芯源微"},
            ],
            "position_prices": {
                "605167": {"code": "605167", "error": "No kline data"},
                "688037": {"code": "688037", "error": "No kline data"},
            },
            "market": make_market(),
            "strategy_pool": {
                "source": "local_pricedb+cf_cross",
                "strategy_id": "407228-local-ma-rps",
                "date": "2026-04-08",
                "total_stocks": 0,
                "stocks": [],
                "error": None,
            },
            "enriched": [],
            "iv_sentiment": {"overall_sentiment": {"signal": "偏乐观"}},
        }
        result = validate_phase1_gate(data)
        assert result.passed is False
        assert len(result.hard_fails) >= 2
        # Verify the actual error messages are useful
        for fail in result.hard_fails:
            assert "605167" in fail or "688037" in fail

    def test_clean_run_all_gates_pass(self):
        """A perfectly clean run passes all gates."""
        # Phase 1 gate
        data = make_phase1_data(position_codes=["605167"])
        g1 = validate_phase1_gate(data)
        assert g1.passed is True

        # Phase 2 gate
        decisions = {
            "market_summary": "Weak day",
            "position_decisions": [
                {"code": "605167", "action": "HOLD", "reason": "Above stop"}
            ],
            "new_positions": [],
            "skip_list": [],
            "watchlist": [{"code": "600000", "name": "Test"}],
            "new_learnings": [],
        }
        g2 = validate_llm_output_gate(decisions, data)
        assert g2.passed is True

        # Phase 3 gate
        apply_log = {"actions": ["HOLD 605167", "Generated report"]}
        g3 = validate_phase3_gate("2026-04-09", apply_log, data)
        assert g3.passed is True

        # Manifest
        m = RunManifest(date="2026-04-09", status=PipelineStatus.SUCCESS)
        m.add_gate(g1)
        m.add_gate(g2)
        m.add_gate(g3)
        m.finalize()
        assert m.status == PipelineStatus.SUCCESS


# ━━━ Runner ━━━

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

### 5. Create `tests/conftest.py`:

```python
"""Pytest configuration for stock-analysis tests."""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests that hit real APIs"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests that hit real APIs")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
```

---

## File Summary

| File | Action | Description |
|------|--------|-------------|
| `scripts/contracts.py` | **CREATE** | Pipeline contracts, gates, manifest, health check |
| `scripts/data_collector.py` | **MODIFY** | Add `_fetch_position_prices_sina()`, rewrite `fetch_position_prices()` with Sina-first fallback chain, add `_enrich_with_mavol30()` |
| `scripts/run_daily.py` | **MODIFY** | Import contracts, add health check, wire Gate 1/2/3 into `--run` flow, save manifest, proper exit codes |
| `tests/test_contracts.py` | **CREATE** | 45+ tests covering all gates, date freshness, manifest, Sina integration, end-to-end scenarios |
| `tests/conftest.py` | **CREATE** | Pytest config with `--run-integration` flag |

## Key Behaviors After Implementation

1. **Pipeline with missing prices:**
   ```
   Gate 1: Validating Phase 1 data...
     ✗ position 605167 (利柏特): price fetch error: No kline data
     ✗ position 688037 (芯源微): price fetch error: No kline data
   Pipeline FAILED at Gate 1 with 2 hard failure(s)
   No LLM call made. No positions modified.
   ```
   Exit code: 1. Stdout JSON has `"status": "failed"`.

2. **Pipeline with stale pool but valid prices:**
   ```
   Gate 1: Validating Phase 1 data...
     ⚠ strategy pool date '2026-04-08' is not today
     ✓ Gate 1 passed
   ```
   Continues as DEGRADED (soft warning, not hard fail for 1-day-old pool).

3. **LLM forgets a position:**
   ```
   Gate 2: Validating LLM response...
     ✗ no decision for active position(s): {'688037'}
   Pipeline FAILED at Gate 2.
   ```

4. **All sources down:**
   ```
   Pre-flight: Checking data sources...
     ✗ sina: down — ConnectionError
     ✗ cheesefortune: down — timeout
     ✗ eastmoney: proxy_blocked
     ⚠ pricedb: ok (latest: 2026-04-08, stale: False)
     ✗ ALL external data sources are down — pipeline will likely fail
   ```

## Implementation Notes

- Do NOT remove the existing `validate_data()` in `validator.py` — it still populates `collection_errors` in the data dict for the LLM prompt. The gates in `contracts.py` are the enforcement layer on top of it.
- The `--apply` path in `main()` does NOT need gates (it's a manual re-apply of an already-validated response).
- The legacy `--phase1` path (no `--run`) does NOT need gates (it just collects data for manual review).
- Only the `--run` path (full automated pipeline) gets gates.
- Health check is advisory — it logs source status but doesn't block the pipeline (the gates handle that based on actual data quality).
- Sina volume is returned in shares (股), convert to lots (手, ÷100) for consistency with AkShare.
- `_enrich_with_mavol30()` supplements Sina data with MAVOL30 from local pricedb, since Sina only returns today's data (not 30-day history).

## Validation

After implementation:
1. `python -m pytest tests/test_contracts.py -v` — all unit tests pass
2. `python -m pytest tests/test_contracts.py -v --run-integration` — Sina integration tests pass
3. `python scripts/run_daily.py --run --no-commit` — runs with gates, produces `manifest.json`
4. Manually corrupt `tracking/605167.json` to have a bad price source → verify Gate 1 catches it
