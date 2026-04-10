# Prompt: Multi-Agent Investment Committee for Stock Analysis Pipeline

You are working in the `stock-analysis` repository.

## Context

The current pipeline uses a single-agent approach: `run_daily.py` collects all data, builds one LLM prompt with `agents/ANALYST.md` instructions, and a single agent makes all buy/hold/sell decisions.

This has a known weakness: **single-perspective bias**. The analyst tends to anchor on one thesis (e.g., valuation-first in V1, momentum-first in V2) and doesn't systematically challenge its own assumptions. Historical result: V1 lost -3.1% while its own WATCH list gained +7.4%.

The Vibe-Trading project (installed at `~/Work/Personal/Vibe-Trading`) implements an investment committee pattern with 4 specialized agents debating in sequence:

```
Bull Advocate → Bear Advocate → Chief Risk Officer → Portfolio Manager
     ↓               ↓                ↓                    ↓
  (parallel)    (parallel)      (reviews both)      (final decision)
```

This prompt adapts that pattern to our stock analysis pipeline.

## Goal

Replace the single ANALYST.md agent with a multi-agent investment committee workflow for position decisions (BUY, SELL, HOLD). Keep the existing data collection pipeline (`run_daily.py` Phase 1) unchanged — only change how decisions are made in Phase 2.

## Read First

1. `agents/ANALYST.md` — current single-agent prompt (the one being replaced)
2. `scripts/run_daily.py` — orchestrator, especially Phase 2 (LLM prompt building)
3. `~/Work/Personal/Vibe-Trading/agent/config/swarm/investment_committee.yaml` — reference pattern
4. `data/strategy-pool.json` — current strategy pool format
5. `data/portfolio.json` — current portfolio format
6. `reports/` — recent daily reports for output format reference

## Architecture

### What Changes

- `agents/ANALYST.md` → split into 4 agent prompt files
- `scripts/run_daily.py` Phase 2 → sequential multi-agent calls instead of one
- Decision output format stays the same (JSON actions compatible with Phase 3 `--apply`)

### What Doesn't Change

- Phase 1 data collection (strategy pool, enrichment, market data, prices)
- Phase 3 apply (position management, reports, git commit)
- Phase 4 validation
- Data sources, file formats, cron schedule

## Agent Definitions

Create 4 new agent prompt files in `agents/`:

### 1. `agents/BULL_ADVOCATE.md`

**Role:** Build the bullish case for each candidate and each current position.

**Input:** All Phase 1 data (same data the current ANALYST.md receives).

**Task:**
- For each candidate in the strategy pool: build a bull thesis
  - Technical: trend alignment, breakout signals, volume confirmation, RPS rank, sector momentum
  - Momentum: price vs MA stack, MACD/RSI regime, relative strength vs market
  - Catalyst: sector rotation, policy tailwinds, earnings momentum
- For each current position: argue for HOLD or ADD
  - Thesis intact? Volume confirming? Sector still rotating in?
- Assign conviction (high/medium/low) to each bull point
- Be data-driven — every point must reference specific numbers from the input data
- Do NOT mention risks or bearish arguments — that's the bear's job

**Output format:**
```json
{
  "candidates": {
    "<code>": {
      "bull_thesis": ["point 1 with data", "point 2 with data"],
      "conviction": "high|medium|low",
      "target_upside_pct": 15,
      "key_levels": {"support": 10.5, "target": 12.8}
    }
  },
  "positions": {
    "<code>": {
      "recommendation": "HOLD|ADD",
      "thesis_intact": true,
      "supporting_points": ["..."]
    }
  }
}
```

### 2. `agents/BEAR_ADVOCATE.md`

**Role:** Surface all risks and build the bearish case.

**Input:** Same Phase 1 data.

**Task:**
- For each candidate: build a bear/risk case
  - Technical: resistance levels, divergences, topping patterns, volume drying up
  - Momentum: overextended? RPS declining? Sector rotation ending?
  - Risk: low volume (< MAVOL30), wide spread, illiquidity, high correlation with existing positions
  - Valuation: if PE/PB is stretched vs history
