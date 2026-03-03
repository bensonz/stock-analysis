#!/usr/bin/env python3
"""
test_simulation.py — Multi-day pipeline + evolver simulation.

Copies ALL real data into a temp directory, then simulates 5 trading days
with mock prices and mock LLM decisions. Shows the full lifecycle:

  Day 1: Normal day, rules pass, agent holds everything
  Day 2: Price drops, stop_proximity fires on 云天化, agent sells it
  Day 3: Agent opens new position with 5% allocation, writes a new rule
  Day 4: Time decay fires on 睿创微纳, agent holds (overrides with reason)
  Day 5 (Fri): Evolver reviews — checks counterfactuals on 云天化 sell

Uses temp dir — zero contamination of real data.

Usage:
    cd /Users/bz/Work/Personal/stock-analysis
    source .venv/bin/activate
    python scripts/test_simulation.py
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Colors
G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[1m"
DIM = "\033[2m"
E = "\033[0m"


def header(day, desc):
    print(f"\n{B}{'━'*70}{E}")
    print(f"{B}📅 {day} — {desc}{E}")
    print(f"{B}{'━'*70}{E}")


def sub(msg):
    print(f"  {msg}")


def ok(msg):
    print(f"  {G}✓{E} {msg}")


def warn(msg):
    print(f"  {Y}⚠{E} {msg}")


def show_portfolio(positions_file):
    data = json.loads(positions_file.read_text())
    p = data.get("portfolio", {})
    active = data.get("activePositions", [])
    print(f"\n  {B}Portfolio Snapshot{E}")
    print(f"  ┌{'─'*45}┐")
    print(f"  │ {'Equity':<20} ¥{p.get('totalEquity',0):>14,.2f}   │")
    print(f"  │ {'Cash':<20} ¥{p.get('cash',0):>14,.2f}   │")
    print(f"  │ {'Invested':<20} ¥{p.get('investedValue',0):>14,.2f}   │")
    print(f"  │ {'Unrealized P&L':<20} ¥{p.get('unrealizedPnl',0):>14,.2f}   │")
    print(f"  │ {'Realized P&L':<20} ¥{p.get('realizedPnl',0):>14,.2f}   │")
    print(f"  │ {'Total Return':<20} {p.get('totalReturnPct',0):>14.2f}%  │")
    print(f"  │ {'Positions':<20} {p.get('positionsUsed',0):>9}/{p.get('positionsMax',10):<4}   │")
    print(f"  └{'─'*45}┘")
    print()
    for pos in active:
        icon = f"{G}▲{E}" if pos.get("pnl_pct", 0) >= 0 else f"{R}▼{E}"
        print(f"    {icon} {pos['name']:<8} ¥{pos['currentPrice']:>8.2f}  {pos['pnl_pct']:>+6.2f}%  "
              f"{pos.get('shares',0):>5} shares  {pos.get('weight_pct',0):.1f}%")


def show_rules(sim_root):
    """Run rules and display results."""
    # We need to run run_rules against the sim positions.json
    positions_file = sim_root / "tracking" / "positions.json"
    data = json.loads(positions_file.read_text())

    import subprocess
    rules_dir = sim_root / "scripts" / "rules"
    rule_files = sorted(rules_dir.glob("check_*.py"))

    total_violations = 0
    for rf in rule_files:
        proc = subprocess.run(
            [sys.executable, str(rf)],
            input=json.dumps(data, ensure_ascii=False),
            capture_output=True, text=True, timeout=10,
        )
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result = {"violations": []}
        violations = result.get("violations", [])
        total_violations += len(violations)
        icon = f"{G}✅{E}" if not violations else f"{Y}⚠️{E}"
        print(f"    {icon} {rf.stem}: {len(violations)} violations")
        for v in violations:
            print(f"       → {v.get('code','')} {v.get('name','')}: {v.get('suggestion','')[:80]}")

    return total_violations


def setup_sim():
    """Copy real data into temp dir, return sim root path."""
    sim_root = Path(tempfile.mkdtemp(prefix="stock-sim-"))
    print(f"  {DIM}Sim directory: {sim_root}{E}")

    # Copy tracking/ (positions, active, closed, daily, config)
    shutil.copytree(PROJECT_ROOT / "tracking", sim_root / "tracking")

    # Copy scripts/ (position_manager, run_daily, rules, etc)
    shutil.copytree(PROJECT_ROOT / "scripts", sim_root / "scripts")

    # Copy agents/
    shutil.copytree(PROJECT_ROOT / "agents", sim_root / "agents")

    # Copy LEARNINGS.md
    shutil.copy2(PROJECT_ROOT / "LEARNINGS.md", sim_root / "LEARNINGS.md")

    # Copy watchlist/ and reports/ and data/ dirs
    for d in ["watchlist", "reports", "data", "logs"]:
        src = PROJECT_ROOT / d
        if src.exists():
            shutil.copytree(src, sim_root / d)
        else:
            (sim_root / d).mkdir(parents=True, exist_ok=True)

    return sim_root


def patch_imports(sim_root):
    """Add sim_root/scripts to sys.path so imports resolve to sim copy."""
    scripts_dir = str(sim_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    # Also patch the PROJECT_ROOT in position_manager
    import importlib
    # We need to reload modules to pick up the sim paths
    # Easiest: just monkey-patch the paths

    import position_manager as pm
    pm.TRACKING_DIR = sim_root / "tracking"
    pm.CLOSED_DIR = sim_root / "tracking" / "closed"
    pm.DAILY_DIR = sim_root / "tracking" / "daily"
    pm.POSITIONS_FILE = sim_root / "tracking" / "positions.json"
    pm.PORTFOLIO_CONFIG_FILE = sim_root / "tracking" / "portfolio_config.json"

    return pm


def sim_day(pm, sim_root, date_str, mock_prices, decisions, day_label):
    """Simulate one trading day."""

    # 1. Regenerate positions with mock prices
    result = pm.regenerate_positions_json(price_data=mock_prices)
    positions_file = sim_root / "tracking" / "positions.json"

    # 2. Show portfolio state
    show_portfolio(positions_file)

    # 3. Run rules (pre-decision)
    sub(f"{B}Rules (pre-decision):{E}")
    violations = show_rules(sim_root)
    if violations:
        warn(f"{violations} rule violation(s) — agent sees these in prompt")
    else:
        ok("All rules pass")

    # 4. Apply decisions
    if decisions:
        sub(f"\n  {B}Agent Decisions:{E}")
        daily_actions = []

        for d in decisions.get("position_decisions", []):
            code = str(d["code"]).split(".")[0]
            action = d["action"]
            icon = "🔴" if action == "SELL" else "🟢" if action == "HOLD" else "🔵"
            sub(f"  {icon} {d.get('name', code)}: {action} — {d.get('reason', '')[:60]}")

            if action == "SELL":
                price = mock_prices.get(code, {}).get("price", 0)
                try:
                    pm.close_position(code=code, reason=d.get("reason", ""), exit_price=price, date=date_str)
                    ok(f"Closed {code}")
                except Exception as e:
                    warn(f"Close failed: {e}")

            daily_actions.append({
                "code": code,
                "name": d.get("name", ""),
                "action": action,
                "price": mock_prices.get(code, {}).get("price"),
                "note": d.get("reason", ""),
            })

        for p in decisions.get("new_positions", []):
            code = str(p["code"]).split(".")[0]
            sub(f"  🆕 Open {p.get('name', code)} @ ¥{p['entry_price']} ({p.get('allocation_pct', 10)}% allocation)")
            try:
                pm.open_position({
                    "code": code,
                    "name": p.get("name", ""),
                    "entryPrice": p["entry_price"],
                    "targetPrice": p.get("target", 0),
                    "stopLoss": p.get("stop", 0),
                    "thesis": p.get("thesis", ""),
                    "rating": p.get("rating", 2),
                    "sector": p.get("sector", ""),
                    "allocation_pct": p.get("allocation_pct", 10),
                    "sourceWatchlist": date_str,
                })
                ok(f"Opened {code}")
            except Exception as e:
                warn(f"Open failed: {e}")

            daily_actions.append({
                "code": code,
                "name": p.get("name", ""),
                "action": "OPEN",
                "price": p["entry_price"],
                "note": p.get("thesis", ""),
            })

        # Write new scripts if any
        for script in decisions.get("new_scripts", []):
            path = sim_root / script["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(script["content"], encoding="utf-8")
            os.chmod(str(path), 0o755)
            ok(f"Agent created rule: {script['path']}")

        # Save daily summary
        pm.save_daily_summary(date_str, daily_actions)

    # 5. Regenerate with updates
    result = pm.regenerate_positions_json(price_data=mock_prices)

    # 6. Post-decision rules
    sub(f"\n  {B}Rules (post-decision):{E}")
    show_rules(sim_root)


def sim_evolver(pm, sim_root):
    """Simulate the Friday evolver pass."""

    sub(f"{B}Evolver reads:{E}")

    # Read closed positions
    closed_dir = sim_root / "tracking" / "closed"
    closed = list(closed_dir.glob("*.json"))
    sub(f"  {len(closed)} closed positions")

    # Read rules
    rules_dir = sim_root / "scripts" / "rules"
    rules = list(rules_dir.glob("check_*.py"))
    sub(f"  {len(rules)} rule scripts")

    # Show what the evolver would analyze
    sub(f"\n  {B}Counterfactual Analysis:{E}")

    for f in sorted(closed)[-3:]:  # Last 3 closed
        p = json.loads(f.read_text())
        name = p.get("name", f.stem)
        entry = p.get("entryPrice", 0)
        exit_p = p.get("exitPrice", 0)
        exit_date = p.get("exitDate", "?")
        pnl_pct = round((exit_p - entry) / entry * 100, 2) if entry else 0
        sub(f"  📋 {name}: sold {exit_date} @ ¥{exit_p} ({pnl_pct:+.1f}%)")

        # In a real evolver, it would check current price
        # We'll simulate: the stock recovered
        if "云天化" in name:
            simulated_current = entry * 1.05  # recovered to +5%
            sub(f"     Current price: ¥{simulated_current:.2f} (+5.0% from entry)")
            sub(f"     {Y}→ Selling was premature. Could have held for +5% instead of {pnl_pct:+.1f}%{E}")
            sub(f"     {Y}→ MODIFY check_stop_proximity: widen from 3% to 2% or add 'market crash' exception{E}")
        elif "扬杰科技" in name:
            simulated_current = entry * 0.88  # continued falling
            sub(f"     Current price: ¥{simulated_current:.2f} (-12.0% from entry)")
            sub(f"     {G}→ Selling was correct. Would be down -12% now vs {pnl_pct:+.1f}% exit{E}")

    # Show rule modifications the evolver would make
    sub(f"\n  {B}Rule Evolution Decisions:{E}")

    # Simulate: modify stop_proximity rule
    stop_rule = rules_dir / "check_stop_proximity.py"
    if stop_rule.exists():
        content = stop_rule.read_text()
        # Simulate adding market crash exception
        new_content = content.replace(
            'Rule: Stop proximity — flag positions within 3% of stop loss.',
            'Rule: Stop proximity — flag positions within 2% of stop loss (widened from 3% after 2026-03-03 false positive).',
        ).replace(
            'Track record: 0 fires, 0 correct, 0 incorrect',
            'Track record: 1 fire, 0 correct, 1 incorrect (云天化 false positive)',
        ).replace(
            'Last modified: 2026-03-03',
            f'Last modified: {datetime.now().strftime("%Y-%m-%d")} (evolver widened threshold)',
        ).replace(
            'distance_pct < 3',
            'distance_pct < 2',
        )
        stop_rule.write_text(new_content)
        ok("MODIFIED check_stop_proximity: 3% → 2% (false positive on 云天化)")

    # Simulate: agent creates new rule based on Week 1 lesson
    new_rule_content = '''#!/usr/bin/env python3
"""
Rule: Market crash detector — if >50% of positions dropped >5% in one day,
flag it as a systemic crash (not individual thesis failure).
Created: {date}
Source: 2026-03-03 crash — all 6 positions dropped 6-8%, was systemic not stock-specific.
Last modified: {date}
Track record: 0 fires
"""
import json, sys

data = json.load(sys.stdin)
positions = data.get("activePositions", [])
violations = []

if len(positions) >= 3:
    big_drops = [p for p in positions if p.get("pnl_pct", 0) < -5]
    if len(big_drops) > len(positions) * 0.5:
        violations.append({{
            "rule": "market_crash_detector",
            "severity": "info",
            "positions_dropping": len(big_drops),
            "total_positions": len(positions),
            "suggestion": "SYSTEMIC CRASH detected — don't panic sell individual positions. "
                          "Wait 1-2 days before making sell decisions unless stop is actually hit.",
        }})

result = {{"rule": "market_crash_detector", "status": "ok" if not violations else "violations", "violations": violations}}
json.dump(result, sys.stdout, ensure_ascii=False)
sys.exit(1 if violations else 0)
'''.format(date=datetime.now().strftime("%Y-%m-%d"))

    new_rule_path = rules_dir / "check_market_crash.py"
    new_rule_path.write_text(new_rule_content)
    os.chmod(str(new_rule_path), 0o755)
    ok("CREATED check_market_crash: detects systemic crashes vs individual failures")

    # Show final rule state
    sub(f"\n  {B}Final Rule Inventory:{E}")
    for r in sorted(rules_dir.glob("check_*.py")):
        # Read first docstring line
        lines = r.read_text().split("\n")
        desc = next((l.strip() for l in lines if l.strip().startswith("Rule:")), r.stem)
        sub(f"    📜 {r.name}: {desc}")

    # Run updated rules
    sub(f"\n  {B}Rules after evolution:{E}")
    show_rules(sim_root)


def main():
    print(f"\n{B}🧪 Multi-Day Pipeline + Evolver Simulation{E}")
    print(f"{'─'*70}")
    print(f"Using real portfolio data in isolated temp directory.")
    print(f"Zero contamination of actual data.\n")

    # Setup
    sim_root = setup_sim()
    ok(f"Copied real data to {sim_root}")

    try:
        # Patch imports to use sim directory
        pm = patch_imports(sim_root)

        # ═══════════════════════════════════════════════════════════
        # DAY 1: Normal day, everything holds
        # ═══════════════════════════════════════════════════════════
        header("Day 1 (Mon) — Normal trading day", "Slight recovery, all holds")

        day1_prices = {
            "300684": {"price": 55.00, "prev_close": 54.01},  # 中石科技 +1.8%
            "600096": {"price": 41.80, "prev_close": 41.18},  # 云天化 +1.5%
            "600499": {"price": 16.60, "prev_close": 16.40},  # 科达制造 +1.2%
            "688002": {"price": 111.50, "prev_close": 110.38},  # 睿创微纳 +1.0%
        }

        day1_decisions = {
            "position_decisions": [
                {"code": "300684", "name": "中石科技", "action": "HOLD", "reason": "Recovery from crash, thesis intact"},
                {"code": "600096", "name": "云天化", "action": "HOLD", "reason": "Bounce, watching ¥39.60 stop"},
                {"code": "600499", "name": "科达制造", "action": "HOLD", "reason": "Stable, overseas thesis intact"},
                {"code": "688002", "name": "睿创微纳", "action": "HOLD", "reason": "Recovering from ¥110 support"},
            ],
            "new_positions": [],
            "new_scripts": [],
        }

        sim_day(pm, sim_root, "2026-03-04", day1_prices, day1_decisions, "Day 1")

        # ═══════════════════════════════════════════════════════════
        # DAY 2: 云天化 drops near stop, rule fires, agent sells
        # ═══════════════════════════════════════════════════════════
        header("Day 2 (Tue) — 云天化 crashes to stop zone", "Stop proximity rule fires")

        day2_prices = {
            "300684": {"price": 54.50, "prev_close": 55.00},
            "600096": {"price": 39.90, "prev_close": 41.80},  # -4.5%! Near ¥39.60 stop
            "600499": {"price": 16.30, "prev_close": 16.60},
            "688002": {"price": 112.00, "prev_close": 111.50},
        }

        day2_decisions = {
            "position_decisions": [
                {"code": "300684", "name": "中石科技", "action": "HOLD", "reason": "Slight pullback, OK"},
                {"code": "600096", "name": "云天化", "action": "SELL", "reason": "Rule violation: only 0.8% above stop ¥39.60. Phosphate sector weak, cutting loss."},
                {"code": "600499", "name": "科达制造", "action": "HOLD", "reason": "Holding"},
                {"code": "688002", "name": "睿创微纳", "action": "HOLD", "reason": "Recovering well"},
            ],
            "new_positions": [],
            "new_scripts": [],
        }

        sim_day(pm, sim_root, "2026-03-05", day2_prices, day2_decisions, "Day 2")

        # ═══════════════════════════════════════════════════════════
        # DAY 3: Agent opens new position + writes a rule
        # ═══════════════════════════════════════════════════════════
        header("Day 3 (Wed) — New opportunity, agent opens position + writes rule",
               "Tests allocation_pct and new_scripts")

        day3_prices = {
            "300684": {"price": 55.80, "prev_close": 54.50},  # +2.4%
            "600499": {"price": 16.80, "prev_close": 16.30},  # +3.1%
            "688002": {"price": 114.00, "prev_close": 112.00},  # +1.8%
        }

        day3_decisions = {
            "position_decisions": [
                {"code": "300684", "name": "中石科技", "action": "HOLD", "reason": "Rallying nicely"},
                {"code": "600499", "name": "科达制造", "action": "HOLD", "reason": "Momentum building"},
                {"code": "688002", "name": "睿创微纳", "action": "HOLD", "reason": "Back above ¥113"},
            ],
            "new_positions": [
                {
                    "code": "601231",
                    "name": "环旭电子",
                    "entry_price": 28.50,
                    "target": 34.00,
                    "stop": 25.60,
                    "thesis": "SiP封装龙头，Apple Vision Pro供应链",
                    "confidence": "medium",
                    "allocation_pct": 5,  # Only 5% — medium confidence
                    "rating": 2,
                    "sector": "半导体封装",
                },
            ],
            "new_scripts": [
                {
                    "path": "scripts/rules/check_sector_concentration.py",
                    "description": "Flag if >40% portfolio in same sector",
                    "content": '#!/usr/bin/env python3\n"""\nRule: Sector concentration — flag if >40% of portfolio value is in one sector.\nCreated: 2026-03-06\nSource: Agent observation — too many semiconductor positions.\nLast modified: 2026-03-06\nTrack record: 0 fires\n"""\nimport json, sys\nfrom collections import defaultdict\n\ndata = json.load(sys.stdin)\npositions = data.get("activePositions", [])\nportfolio = data.get("portfolio", {})\ntotal_equity = portfolio.get("totalEquity", 1)\n\nsector_values = defaultdict(float)\nfor p in positions:\n    sector = p.get("sector", "unknown")\n    sector_values[sector] += p.get("currentValue", 0)\n\nviolations = []\nfor sector, value in sector_values.items():\n    pct = value / total_equity * 100\n    if pct > 40:\n        violations.append({\n            "rule": "sector_concentration",\n            "sector": sector,\n            "concentration_pct": round(pct, 1),\n            "suggestion": f"Sector {sector} is {pct:.1f}% of portfolio (>40% limit). Diversify.",\n        })\n\nresult = {"rule": "sector_concentration", "status": "ok" if not violations else "violations", "violations": violations}\njson.dump(result, sys.stdout, ensure_ascii=False)\nsys.exit(1 if violations else 0)\n',
                },
            ],
        }

        sim_day(pm, sim_root, "2026-03-06", day3_prices, day3_decisions, "Day 3")

        # Verify the new position has correct sizing
        positions_data = json.loads((sim_root / "tracking" / "positions.json").read_text())
        new_pos = [p for p in positions_data["activePositions"] if p["code"] == "601231"]
        if new_pos:
            p = new_pos[0]
            expected_shares = int(1_000_000 * 0.05 // 28.50)  # 5% of 1M
            sub(f"\n  {B}Position Sizing Check:{E}")
            sub(f"    环旭电子: allocation_pct={p.get('allocation_pct')}%, shares={p.get('shares')}, expected≈{expected_shares}")
            if p.get("allocation_pct") == 5:
                ok("Allocation percentage correctly stored")
            else:
                warn(f"Expected allocation_pct=5, got {p.get('allocation_pct')}")

        # ═══════════════════════════════════════════════════════════
        # DAY 4: Time decay fires on 睿创微纳, agent overrides
        # ═══════════════════════════════════════════════════════════
        header("Day 4 (Thu) — Time decay fires, agent overrides",
               "Tests rule override behavior")

        day4_prices = {
            "300684": {"price": 56.50, "prev_close": 55.80},
            "600499": {"price": 17.00, "prev_close": 16.80},
            "688002": {"price": 115.00, "prev_close": 114.00},  # Still only +0.3% from entry
            "601231": {"price": 29.10, "prev_close": 28.50},   # New position up 2.1%
        }

        day4_decisions = {
            "position_decisions": [
                {"code": "300684", "name": "中石科技", "action": "HOLD", "reason": "Trend intact"},
                {"code": "600499", "name": "科达制造", "action": "HOLD", "reason": "Approaching target zone"},
                {"code": "688002", "name": "睿创微纳", "action": "HOLD",
                 "reason": "OVERRIDE time_decay: Catalyst imminent (new military contract rumor). Extending hold to 2026-03-10."},
                {"code": "601231", "name": "环旭电子", "action": "HOLD", "reason": "Day 2, early"},
            ],
            "new_positions": [],
            "new_scripts": [],
        }

        sim_day(pm, sim_root, "2026-03-07", day4_prices, day4_decisions, "Day 4")

        # ═══════════════════════════════════════════════════════════
        # DAY 5 (Fri): Evolver reviews the week
        # ═══════════════════════════════════════════════════════════
        header("Day 5 (Fri) — Weekly Evolution",
               "Evolver reviews rules + counterfactuals")

        sim_evolver(pm, sim_root)

        # ═══════════════════════════════════════════════════════════
        # Final state
        # ═══════════════════════════════════════════════════════════
        header("Final Portfolio State", "After 5 simulated days")

        # Regenerate with Day 4 prices (last trading day)
        pm.regenerate_positions_json(price_data=day4_prices)
        show_portfolio(sim_root / "tracking" / "positions.json")

        # Show all daily summaries created
        sub(f"{B}Daily summaries created:{E}")
        daily_dir = sim_root / "tracking" / "daily"
        for f in sorted(daily_dir.glob("*.json"))[-5:]:
            d = json.loads(f.read_text())
            actions = d.get("actions", [])
            action_summary = ", ".join(f"{a['action']} {a.get('name','')}" for a in actions[:3])
            sub(f"  📄 {f.name}: {action_summary}")

        print(f"\n{B}{'━'*70}{E}")
        print(f"{G}{B}✓ Simulation complete — real data untouched{E}")
        print(f"{DIM}  Sim dir: {sim_root}{E}")
        print(f"{DIM}  (will be auto-cleaned by OS, or: rm -rf {sim_root}){E}")
        print(f"{B}{'━'*70}{E}")

    except Exception as e:
        import traceback
        print(f"\n{R}ERROR: {e}{E}")
        traceback.print_exc()
        print(f"\n{DIM}Sim dir preserved for debugging: {sim_root}{E}")
        sys.exit(1)


if __name__ == "__main__":
    main()
