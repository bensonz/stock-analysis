"""RENAMED from test_full_pipeline.py (repo audit 2026-09-01).

Under pytest its 7 test_* functions could NEVER fail: every assertion routed
through a check() helper that prints and counts instead of raising, so a
failing check was invisible green — and test_4_rules subprocessed the whole
rule engine against LIVE tracking/positions.json on every suite run. It was
fake coverage over live state. The prefix rename removes it from collection;
run it BY HAND as the smoke tool it actually is:

    python3 scripts/manual_full_pipeline_check.py

Original docstring follows.
"""
#!/usr/bin/env python3
"""
test_full_pipeline.py — End-to-end simulation of the daily + evolution pipeline.

Simulates a multi-day run without real API calls or LLM tokens.
Uses mock data to verify:
  1. Portfolio tracking math (equity, cash, P&L)
  2. Position sizing (allocation_pct → shares)
  3. Rule execution (pre and post apply)
  4. new_scripts creation
  5. Realized P&L from closed positions
  6. Log completeness

Usage:
    cd /Users/bz/Work/Personal/stock-analysis
    source .venv/bin/activate
    python scripts/test_full_pipeline.py
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

# Test uses a temp copy to avoid mutating real data
ORIGINAL_TRACKING = PROJECT_ROOT / "tracking"
ORIGINAL_RULES = PROJECT_ROOT / "scripts" / "rules"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    END = "\033[0m"


def ok(msg):
    print(f"  {Colors.GREEN}✓{Colors.END} {msg}")


def fail(msg):
    print(f"  {Colors.RED}✗{Colors.END} {msg}")


def warn(msg):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")


def section(msg):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")


passed = 0
failed = 0


def check(condition, msg_pass, msg_fail=None):
    global passed, failed
    if condition:
        ok(msg_pass)
        passed += 1
    else:
        fail(msg_fail or f"FAILED: {msg_pass}")
        failed += 1


def test_1_portfolio_config():
    """Test portfolio config loading."""
    section("Test 1: Portfolio Config")
    from position_manager import load_portfolio_config
    config = load_portfolio_config()
    check(config["starting_capital"] == 1_000_000, "Starting capital = ¥1,000,000")
    check(config["max_position_pct"] == 10, "Max position size = 10%")
    check(config["max_positions"] == 10, "Max positions = 10")
    check(config["min_cash_pct"] == 0, "Min cash reserve = 0% (fully deployable)")


def test_2_realized_pnl():
    """Test realized P&L computation from closed positions."""
    section("Test 2: Realized P&L")
    from position_manager import compute_realized_pnl, load_portfolio_config

    config = load_portfolio_config()
    realized = compute_realized_pnl()
    print(f"  Realized P&L: ¥{realized:,.2f}")

    # Check each closed position
    closed_dir = PROJECT_ROOT / "tracking" / "closed"
    if closed_dir.exists():
        for f in closed_dir.glob("*.json"):
            p = json.loads(f.read_text())
            entry = p.get("entryPrice", 0)
            exit_p = p.get("exitPrice", 0)
            shares = p.get("shares") or int((config["starting_capital"] * config["max_position_pct"] / 100) // entry)
            pnl = (exit_p - entry) * shares
            name = p.get("name", f.stem)
            direction = "📈" if pnl >= 0 else "📉"
            print(f"    {direction} {name}: entry=¥{entry} exit=¥{exit_p} shares={shares} P&L=¥{pnl:,.2f}")

    check(isinstance(realized, float), "Realized P&L is a number")
    # With current closed positions (all losses), realized should be negative
    check(realized != 0, f"Realized P&L is non-zero (¥{realized:,.2f})")


def test_3_regenerate_positions():
    """Test positions.json regeneration — READ ONLY, validates current state."""
    section("Test 3: Portfolio Validation (current positions.json)")
    from position_manager import load_active_positions

    active = load_active_positions()
    if not active:
        warn("No active positions — skipping")
        return

    # Read current positions.json (don't regenerate — that mutates files)
    positions_file = PROJECT_ROOT / "tracking" / "positions.json"
    result = json.loads(positions_file.read_text())
    portfolio = result.get("portfolio", {})
    positions = result.get("activePositions", [])

    print(f"  Portfolio equity: ¥{portfolio.get('totalEquity', 0):,.2f}")
    print(f"  Cash: ¥{portfolio.get('cash', 0):,.2f} ({portfolio.get('cashPct', 0):.1f}%)")
    print(f"  Invested: ¥{portfolio.get('investedValue', 0):,.2f}")
    print(f"  Unrealized: ¥{portfolio.get('unrealizedPnl', 0):,.2f}")
    print(f"  Realized: ¥{portfolio.get('realizedPnl', 0):,.2f}")
    print(f"  Total Return: {portfolio.get('totalReturnPct', 0):.2f}%")

    # Validate math
    check("portfolio" in result, "Portfolio block exists")
    check(len(positions) > 0, f"{len(positions)} active positions")

    # cash + investedValue ≈ totalEquity
    equity_check = abs(portfolio["cash"] + portfolio["investedValue"] - portfolio["totalEquity"]) < 1
    check(equity_check, f"cash + invested = equity ({portfolio['cash']:.0f} + {portfolio['investedValue']:.0f} = {portfolio['totalEquity']:.0f})")

    # unrealized + realized = totalPnl
    pnl_check = abs(portfolio["unrealizedPnl"] + portfolio["realizedPnl"] - portfolio["totalPnl"]) < 1
    check(pnl_check, f"unrealized + realized = totalPnl ({portfolio['unrealizedPnl']:.0f} + {portfolio['realizedPnl']:.0f} = {portfolio['totalPnl']:.0f})")

    # totalReturnPct = totalPnl / startingCapital * 100
    expected_return = portfolio["totalPnl"] / portfolio["startingCapital"] * 100
    return_check = abs(portfolio["totalReturnPct"] - expected_return) < 0.01
    check(return_check, f"Return % math correct ({portfolio['totalReturnPct']:.2f}%)")

    # Each position has required fields
    for p in positions:
        has_fields = all(k in p for k in ["shares", "allocation_pct", "allocatedCapital", "currentValue", "unrealizedPnl", "weight_pct"])
        check(has_fields, f"{p['name']}: has all portfolio fields (shares={p.get('shares')}, alloc={p.get('allocation_pct')}%)")

    # Weight pcts should sum to roughly (investedValue / totalEquity * 100)
    weight_sum = sum(p["weight_pct"] for p in positions)
    expected_weight = portfolio["investedValue"] / portfolio["totalEquity"] * 100 if portfolio["totalEquity"] else 0
    check(abs(weight_sum - expected_weight) < 1, f"Weight sum ({weight_sum:.1f}%) ≈ invested/equity ({expected_weight:.1f}%)")


def test_4_rules():
    """Test rule runner."""
    section("Test 4: Rule Runner")
    from run_rules import run_all_rules

    results = run_all_rules()
    print(f"  Total rules: {results.get('total_rules', 0)}")
    print(f"  Violations: {results.get('total_violations', 0)}")

    check(results.get("total_rules", 0) >= 3, f"At least 3 rules loaded ({results.get('total_rules', 0)})")

    for r in results.get("rules", []):
        status_icon = "✅" if r["status"] == "ok" else "⚠️"
        print(f"    {status_icon} {r['rule']}: {r['status']} ({len(r.get('violations', []))} violations)")
        check(r.get("exit_code") in (0, 1), f"Rule {r['rule']} exited cleanly (code {r.get('exit_code')})")
        check(r.get("error") is None, f"Rule {r['rule']} no errors")


def test_5_apply_functions_exist():
    """Verify apply pipeline functions exist and are importable.

    NOTE: We do NOT call phase3_apply here — it mutates real tracking files.
    Use test_simulation.py for full end-to-end testing (runs in temp dir).
    """
    section("Test 5: Apply Pipeline (import check only — no mutation)")

    from run_daily import phase3_apply, phase4_validate_and_log, _parse_llm_response
    check(callable(phase3_apply), "phase3_apply is importable")
    check(callable(phase4_validate_and_log), "phase4_validate_and_log is importable")
    check(callable(_parse_llm_response), "_parse_llm_response is importable")

    # Test JSON parsing without touching any files
    test_json = '{"position_decisions": [], "new_positions": [], "watchlist": [], "market_summary": "test"}'
    parsed = _parse_llm_response(test_json)
    check(parsed.get("market_summary") == "test", "JSON parser works on clean input")

    wrapped = '```json\n' + test_json + '\n```'
    parsed2 = _parse_llm_response(wrapped)
    check(parsed2.get("market_summary") == "test", "JSON parser handles ```json``` blocks")

    check(True, "⚠️  Full apply test is in test_simulation.py (uses temp dir, safe)")


def test_6_open_position_sizing():
    """Test that open_position respects allocation_pct and lot size rules."""
    section("Test 6: Position Sizing + Lot Rules")
    from position_manager import load_portfolio_config

    config = load_portfolio_config()
    starting = config["starting_capital"]

    # Test lot size rounding: 688xxx = 200, others = 100
    test_cases = [
        ("300684", 55.39, 10, 100, "中石科技 (SZ, lot=100)"),
        ("688002", 114.65, 10, 200, "睿创微纳 (688, lot=200)"),
        ("688630", 201.72, 10, 200, "芯碁微装 (688, lot=200)"),
        ("600499", 17.48, 10, 100, "科达制造 (SH, lot=100)"),
        ("601231", 28.50, 5, 100, "环旭电子 (SH, 5% alloc, lot=100)"),
    ]

    for code, price, alloc_pct, lot, label in test_cases:
        capital = starting * alloc_pct / 100
        raw = int(capital // price)
        shares = (raw // lot) * lot or lot
        check(shares % lot == 0, f"{label}: {shares} shares divisible by {lot}")
        check(shares >= lot, f"{label}: {shares} shares >= minimum {lot}")
        check(shares > 0, f"{label}: {shares} shares (¥{shares * price:,.0f})")


def test_7_evolver_prerequisites():
    """Test that the evolver has everything it needs."""
    section("Test 7: Evolver Prerequisites")

    check((PROJECT_ROOT / "agents" / "EVOLVER.md").exists(), "EVOLVER.md exists")
    check((PROJECT_ROOT / "LEARNINGS.md").exists(), "LEARNINGS.md exists")
    check((PROJECT_ROOT / "scripts" / "run_rules.py").exists(), "run_rules.py exists")

    rules = list((PROJECT_ROOT / "scripts" / "rules").glob("check_*.py"))
    check(len(rules) >= 3, f"{len(rules)} rule scripts found")

    # Each rule has proper docstring
    for r in rules:
        content = r.read_text()
        has_docstring = '"""' in content
        has_stdin = "json.load(sys.stdin)" in content
        has_stdout = "json.dump(" in content
        check(has_docstring and has_stdin and has_stdout, f"{r.name}: proper format (docstring + stdin/stdout)")

    closed = list((PROJECT_ROOT / "tracking" / "closed").glob("*.json"))
    check(len(closed) > 0, f"{len(closed)} closed positions for counterfactual analysis")

    daily = list((PROJECT_ROOT / "tracking" / "daily").glob("*.json"))
    check(len(daily) > 0, f"{len(daily)} daily logs for history review")


def main():
    global passed, failed

    print(f"\n{Colors.BOLD}🧪 Stock Analysis Pipeline — Full Test Suite{Colors.END}")
    print(f"Working dir: {PROJECT_ROOT}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_1_portfolio_config()
    test_2_realized_pnl()
    test_3_regenerate_positions()
    test_4_rules()
    test_5_apply_functions_exist()
    test_6_open_position_sizing()
    test_7_evolver_prerequisites()

    # No cleanup needed — this test suite is read-only.
    # For mutation tests, use test_simulation.py (runs in temp dir).

    section("Results")
    total = passed + failed
    print(f"\n  {Colors.GREEN}{passed} passed{Colors.END}, {Colors.RED}{failed} failed{Colors.END} out of {total} checks")

    if failed > 0:
        print(f"\n  {Colors.RED}SOME TESTS FAILED{Colors.END}")
        sys.exit(1)
    else:
        print(f"\n  {Colors.GREEN}ALL TESTS PASSED ✓{Colors.END}")
        sys.exit(0)


if __name__ == "__main__":
    main()