- For each current position: argue for SELL or REDUCE if warranted
  - Thesis broken? Volume failing? Sector rotating out?
  - Time stop or price stop triggered?
- Assign severity (high/medium/low) to each risk point
- Be the devil's advocate — find what the bull is missing
- Do NOT argue for buying — that's the bull's job

**Output format:**
```json
{
  "candidates": {
    "<code>": {
      "bear_thesis": ["risk 1 with data", "risk 2 with data"],
      "severity": "high|medium|low",
      "downside_risk_pct": -8,
      "key_levels": {"resistance": 13.2, "stop_loss": 9.8}
    }
  },
  "positions": {
    "<code>": {
      "recommendation": "HOLD|SELL|REDUCE",
      "concerns": ["..."],
      "stop_triggered": false
    }
  }
}
```

### 3. `agents/RISK_OFFICER.md`

**Role:** Independent risk review — assess both sides, size positions, enforce rules.

**Input:** Phase 1 data + bull output + bear output.

**Task:**
- Score the reliability of each bull and bear point (1-5)
- Identify blind-spot risks neither side covered
- Portfolio-level risk check:
  - Correlation between candidates and existing positions
  - Sector concentration (max 2 positions per sector)
  - Total position count (max per portfolio rules)
  - Cash floor (current rule: maintain minimum cash %)
- Position sizing:
  - Max position size based on portfolio rules
  - Adjust for IV rank / volatility regime (sizing throttle when IV rank < 15%)
  - Kelly-inspired sizing based on conviction vs risk
- Enforce hard rules:
  - -5% hard stop (from ANALYST.md V2)
  - 10-day time stop for positions not working
  - No adding to losers
  - Volume must be > 50% of MAVOL30 for new entries

**Output format:**
```json
{
  "candidates": {
    "<code>": {
      "bull_reliability": 4,
      "bear_reliability": 3,
      "blind_spots": ["..."],
      "sizing_recommendation": "2% of portfolio",
      "risk_verdict": "approve|conditional|reject",
      "conditions": ["wait for volume confirmation"]
    }
  },
  "positions": {
    "<code>": {
      "stop_check": "ok|triggered",
      "time_stop_check": "ok|triggered",
      "risk_verdict": "hold|reduce|exit",
      "reasoning": "..."
    }
  },
  "portfolio_risk": {
    "sector_concentration": "ok|warning",
    "position_count": "ok|warning",
    "cash_floor": "ok|warning",
    "sizing_throttle_active": true,
    "overall_risk_level": "low|moderate|elevated"
  }
}
```

### 4. `agents/PORTFOLIO_MANAGER.md`

**Role:** Final decision maker. Weighs all inputs, makes executable decisions.

**Input:** Phase 1 data + bull output + bear output + risk output.

**Task:**
- Make the final call on each candidate: BUY (with size) or PASS
- Make the final call on each position: HOLD, SELL, or ADD
- Resolve disagreements between bull and bear with reasoning
- Respect risk officer's hard vetoes (stop triggers, sizing throttle)
- Can override risk officer's soft recommendations with explicit reasoning
- Consider macro context (market breadth, index regime) in timing
- Produce the EXACT same JSON action format that `run_daily.py --apply` expects

**Output:** The final JSON response — same schema as current ANALYST.md output:
```json
{
  "actions": [
    {
      "code": "605167",
      "action": "HOLD",
      "reason": "Bull thesis intact (RPS 88, sector momentum). Bear flags weak volume — valid but not actionable yet. Risk approves. Monitor for volume recovery.",
      "price": 17.61,
      "stop_loss": 16.38
    }
  ],
  "new_positions": [],
  "watchlist_updates": [],
  "hypothesis_updates": [],
  "learnings": []
}
```

The PM's `reason` field should reference which bull/bear points were decisive.

## Implementation in `run_daily.py`

### Phase 2 Changes

Currently Phase 2 builds one big prompt and makes one LLM call. Change to:

