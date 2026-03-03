#!/usr/bin/env python3
"""
run_rules.py — Execute all rule scripts in scripts/rules/ against current portfolio.

Usage:
    python scripts/run_rules.py              # Run all rules, JSON output
    python scripts/run_rules.py --human      # Human-readable output
    python scripts/run_rules.py --json-input FILE  # Use custom input instead of positions.json

Each rule script receives positions.json on stdin and outputs results on stdout.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RULES_DIR = PROJECT_ROOT / "scripts" / "rules"
POSITIONS_FILE = PROJECT_ROOT / "tracking" / "positions.json"


def run_all_rules(portfolio_data: dict | None = None) -> dict:
    """Run all rule scripts and collect results.

    Args:
        portfolio_data: Portfolio JSON to pass to rules. If None, reads positions.json.

    Returns:
        Dict with overall status and per-rule results.
    """
    if portfolio_data is None:
        if not POSITIONS_FILE.exists():
            return {"status": "error", "message": "positions.json not found", "rules": []}
        portfolio_data = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))

    input_json = json.dumps(portfolio_data, ensure_ascii=False)

    rule_files = sorted(RULES_DIR.glob("*.py"))
    # Skip __init__.py and non-rule files
    rule_files = [f for f in rule_files if f.name not in ("__init__.py", "run_rules.py")]

    if not rule_files:
        return {"status": "ok", "message": "No rules found", "rules": []}

    results = []
    total_violations = 0

    for rule_file in rule_files:
        rule_name = rule_file.stem
        try:
            proc = subprocess.run(
                [sys.executable, str(rule_file)],
                input=input_json,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(PROJECT_ROOT),
            )
            try:
                output = json.loads(proc.stdout) if proc.stdout.strip() else {}
            except json.JSONDecodeError:
                output = {"raw_output": proc.stdout[:500]}

            violations = output.get("violations", [])
            total_violations += len(violations)

            results.append({
                "rule": rule_name,
                "file": str(rule_file.relative_to(PROJECT_ROOT)),
                "status": "ok" if proc.returncode == 0 else "violations",
                "exit_code": proc.returncode,
                "violations": violations,
                "error": proc.stderr.strip() if proc.returncode not in (0, 1) else None,
            })
        except subprocess.TimeoutExpired:
            results.append({
                "rule": rule_name,
                "file": str(rule_file.relative_to(PROJECT_ROOT)),
                "status": "timeout",
                "exit_code": -1,
                "violations": [],
                "error": "Rule timed out after 10s",
            })
        except Exception as e:
            results.append({
                "rule": rule_name,
                "file": str(rule_file.relative_to(PROJECT_ROOT)),
                "status": "error",
                "exit_code": -1,
                "violations": [],
                "error": str(e),
            })

    return {
        "status": "ok" if total_violations == 0 else "violations",
        "total_rules": len(results),
        "total_violations": total_violations,
        "rules": results,
    }


def main():
    human_mode = "--human" in sys.argv

    # Custom input file
    portfolio_data = None
    if "--json-input" in sys.argv:
        idx = sys.argv.index("--json-input")
        if idx + 1 < len(sys.argv):
            portfolio_data = json.loads(Path(sys.argv[idx + 1]).read_text(encoding="utf-8"))

    results = run_all_rules(portfolio_data)

    if human_mode:
        print(f"📋 Rule Check ({results['total_rules']} rules, {results['total_violations']} violations)")
        print("=" * 50)
        for r in results["rules"]:
            icon = "✅" if r["status"] == "ok" else "⚠️" if r["status"] == "violations" else "❌"
            print(f"\n{icon} {r['rule']}")
            if r["error"]:
                print(f"  Error: {r['error']}")
            for v in r["violations"]:
                print(f"  → {v.get('code', '?')} {v.get('name', '')}: {v.get('suggestion', v)}")
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
