# Docs Staleness Audit — 2026-08-31

*Verbatim report from the read-only docs survey agent. 79 hand-written
markdown files audited: 12 STALE (actively misleading), 26 DEAD
(finished/abandoned, zero inbound refs), rest CURRENT or CURRENT-as-record.*

## Two findings that matter most (both in files the running system reads)

1. **agents/ANALYST.md contradicts itself about the time stop TWO LINES APART.**
   - `:111` "Time stop: 15 trading days with <3% gain"
   - `:112` "If the event hasn't moved the stock in 10 days, your timing is wrong"
   - `:197` "| 20-day time stop with exceptions | 10-day time stop, no exceptions |"
   - `:271` "days_held is mandatory — triggers time stop check at 10 days"

   Ground truth: `scripts/rules/check_time_decay.py:80` THRESHOLD_DAYS = 15,
   `:81` MIN_GAIN_PCT = 3.0. The 2026-08-17 10d→15d change was applied to
   Rule 5 only. Same missed edit in `agents/WEEKLY_AUDIT.md:143`,
   `agents/TRACKER.md:39`, `docs/backtest/RESULTS.md:6`. This is the LIVE
   system prompt (`run_daily.py:1393`, `llm_client.py:1147`) — the model
   reads all four lines every run.

2. **TRACKER_SCHEMA.md no longer describes the files it claims to**
   (CLAUDE.md points at it as THE schema):
   - documents `capital`/`capitalPct`; real fields are
     `allocatedCapital`/`allocation_pct`
   - documents trackerVersion "1.0"; `position_manager.py:593` writes "2.1"
   - Action table lists ADD/PARTIAL_EXIT/EXIT; real vocabulary across 423
     history entries is OPEN(64)/HOLD(267)/RAISE_STOP(31)/SELL(61). ADD and
     PARTIAL_EXIT never occur; EXIT is never written.
   - exitReason enum: ZERO of 61 closed positions conform — it is free-text
     LLM prose.
   - omits entrySlot, sourceWatchlist, the 2a-i history widening, the `slot`
     field, and the entire positions.json aggregate file.

## Verdict table (path | verdict | evidence)

### Root / live state

| path | verdict | evidence |
|---|---|---|
| README.md | STALE | `:34` "查看 reports/ 目录获取每日分析报告" — reports/ holds per-stock DEEP reports; daily output is runs/<date>/<slot>/output/report.md + site/index.html |
| CLAUDE.md | STALE (1 line) | `:7` "~15:35 afternoon"; the plist schedules 15:05 |
| TRACKER_SCHEMA.md | STALE (heavy) | see finding 2 |
| tracking/README.md | STALE (minor) | `:10` "Updated daily by tracker subagent" — no such subagent; position_manager.py writes these |
| LEARNINGS.md | CURRENT | 262KB prompt corpus, read every run at run_daily.py:394 |

### agents/ (live prompt specs)

| path | verdict | evidence |
|---|---|---|
| ANALYST.md | STALE | time stop (above); `:102` "Maximum 8 positions, minimum 20% cash" vs portfolio_config max_positions:10 min_cash_pct:0; duplicate "Rule 2c" heading at `:62` and `:70` |
| DEEP_REPORT.md | CURRENT | every tool/field verified vs scripts/research/deep_report.py |
| DEEP_VERIFY.md | CURRENT | output schema matches deep_verify.py:391-399,430 |
| WEEKLY_AUDIT.md | STALE | `:143` "10-day time stops"; `:29` `runs/$d/output/report.md` missing <slot> — with 2>/dev/null it SILENTLY prints nothing for every run since 2026-07, so "THIS WEEK'S RUNS" is guaranteed empty; `:39` reads empty watchlist/ |
| EVOLVER.md | STALE/orphaned | `:30` tracking/daily/ and `:39` watchlist/ are empty dirs; weekly cron gone. Rule-engine contract `:55-68` is exactly right |
| TRACKER.md | STALE/orphaned | `:39` ">20 days with <5% gain" (real 15d/<3%); `:179-180` regenerates positions.json WITHOUT the portfolio block — running it as written destroys totalEquity/realizedPnl/positionsUsed; `:89`/`:208` put 创业板 in the 10% limit bucket (it's 20%), BJ at 20% (it's 30%) |
| DAILY_AUDIT.md | DEAD | superseded by scripts/doctor.py which never reads it; every runs/ path omits <slot>; `:13` sorts slots alphabetically which run_paths.py:21 forbids |
| RESEARCHER.md | DEAD | browser-scrape role never built; strategy id 352390 vs live 407228; profile "openclaw" — no Playwright anywhere; writes to empty/nonexistent dirs |
| ORCHESTRATOR.md | DEAD | "3-agent system" replaced by one Python pipeline; logs/ referenced 8× and does not exist; sessions_spawn: API appears nowhere in repo; File Structure omits runs/ entirely |