```python
# Phase 2: Multi-agent investment committee
# Step 1: Bull and Bear run in parallel (same input data)
bull_prompt = build_agent_prompt("agents/BULL_ADVOCATE.md", phase1_data)
bear_prompt = build_agent_prompt("agents/BEAR_ADVOCATE.md", phase1_data)

bull_output = call_llm(bull_prompt)  # can run in parallel
bear_output = call_llm(bear_prompt)  # can run in parallel

# Step 2: Risk Officer reviews both
risk_prompt = build_agent_prompt("agents/RISK_OFFICER.md", phase1_data, 
                                  bull=bull_output, bear=bear_output)
risk_output = call_llm(risk_prompt)

# Step 3: PM makes final decision
pm_prompt = build_agent_prompt("agents/PORTFOLIO_MANAGER.md", phase1_data,
                                bull=bull_output, bear=bear_output, risk=risk_output)
final_output = call_llm(pm_prompt)

# Phase 3: Apply final_output (unchanged)
```

### Parallelism

Bull and Bear agents receive identical input and don't depend on each other → run them in parallel to save time. Risk and PM are sequential.

### Cost Consideration

4 LLM calls instead of 1. Each call can use a smaller context since the agents are more focused:
- Bull/Bear: only need Phase 1 data (same as current single call)
- Risk: Phase 1 data + bull/bear outputs (summaries, not full data)
- PM: Phase 1 data (summary) + bull/bear/risk outputs

To manage cost:
- Bull and Bear get full Phase 1 data
- Risk and PM get a condensed version of Phase 1 data (market summary, position list, candidate list) plus the upstream agent outputs
- Total token usage should be ~2-3x current, not 4x

### Intermediate Outputs

Save all agent outputs for audit trail:
- `reports/YYYY-MM-DD/bull_output.json`
- `reports/YYYY-MM-DD/bear_output.json`  
- `reports/YYYY-MM-DD/risk_output.json`
- `reports/YYYY-MM-DD/pm_decision.json` (this is the final `response.json`)

### Fallback

If any agent call fails, fall back to the current single-agent ANALYST.md approach. Don't let the pipeline fail just because one agent times out.

## Migration

### Keep ANALYST.md

Don't delete `agents/ANALYST.md` — keep it as the fallback and for the current cron job until the committee is validated. Add a flag:

```python
# In run_daily.py or config
DECISION_MODE = "committee"  # or "single" for fallback
```

### Validation Period

Run both modes in parallel for 1-2 weeks:
1. Committee makes the actual decisions
2. Single analyst runs shadow mode (output saved but not applied)
3. Compare decision quality after 2 weeks

## Constraints

- Do NOT change Phase 1 (data collection) or Phase 3 (apply) logic
- Final output JSON must be compatible with existing `--apply` handler
- Each agent prompt must be self-contained (no cross-references between agent files)
- Agent prompts should include the current portfolio rules (stop losses, sizing, etc.) inline — don't reference ANALYST.md
- Keep the existing cron schedule and delivery mechanism
- Handle LLM failures gracefully — retry once, then fall back to single-agent

## Deliverables

1. Four agent prompt files: `BULL_ADVOCATE.md`, `BEAR_ADVOCATE.md`, `RISK_OFFICER.md`, `PORTFOLIO_MANAGER.md`
2. Updated `run_daily.py` with committee mode
3. Config flag to switch between committee and single-agent mode
4. Intermediate output saving for audit trail
5. Brief summary of changes and any design decisions made

## Key Rules to Embed in All Agent Prompts

These rules from ANALYST.md V2 must be distributed across the appropriate agents:

- **Momentum-first, sector-first** — Bull and PM
- **RPS 75-95% sweet spot** — Bull (as a positive signal), Bear (flag if outside range)
- **-5% hard stop** — Risk Officer (enforce), PM (respect)
- **10-day time stop** — Risk Officer (enforce), PM (respect)
- **No WATCH category** — PM (buy small or skip, never defer to watchlist)
- **Volume > 50% MAVOL30 for entries** — Risk Officer (gate), Bull (flag when strong)
- **Sizing throttle at low IV rank** — Risk Officer (enforce)
- **Max sector concentration** — Risk Officer (enforce)
- **Cash floor** — Risk Officer (enforce)
