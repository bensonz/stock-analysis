#!/usr/bin/env python3
"""
event_triage.py — the LLM half of the event inbox's AI triage.

Owner decision 2026-10-12: "AI decides, owner can overrule." The owner should
not have to open tracking/calendar/event_inbox.md. So each NEW undecided candidate gets
one judgement — keep/skip, impact, direction, a one-line reason — from the
pipeline's configured model, and event_inbox.triage() applies it at once.

This module only builds the prompt (agents/EVENT_TRIAGE.md + the data), makes
ONE small call with no tools through llm_client's provider config, and pulls
the `decisions` object out of the reply. It writes nothing; every state change
and every per-item validity check lives in event_inbox.triage(). Rules and
limits: docs/EVENT_INBOX/DECISIONS.md D12–D19.
"""
import sys
from datetime import date as _date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import llm_client  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "agents" / "EVENT_TRIAGE.md"

#: a judgement per row is ~60 output tokens, but a reasoning model bills its
#: thinking against the same ceiling: the first live call (22 rows, DeepSeek
#: V4 Pro) used 15185 of 16384. The cap truncates, it does not reserve, so
#: take llm_client's endpoint ceiling — a truncated reply would fail and be
#: retried with the same rows every run.
MAX_OUTPUT_TOKENS = llm_client.MAX_OUTPUT_TOKENS
TEMPERATURE = 0.0
#: httpx's per-read timeout. It does NOT bound the call: the first live call
#: ran ~295 s against 180 (the endpoint keeps the connection alive while it
#: thinks). event_inbox.triage() bounds the wall time instead.
CALL_TIMEOUT_SEC = 180
#: Owner 2026-10-13: triage is a simple sort, and a missed or extra event is
#: cheap, so DeepSeek thinking is OFF (the first call, with it on, took ~295 s).
#: DeepSeek's documented switch; sent only to deepseek-* models, because other
#: OpenAI-compatible endpoints may reject an unknown body field.
DEEPSEEK_EXTRA_BODY = {"thinking": {"type": "disabled"}}

_WEEKDAY_ZH = "一二三四五六日"


def _cell(s) -> str:
    return str(s).replace("|", "/").replace("\n", " ").strip()


def build_prompt(today: _date, candidates: list, calendar: list,
                 spec_path: Path = SPEC_FILE) -> str:
    """Spec + today + what the calendar already holds + the candidate table.

    candidates: dicts with id, impact_date, region, name, importance, beijing_time.
    calendar:   dicts with impact_date (or None for ongoing), name, impact.
    """
    L = [spec_path.read_text(encoding="utf-8").rstrip(), "",
         "## Today", "",
         f"{today.isoformat()} (星期{_WEEKDAY_ZH[today.weekday()]})", "",
         "## Already on the calendar", "",
         "A股影响日 · 名称 · impact. Do not keep a candidate that duplicates one of these.", ""]
    if not calendar:
        L.append("（空）")
    for c in calendar:
        L.append(f"- {c.get('impact_date') or '持续中'} · {_cell(c.get('name', ''))} "
                 f"· {c.get('impact', '?')}")
    L += ["", f"## Candidates ({len(candidates)})", "",
          "| id | A股影响日 | 地区 | 名称 | 华尔街见闻重要性 | 北京时间 |",
          "|---|---|---|---|---|---|"]
    for c in candidates:
        L.append(f"| {c['id']} | {c['impact_date']} | {_cell(c['region'])} | "
                 f"{_cell(c['name'])} | {c['importance']} | {c['beijing_time']} |")
    return "\n".join(L) + "\n"


def call_model(prompt: str) -> tuple[str, dict]:
    """One no-tools call on the pipeline's provider. Raises on any failure.

    `openai` and `hybrid` both use the OpenAI-compatible model — in hybrid
    mode that model makes the final decision too; `anthropic` uses Claude.
    """
    provider = llm_client.normalize_llm_provider()
    messages = [{"role": "user", "content": prompt}]
    if provider == "anthropic":
        client = llm_client._build_anthropic_client()
        model = llm_client.DEFAULT_MODEL
        text, tin, tout, _ = llm_client._run_anthropic_text_once(
            client, messages, model, MAX_OUTPUT_TOKENS, TEMPERATURE,
            label="[event-triage] ")
        finish = None
    else:
        client = llm_client._build_openai_client()
        model = llm_client.OPENAI_MODEL
        extra = ({"extra_body": DEEPSEEK_EXTRA_BODY}
                 if model.lower().startswith("deepseek") else {})
        resp = client.chat.completions.create(
            model=model, messages=messages, max_tokens=MAX_OUTPUT_TOKENS,
            temperature=TEMPERATURE, timeout=CALL_TIMEOUT_SEC, **extra)
        choice = resp.choices[0]
        text = choice.message.content or ""
        usage = resp.usage
        tin = getattr(usage, "prompt_tokens", 0) or 0
        tout = getattr(usage, "completion_tokens", 0) or 0
        finish = getattr(choice, "finish_reason", None)
    if finish == "length":
        raise RuntimeError(f"reply truncated at max_tokens={MAX_OUTPUT_TOKENS}")
    return text, {"provider": provider, "model": model,
                  "tokens_in": tin, "tokens_out": tout}


def extract(text: str) -> dict:
    """The reply's `decisions` object, keyed by inbox id. Raises if absent."""
    doc = llm_client._parse_json_from_text(text or "")
    decisions = doc.get("decisions")
    if not isinstance(decisions, dict):
        raise ValueError(f"reply has no `decisions` object ({len(text or '')} chars)")
    return decisions
