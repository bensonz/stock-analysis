# Add Portfolio Value Tracking + Dynamic Position Sizing + Self-Evolution

## Context

`tracking/positions.json` has no portfolio-level data (equity, cash, P&L). The `totalPnl` in daily summaries is just a sum of per-position PnL percentages, which is meaningless as a portfolio metric.

More importantly: the agent should **decide allocation percentages** per position (max 10% of portfolio) and should be able to **write its own scripts/rules** to enforce the learnings it creates.

## Design Principles

1. **Agent decides sizing** — not equal-weight. The agent allocates 1-10% of total equity per position based on conviction.
2. **Self-evolution** — the agent can create/modify scripts in `scripts/rules/` to enforce its learnings programmatically. These scripts run as validators during Phase 3 (apply) and Phase 4 (validate).
3. **Accurate P&L** — track actual dollar values, not just percentages.

## Part 1: Portfolio Config & Tracking

### 1a. Create `tracking/portfolio_config.json` (NEW)

```json
{
  "starting_capital": 1000000,
  "max_position_pct": 10,
  "max_positions": 10,
  "created": "2026-02-03",
  "currency": "CNY"
}
```

### 1b. Update position tracking files

Each tracking file (`tracking/{code}.json`) needs new fields at open time:
- `allocation_pct`: What % of portfolio the agent decided to allocate (1-10)
- `shares`: Number of shares (computed from allocation)
- `allocatedCapital`: shares × entryPrice

For existing positions that lack these fields, **backfill** using 10% default:
```python
shares = int((starting_capital * 0.10) // entry_price)
```

### 1c. Update `scripts/position_manager.py`

#### `load_portfolio_config()` — NEW
Read `tracking/portfolio_config.json`.

#### `compute_realized_pnl()` — NEW
Scan `tracking/closed/*.json`, compute realized P&L:
```python
for each closed position:
    shares = p.get("shares") or int((config["starting_capital"] * 0.10) // p["entryPrice"])
    realized += (p["exitPrice"] - p["entryPrice"]) * shares
```

#### `open_position()` — UPDATE
Accept `allocation_pct` from agent decisions. Compute shares:
```python
config = load_portfolio_config()
portfolio_value = compute_current_equity()  # or use starting_capital as base
alloc = allocation_pct / 100  # e.g. 0.07 for 7%
capital = portfolio_value * alloc
shares = int(capital // entry_price)
```
Save `allocation_pct`, `shares`, `allocatedCapital` into the tracking file.

#### `regenerate_positions_json(price_data)` — UPDATE
Add per-position value fields and a `portfolio` summary block:

Per position:
```python
shares = p.get("shares") or int((config["starting_capital"] * max_pct / 100) // p["entryPrice"])
allocated = shares * p["entryPrice"]
current_val = shares * current_price
unrealized = current_val - allocated
```

Portfolio summary:
```python
{
    "portfolio": {
        "startingCapital": 1000000,
        "totalEquity": cash + sum(current_values),
        "cash": starting_capital - sum(allocated) + realized_pnl,
        "investedValue": sum(current_values),
        "unrealizedPnl": sum(unrealized for each position),
        "realizedPnl": from closed positions,
        "totalPnl": unrealized + realized,
        "totalReturnPct": (totalEquity - startingCapital) / startingCapital * 100,
        "positionsUsed": N,
        "positionsMax": 10,
        "cashPct": cash / totalEquity * 100,
        "dayPnl": sum of today's price changes * shares (if price_data available)
    }
}
```

Per position (add to existing fields):
```python
{
    "shares": 1805,
    "allocation_pct": 8.5,
    "allocatedCapital": 99978.95,
    "currentValue": 97488.05,
    "unrealizedPnl": -2490.90,
    "weight_pct": 9.4  // currentValue / totalEquity * 100
}
```

## Part 2: Agent-Decided Position Sizing

### 2a. Update `agents/ANALYST.md` — Required Output JSON

In the `new_positions` array, add `allocation_pct`:
```json
{
    "code": "688630",
    "name": "芯碁微装",
    "entry_price": 201.72,
    "allocation_pct": 7,
    "target": 240,
    "stop": 182,
    "thesis": "...",
    "confidence": "high"
}
```

Add sizing guidelines to the Decision Framework:
```
### Position Sizing Rules
- allocation_pct: 1-10% of total portfolio equity
- High confidence + strong catalyst + good R:R → 8-10%
- Medium confidence → 5-7%
- Low confidence / speculative → 3-5%
- After a drawdown (portfolio < -5% from peak) → reduce all new sizing by 2pp
- Never allocate >10% to a single position
- Total invested (sum of all allocations) should not exceed 80% — keep ≥20% cash
- Include allocation_pct in your new_positions JSON output
```

### 2b. Update `scripts/run_daily.py` Phase 3

When processing `new_positions`, read `allocation_pct` from the agent's decision and pass it to `open_position()`.

## Part 3: Self-Evolution — Agent-Written Rule Scripts

### 3a. Create `scripts/rules/` directory

