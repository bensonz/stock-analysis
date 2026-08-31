# Fix: `_parse_json_from_text` must prefer a JSON object (dict), not the first block

## Problem

On 2026-06-04 the daily pipeline **failed at Gate 2** ("LLM response is empty or not a dict") even though DeepSeek V4 Pro produced a complete, correct analysis.

Root cause: `_parse_json_from_text(text)` in `scripts/llm_client.py` returns the **first** ```` ```json ```` fenced block it can parse. DeepSeek V4 Pro tends to emit **multiple** fenced JSON blocks in one response (e.g. a `learnings` **array** in one block and the main decision **object** in another). The function grabbed the array (`[...]`), returned a `list`, and Gate 2 rejected it because it expects a `dict`.

GPT-5.4 never triggered this because it returned a single clean object. This is a DeepSeek output-format quirk we must tolerate.

Evidence: `runs/2026-06-04/gpt_response.txt` contains the full valid decision object (ends with `"market_call": "防御"`), but `runs/2026-06-04/response.json` / `response_gpt.json` contain only the `learnings` array.

## Required change

Edit `_parse_json_from_text` in `scripts/llm_client.py` so it:

1. **Prefers a JSON object (dict).** When scanning candidates (direct parse, all ```` ```json ```` blocks, and brace-matched substrings), collect every successfully-parsed JSON value, then **return the first one that is a `dict`**. Only fall back to a non-dict (e.g. list) if no dict was found AND the caller can handle it — but since all callers expect a dict, returning `{}` when no dict is found is acceptable and preferable to returning a list.
2. **Tries ALL ```` ```json ```` blocks**, not just the first parseable one — keep going until a dict is found.
3. **Also brace-matches for objects across the whole text** as a final fallback (the existing brace-matching loop already finds `{...}` objects — make sure it runs even if an array was parsed earlier, and that it's reached when fenced blocks only yielded arrays).
4. Keep the existing behaviour for the normal single-object case (no regression for GPT-5.4 outputs).

Suggested shape (implementer may adjust):
```python
def _parse_json_from_text(text: str) -> dict:
    """Extract a JSON OBJECT (dict) from LLM response text.

    LLMs (esp. DeepSeek V4 Pro) may emit multiple fenced JSON blocks,
    e.g. a learnings array AND the decision object. We must return the
    dict, not whichever block appears first.
    """
    candidates = []

    # 1. Direct parse
    try:
        candidates.append(json.loads(text))
    except (json.JSONDecodeError, TypeError):
        pass

    if text:
        # 2. All ```json fenced blocks
        for block in re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL):
            try:
                candidates.append(json.loads(block.strip()))
            except json.JSONDecodeError:
                continue

        # 3. Brace-matched objects across whole text
        brace_count = 0
        start = None
        for i, ch in enumerate(text):
            if ch == "{":
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0 and start is not None:
                    try:
                        candidates.append(json.loads(text[start:i + 1]))
                    except json.JSONDecodeError:
                        pass
                    start = None

    # Prefer the first dict
    for c in candidates:
        if isinstance(c, dict):
            return c
    return {}
```

Note: the fenced-block regex is loosened to `` ```(?:json)? `` so blocks fenced as plain ```` ``` ```` (no `json` tag) are also caught — DeepSeek sometimes omits the language tag.

## Tests

Add to `scripts/test_llm_client.py`:
- A response with a `learnings` **array** fenced block FOLLOWED by a decision **object** fenced block → returns the object (dict with expected keys).
- A response with the object block FIRST, array second → still returns the object.
- Plain single-object response (GPT-style) → unchanged behaviour.
- Object fenced with ```` ``` ```` (no `json` tag) → parsed.
- No valid dict anywhere → returns `{}`.

## Acceptance

- `.venv/bin/python -m pytest scripts/test_llm_client.py -q` passes (existing 7 + new cases).
- Re-running analysis on the 2026-06-04 captured response (`runs/2026-06-04/gpt_response.txt`) parses into the decision dict (not the learnings array), i.e. Gate 2 would pass.
- No regression for single-object (GPT) responses.

## When done
Append a Done section (summary, files, test counts) and move this file to `docs/prompts/done/`.
