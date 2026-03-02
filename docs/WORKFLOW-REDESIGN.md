# Stock Analysis Workflow Redesign

## Current Problems

1. **Data inconsistency** — `positions.json` not updated when tracker opens/closes positions. Today: tracker opened 688630 but positions.json still shows 5. Orchestrator summary said "0 new positions" when there was 1.
2. **Proxy failures** — Python scripts (AkShare → Eastmoney) go through Surge proxy and fail with `ProxyError`. Market data, breadth, sector data all broken.
3. **Role bleeding** — Researcher reports on current positions (that's tracker's job). Report has "当前持仓最新状态" section.
4. **Unreliable orchestration** — Cron frequently fails (gateway restarts, Telegram delivery crashes, auth 401s). The orchestrator agent spawns 3 sub-agents with no verification of actual output.
5. **No validation** — Agent says "done" but files may be incomplete, malformed, or inconsistent. Nobody checks.
6. **Browser dependency** — Step 3 (scan CheeseForTune) requires launching a browser to scrape a web page. Fragile, slow, and environment-dependent.
7. **Too many agents** — 3 separate LLM sessions for what could be a more structured pipeline.
8. **Phantom data** — `data/prices/` almost always empty, `memory/` was empty, report can contain stale/wrong position data.

## Proposed Architecture: Script-First, Agent-Light

### Core Principle
**Scripts do the deterministic work. LLM does the judgment.**

Data fetching, file management, validation, and state transitions should be Python scripts that always work. The LLM should only be called for things that need judgment: evaluating positions, analyzing opportunities, writing insights.

### Pipeline Structure

```
┌─────────────────────────────────────────────────┐
│  run_daily.py  (orchestrator script)            │
│                                                  │
│  Phase 1: DATA COLLECTION (pure Python)          │
│    ├─ fetch_strategy_pool()     # CheeseForTune API  │
│    ├─ enrich_stocks()           # CheeseForTune batch │
│    ├─ fetch_market_overview()   # AkShare indices     │
│    ├─ fetch_position_prices()   # AkShare positions   │
│    └─ validate_data()           # Check completeness  │
│                                                  │
│  Phase 2: ANALYSIS (LLM — single agent call)     │
│    ├─ Input: all data from Phase 1 as JSON       │
│    ├─ Evaluate positions (HOLD/SELL/RAISE_STOP)  │
│    ├─ Evaluate new candidates (BUY/WATCH/AVOID)  │
│    ├─ Missed opportunity check                   │
│    └─ Output: structured JSON decisions          │
│                                                  │
│  Phase 3: EXECUTION (pure Python)                │
│    ├─ apply_decisions()         # Update tracking files │
│    ├─ update_positions_json()   # Always in sync       │
│    ├─ generate_report()         # From structured data │
│    ├─ update_learnings()        # Append new lessons   │
│    ├─ git_commit()              # Always commit        │
│    └─ validate_output()         # Verify all files     │
│                                                  │
│  Phase 4: RESULTS                                │
│    └─ Print summary to stdout                    │
└─────────────────────────────────────────────────┘
```

### Key Changes

#### 1. Single orchestrator script (`scripts/run_daily.py`)
- Pure Python entry point
- Handles all file I/O, validation, error handling
- Sets `NO_PROXY` for Chinese financial APIs
- Produces a structured data bundle for the LLM
- Applies LLM decisions back to files
- **No browser needed** — CheeseForTune API replaces browser scraping

#### 2. Single LLM call instead of 3 agents
- One agent receives ALL context (market data + positions + watchlist history + learnings)
- Returns a single structured JSON with all decisions
- No sub-agent spawning, no coordination failures
- Prompt is deterministic — same inputs always ask for same structure

#### 3. Data collection is script-only
```python
# scripts/run_daily.py

import os
os.environ['NO_PROXY'] = '*.eastmoney.com,*.push2.eastmoney.com'

def collect_data(date: str) -> dict:
    """Phase 1: Collect all data. Pure Python, no LLM."""
    data = {}
    
    # 1. Strategy pool from CheeseForTune API
    data['strategy_pool'] = fetch_strategy_pool()  # API, not browser
    
    # 2. Enrich stocks in buy zone (RPS 75-95%)
    candidates = [s for s in data['strategy_pool'] if 75 <= s['rps120'] <= 95]
    data['enriched'] = batch_enrich(candidates)
    
    # 3. Market overview
    data['market'] = fetch_market_indices()
    
    # 4. Position prices
    positions = load_active_positions()
    data['positions'] = fetch_position_prices(positions)
    
    # 5. Recent watchlists (for missed opportunity analysis)
    data['recent_watchlists'] = load_recent_watchlists(days=5)
    
    # 6. Current learnings
    data['learnings'] = read_file('LEARNINGS.md')
    
    # Validate
    errors = validate_data(data)
    data['collection_errors'] = errors
    
    return data
```

#### 4. LLM receives structured input, returns structured output
```python
def analyze(data: dict) -> dict:
    """Phase 2: LLM analysis. Single call."""
    
    prompt = f"""You are a stock analysis system. Given the following market data,
    return a JSON with your analysis decisions.
    
    ## Data
    {json.dumps(data, ensure_ascii=False)}
    
    ## Required Output (JSON)
    {{
      "position_decisions": [
        {{"code": "300373", "action": "HOLD|SELL|RAISE_STOP", "reason": "...", "new_stop": null}}
      ],
      "new_positions": [
        {{"code": "688630", "action": "OPEN", "entry_price": 201.72, "target": 240, "stop": 182, "thesis": "...", "confidence": "high|medium"}}
      ],
      "watchlist": [
        {{"code": "688377", "recommendation": "BUY|WATCH|AVOID", "confidence": "...", "reasoning": "..."}}
      ],
      "missed_opportunities": [
        {{"code": "...", "recommended_date": "...", "recommended_price": 0, "current_price": 0, "return_pct": 0, "lesson": "..."}}
      ],
      "new_learnings": ["..."],
      "market_summary": "..."
    }}"""
    
    result = call_llm(prompt)
    return json.loads(result)
```

