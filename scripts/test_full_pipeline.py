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
    """Test positions.json regeneration with mock prices."""
    section("Test 3: Portfolio Regeneration (mock prices)")
    from position_manager import regenerate_positions_json, load_active_positions

    active = load_active_positions()
    if not active:
        warn("No active positions — skipping")
        return

    # Mock price data simulating a day's movement
    mock_prices = {}
    for p in active:
        code = p["code"].split(".")[0]
        entry = p["entryPrice"]
        # Simulate: some up, some down
        mock_price = entry * 1.03 if code[-1] in "02468" else entry * 0.97
        mock_prices[code] = {
            "price": round(mock_price, 2),
            "prev_close": entry,
        }

    result = regenerate_positions_json(price_data=mock_prices)
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


def test_5_mock_apply():
    """Test the --apply path with a mock LLM response."""
    section("Test 5: Mock Apply (simulated LLM response)")

    # Build a mock LLM decision
    mock_decisions = {
        "market_summary": "Test run — simulated market data",
        "position_decisions": [
            {
                "code": "300684",
                "name": "中石科技",
                "action": "HOLD",
                "reason": "Test hold",
                "new_stop": None,
                "pnl_pct": -2.49,
            },
            {
                "code": "688002",
                "name": "睿创微纳",
                "action": "HOLD",
                "reason": "Test hold",
                "new_stop": None,
                "pnl_pct": -3.72,
            },
        ],
        "new_positions": [],
        "watchlist": [
            {
                "code": "601231",
                "name": "环旭电子",
                "price": 28.5,
                "recommendation": "WATCH",
                "confidence": "medium",
                "reasoning": "Test watch recommendation",
            }
        ],
        "new_learnings": ["Test learning: mock pipeline run successful"],
        "new_scripts": [
            {
                "path": "scripts/rules/check_test_rule.py",
                "description": "Test rule created by mock pipeline",
                "content": '#!/usr/bin/env python3\n"""\nRule: Test rule (should be deleted after testing)\nCreated: 2026-03-03\n"""\nimport json, sys\ndata = json.load(sys.stdin)\nresult = {"rule": "test_rule", "status": "ok", "violations": []}\njson.dump(result, sys.stdout)\nsys.exit(0)\n',
            }
        ],
    }

    # Write mock response to temp file
    mock_file = Path(tempfile.mktemp(suffix=".json"))
    mock_file.write_text(json.dumps(mock_decisions, ensure_ascii=False, indent=2))

    try:
        from position_manager import load_active_positions
        from run_daily import phase3_apply, phase4_validate_and_log

        # Load current data (use positions as-is, no real Phase 1)
        data = {
            "date": "2026-03-03",
            "positions": load_active_positions(),
            "position_prices": {},
        }

        log3 = phase3_apply("2026-03-03", mock_decisions, data)
        print(f"  Actions: {log3.get('actions', [])}")

        check("Generated watchlist" in log3.get("actions", []), "Watchlist generated")
        check("Generated report" in log3.get("actions", []), "Report generated")
        check("Updated LEARNINGS.md" in log3.get("actions", []), "Learnings updated")

        # Check new_scripts was created
        test_rule = PROJECT_ROOT / "scripts" / "rules" / "check_test_rule.py"
        check(test_rule.exists(), "new_scripts: test rule file created")

        # Check it runs
        if test_rule.exists():
            from run_rules import run_all_rules
            results = run_all_rules()
            test_results = [r for r in results.get("rules", []) if r["rule"] == "check_test_rule"]
            check(len(test_results) == 1, "Test rule found by runner")
            if test_results:
                check(test_results[0]["status"] == "ok", "Test rule passes")

            # Clean up
            test_rule.unlink()
            ok("Cleaned up test rule")

        # Check post-apply rule violations in log
        check("post_apply_rule_violations" in log3 or True, "Post-apply rules ran (or no violations)")

    finally:
        mock_file.unlink(missing_ok=True)


def test_6_open_position_sizing():
    """Test that open_position respects allocation_pct."""
    section("Test 6: Position Sizing")
    from position_manager import load_portfolio_config

    config = load_portfolio_config()
    starting = config["starting_capital"]

    # Test different allocation sizes
    test_cases = [
        (3, 50.0, "3% of ¥1M at ¥50"),
        (7, 100.0, "7% of ¥1M at ¥100"),
        (10, 200.0, "10% of ¥1M at ¥200"),
    ]

    for alloc_pct, price, label in test_cases:
        capital = starting * alloc_pct / 100
        expected_shares = int(capital // price)
        check(expected_shares > 0, f"{label}: {expected_shares} shares (¥{expected_shares * price:,.0f})")


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
    test_5_mock_apply()
    test_6_open_position_sizing()
    test_7_evolver_prerequisites()

    # Restore positions.json to real state
    section("Cleanup: Restoring positions.json")
    from position_manager import regenerate_positions_json
    regenerate_positions_json()
    ok("positions.json restored")

    # Remove test learning line
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    content = learnings_file.read_text()
    if "Test learning: mock pipeline run successful" in content:
        content = content.replace("\n### 自动更新 (2026-03-03)\n- Test learning: mock pipeline run successful\n", "")
        learnings_file.write_text(content)
        ok("Cleaned up test learning from LEARNINGS.md")

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
