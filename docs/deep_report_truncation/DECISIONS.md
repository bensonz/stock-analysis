# Decisions

**D1 — compare headings, H2 and deeper only.** The H1 title carries the rating (评级 x/5), which a revision may change, and some drafts have a stray "# 报告". Section headings are stable across a numbers-only revision.

**D2 — structure check plus stop reason, not either alone.** finish_reason catches a cut inside the last section (no heading lost); the heading check catches a cut when the provider reports nothing (and the final draft-vs-published comparison catches anything the per-step guards miss).

**D3 — `meta=` out-parameter, not a 5-tuple return.** The tool loops are shared with the daily pipeline; changing their return shape would touch every caller. The daily pipeline gets only the new WARNING line.

**D4 — cut-off draft: re-ask, then refuse.** Same doctrine as the 2026-08-07 stub guard: an old complete report is better than a new incomplete one. Rejected: publish with a banner (strip_preamble would also drop a banner placed before the H1).

**D5 — revision rejected twice: keep the prior text.** Its failed numbers then go through cleanup + the mechanical guard, which already exist for this case.

**Not done — raising MAX_TOKENS (16384).** DeepSeek thinking spends from the same budget; the guards make a cut visible and recoverable, a bigger budget only makes it rarer. Revisit if `rejected_rewrites` shows up often.

**Not done — bear pass truncation.** Its loop now prints the WARNING; the brief is not re-asked.
