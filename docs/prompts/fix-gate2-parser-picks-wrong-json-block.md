# Fix: Gate 2 fails midday — `_parse_llm_response` picks the wrong JSON block

## Symptom
The 11:35 (midday) pipeline run fails at Gate 2 three days running (2026-06-17/18/19) with
varying errors, while the 15:35 (post-market) run succeeds every time:

- 2026-06-17: `LLM response is empty or not a dict`
- 2026-06-18: `LLM response is empty or not a dict` (response.json was a JSON **array** of observations)
- 2026-06-19: `no decision for active position(s): {688401, 002436, 300037, 300236, 002947}`
  + soft warns `missing market_summary`, `missing watchlist`

In every failed case the LLM **did** produce a complete, correct analysis
(see `runs/<date>/gpt_response.txt`, 20KB+ memo). The data is good; only the
**extracted JSON object is wrong**.

## Root cause (confirmed)
`scripts/run_daily.py` → `_parse_llm_response(text)` (around line 2016) returns the
**first** JSON value it can parse from the model's text:

1. tries `json.loads(text)` whole,
2. else returns the **first** ```json fenced block,
3. else returns the **first** balanced `{...}` object.

The DeepSeek prompt asks the model to emit BOTH:
- a **hypothesis/observation** JSON object/array (keys: `text`, `type`, `tags`,
  `evidence_type`, `related_hypothesis`, `mechanism`), and
- the **main decision** JSON object (keys include `positions`/per-holding decisions,
  `market_summary`, `watchlist`).

On midday runs the model frequently emits the hypothesis block **first**. The parser
grabs that fragment and returns it, so Gate 2 sees an object with no position decisions
(or a list) and fails. Post-market runs happen to emit the decision block first → pass.

Evidence: `runs/2026-06-19/response.json` =
`{"text","type","tags","evidence_type","related_hypothesis","mechanism"}` — that's the
hypothesis fragment, not the decision object.

## Required fix (parser should select the DECISION object, not "first block")
In `_parse_llm_response`, instead of returning the first parseable JSON:

1. Collect **all** candidate JSON values (whole-text, every ```json block, and every
   top-level balanced `{...}` / `[...]`).
2. Score each candidate and return the one that looks like the **decision object**:
   - must be a `dict`
   - prefer one containing any of these keys: `positions`, `market_summary`, `watchlist`,
     or per-position decision keys (whatever the schema in `contracts.py`
     `validate_llm_output_gate` expects — align with it).
   - explicitly **reject** hypothesis/observation fragments: a dict whose keys are a
     subset of `{text, type, tags, evidence_type, related_hypothesis, mechanism}`.
3. If multiple decision-shaped candidates exist, prefer the **last** one (the model
   tends to put final answer last) — but key-match should win over position.
4. If none match, return `{}` (existing behavior) so Gate 2 still fails loudly.

## Also (defense in depth — confirm against `contracts.py`)
- `validate_llm_output_gate` (contracts.py ~line 218) is the source of truth for the
  required decision schema. Make the parser's "is this the decision object?" check use
  the SAME key set so they can't drift.
- Consider tightening the **prompt** (`agents/ANALYST.md` / prompt builder) to emit the
  decision object in a single clearly-delimited fenced block, e.g. wrap it in
  ```json DECISION ... ``` or a sentinel, and have the parser prefer that block. This
  removes the ambiguity at the source. (Parser fix is still required as a safety net.)

## Tests to add
- Unit test `_parse_llm_response` with a fixture where a hypothesis block precedes the
  decision block → must return the decision block.
- Fixture where output is a bare observation array → must NOT be returned as decision;
  parser returns `{}` (or the real decision block if present).
- Regression fixtures from `runs/2026-06-17/`, `2026-06-18/`, `2026-06-19/`
  `gpt_response.txt` → parser must extract a Gate-2-passing decision object (or, if the
  decision block is genuinely absent in that raw text, document that and the prompt fix
  becomes mandatory).

## Do NOT
- Do not hand-edit any `runs/<date>/` outputs or apply these failed days retroactively
  unless Benson asks.
- Keep failure loud: if no decision object is found, Gate 2 should still hard-fail.

## Acceptance
- Re-running the three failed days' raw responses through the patched parser yields a
  decision dict that passes `validate_llm_output_gate`.
- New unit tests pass.
- No change to position-application logic; only parsing/selection + (optional) prompt.
