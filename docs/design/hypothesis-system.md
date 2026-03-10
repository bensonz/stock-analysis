# Hypothesis-Based Learning System — Design Doc

## Problem

The current learning system treats every observation as a rule. LEARNINGS.md is 600+ lines of contradictory "lessons" that the analyst gets as a truncated blob. There's no:
- Distinction between observation, hypothesis, and validated rule
- Sample size tracking
- Hit rate measurement
- Confidence scoring
- Expiry/retirement of stale learnings
- Mechanism for contradictory evidence to weaken a hypothesis

## Design

### Data Model: `tracking/hypotheses.json`

```json
{
  "version": 2,
  "lastUpdated": "2026-03-10",
  "hypotheses": [
    {
      "id": "h001",
      "text": "ST stocks underperform 80% of the time — avoid",
      "type": "heuristic",
      "status": "hypothesis",
      "created": "2026-03-10",
      "lastTested": "2026-03-10",
      "evidence": {
        "supporting": [
          {"date": "2026-03-05", "detail": "ST某某 -12% in 3 days after entry signal"}
        ],
        "contradicting": [
          {"date": "2026-03-07", "detail": "ST某某 +8% in 5 days, outperformed market"}
        ]
      },
      "sampleSize": 2,
      "hitRate": 0.50,
      "confidence": 0.50,
      "tags": ["entry-filter", "stock-selection"],
      "parentRule": null,
      "retiredDate": null,
      "retiredReason": null
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Auto-incrementing h001, h002, etc. |
| `text` | string | Human-readable description |
| `type` | enum | `heuristic` (probabilistic filter), `signal` (market condition), `rule` (hard constraint), `observation` (raw pattern) |
| `status` | enum | `observation` → `hypothesis` → `validated` → `rule` / `retired` |
| `evidence.supporting` | array | Cases where the hypothesis held |
| `evidence.contradicting` | array | Cases where it didn't |
| `sampleSize` | int | Total evidence count (supporting + contradicting) |
| `hitRate` | float | supporting / sampleSize |
| `confidence` | float | Bayesian-ish: starts at 0.5, moves toward 0 or 1 with evidence |
| `tags` | array | Categories for filtering (entry-filter, exit-rule, sector, timing, etc.) |
| `parentRule` | string | Links to V2 rule it modifies (e.g., "rule5-time-stop") |

### Status Lifecycle

```
observation (1 data point, raw pattern)
    → hypothesis (2+ data points, proposed mechanism)
        → validated (5+ data points, hitRate > 0.65)
            → rule (10+ data points, hitRate > 0.75, promoted to ANALYST.md)
        → retired (hitRate < 0.40 after 5+ samples, OR stale > 30 days with no new evidence)
```

### How It Integrates

1. **Daily pipeline (run_daily.py)**:
   - Phase 2 (prompt building): Include only `validated` + `rule` hypotheses in the analyst prompt. `observation` and `hypothesis` are tracked but not shown to analyst.
   - Phase 3 (apply): LLM returns `new_learnings` → `_append_learnings()` is replaced by `_process_learnings()` which:
     a. Checks if the learning matches an existing hypothesis (fuzzy match by tags + keywords)
     b. If match: adds evidence (supporting or contradicting), recalculates hitRate/confidence
     c. If new: creates as `observation` (status), auto-promotes to `hypothesis` if analyst provides mechanism
     d. Auto-promotes/demotes based on thresholds

2. **Analyst prompt (ANALYST.md output format)**:
   - `new_learnings` field changes to:
   ```json
   "new_learnings": [
     {
       "text": "Breadth <0.5:1 is a no-entry signal",
       "type": "signal",
       "tags": ["entry-filter", "market-regime"],
       "evidence_type": "supporting",
       "related_hypothesis": "h003",
       "mechanism": "When 70%+ of stocks fall, even strong setups get dragged down by selling pressure"
     }
   ]
   ```

3. **Prompt injection**: Instead of dumping 200 lines of LEARNINGS.md, the prompt gets:
   ```
   ## Active Rules (validated, hitRate > 75%)
   - [h003] Breadth <0.5:1 = no new entries (hitRate: 83%, n=12)
   - [h007] -5% stop is non-negotiable (hitRate: 90%, n=10)

   ## Working Hypotheses (testing, hitRate > 50%)  
   - [h012] IV Rank <15% = reduce sizing 50% (hitRate: 67%, n=3)
   - [h015] Sector cold 3+ days = SELL (hitRate: 60%, n=5)
   ```
   This is ~20 lines instead of 200, and each has a confidence score.

### Validation Engine: `scripts/hypothesis_manager.py`

Core functions:
- `load_hypotheses()` / `save_hypotheses()`
- `find_matching(text, tags)` → fuzzy match existing hypotheses
- `add_evidence(hypothesis_id, evidence_type, detail)` → update stats
- `create_hypothesis(text, type, tags, mechanism)` → new entry
- `promote_check(hypothesis)` → auto-promote if thresholds met
- `retire_check(hypothesis)` → auto-retire if hitRate drops or stale
- `get_active_for_prompt()` → returns only validated+rule status hypotheses, formatted for prompt
- `get_all_summary()` → full dashboard for human review

### Migration from LEARNINGS.md

One-time script to:
1. Parse existing LEARNINGS.md sections (策略教训, 待验证假设, etc.)
2. Create hypothesis entries with appropriate status based on existing labels
3. Existing "✅ 有效策略" → status: `validated`
4. Existing "❌ 失败教训" → status: `validated` (negative rule)
5. Existing "🔄 待验证假设" → status: `hypothesis`
6. Everything in "自动更新" → status: `observation`
7. Archive LEARNINGS.md → LEARNINGS.md.archive

### Testing Strategy

**Unit tests** (`scripts/test_hypothesis_manager.py`):
1. `test_create_hypothesis` — new hypothesis gets correct defaults
2. `test_add_supporting_evidence` — hitRate increases correctly
3. `test_add_contradicting_evidence` — hitRate decreases correctly
4. `test_auto_promote_to_hypothesis` — observation with 2+ evidence promotes
5. `test_auto_promote_to_validated` — hypothesis with 5+ evidence and hitRate >0.65 promotes
6. `test_auto_promote_to_rule` — validated with 10+ evidence and hitRate >0.75 promotes
7. `test_auto_retire_low_hitrate` — hypothesis with hitRate <0.40 after 5+ samples retires
8. `test_auto_retire_stale` — no new evidence in 30 days → retires
9. `test_fuzzy_match` — "avoid ST stocks" matches "ST stocks tend to underperform"
10. `test_no_false_match` — unrelated learnings don't match
11. `test_get_active_for_prompt` — only returns validated + rule, formatted correctly
12. `test_contradicting_evidence_weakens` — adding contradicting evidence can demote rule → validated → hypothesis
13. `test_confidence_bounds` — confidence stays in [0, 1]
14. `test_duplicate_evidence_ignored` — same date+detail doesn't double-count

**Integration tests**:
15. `test_process_learnings_new` — `_process_learnings()` with novel learning creates observation
16. `test_process_learnings_existing` — learning matching existing hypothesis adds evidence
17. `test_prompt_injection` — prompt builder uses hypothesis manager, output is compact
18. `test_migration` — LEARNINGS.md migration produces correct hypothesis entries
19. `test_full_cycle` — observation → hypothesis → validated → rule lifecycle

**Simulation test** (using historical data):
20. `test_historical_replay` — replay all `new_learnings` from runs/2026-*/response.json through the hypothesis manager. Verify: no crashes, reasonable hitRates, duplicates handled, final state is sensible.