This is where the agent writes executable rule scripts. Each script is a standalone Python file that:
- Takes the current portfolio state as JSON on stdin
- Outputs violations/warnings as JSON on stdout
- Exit code 0 = pass, exit code 1 = violations found

Example: `scripts/rules/check_time_decay.py`
```python
#!/usr/bin/env python3
"""Rule: Positions held >20 days with <5% gain should be flagged for SELL.
Created by analysis agent on 2026-02-15 based on LEARNINGS #1.
"""
import json, sys
from datetime import datetime, date

data = json.load(sys.stdin)
today = date.today()
violations = []

for p in data.get("activePositions", []):
    entry = datetime.strptime(p["entryDate"], "%Y-%m-%d").date()
    days = (today - entry).days
    if days > 20 and p.get("pnl_pct", 0) < 5:
        violations.append({
            "code": p["code"],
            "name": p["name"],
            "rule": "time_decay_20d",
            "days_held": days,
            "pnl_pct": p.get("pnl_pct", 0),
            "suggestion": "SELL or justify exception",
        })

if violations:
    json.dump({"status": "violations", "violations": violations}, sys.stdout)
    sys.exit(1)
else:
    json.dump({"status": "ok"}, sys.stdout)
    sys.exit(0)
```

### 3b. Create `scripts/run_rules.py` — Rule Runner (NEW)

```python
"""Run all rule scripts in scripts/rules/ against current portfolio state."""
```

- Loads `tracking/positions.json`
- Iterates over all `scripts/rules/*.py` files
- Runs each one with portfolio JSON on stdin
- Collects results
- Returns summary: which rules passed, which had violations

### 3c. Integrate into pipeline

In `run_daily.py`:
- **Phase 1:** After data collection, run `run_rules.py` on current positions. Include results in the prompt data as `rule_violations`.
- **Phase 3 (apply):** After applying decisions, run rules again on the NEW state. If violations exist, include them in the log as warnings (don't block — the agent decided to override).
- **Phase 4 (validate):** Add rule check results to validation output.

### 3d. Update `agents/ANALYST.md` — Self-Evolution Instructions

Add a section:
```
### Self-Evolution: Writing Rule Scripts

You can create or modify Python scripts in `scripts/rules/` to enforce your learnings.
Each time you add a new learning to LEARNINGS.md, consider:
- Can this learning be checked programmatically?
- If yes, write a rule script for it.

Include in your JSON output:
"new_scripts": [
    {
        "path": "scripts/rules/check_overextended.py",
        "description": "Flag positions where 5-day cumulative gain >12%",
        "content": "#!/usr/bin/env python3\n..."
    }
]

The pipeline will write these files automatically.

Rules you create will be run BEFORE your next analysis — you'll see
the violations in the data and can decide to follow or override them.
```

### 3e. Update `scripts/run_daily.py` Phase 3

After processing `new_positions` and `position_decisions`, check for `new_scripts`:
```python
for script in decisions.get("new_scripts", []):
    path = PROJECT_ROOT / script["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script["content"])
    path.chmod(0o755)
    log["actions"].append(f"Created rule: {script['path']}")
```

## Part 4: Fix Daily Summary Stats

In `run_daily.py` Phase 3, the `portfolioStats` block should use actual dollar values:
```python
stats = {
    "totalPositions": len(active),
    "totalEquity": portfolio["totalEquity"],
    "dayPnl": portfolio.get("dayPnl", 0),
    "dayReturnPct": round(portfolio.get("dayPnl", 0) / portfolio["totalEquity"] * 100, 2),
    "totalReturnPct": portfolio["totalReturnPct"],
    "unrealizedPnl": portfolio["unrealizedPnl"],
    "realizedPnl": portfolio["realizedPnl"],
    "cashPct": portfolio["cashPct"],
}
```

## Files to Create
- `tracking/portfolio_config.json`
- `scripts/rules/` directory
- `scripts/run_rules.py`
- `scripts/rules/check_time_decay.py` (example, agent will create more)

## Files to Modify
- `scripts/position_manager.py` — portfolio config, realized P&L, sizing, portfolio summary
- `scripts/run_daily.py` — Phase 1 (run rules), Phase 3 (new_scripts, sizing, stats)
- `agents/ANALYST.md` — sizing rules, self-evolution instructions, new_scripts output

## NOT in Scope (handled separately, not by coding agent)
- Weekly evolution cron job — B1 sets this up directly
- Historical NAV curve / time series (future feature)
- Transaction cost / slippage modeling
- Risk budgeting / VAR

## Acceptance Criteria
1. `positions.json` has a `portfolio` block with equity, cash, unrealized/realized P&L, return %
2. Each position has shares, allocatedCapital, currentValue, unrealizedPnl, weight_pct
3. Agent can specify `allocation_pct` (1-10%) for new positions
4. `scripts/rules/` exists, `run_rules.py` works, at least 1 example rule
5. Agent can output `new_scripts` in its JSON, and the pipeline creates them
6. Rule violations are included in the Phase 2 prompt data
7. Daily summary uses actual dollar P&L, not summed percentages
