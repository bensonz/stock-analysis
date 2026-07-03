# Prompt: Fix LLM response JSON extraction (Gate 2 "empty or not a dict" false failure)

> **Repo:** `stock-analysis` (`/Users/bz/Work/Personal/stock-analysis`)
> **Files:** `scripts/llm_client.py` (response extraction) and/or `scripts/run_daily.py` (Gate 2 validation + where `response.json` is written). Find the exact extractor that writes `runs/<date>/response.json`.
> **Severity:** MEDIUM — silent latent bug. Today (2026-07-02) it caused a false Gate-2 FAILED, but the analysis conclusion was "100% cash / hard-blocked" so nothing was lost. On a day with real actions (buys/sells/stops), this same bug would drop the entire decision set.

## Root cause (verified from 2026-07-02 15:35 run)

The analyst returned a **markdown research memo** (prose + tables), NOT a bare JSON object. Inside it were **two** fenced code blocks:
1. A ```` ```json ```` block containing the **decisions object** (`{ "new_positions": [...], "position_actions": [...], "market_sentiment": ..., "market_call": ... }`)
2. A second ```` ```json ```` block (or trailing array) containing the **learnings array** (`[ {...}, {...} ]`)

Evidence:
- `runs/2026-07-02/gpt_response.txt` starts with `## Research Memo — 2026-07-02` (markdown, not JSON)
- Contains 4 backtick-fences (= 2 code blocks)
- `runs/2026-07-02/response.json` parsed as a **`list`** (it captured the learnings array), not the decisions **`dict`**
- Gate 2 does `isinstance(response, dict)` → got a list → `"LLM response is empty or not a dict"` → hard FAIL

So the extractor grabbed the **wrong fenced block** (last one / the array), and Gate 2 rejected it.

## The fix

Make the response extractor robust to markdown-wrapped, multi-block responses. The extractor that produces `response.json` should:

1. **Prefer fenced JSON blocks:** scan for all ```` ```json ... ``` ```` (and bare ```` ``` ... ``` ````) blocks in the raw text.
2. **Select the correct block by shape, not position:** the decisions payload is a **JSON object (dict)** containing the expected keys (`new_positions`, `position_actions`, and/or `market_call`/`market_sentiment`). The learnings payload is a **JSON array**. Choose the **object that contains the decision keys** as the primary `response`, regardless of whether it's the first or last block.
3. **Route learnings separately:** if a second block is a JSON array (learnings), capture it into the learnings channel the apply-step expects (check how `_apply_learnings` currently receives learnings — today it may expect them inside the dict; preserve whatever contract exists, just don't let the array clobber the decisions dict).
4. **Fallback:** if no fenced block parses as a dict-with-decision-keys, attempt to locate the first balanced `{...}` object in the raw text that contains those keys (brace-matching), and parse that.
5. **Never write a bare list to `response.json`** as the decisions payload. If only an array is found, that's a real failure — fail Gate 2 with a clearer message (`"Extracted JSON was an array (likely learnings), no decisions object found"`).

## Also improve Gate 2 diagnostics

When Gate 2 fails, log: the type actually extracted (dict/list/None), the number of fenced blocks found, and the first 200 chars of `gpt_response.txt`. This would have made today's diagnosis instant.

## Acceptance criteria

- Feed the **actual `runs/2026-07-02/gpt_response.txt`** (markdown memo with 2 json blocks: decisions dict + learnings array) through the extractor → `response.json` is the **decisions dict**, Gate 2 **passes**, learnings are still captured.
- A response that is a **bare JSON object** (no markdown fence) still parses (don't regress the happy path).
- A response with **only** a learnings array and no decisions dict → Gate 2 fails with the new clearer message.
- Add a unit test using a fixture copied from `runs/2026-07-02/gpt_response.txt` (the real failing case) asserting the decisions dict is extracted.

## Note

Do NOT change the analyst's output format instructions to "just return JSON" as the fix — the markdown memo is useful and the analyst may keep producing it. Make the *parser* robust instead. (If you also want to tighten `ANALYST.md` to emit a single clearly-delimited decisions block, that's a complementary belt-and-suspenders improvement, but the parser must be the primary fix.)
