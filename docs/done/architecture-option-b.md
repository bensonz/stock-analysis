# Architecture: Option B — Sequential Claude→GPT Collaboration

_2026-03-11_

## Problem

Current `call_llm()` in `llm_client.py` runs 4 passes:

| Pass | Model | Input | Purpose |
|------|-------|-------|---------|
| P1 | Claude | Raw prompt (213KB) | Research + draft |
| P2 | Claude | Same conv + REFINE_PROMPT | "Output clean JSON" |
| P3 | GPT-5.4 | Raw prompt (213KB, fresh) | Independent research + draft |
| P4 | GPT-5.4 | Same conv + REFINE_PROMPT | "Output clean JSON" |

Issues:
1. **P2 is wasted** — just reformats JSON, no real refinement
2. **P3 ignores Claude's work** — starts fresh with the same raw data
3. **P4 is the final answer** — Claude's analysis is thrown away entirely
4. **GPT hangs** — 213KB prompt through proxy with no timeout, frequently stalls
5. **Double token cost** — both models process the full 500K-token prompt independently

## Option B: Sequential Handoff

```
┌─────────────────────────────────────────────────────┐
│  Phase 1 (unchanged): run_daily.py collects data    │
│  Output: phase1.json + prompt.md (~213KB)            │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  Pass 1: Claude (full prompt)                        │
│  - Gets ANALYST.md instructions + all market data    │
│  - Has tool access (web_search, web_fetch)           │
│  - Produces: research memo + preliminary decisions   │
│  - Output format: structured analysis (NOT final     │
│    JSON — free to think, reason, flag uncertainties)  │
└──────────────────────┬──────────────────────────────┘
                       │ claude_memo (~10-15KB)
                       ▼
┌─────────────────────────────────────────────────────┐
│  Pass 2: GPT-5.4 (condensed prompt + Claude memo)    │
│  - Gets: ANALYST.md + SUMMARY data + Claude's memo   │
│  - Does NOT get full 213KB raw data                   │
│  - Role: final decision-maker / risk committee        │
│  - Can challenge Claude's reasoning                   │
│  - Produces: final JSON decisions                     │
│  - No tool access needed (Claude already researched)  │
└──────────────────────┬──────────────────────────────┘
                       │ response.json
                       ▼
┌─────────────────────────────────────────────────────┐
│  Phase 3+4 (unchanged): apply + validate + commit    │
└─────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Claude gets the full prompt (unchanged)

Claude handles the 213KB prompt fine (500K tokens is within its 1M context). It has tool access for web searches. This pass stays exactly as-is — Pass 1 in current code.

### 2. Claude outputs a **research memo**, not JSON

Current P1 already produces analysis text before P2 reformats it. We keep that — but now it's the *product*, not a throwaway draft.

The memo should contain:
- Market regime assessment (bull/bear/range, breadth, sentiment)
- Sector analysis (top/bottom sectors, catalysts, rotation signals)
- For each stock in the pool: thesis, key data points, risk flags, preliminary verdict
- Position management recommendations for existing holdings
- Watchlist updates with rationale
- Explicit uncertainty flags ("I'm unsure about X because...")

This is what `pass1_response.txt` already looks like. We just stop asking Claude to also produce JSON.

### 3. GPT gets a **condensed** prompt

This is the critical change. GPT does NOT see the full 213KB raw data. Instead it gets:

```
[ANALYST.md instructions — what JSON schema to output, rules, constraints]

[SUMMARY BLOCK — ~5-10KB condensed from phase1.json]
  - Portfolio snapshot (current positions, P&L, cash)
  - Market indices (values + % change)
  - Top/bottom 5 sectors
  - Strategy pool: for each stock, just: name, price, change%, RPS, sector, PE, in_pool_since
  - Existing position details

