# Decisions

**D1 — compare headings, H2 and deeper only.** The H1 title carries the rating (评级 x/5), which a revision may change, and some drafts have a stray "# 报告". Section headings are stable across a numbers-only revision.

**D2 — structure check plus stop reason, not either alone.** finish_reason catches a cut inside the last section (no heading lost); the heading check catches a cut when the provider reports nothing (and the final draft-vs-published comparison catches anything the per-step guards miss).

**D3 — `meta=` out-parameter, not a 5-tuple return.** The tool loops are shared with the daily pipeline; changing their return shape would touch every caller. The daily pipeline gets only the new WARNING line.

**D4 — cut-off draft: re-ask, then refuse.** Same doctrine as the 2026-08-07 stub guard: an old complete report is better than a new incomplete one. Rejected: publish with a banner (strip_preamble would also drop a banner placed before the H1).

**D5 — revision rejected twice: keep the prior text.** Its failed numbers then go through cleanup + the mechanical guard, which already exist for this case.

**D6 — MAX_TOKENS 16384 → 65536 (owner, 2026-10-13).** = llm_client.MAX_OUTPUT_TOKENS, the probed DeepSeek ceiling. The 688018 re-run hit 16384 on the Claude draft AND the DeepSeek cleanup. A cap truncates, it does not reserve; billing follows tokens generated.

**D7 — anthropic calls always stream.** anthropic 0.84 raises ValueError for a non-streaming request above ~21k max_tokens (10-minute guard) before any network I/O — so the daily pipeline's `--llm-provider anthropic` path (already at 65536) was broken too, unnoticed because the daily run uses openai. `messages.stream(...).get_final_message()` returns the same Message. Live-probed through the relay: tool call round-trip OK, stop_reason end_turn. Always, not above a threshold: one path, no hidden switch.

**D8 — cleanup timeout 900s, judge keeps 120s.** The cleanup is one non-streaming DeepSeek call that re-emits the report; at the old cap it was cut off inside 120s. At 65536 it can run for minutes; three timeouts would crash verify into the UNVERIFIED fallback.

**Not done — bear pass truncation.** Its loop now prints the WARNING; the brief is not re-asked.