Orphan census (grep across scripts/, *.sh, ops/launchd/): only ANALYST.md,
DEEP_REPORT.md, DEEP_VERIFY.md are loaded by code. TRACKER / RESEARCHER /
ORCHESTRATOR / DAILY_AUDIT have ZERO code refs; WEEKLY_AUDIT is run by hand.

### audit/

| path | verdict | evidence |
|---|---|---|
| OPEN.md | CURRENT (generated) | header confirms "由 scripts/doctor.py --open 生成, 不要手改" |
| ACCEPTED.md | CURRENT | 11 accepted instance ids all real |

### docs/ active

| path | verdict | evidence |
|---|---|---|
| RUNBOOK.md | CURRENT | schedule verified vs both plists; post-move paths correct |
| HARNESS/IMPLEMENTATION_PLAN.md | STALE | `:91` Stage 2 "Not Started" — doctor SHIPPED 08-22; `:135` Stage 4 "Not Started" — launchd shipped; `:138` Stage 5 targets a layout the owner overruled |
| HARNESS/TODO.md | CURRENT | genuinely open work |
| HARNESS/PROGRESS.md | CURRENT-as-record | |
| HARNESS/DECISIONS.md | CURRENT | D1–D12 rationale |
| HARNESS/CHECKLIST.md | CURRENT, UNVERIFIED | `:17` "7 known pre-existing failures" — not re-counted by this agent; verified separately by the coordinator (7 failed / 759 passed at the time) |
| audits/CANDIDATE_ALPHA.md | CURRENT | reproduce path post-move |
| audits/EXIT_ABLATION.md | CURRENT | post-move path; cited 4× from code |
| audits/WEEKLY_2026-08-16.md | CURRENT-as-record | commands reference pre-move paths (records; leave) |
| audits/WEEKLY_AUDIT_2026-08-02/08.md | CURRENT-as-record | same |
| WORKLOG_2026-07-27_to_07-31.md | CURRENT-as-record | same |
| gex_audition/RESULTS.md | CURRENT | reproducible via research/ path |
| pricedb_adjustment/IMPACT.md | CURRENT | cited from price_adjust.py:21 |
| tracking_fixes/CLOSED_OVERWRITE_RECOVERY_2026-08-06.md | CURRENT | sole explanation of an equity-curve discontinuity |
| IFIND_EVAL/* | CURRENT | the three silent-failure traps CLAUDE.md cites are present and correct |
| harness-engineering.md | CURRENT (canonical) | NOT a duplicate of the done/ copy (zero shared lines) |
| design/hypothesis-system.md | STALE (one section) | migration step 7 "Archive LEARNINGS.md" never happened; 154/180 hypotheses still status=observation |
| backtest/RESULTS.md | STALE — KEEP (5 inbound refs) | `:6` "defaults are now 10/3.0" — code reads 15/3.0 |
| pricedb_repair/PROGRESS.md | STALE — KEEP (cited from providers.py:287) | `:74` "akshare primary" superseded 08-25; APPEND a supersession line, do not rewrite |
| pricedb_intraday_coverage/FINDINGS.md | STALE | "in progress"/"TODO" items landed |
| deep_report_verify/IMPLEMENTATION_PLAN.md | STALE | `:47` "In Progress" contradicted by `:68` "Complete" for the SAME stage |
| tracking/PROGRESS.md | STALE (abandoned) | newest entry 2026-07-08; says 15:35; pre-move paths |
| prompts/fix-gate2-parser-picks-wrong-json-block.md | STALE (partly done) | prefer-dict landed; key-based scoring did NOT — run_daily.py:2757-2766 still returns the FIRST dict block |
| prompts/fix-llm-response-json-extraction.md | STALE (mostly done) | bare-list guard landed; shape-based selection absent |

### DEAD (0 inbound refs each, grep-proven)

- docs/TODO.md, docs/CHECKLIST.md, docs/IMPLEMENTATION_PLAN.md — all stages
  Complete, all items shipped (docs/DECISIONS.md is the keeper of the three)
- docs/rps-sparse-window-guard/ (5 files) — Complete; code live
- docs/run-artifact-observability/ (5 files) — Complete; "No open TODOs"
- docs/codex/eastmoney-direct-pricedb/IMPLEMENTATION_PLAN.md — Complete AND
  INVERTED: instructs eastmoney-before-AkShare vs providers.py "remain
  RETIRED — do not re-add". **Highest-risk dead file**: a reader finding it
  first would implement what the codebase forbids.
- docs/codex/akshare-pricedb-provider/IMPLEMENTATION_PLAN.md — Complete; premise retired
- docs/WORKFLOW-REDESIGN.md — fully superseded by CLAUDE.md
- docs/prompts/debate-enhancement-plan.md — NEVER BUILT (0 of 5 files exist)
- docs/prompts/multi-agent-investment-committee.md — NEVER BUILT (0 of 4)
- docs/prompts/breadth-aware-entry-gate.md — never acted on; its own line
  pointers are wrong
- docs/prompts/local-price-db-ma-rps.md — DONE → became scripts/pricedb/;
  eastmoney mandate now a grep hazard
- docs/prompts/fix-deepseek-json-parse-prefer-object.md — DONE → done/
- docs/prompts/fix-phase3-open-position-validation.md — DONE → done/
- docs/prompts/split-run-outputs-and-block-same-day-sell.md — DONE, better than specced
- docs/prompts/options-scan-db-arg-swap-fix.md + done/options-scan-latency-fix.md
  — FOREIGN WORK ORDERS for /opt/options-learn; this repo only consumes it over HTTP
- docs/backtest/IMPLEMENTATION_PLAN.md — 1a-1c Complete; fold D1–D5 rationale
  into RESULTS.md before deleting

## Safe to fix mechanically

- CLAUDE.md:7 15:35→15:05 (same at docs/tracking/PROGRESS.md:5)
- ANALYST.md:112,197,271 10→15 days; WEEKLY_AUDIT.md:143; TRACKER.md:39;
  backtest/RESULTS.md:6
- WEEKLY_AUDIT.md:29 + DAILY_AUDIT.md paths — insert missing <slot>
- HARNESS/IMPLEMENTATION_PLAN.md status lines; deep_report_verify plan `:47`
- pricedb_repair/PROGRESS.md:74 — append supersession line only
- pricedb_intraday_coverage/FINDINGS.md — mark landed
- README.md:34; tracking/README.md:9-10
- DELETE the 10 fully-closed plan files

## Needs a human / strategy decision

1. ANALYST.md:102 8-pos/20%-cash vs config 10/0 — model receives both numbers
2. TRACKER_SCHEMA.md rewrite vs delete; exitReason enum vs free-text is the
   sharpest question
3. The four orphaned agents/*.md — executable-looking wrong instructions
   beside the live prompt
4. eastmoney codex plan — delete or stamp SUPERSEDED
5. The two foreign options-scan files — move to options-learn or delete
6. hypothesis-system.md's unfinished migration — finish or amend
7. HARNESS/CHECKLIST.md:17 failure count — re-count in clean worktree
   (closed by coordinator: still 7 at audit time)
