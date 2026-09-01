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


# Gate-severity epoch. Before this date `degraded` was produced by rules that
# have since been retired: a dead V1 `watchlist` check fired on every run and
# risk-engine findings counted as degradation, so 115 of 147 historical runs
# say `degraded` and the word carried no information (fixed 6ab9377).
#
# Those manifests are NOT rewritten. A past run's manifest is the record of
# what that run reported; recomputing it would make history claim something it
# never said — the same reasoning that kept HISTORY_SCHEMA_EPOCH's pre-epoch
# events unreplayed rather than back-filled with invented values, and that kept
# the 奥来德 T+1 trade on the books with a marker instead of deleting it.
#
# Consumers that compare run health across time MUST split on this date and say
# so in their output. Anything reading pre-epoch `status` as comparable to
# post-epoch `status` is reading noise.
GATE_SEVERITY_EPOCH = "2026-08-19"


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
    notes: list[str] = field(default_factory=list)


class PipelineGate:
    """Gate between pipeline phases. Accumulates checks, fails loudly on hard violations."""

    def __init__(self, name: str):
        self.name = name
        self.hard_fails: list[str] = []
        self.soft_warns: list[str] = []
        self.notes: list[str] = []

    def hard(self, condition: bool, msg: str):
        """Add a hard requirement. If condition is False, pipeline must stop."""
        if not condition:
            self.hard_fails.append(msg)

    def soft(self, condition: bool, msg: str):
        """Something is WRONG but not fatal. Sets run status to `degraded`.

        Reserve this for actual defects. 2026-08-19: 94% of runs (116/123) were
        `degraded`, 120 of them on a single dead check — so the status carried no
        information and nothing ever stood out. Routine observations belong in
        `note()`.
        """
        if not condition:
            self.soft_warns.append(msg)

    def note(self, msg: str):
        """Record something worth seeing that is NOT a defect.

        Recorded in the manifest and surfaced in the report, but does not touch
        run status. The risk engine's WATCH/WARNING output is the motivating
        case: a position sitting 4% above its stop is the rules working, not the
        pipeline degrading.
        """
        self.notes.append(msg)

    def check(self) -> GateResult:
        """Evaluate the gate. Returns GateResult with pass/fail and messages."""
        passed = len(self.hard_fails) == 0
        return GateResult(
            name=self.name,
            passed=passed,
            hard_fails=list(self.hard_fails),
            soft_warns=list(self.soft_warns),
            notes=list(self.notes),
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

    # ── Data-quality health (2026-08-01, post-outage): never analyze
    # antique or corrupt price data politely. Absent block = older run
    # replay / minimal test fixture → skip (backward compatible). ──
    health = data.get("db_health") or {}
    if health.get("check_failed"):
        # The checker itself died. Before 2026-09-01 this left db_health
        # absent, which skipped all three gates below — the exact gates that
        # halted the DNS-outage runs. A dead smoke detector is a hard fail.
        gate.hard(False,
                  f"db_health check itself failed ({health['check_failed']}) — "
                  f"cannot certify price data; halt rather than analyze blind")
    if health:
        lag = health.get("lag_sessions")
        if lag is not None:
            gate.hard(
                lag <= 1,
                f"price DB is {lag} sessions stale "
                f"(latest {health.get('latest_price_date')}, "
                f"expected {health.get('expected_latest')}) — halt, do not "
                f"screen on antique data"
            )
            gate.soft(lag == 0, f"price DB is {lag} session stale (coverage-floor fallback in effect)")
        gate.hard(
            not health.get("latest_partial"),
            f"latest price day is partial "
            f"({health.get('latest_row_count')} rows vs "
            f"~{health.get('median_row_count_30d')}) — run 'pricedb.py repair'"
        )
        spot = health.get("spot_check") or {}
        gate.hard(
            not spot.get("mismatches"),
            f"cross-source spot audit found {len(spot.get('mismatches', []))} "
            f"price mismatches vs sina — DB values may be corrupt"
        )

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
    seen_codes: dict[str, str] = {}  # code -> first action seen

    for d in position_decisions:
        code = str(d.get("code", "")).split(".")[0]

        # Detect duplicate decisions for same position
        if code in seen_codes:
            gate.hard(
                False,
                f"position {code}: duplicate decision ('{seen_codes[code]}' and '{d.get('action', '')}') — exactly one required"
            )
        else:
            seen_codes[code] = d.get("action", "")

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

        # Numeric fields must be actual numbers, not strings
        numeric_fields = {"entry_price", "stop", "target"}
        for fname in numeric_fields:
            fval = p.get(fname)
            if fval is not None and not isinstance(fval, (int, float)):
                gate.hard(
                    False,
                    f"new position {code}: '{fname}' must be numeric, got {type(fval).__name__} '{fval}'"
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
    # NOTE: there used to be a `gate.soft("watchlist" in decisions, ...)` here.
    # `watchlist` is the V1 response schema; V2 replaced it with skip_list +
    # new_positions months ago (see report_generator.py's V1/V2 comments), and
    # watchlist.json is produced separately by generate_watchlist_json and has
    # always existed. So the check asked for a key that must not be there and
    # fired on all 120 V2 runs, single-handedly making 94% of history "degraded".
    # Removed 2026-08-19. If you want to assert the artifact, assert the FILE.

    return gate.check()


# ─── Gate 3: Phase 3 → Phase 4 (Apply → Commit) ───

def validate_phase3_gate(date: str, apply_log: dict, data: dict,
                         decisions: dict | None = None) -> GateResult:
    """Validate Phase 3 output before committing.

    Hard failures:
    - Actions contain ERROR entries
    - Position file inconsistency (positions.json vs tracking/*.json)
    - An intended new position neither opened nor accounted for by a SKIP

    Soft warnings:
    - Price corrections applied
    - Fallback prices used
    - Intended new positions that were skipped (the report must not call these
      "今日开仓")
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
    # Rule output is the risk engine doing its job, not the pipeline degrading —
    # recorded as notes so it reaches the report without setting run status.
    # A rule that ERRORED is different: that is a real defect.
    if rule_violations.get("status") == "violations":
        for rule in rule_violations.get("rules", []):
            if rule.get("status") == "violations":
                for v in rule.get("violations", []):
                    gate.note(f"rule {rule['rule']}: {v.get('suggestion', v.get('code', '?'))}")
    for rule in rule_violations.get("rules", []):
        if rule.get("error"):
            gate.soft(False, f"rule {rule.get('rule')} failed to run: {rule['error']}")

    # ── Check persisted state consistency ──
    opened_codes = {a.split()[1] for a in actions
                    if isinstance(a, str) and a.startswith("OPEN ") and len(a.split()) > 1}
    _check_position_file_consistency(gate, run_date=date, opened_codes=opened_codes)

    # ── Intent vs reality ──
    # 2026-08-17: the LLM asked to open 688019, position_manager refused it on a
    # sizing bug, and report.md still printed "今日开仓 1只" with an entry price
    # and a thesis. Every gate passed. Nothing in the pipeline compared what we
    # said we did against what we did — the same shape as the 07-20 and 08-14
    # failures. A skip is legitimate; a *silent* skip is not.
    intended = [p for p in ((decisions or {}).get("new_positions") or [])
                if isinstance(p, dict) and p.get("code")]
    if intended:
        skip_codes = {a.split()[2].rstrip(":") for a in actions
                      if isinstance(a, str) and a.startswith("SKIP OPEN ")
                      and len(a.split()) > 2}
        skipped_all = any(isinstance(a, str) and a.startswith("SKIP OPEN ALL")
                          for a in actions)
        for p in intended:
            code = str(p["code"]).split(".")[0]
            if code in opened_codes:
                continue
            if code in skip_codes or skipped_all:
                reason = next((a for a in actions if isinstance(a, str)
                               and a.startswith(f"SKIP OPEN {code}")), "SKIP OPEN ALL")
                gate.soft(False, f"intended new position not opened: {reason}")
            else:
                gate.hard(False,
                          f"intended new position {code} ({p.get('name', '?')}) was "
                          f"neither opened nor skipped with a reason — apply phase "
                          f"lost it silently")

    return gate.check()


def _check_position_file_consistency(gate: PipelineGate, tracking_dir=None,
                                     run_date=None, opened_codes=None):
    """Verify positions.json matches tracking/*.json on disk.

    tracking_dir is injectable so tests can exercise this against a temp
    directory (the real one is the default)."""
    future_dated = []
    opened_codes = set(opened_codes or ())
    import json
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    tracking_dir = Path(tracking_dir) if tracking_dir else project_root / "tracking"
    positions_file = tracking_dir / "positions.json"

    if not positions_file.exists():
        gate.hard(False, "positions.json does not exist after apply")
        return

    try:
        pos_data = json.loads(positions_file.read_text(encoding="utf-8"))
        pos_codes = {p["code"] for p in pos_data.get("activePositions", [])}
    except (json.JSONDecodeError, KeyError) as e:
        gate.hard(False, f"positions.json is invalid: {e}")
        return

    tracking_codes = set()
    for f in tracking_dir.glob("*.json"):
        if f.name == "positions.json":
            continue
        try:
            fdata = json.loads(f.read_text(encoding="utf-8"))
            # tracking/ holds non-position state too (rotation_ledger.json is
            # a LIST) — only dicts can be positions (2026-08-11)
            if isinstance(fdata, dict) and fdata.get("status") == "active":
                tracking_codes.add(fdata["code"])
                # 2026-08-14: a slot that ran past midnight stamped entryDate
                # from the wall clock, dating 600160 a day ahead of the close
                # it actually bought — which runs the time-stop clock late.
                # Only positions THIS run opened: pre-existing holdings are
                # legitimately dated after an old --date backfill's run date.
                entry_date = fdata.get("entryDate")
                if (run_date and entry_date and entry_date > run_date
                        and fdata["code"] in opened_codes):
                    future_dated.append(f"{fdata['code']}({entry_date})")
        except (json.JSONDecodeError, KeyError):
            continue

    if pos_codes != tracking_codes:
        diff = pos_codes.symmetric_difference(tracking_codes)
        gate.hard(False, f"positions.json mismatch with tracking files: {diff}")

    if future_dated:
        gate.soft(False, f"entryDate ahead of run date {run_date} (time-stop "
                         f"clock will run late): {', '.join(sorted(future_dated))}")


# ─── Run Manifest ───

@dataclass
class RunManifest:
    """Machine-readable summary of a pipeline run."""
    date: str
    status: PipelineStatus
    slot: str = "afternoon"
    run_started_at: str = ""
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
            "notes": getattr(result, "notes", []),
        }

    def finalize(self):
        """Set overall status from gate results and phase-level errors."""
        any_hard_fail = any(not g["passed"] for g in self.gates.values())
        any_soft_warn = any(len(g["soft_warns"]) > 0 for g in self.gates.values())

        # Check for CRITICAL errors in phase details (e.g., from validate_output)
        any_critical = False
        for phase in self.phases.values():
            for err in phase.get("errors", []):
                if isinstance(err, str) and err.startswith("CRITICAL"):
                    any_critical = True
                    break

        if any_hard_fail or any_critical:
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
            "slot": self.slot,
            "run_started_at": self.run_started_at,
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

    # 3. Local pricedb
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