[CLAUDE'S RESEARCH MEMO — ~10-15KB, verbatim from Pass 1]

[DECISION INSTRUCTIONS]
You are the final decision-maker. Claude has done the research above.
Your job:
1. Review Claude's analysis critically — challenge assumptions, check for bias
2. Output the final JSON decisions
3. If you disagree with Claude on a stock, explain why briefly in the JSON reasoning field
4. You may override Claude's recommendations
5. Output ONLY valid JSON starting with {
```

Total GPT input: **~30-40KB** instead of 213KB. That's ~70-80K tokens instead of 500K. Faster, cheaper, and won't hang.

### 4. GPT has NO tool access

Claude already did the web research. GPT's job is judgment, not data gathering. This eliminates the tool loop for GPT entirely — single API call, single response.

### 5. Fallback: Claude produces JSON too

If GPT fails (timeout, parse error, proxy down), we fall back to Claude's preliminary decisions. Claude's memo should include tentative JSON decisions at the end so we're never stuck.

## Implementation Changes

### `llm_client.py`

```python
def call_llm(prompt, ...) -> dict:
    # Pass 1: Claude — full prompt with tools (UNCHANGED)
    pass1_text = _run_tool_loop(client, messages, ...)
    
    # Extract/request Claude's fallback JSON
    # (Already in pass1_text or request it as a follow-up)
    claude_json = _parse_llm_response(pass1_text)
    
    # Pass 2: GPT — condensed prompt + Claude's memo (NEW)
    gpt_prompt = build_gpt_prompt(
        analyst_md=analyst_instructions,   # ANALYST.md decision rules
        summary=build_summary(data),       # Condensed market data
        claude_memo=pass1_text,            # Claude's full research
    )
    
    # Single call, no tools, with timeout
    gpt_response = oai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": gpt_prompt}],
        max_tokens=16384,
        temperature=0.3,
        timeout=120,  # 2 min max — no more hanging
    )
    gpt_text = gpt_response.choices[0].message.content
    gpt_json = _parse_llm_response(gpt_text)
    
    return {
        "text": gpt_text if gpt_json else pass1_text,
        "claude_memo": pass1_text,
        "claude_json": claude_json,       # Fallback
        "gpt_json": gpt_json,             # Primary
        "fallback_used": not bool(gpt_json),
        ...
    }
```

### New function: `build_summary(data: dict) -> str`

Condenses `phase1.json` (250KB) into ~5-10KB:

```python
def build_summary(data: dict) -> str:
    """Condense phase1 data for GPT's condensed prompt."""
    sections = []
    
    # Portfolio snapshot
    sections.append(format_portfolio(data["positions"], data["cash"]))
    
    # Market indices — just values + change%
    sections.append(format_indices(data["market"]))
    
    # Top/bottom sectors — name + change% only
    sections.append(format_sectors(data["sectors"], top_n=10))
    
    # Strategy pool — table: name | price | chg% | RPS | sector | PE
    sections.append(format_pool_table(data["pool"]))
    
    # Existing positions — entry price, P&L, days held, stop levels
    sections.append(format_positions_detail(data["positions"]))
    
    return "\n\n".join(sections)
```

### New function: `build_gpt_prompt(...) -> str`

```python
def build_gpt_prompt(analyst_md: str, summary: str, claude_memo: str) -> str:
    return f"""# Decision Instructions

{analyst_md}

---

# Market Data Summary

{summary}

---

# Research Analysis (by Claude)

The following research memo was produced by a senior analyst who reviewed
the full market data, ran web searches for catalysts/news, and formed
preliminary views. Review it critically.

{claude_memo}

---

# Your Task

You are the portfolio manager making final decisions. Based on the research
above and the market data summary:

1. Critically evaluate the analyst's recommendations
2. Check for confirmation bias, recency bias, or missing risk factors
3. Make your final decisions
4. Output ONLY valid JSON starting with {{ — no markdown, no explanation
5. Follow the exact JSON schema specified in the Decision Instructions above
"""
```

### `run_daily.py` changes

Minimal — `call_llm()` return dict changes slightly:

```python
# Current:
decisions = _parse_llm_response(llm_result["text"])

# New:
decisions = llm_result.get("gpt_json") or llm_result.get("claude_json")
if not decisions:
    decisions = _parse_llm_response(llm_result["text"])
```

Save both responses:
```python
(run_dir / "claude_memo.txt").write_text(llm_result["claude_memo"])
(run_dir / "response_claude.json").write_text(json.dumps(llm_result["claude_json"]))
(run_dir / "response_gpt.json").write_text(json.dumps(llm_result["gpt_json"]))
```

## Token Economics

| | Current (4-pass) | Option B |
|---|---|---|
| Claude input | ~500K × 2 passes = ~1M | ~500K × 1 pass |
| Claude output | ~10K + ~8K = ~18K | ~15K (memo + fallback JSON) |
| GPT input | ~500K × 2 passes = ~1M | ~80K × 1 pass |
| GPT output | ~10K + ~8K = ~18K | ~10K (final JSON only) |
| **Total input** | **~2M tokens** | **~580K tokens** (-71%) |
| **Total output** | **~36K tokens** | **~25K tokens** (-31%) |
| Wall time | 300s+ (GPT often hangs) | ~180s (Claude research + 1 fast GPT call) |

## Why GPT Gets Stuck (Current)

1. **No timeout** on `client.chat.completions.create()` at line 339
2. Prompt is 213KB / ~500K tokens through `duckcoding.com` proxy
3. Proxy may buffer the entire response or have its own timeout issues
4. GPT-5.4 may struggle with 500K context + tool loops on a relay

Option B fixes all of this: GPT sees ~80K tokens, no tools, with an explicit 120s timeout.

## File Changes Required

| File | Change |
|------|--------|
| `scripts/llm_client.py` | Rewrite `call_llm()`: remove P2/P3/P4, add `build_summary()`, `build_gpt_prompt()`, single GPT call with timeout |
| `scripts/run_daily.py` | Update `call_llm()` return handling, save `claude_memo.txt` + both JSON files |
| `agents/ANALYST.md` | Add instruction for Claude to produce research memo format (not just JSON). Add fallback JSON request. |

No changes to: `data_collector.py`, `position_manager.py`, `report_generator.py`, `validator.py`, phase 1 or phase 3/4 logic.

## Rollback

Keep the old `call_llm()` as `call_llm_v1()` for one release cycle. Add `--legacy-llm` flag to `run_daily.py` to use the old 4-pass approach if needed.

## Open Questions

1. **Should Claude's memo have a fixed structure?** (e.g., required sections: Market, Sectors, Stocks, Positions, Watchlist) — or freeform? Fixed structure makes GPT's job easier but constrains Claude.
2. **Should GPT see any raw data at all?** Current spec gives it a summary table. Alternative: give it nothing but the memo, pure "judge the analyst" role. Risk: can't catch data errors Claude made.
3. **ANALYST.md split?** Currently one file for both models. Might want `ANALYST.md` (shared rules/schema) + `RESEARCHER.md` (Claude-specific) + `PM.md` (GPT-specific). Overkill for now — defer.
