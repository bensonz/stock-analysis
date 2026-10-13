# Deep report: detect and reject cut-off rewrites

Trigger (2026-10-13): `reports/688018-乐鑫科技/688018-2026-10-13-deep.md` ends
mid-sentence ("筹码与内部人：近 6 月") with no §3 关键日期 / §4 风险提示, yet
its footer says 76/76 verified. The round-1 draft (claims up to char ~11.1k)
had both sections, including the bear brief's #1 risk (301/232 tariffs); the
round-1 revision came back at ~6.7k. Three layers let it through:
1. tool loops treated "no tool calls" as "done" and ignored finish_reason;
2. the revise guard rejected only < 40% of the prior text;
3. the verifier checks numbers in the text that exists — it cannot see gaps.

## Stage 1: Stop reason out of the tool loops
**Goal**: `_run_tool_loop` / `_run_openai_tool_loop` take `meta=`; record `stop_reason`, `truncated`; always warn on truncation
**Tests**: 4 in `scripts/test_llm_client.py`
**Status**: Complete

## Stage 2: Rewrite guard in deep_verify
**Goal**: `rewrite_rejection(before, after, stop)` — empty / cut off / < 40% / lost H2+ section; revise retried once then prior text kept; cleanup rejected → mechanical guard only; final text vs draft → `final.lost_sections` + 报告不完整 banner
**Tests**: 7 in `scripts/test_deep_verify.py`
**Status**: Complete

## Stage 3: Wire into deep_report
**Goal**: revise/cleanup runners return the stop reason; a cut-off first draft is re-asked with a "compress, finish all sections" nudge, refused if still cut off
**Tests**: 5 in `scripts/test_deep_report.py`
**Status**: Complete

## Stage 4: Re-run 688018
**Pass criteria**: report has §3 关键日期 and §4 风险提示; tariff risk present; `final.lost_sections == []`; any rejected rewrite visible in the audit
**Status**: In Progress
