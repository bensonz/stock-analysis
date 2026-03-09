# Stock Analysis Pipeline Enhancement: Bull/Bear Debate + Automated Reflection

**Date:** 2026-03-08  
**Inspired by:** [TradingAgents](https://github.com/TauricResearch/TradingAgents) multi-agent debate architecture  
**Scope:** 3 phases, each independently testable and deployable

---

## Overview

Current pipeline: `Phase 1 (data) → Phase 2 (single LLM prompt) → Phase 3 (apply) → Phase 4 (validate)`

Enhanced pipeline: `Phase 1 (data) → Phase 2A (bull/bear debate) → Phase 2B (synthesis + decision) → Phase 3 (apply) → Phase 4 (validate) → Phase 5 (weekly reflection)`

The key idea from TradingAgents: **force the LLM to argue both sides before deciding.** Currently, one analyst prompt does everything — analysis, position management, and decisions — in a single shot. This creates confirmation bias: once the model forms an initial view, it builds the entire analysis around it.

---

## Phase 1: Bull/Bear Debate (新增 Phase 2A)

### What it does

After data collection, before the final analyst call, run **two separate LLM calls**:

1. **Bull Analyst** — given the same data, argues FOR every candidate stock, finds the strongest momentum plays, and aggressively pushes for entries. Also argues FOR holding every current position.
2. **Bear Analyst** — argues AGAINST every candidate, finds every risk, every reason to skip, every reason to sell current positions.

Then the existing Analyst (Phase 2B) receives **both reports** alongside the raw data, and makes the final call.

### Implementation

**New file: `scripts/debate.py`**

```python
"""
debate.py — Bull/Bear debate phase for stock analysis pipeline.

Generates two opposing analysis reports from the same data,
which are then fed into the main analyst prompt for synthesis.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

BULL_PROMPT_TEMPLATE = (PROJECT_ROOT / "agents" / "BULL.md").read_text
BEAR_PROMPT_TEMPLATE = (PROJECT_ROOT / "agents" / "BEAR.md").read_text


def build_bull_prompt(data: dict) -> str:
    """Build the bull analyst prompt from Phase 1 data."""
    template = BULL_PROMPT_TEMPLATE()
    payload = _build_debate_payload(data)
    return f"{template}\n\n## 今日数据\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"


def build_bear_prompt(data: dict) -> str:
    """Build the bear analyst prompt from Phase 1 data."""
    template = BEAR_PROMPT_TEMPLATE()
    payload = _build_debate_payload(data)
    return f"{template}\n\n## 今日数据\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"


def _build_debate_payload(data: dict) -> dict:
    """Extract the subset of data relevant for debate.
    
    Lighter than the full Phase 2 payload — no portfolio management fields,
    just market + candidates + positions for analysis.
    """
    return {
        "date": data["date"],
        "market": data.get("market", {}),
        "strategy_pool": {
            "total_stocks": data.get("strategy_pool", {}).get("total_stocks"),
            "stocks": data.get("strategy_pool", {}).get("stocks", []),
        },
        "enriched_candidates": data.get("enriched", []),
        "active_positions": [
            {
                "code": p["code"],
                "name": p["name"],
                "entryDate": p["entryDate"],
                "entryPrice": p["entryPrice"],
                "currentStop": p.get("currentStop"),
                "sector": p.get("sector", ""),
                "rps120": p.get("rps120"),
                "catalysts": p.get("catalysts", []),
                "pnl_pct": p.get("pnl_pct"),
                "days_held": p.get("days_held"),
            }
            for p in data.get("positions", [])
        ],
        "position_prices": data.get("position_prices", {}),
        "iv_sentiment": data.get("iv_sentiment", {}),
    }
```

**New file: `agents/BULL.md`**

```markdown
# Bull Analyst — Make the Case FOR

You are the Bull Analyst for an A-share momentum trading system. Your job is to find every reason to BUY and HOLD.

## Your Mandate
- For each candidate stock: argue WHY it should be bought NOW
- For each active position: argue WHY it should be held or added to
- Find the strongest sector momentum plays
- Identify catalysts that others might underweight
- Be aggressive but data-backed — no blind optimism

## Rules
1. Use momentum data (RPS, sector rank) to find strength
2. Highlight catalysts: earnings surprise, industry shifts, policy tailwinds
3. For positions in drawdown: argue why the thesis is still valid IF it is
4. Don't invent data. Use what's provided.
5. Acknowledge risks but argue why they're priced in or manageable

## Output Format (JSON)
{
  "bull_cases": [
    {
      "code": "600352",
      "name": "浙江龙盛",
      "bull_thesis": "Why this should be bought/held",
      "key_catalysts": ["catalyst1", "catalyst2"],
      "sector_momentum": "top X%",
      "rps_assessment": "sweet spot / extended / etc",
      "conviction": "strong / moderate / weak",
      "counter_to_bear": "Pre-emptive rebuttal of likely bear arguments"
    }
  ],
  "market_bull_case": "Why current market conditions favor buying",
  "sector_opportunities": ["sector1 — why", "sector2 — why"]
}
```

**New file: `agents/BEAR.md`**

```markdown
# Bear Analyst — Make the Case AGAINST

You are the Bear Analyst for an A-share momentum trading system. Your job is to find every reason to SELL, SKIP, or be cautious.

## Your Mandate
- For each candidate stock: argue WHY it should NOT be bought
- For each active position: argue WHY it should be sold or reduced
- Find every risk, every red flag, every reason for caution
- Identify sector rotation risks, valuation extremes, momentum exhaustion
- Be skeptical but data-backed — no blind pessimism

## Rules
1. Check if momentum is exhausting (RPS too high, extended runs)
2. Look for sector rotation away from current holdings
3. For candidates: find risk factors, poor fundamentals, stale catalysts
4. For positions: check stop proximity, time decay, sector weakness
5. Don't invent data. Use what's provided.
6. Acknowledge strength but argue why it's already priced in

## Output Format (JSON)
{
  "bear_cases": [
    {
      "code": "600352",
      "name": "浙江龙盛",
      "bear_thesis": "Why this should NOT be bought / should be sold",
      "key_risks": ["risk1", "risk2"],
      "sector_concern": "description",
      "momentum_assessment": "overextended / fading / etc",
      "conviction": "strong / moderate / weak",
      "counter_to_bull": "Pre-emptive rebuttal of likely bull arguments"
    }
  ],
  "market_bear_case": "Why current market conditions favor caution",
  "sector_risks": ["sector1 — why risky", "sector2 — why rotating out"]
}
```

**Modification to `run_daily.py`** — new Phase 2A before existing Phase 2:

```python
# In phase2_build_prompt(), add debate reports to the prompt:

def phase2_build_prompt(data: dict, bull_report: str = None, bear_report: str = None) -> str:
    """Phase 2B: Build LLM prompt from collected data + debate reports."""
    analyst_prompt = (PROJECT_ROOT / "agents" / "ANALYST.md").read_text(encoding="utf-8")
    
    # ... existing payload building ...
    
    debate_section = ""
    if bull_report and bear_report:
        debate_section = f"""
## Bull/Bear 辩论报告

### 🐂 Bull Analyst Report
{bull_report}

### 🐻 Bear Analyst Report  
{bear_report}

**重要：** 以上是两个独立分析师分别从多头和空头角度的分析。你需要综合双方论点做出最终决策。
当Bull和Bear观点冲突时，用数据裁决，不要简单取中间值。
"""
    
    prompt = f"""{analyst_prompt}

{debate_section}

## 今日数据 (由 run_daily.py 自动收集)

```json
{json.dumps(payload, ensure_ascii=False, indent=2)}
```

请根据以上数据和辩论报告进行分析，按照 Required Output JSON 格式返回你的决策。
"""
    return prompt
```

**Modification to `ANALYST.md`** — add section acknowledging debate:

```markdown
## Debate Integration (if debate reports provided)

When Bull and Bear reports are included:
1. **Don't average** — if Bull says BUY and Bear says SKIP, don't default to WATCH
2. **Evaluate evidence quality** — whose data points are stronger?
3. **Sector first** — if Bear's sector concern is valid, Bull's stock thesis doesn't matter
4. **Note disagreements** — in your market_summary, mention where Bull/Bear diverged and why you sided with one
5. **Use Bear as stop-loss discipline** — Bear's risks inform your stop placement and position sizing
```

### How to run (modified pipeline)

```
Phase 1:  python scripts/run_daily.py --phase1
Phase 2A: Cron agent sends bull_prompt to LLM → saves bull_report.json
          Cron agent sends bear_prompt to LLM → saves bear_report.json
Phase 2B: Cron agent sends main prompt (with debate) to LLM → saves response.json
Phase 3:  python scripts/run_daily.py --apply response.json
Phase 4:  Validation
```

### Testing Plan

**Test 1: Prompt quality check**
- Run Phase 1 for 2026-03-06
- Generate bull_prompt and bear_prompt from the data
- Manually review: are the prompts clear? Do they contain all needed data?
- **Expected result:** Two well-formed prompts, each ~2K-5K tokens, containing market + candidate data

**Test 2: LLM response quality**
- Send bull_prompt and bear_prompt to Claude
- **Expected result (bull):** JSON with bull_cases for each candidate, market_bull_case, sector_opportunities. Should argue FOR stocks with specific data (RPS numbers, catalyst details).
- **Expected result (bear):** JSON with bear_cases for each candidate, market_bear_case, sector_risks. Should argue AGAINST with specific data (risk factors, sector weakness, momentum exhaustion).
- **Quality check:** Do they disagree? If both say the same thing for every stock, the prompts need work. We want genuine tension.

**Test 3: Synthesis quality**
- Send the combined prompt (analyst + debate + data) to Claude
- Compare output with a baseline run (no debate, current pipeline)
- **Expected result:** Final decisions should be MORE decisive (fewer wishy-washy HOLD calls), better reasoned (citing specific bull/bear arguments), and market_summary should mention where debates were resolved.
- **Quality check:** Count the number of times the analyst references bull/bear arguments. Should be >3 references minimum.

**Test 4: Backtesting (1 week)**
- Run enhanced pipeline on 2026-03-03 through 2026-03-06 using saved Phase 1 data
- Compare decisions with actual pipeline decisions from those days
- **Expected result:** At least 1-2 decisions differ from original. The differences should be MORE correct based on what actually happened the next day.

---

## Phase 2: Automated Weekly Reflection (新增 Phase 5)

### What it does

Every Friday (or configurable), automatically:
1. Load all runs from the past week
2. For each position decision (BUY/SELL/HOLD), calculate actual P&L outcome
3. Ask LLM to reflect: what went right, what went wrong, and why
4. Store structured reflections in `LEARNINGS.md` AND a searchable memory store
5. Next week's analyst prompt includes relevant past reflections (BM25 matched)

This replaces the current manual `new_learnings` field with automated, outcome-graded reflection.

### Implementation

**New file: `scripts/weekly_reflection.py`**

```python
"""
weekly_reflection.py — Automated post-week reflection and learning extraction.

Runs after market close on Friday (or manually). Reviews the week's decisions
against actual outcomes and generates structured learnings.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
REFLECTIONS_DIR = PROJECT_ROOT / "reflections"
REFLECTIONS_DIR.mkdir(exist_ok=True)


def collect_week_outcomes(end_date: str) -> list[dict]:
    """Collect all decisions and their outcomes for the past 5 trading days.
    
    For each decision made during the week:
    - BUY: what was the return after 1, 3, 5 days?
    - SELL: what happened to the stock after selling?
    - HOLD: was the position up or down at week end?
    - SKIP: did the skipped stock go up or down?
    
    Returns list of {decision, outcome, pnl, context} dicts.
    """
    # Implementation: iterate over runs, match with price data
    pass


def build_reflection_prompt(outcomes: list[dict], learnings_excerpt: str) -> str:
    """Build the reflection prompt for the LLM.
    
    The prompt asks the LLM to:
    1. Grade each decision (correct/incorrect/neutral)
    2. Identify patterns in mistakes
    3. Extract 3-5 actionable learnings
    4. Generate a "situation query" for future BM25 matching
    """
    template = (PROJECT_ROOT / "agents" / "REFLECTOR.md").read_text(encoding="utf-8")
    
    payload = {
        "week_ending": outcomes[0]["date"] if outcomes else "unknown",
        "decisions_and_outcomes": outcomes,
        "current_learnings": learnings_excerpt,
    }
    
    return f"{template}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"


def store_reflection(week_date: str, reflection: dict) -> None:
    """Store reflection to both LEARNINGS.md and reflections/ archive."""
    # Append to LEARNINGS.md
    learnings_file = PROJECT_ROOT / "LEARNINGS.md"
    new_entries = reflection.get("new_learnings", [])
    if new_entries:
        with open(learnings_file, "a", encoding="utf-8") as f:
            f.write(f"\n### 周度复盘 ({week_date})\n\n")
            for entry in new_entries:
                f.write(f"- {entry}\n")
    
    # Save full reflection to archive
    ref_file = REFLECTIONS_DIR / f"{week_date}.json"
    ref_file.write_text(json.dumps(reflection, ensure_ascii=False, indent=2), encoding="utf-8")
```

**New file: `agents/REFLECTOR.md`**

```markdown
# Weekly Reflector — Learn From Outcomes

You are reviewing this week's trading decisions against actual outcomes. Your job is to extract honest, actionable learnings.

## Process
1. For each decision, grade it:
   - ✅ CORRECT: BUY that went up, SELL that would have gone down, HOLD that continued up
   - ❌ INCORRECT: BUY that went down, missed SELL that crashed, HOLD that should have been sold
   - ➖ NEUTRAL: too early to tell, or marginal outcome
   
2. Find PATTERNS in mistakes (don't just list individual errors):
   - Did you consistently misjudge a sector?
   - Did you ignore bear signals that turned out right?
   - Were your stops too tight or too loose?
   - Did momentum exhaustion catch you?

3. Extract 3-5 SPECIFIC, ACTIONABLE learnings:
   - BAD: "Should have been more careful" (useless)
   - GOOD: "When RPS20 > 95% AND sector rank drops 2+ spots in 3 days, sell immediately — this pattern preceded -8% drops in 3/4 cases this week"

4. Generate a "situation fingerprint" — a 1-2 sentence description of this week's market regime for future BM25 matching.

## Output Format (JSON)
{
  "week_ending": "2026-03-07",
  "grades": [
    {
      "date": "2026-03-03",
      "code": "300684",
      "action": "HOLD",
      "grade": "INCORRECT",
      "outcome_pnl": -5.2,
      "reason": "Held through sector rotation, should have sold when sector dropped to bottom 30%"
    }
  ],
  "patterns": [
    "Pattern description with specific data"
  ],
  "new_learnings": [
    "Specific actionable learning"
  ],
  "situation_fingerprint": "Week of sector rotation from tech→resources with IV spike, momentum exhaustion in AI/semiconductor names",
  "overall_grade": "2/5 correct, 2 incorrect, 1 neutral",
  "biggest_mistake": "description",
  "biggest_win": "description"
}
```

### Testing Plan

**Test 1: Outcome collection**
- Run `collect_week_outcomes("2026-03-07")` on existing run data
- **Expected result:** List of 10-20 decision+outcome pairs from the week, each with actual P&L calculated from price data. Format should include: date, code, name, action taken, entry/exit price, outcome price, P&L %.

**Test 2: Reflection quality**
- Send reflection prompt to Claude with real week outcomes
- **Expected result:** JSON with grades for each decision, 2-3 patterns identified, 3-5 specific learnings. Learnings should reference specific numbers (not vague). situation_fingerprint should be a useful search query.
- **Quality check:** Compare auto-generated learnings with the manual ones already in LEARNINGS.md for the same week. Are the auto ones more specific? Do they catch things the manual ones missed?

**Test 3: Memory retrieval**  
- Store 4 weeks of reflections
- Query with a new week's market description
- **Expected result:** BM25 retrieves the most relevant past week. E.g., if current week has "sector rotation from tech to resources", it should retrieve past weeks with similar patterns, not just any random week.

**Test 4: Feedback loop**
- Run full pipeline for a week WITH past reflections included in the analyst prompt
- Compare decisions with a control run WITHOUT reflections
- **Expected result:** At least 1 decision changes due to past learning. E.g., "Last time IV was this low and we held, we got burned. This time, tightening stops."

---

## Phase 3: Risk Sizing Debate (Optional Enhancement)

### What it does

After the analyst makes BUY decisions, run a quick debate on position sizing:

- **Aggressive voice:** "Go 10% allocation, catalyst is strong, sector is hot"
- **Conservative voice:** "Go 3%, the stock is extended, IV is low which means complacency"
- **Final sizing:** Analyst synthesizes into final allocation_pct

This is lighter than the full bull/bear debate — just a quick 2-call exchange focused ONLY on sizing, not direction.

### Why it's separate

Direction (buy/sell/hold) and sizing are different skills. Your current system sometimes does "BUY at 7% allocation" when the bull case is strong but the bear risks are real — the answer should be "BUY at 3%" (buy the direction, reduce the size). The sizing debate surfaces this.

### Implementation

Add to the Phase 2B prompt output format:

```json
{
  "new_positions": [
    {
      "code": "600352",
      "allocation_pct": 7,
      "sizing_rationale": "Bull: sector leader + fresh catalyst. Bear: RPS20 overextended. Compromise: 5% instead of 7%",
      ...
    }
  ]
}
```

Or implement as a separate LLM call after Phase 2B, reviewing each new_position and adjusting sizing.

### Testing Plan

**Test 1: Sizing quality**
- Take 10 historical BUY decisions with known outcomes
- Run sizing debate on each
- **Expected result:** Positions that later lost >5% should get SMALLER allocations from the debate (conservative voice wins on those). Positions that gained >10% should get SIMILAR or LARGER allocations.
- **Quality metric:** If we re-weighted the portfolio using debate-adjusted sizes, does total P&L improve vs original sizes?

---

## Rollout Order

| Phase | What | Effort | Impact | Dependencies |
|-------|------|--------|--------|--------------|
| **Phase 1** | Bull/Bear debate | 2-3 days | High — directly improves decision quality | New BULL.md, BEAR.md, modify run_daily.py |
| **Phase 2** | Weekly reflection | 1-2 days | Medium — improves over time as memory builds | New REFLECTOR.md, weekly_reflection.py, cron job |
| **Phase 3** | Sizing debate | 1 day | Medium — reduces drawdowns on bad entries | Modify Phase 2B prompt or add post-processing |

**Recommended:** Do Phase 1 first, run it for 1-2 weeks, measure impact, then add Phase 2.

---

## Success Metrics

After 2 weeks of running the enhanced pipeline:

1. **Decision quality:** Compare win rate (% of BUY decisions that are profitable after 5 days) with vs without debate. Target: +5-10pp improvement.
2. **Loss reduction:** Average loss on incorrect BUYs should decrease (bear catches more bad entries). Target: avg loss improves from -5% to -3%.
3. **Conviction clarity:** Fewer "moderate" conviction calls, more "strong" or "skip". The debate should polarize decisions.
4. **Learning specificity:** Auto-generated learnings should be more specific than manual ones (contain numbers, dates, specific patterns vs vague advice).

---

## Cron Integration

The enhanced pipeline fits into your existing cron job (14:30 CST daily):

```
Phase 1:  run_daily.py --phase1                    (~10 min, data collection)
Phase 2A: debate.py → bull_prompt + bear_prompt     (build prompts, <1 sec)
          LLM call: bull_prompt → bull_report       (~30 sec)
          LLM call: bear_prompt → bear_report       (~30 sec)
Phase 2B: run_daily.py prompt (with debate)         (build combined prompt, <1 sec)
          LLM call: combined → response.json        (~60 sec)
Phase 3:  run_daily.py --apply response.json        (<5 sec)
Phase 4:  Validation                                (<5 sec)

Weekly (Friday):
Phase 5:  weekly_reflection.py                      (~60 sec)
```

Total added time: ~60 sec (2 extra LLM calls for debate). Total pipeline: ~12-13 min vs current ~11 min.