#### 5. Execution is deterministic
```python
def execute(decisions: dict, data: dict):
    """Phase 3: Apply decisions. Pure Python."""
    
    # Apply position decisions
    for d in decisions['position_decisions']:
        if d['action'] == 'SELL':
            close_position(d['code'], d['reason'], data)
        elif d['action'] == 'RAISE_STOP':
            update_stop(d['code'], d['new_stop'])
        update_position_history(d['code'], d)
    
    # Open new positions
    for p in decisions['new_positions']:
        create_position(p)
    
    # ALWAYS regenerate positions.json
    regenerate_positions_json()
    
    # Generate report from structured data
    generate_report(data, decisions)
    
    # Save watchlist
    save_watchlist(data, decisions)
    
    # Update learnings
    if decisions.get('new_learnings'):
        append_learnings(decisions['new_learnings'])
    
    # Git commit
    git_commit(f"daily: {date}")
    
    # Validate everything
    validate_output(date)
```

#### 6. Validation at every step
```python
def validate_output(date: str) -> list[str]:
    """Check all output files are consistent."""
    errors = []
    
    # positions.json matches tracking/*.json
    pos = load_positions_json()
    tracking = load_all_tracking_files()
    active_codes = {t['code'] for t in tracking if t['status'] != 'closed'}
    pos_codes = {p['code'] for p in pos['activePositions']}
    if active_codes != pos_codes:
        errors.append(f"positions.json mismatch: {active_codes ^ pos_codes}")
    
    # No closed positions in tracking/ root
    for f in glob('tracking/*.json'):
        if 'positions.json' in f: continue
        d = json.load(open(f))
        if d.get('status') == 'closed':
            errors.append(f"{f} is closed but not in closed/")
    
    # Watchlist exists
    if not Path(f'watchlist/{date}.json').exists():
        errors.append(f"Missing watchlist/{date}.json")
    
    # Report exists
    if not Path(f'reports/{date}.md').exists():
        errors.append(f"Missing reports/{date}.md")
    
    return errors
```

### File Structure (simplified)

```
stock-analysis/
├── scripts/
│   ├── run_daily.py          # 🆕 Main orchestrator
│   ├── data_collector.py     # 🆕 All data fetching
│   ├── position_manager.py   # 🆕 Position state machine
│   ├── report_generator.py   # 🆕 Report from structured data
│   ├── validator.py          # 🆕 Consistency checks
│   ├── cheesefortune_client.py  # Existing, keep
│   ├── fetch_price.py        # Existing, keep (add NO_PROXY)
│   └── fetch_and_save.py     # Existing, keep (add NO_PROXY)
├── agents/
│   └── ANALYST.md            # 🔄 Single analysis prompt (replaces 3 agents)
├── tracking/
│   ├── positions.json        # Always regenerated by script
│   ├── {code}.json           # Individual positions
│   ├── closed/               # Closed positions
│   └── daily/                # Daily action logs
├── watchlist/                # Daily watchlists
├── reports/                  # Daily reports
├── data/
│   ├── crawl/                # Raw strategy pool data
│   ├── market/               # Market snapshots
│   └── prices/               # Price snapshots
├── LEARNINGS.md              # Accumulated wisdom
└── docs/
    └── WORKFLOW-REDESIGN.md  # This file
```

### Cron Setup

```python
# The cron job just runs the script — no agent orchestration
# openclaw cron payload:
"""
cd /Users/bz/Work/Personal/stock-analysis
source .venv/bin/activate
python scripts/run_daily.py 2>&1
"""
```

Or even simpler — use system crontab instead of OpenClaw cron:
```
30 14 * * 1-5 cd /Users/bz/Work/Personal/stock-analysis && .venv/bin/python scripts/run_daily.py >> logs/cron.log 2>&1
```

### Benefits

1. **Deterministic data collection** — Scripts always produce same file structure, always set NO_PROXY, always validate
2. **Single LLM call** — No coordination failures, no sub-agent timeouts, no delivery issues
3. **Consistent state** — positions.json always matches tracking files (script enforces it)
4. **Debuggable** — Each phase logs to a file, you can re-run any phase independently
5. **No browser** — CheeseForTune API for strategy pool (already have the client)
6. **Cheaper** — 1 LLM call vs 3+ agent sessions with their own system prompts
7. **Testable** — Each Python function can be unit tested

### Migration Plan

1. **Immediate fixes** (today):
   - Add `NO_PROXY` to all Python scripts for Eastmoney
   - Fix positions.json (regenerate from tracking files)
   - Remove position reporting from researcher prompt

2. **Phase 1** — Build `scripts/run_daily.py` with data collection + validation
3. **Phase 2** — Build single LLM analysis prompt + execution layer
4. **Phase 3** — Replace cron job, test for 1 week alongside old system
5. **Phase 4** — Remove old 3-agent orchestrator

### Open Questions

- Should we still use CheeseForTune browser scrape for the initial stock list, or can the API provide the full strategy pool? (Need to check if there's an API endpoint for strategy screening results)
- Keep OpenClaw cron or switch to system crontab? (System crontab is simpler but loses the dashboard visibility)
- How should the LLM call work — direct API call from Python, or still spawn via OpenClaw sessions_spawn?
