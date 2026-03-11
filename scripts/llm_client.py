#!/usr/bin/env python3
"""
llm_client.py — Sequential Claude→GPT collaboration pipeline.

Pass 1: Claude (full prompt + tools) → research memo + fallback JSON
Pass 2: GPT-5.4 (condensed prompt + Claude memo, no tools) → final JSON decisions

Tools: web_search (Tavily), web_fetch (direct HTTP) — Claude only
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import anthropic
import openai
import requests

# Load .env from project root (for TAVILY_API_KEY etc.)
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# --- Config ---

DEFAULT_MODEL = "claude-opus-4-6"
MAX_TOOL_ROUNDS = 15  # Safety cap on tool-use loops per pass
FETCH_TIMEOUT = 15  # seconds per web fetch
FETCH_MAX_CHARS = 8000  # max chars per fetch result

# --- Tools ---

TOOLS = [
    {
        "name": "web_fetch",
        "description": (
            "Fetch and extract readable content from a URL (HTML → text). "
            "Use for specific news articles, stock pages, financial portals. "
            "Returns extracted text content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "HTTP or HTTPS URL to fetch.",
                },
                "maxChars": {
                    "type": "integer",
                    "description": f"Maximum characters to return (default {FETCH_MAX_CHARS}).",
                    "default": FETCH_MAX_CHARS,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web via Tavily. Returns structured results with titles, URLs, and content snippets. "
            "Use for finding recent news, sector analysis, stock catalysts, macro events. "
            "Supports Chinese and English queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in Chinese or English.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (default 5, max 10).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
]


# --- Tool implementations ---

def _extract_text(html: str, max_chars: int) -> str:
    """Extract readable text from HTML. Simple but effective."""
    # Remove script/style
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Decode entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"')
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def execute_web_fetch(url: str, max_chars: int = FETCH_MAX_CHARS) -> str:
    """Fetch a URL and return extracted text."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or "utf-8"

        if resp.status_code != 200:
            return f"HTTP {resp.status_code}: {resp.reason}"

        return _extract_text(resp.text, max_chars)
    except requests.Timeout:
        return f"Timeout fetching {url} (>{FETCH_TIMEOUT}s)"
    except Exception as e:
        return f"Error fetching {url}: {e}"


def execute_web_search(query: str, max_results: int = 5) -> str:
    """Search via Tavily API. Returns structured results."""
    api_key = os.environ.get("TAVILY_API_KEYS") or os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return "Error: No Tavily API key. Set TAVILY_API_KEYS or TAVILY_API_KEY."

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": min(max_results, 10),
                "search_depth": "basic",
                "include_answer": True,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return f"Tavily HTTP {resp.status_code}: {resp.text[:200]}"

        data = resp.json()
        parts = []

        # Include Tavily's AI answer if available
        if data.get("answer"):
            parts.append(f"AI Summary: {data['answer']}\n")

        # Format results
        for i, r in enumerate(data.get("results", []), 1):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")[:500]
            parts.append(f"{i}. [{title}]({url})\n{content}\n")

        return "\n".join(parts) if parts else "No results found."
    except requests.Timeout:
        return "Tavily search timed out (>15s)"
    except Exception as e:
        return f"Tavily search error: {e}"


def execute_tool(name: str, input_data: dict) -> str:
    """Dispatch a tool call to its implementation."""
    if name == "web_fetch":
        return execute_web_fetch(
            url=input_data["url"],
            max_chars=input_data.get("maxChars", FETCH_MAX_CHARS),
        )
    elif name == "web_search":
        return execute_web_search(
            query=input_data["query"],
            max_results=input_data.get("max_results", 5),
        )
    else:
        return f"Unknown tool: {name}"


# --- LLM call with tool loop ---

def _run_tool_loop(
    client: anthropic.Anthropic,
    messages: list,
    model: str,
    max_tokens: int,
    temperature: float,
    tool_log: list,
    label: str = "",
) -> tuple[str, int, int, int]:
    """Run LLM with tool-use loop until final text response.

    Returns: (final_text, input_tokens, output_tokens, rounds)
    """
    total_input = 0
    total_output = 0

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        print(f"  {label}round {round_num}...", file=sys.stderr, end="", flush=True)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=TOOLS,
            messages=messages,
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_use_blocks:
            final_text = "\n".join(b.text for b in text_blocks)
            print(f" done ({total_input}+{total_output} tokens)", file=sys.stderr)
            # Append assistant response to messages for conversation continuity
            # Convert to dicts to avoid Pydantic serialization issues on re-send
            content_dicts = [b.model_dump() if hasattr(b, "model_dump") else b for b in response.content]
            messages.append({"role": "assistant", "content": content_dicts})
            return final_text, total_input, total_output, round_num

        # Execute tool calls
        # Convert to dicts to avoid Pydantic serialization issues on re-send
        content_dicts = [b.model_dump() if hasattr(b, "model_dump") else b for b in response.content]
        messages.append({"role": "assistant", "content": content_dicts})

        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input
            print(f" → {tool_name}({_summarize_input(tool_input)})", file=sys.stderr, end="", flush=True)

            result_text = execute_tool(tool_name, tool_input)
            tool_log.append({
                "pass": label.strip(),
                "round": round_num,
                "tool": tool_name,
                "input": tool_input,
                "result_length": len(result_text),
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_results})
        print("", file=sys.stderr)

    # Hit max rounds
    print(f"  WARNING: Hit max tool rounds ({MAX_TOOL_ROUNDS})", file=sys.stderr)
    final_text = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            if isinstance(msg["content"], list):
                for b in msg["content"]:
                    if hasattr(b, "text"):
                        final_text = b.text
                        break
            break
    return final_text, total_input, total_output, MAX_TOOL_ROUNDS


# --- OpenAI tool definitions (parallel to Anthropic TOOLS) ---

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch and extract readable content from a URL (HTML → text). "
                "Use for specific news articles, stock pages, financial portals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "HTTP or HTTPS URL to fetch."},
                    "maxChars": {"type": "integer", "description": f"Max chars to return (default {FETCH_MAX_CHARS})."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web via Tavily. Returns structured results with titles, URLs, and content snippets. "
                "Use for finding recent news, sector analysis, stock catalysts, macro events."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query in Chinese or English."},
                    "max_results": {"type": "integer", "description": "Number of results (default 5, max 10)."},
                },
                "required": ["query"],
            },
        },
    },
]


def _run_openai_tool_loop(
    client: openai.OpenAI,
    messages: list,
    model: str,
    max_tokens: int,
    temperature: float,
    tool_log: list,
    label: str = "",
) -> tuple[str, int, int, int]:
    """Run OpenAI LLM with tool-use loop until final text response.

    Returns: (final_text, input_tokens, output_tokens, rounds)
    """
    total_input = 0
    total_output = 0

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        print(f"  {label}round {round_num}...", file=sys.stderr, end="", flush=True)

        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=OPENAI_TOOLS,
            messages=messages,
        )

        choice = response.choices[0]
        usage = response.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
        total_input += usage.prompt_tokens
        total_output += usage.completion_tokens

        msg = choice.message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            # Final text response
            final_text = msg.content or ""
            print(f" done ({total_input}+{total_output} tokens)", file=sys.stderr)
            messages.append({"role": "assistant", "content": final_text})
            return final_text, total_input, total_output, round_num

        # Append assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        # Execute tool calls
        for tc in tool_calls:
            tool_name = tc.function.name
            try:
                tool_input = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_input = {}

            print(f" → {tool_name}({_summarize_input(tool_input)})", file=sys.stderr, end="", flush=True)

            result_text = execute_tool(tool_name, tool_input)
            tool_log.append({
                "pass": label.strip(),
                "round": round_num,
                "tool": tool_name,
                "input": tool_input,
                "result_length": len(result_text),
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text,
            })

        print("", file=sys.stderr)

    # Hit max rounds
    print(f"  WARNING: Hit max tool rounds ({MAX_TOOL_ROUNDS})", file=sys.stderr)
    # Return last assistant text
    for msg_item in reversed(messages):
        if msg_item.get("role") == "assistant" and msg_item.get("content"):
            return msg_item["content"], total_input, total_output, MAX_TOOL_ROUNDS
    return "", total_input, total_output, MAX_TOOL_ROUNDS


OPENAI_MODEL = "gpt-5.4"
GPT_TIMEOUT = 120  # seconds — no more hanging


def build_gpt_prompt(analyst_md: str, summary: str, claude_memo: str) -> str:
    """Build the condensed prompt for GPT's decision-making pass."""
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


def build_summary(phase1_data: dict) -> str:
    """Condense phase1 data (~250KB) into ~5-10KB for GPT."""
    sections = []

    # Portfolio snapshot
    pf = phase1_data.get("portfolio", {})
    if pf:
        sections.append(
            "## Portfolio Snapshot\n"
            f"- Equity: {pf.get('totalEquity', '?'):,} / Cash: {pf.get('cash', '?'):,} ({pf.get('cashPct', '?')}%)\n"
            f"- Positions: {pf.get('positionsUsed', 0)}/{pf.get('positionsMax', 10)}\n"
            f"- Unrealized P&L: {pf.get('unrealizedPnl', 0):,} | Realized: {pf.get('realizedPnl', 0):,}\n"
            f"- Total return: {pf.get('totalReturnPct', 0)}%"
        )

    # Market indices
    market = phase1_data.get("market", {})
    indices = market.get("indices", [])
    if indices:
        idx_lines = ["## Market Indices"]
        for idx in indices:
            name = idx.get("name", idx.get("code", "?"))
            idx_lines.append(f"- {name}: {idx.get('close', '?')} ({idx.get('change_pct', '?')}%)")
        sections.append("\n".join(idx_lines))

    # Breadth
    breadth = market.get("breadth", {})
    if breadth:
        up = breadth.get("up", 0)
        down = breadth.get("down", 0)
        ratio = f"{up/down:.1f}:1" if down > 0 else "N/A"
        sections.append(f"## Breadth\n- Up: {up} / Down: {down} / Ratio: {ratio}")

    # Top/bottom sectors
    sector_data = market.get("sectors", [])
    if sector_data:
        top = sector_data[:10]
        bottom = sector_data[-5:] if len(sector_data) > 10 else []
        lines = ["## Sectors (top 10)"]
        for s in top:
            lines.append(f"- {s.get('name', '?')}: {s.get('change_pct', '?')}%")
        if bottom:
            lines.append("\n**Bottom 5:**")
            for s in bottom:
                lines.append(f"- {s.get('name', '?')}: {s.get('change_pct', '?')}%")
        sections.append("\n".join(lines))

    # Strategy pool — compact table
    pool = phase1_data.get("strategy_pool", {}).get("stocks", [])
    if pool:
        lines = ["## Strategy Pool", "| Code | Name | Price | Chg% | RPS120 | Sector | PE |", "|---|---|---|---|---|---|---|"]
        for s in pool:
            lines.append(
                f"| {s.get('code', '?')} | {s.get('name', '?')} | {s.get('price', '?')} "
                f"| {s.get('change_pct', '?')} | {s.get('rps120', '?')} "
                f"| {s.get('sector', '?')} | {s.get('pe', '?')} |"
            )
        sections.append("\n".join(lines))

    # Enriched candidates summary
    enriched = phase1_data.get("enriched_candidates", [])
    if enriched:
        lines = ["## Enriched Candidates"]
        for c in enriched:
            lines.append(
                f"- **{c.get('code', '?')} {c.get('name', '?')}**: "
                f"RPS120={c.get('rps120', '?')}, sector={c.get('sector', '?')}, "
                f"PE={c.get('pe', '?')}, "
                f"dist_ma5={c.get('dist_ma5_pct', '?')}%, "
                f"dist_ma10={c.get('dist_ma10_pct', '?')}%, "
                f"dist_ma20={c.get('dist_ma20_pct', '?')}%"
            )
        sections.append("\n".join(lines))

    # Active positions
    positions = phase1_data.get("active_positions", [])
    if positions:
        lines = ["## Active Positions"]
        for p in positions:
            lines.append(
                f"- **{p.get('code', '?')} {p.get('name', '?')}**: "
                f"entry={p.get('entryPrice', '?')} on {p.get('entryDate', '?')}, "
                f"stop={p.get('stopLoss', '?')}, target={p.get('targetPrice', '?')}, "
                f"sector={p.get('sector', '?')}"
            )
        sections.append("\n".join(lines))

    # Position prices
    pos_prices = phase1_data.get("position_prices", {})
    if pos_prices:
        lines = ["## Position Prices (live)"]
        for code, info in pos_prices.items():
            if isinstance(info, dict):
                lines.append(f"- {code}: {info.get('current_price', '?')} ({info.get('change_pct', '?')}%)")
            else:
                lines.append(f"- {code}: {info}")
        sections.append("\n".join(lines))

    # IV Sentiment
    iv = phase1_data.get("iv_sentiment", {})
    if iv:
        lines = ["## IV Sentiment"]
        for k, v in iv.items():
            if isinstance(v, dict):
                lines.append(f"- {k}: IV={v.get('iv', '?')}, IVRank={v.get('iv_rank', '?')}%")
            else:
                lines.append(f"- {k}: {v}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16384,
    temperature: float = 0.3,
    output_dir: Path | None = None,
    phase1_data: dict | None = None,
) -> dict:
    """Sequential Claude→GPT pipeline.

    Pass 1: Claude (full prompt + tools) → research memo + fallback JSON
    Pass 2: GPT-5.4 (condensed summary + Claude memo, no tools) → final JSON

    Returns dict with claude_memo, claude_json, gpt_json, fallback_used, etc.
    """
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("No API key found. Set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY.")

    client = anthropic.Anthropic(base_url=base_url, api_key=api_key)
    messages = [{"role": "user", "content": prompt}]
    tool_log = []
    start_time = time.time()

    # --- Pass 1: Claude — full prompt with tools (research memo) ---
    print("  [Pass 1] Claude research...", file=sys.stderr)
    pass1_text, in1, out1, rounds1 = _run_tool_loop(
        client, messages, model, max_tokens, temperature, tool_log, label="P1 "
    )
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "claude_memo.txt").write_text(pass1_text, encoding="utf-8")

    # Extract Claude's fallback JSON from the memo
    claude_json = _parse_json_from_text(pass1_text)

    total_input = in1
    total_output = out1
    total_rounds = rounds1

    # --- Pass 2: GPT-5.4 — condensed prompt + Claude's memo ---
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    openai_base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    gpt_text = ""
    gpt_json = {}
    fallback_used = False

    if openai_key and phase1_data:
        try:
            oai_client = openai.OpenAI(api_key=openai_key, base_url=openai_base)

            # Build condensed prompt: ANALYST.md + summary + Claude memo
            analyst_md = (Path(__file__).parent.parent / "agents" / "ANALYST.md").read_text(encoding="utf-8")
            summary = build_summary(phase1_data)
            gpt_prompt = build_gpt_prompt(analyst_md, summary, pass1_text)

            print("  [Pass 2] GPT-5.4 decision...", file=sys.stderr)
            print(f"    GPT prompt: ~{len(gpt_prompt)//1000}KB", file=sys.stderr)

            # Single call, no tools, with timeout
            response = oai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": gpt_prompt}],
                max_tokens=16384,
                temperature=0.3,
                timeout=GPT_TIMEOUT,
            )
            gpt_text = response.choices[0].message.content or ""
            usage = response.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
            total_input += usage.prompt_tokens
            total_output += usage.completion_tokens
            total_rounds += 1

            print(f"    done ({usage.prompt_tokens}+{usage.completion_tokens} tokens)", file=sys.stderr)

            if output_dir:
                (output_dir / "gpt_response.txt").write_text(gpt_text, encoding="utf-8")

            gpt_json = _parse_json_from_text(gpt_text)
            if not gpt_json:
                print("  WARNING: Could not parse GPT response as JSON", file=sys.stderr)

        except Exception as e:
            print(f"  WARNING: GPT-5.4 pass failed: {e}", file=sys.stderr)
    elif not openai_key:
        print("  [Skip] No OPENAI_API_KEY — Claude-only mode", file=sys.stderr)
    elif not phase1_data:
        print("  [Skip] No phase1_data — Claude-only mode", file=sys.stderr)

    # Determine primary result
    if gpt_json:
        primary_text = gpt_text
        fallback_used = False
    else:
        primary_text = pass1_text
        fallback_used = True
        if claude_json:
            print("  Using Claude fallback JSON", file=sys.stderr)
        else:
            print("  WARNING: Neither GPT nor Claude produced valid JSON", file=sys.stderr)

    return {
        "text": primary_text,
        "claude_memo": pass1_text,
        "claude_json": claude_json,
        "gpt_json": gpt_json,
        "fallback_used": fallback_used,
        "tool_calls": tool_log,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "rounds": total_rounds,
        "duration_sec": round(time.time() - start_time, 1),
    }


def _parse_json_from_text(text: str) -> dict:
    """Extract JSON object from LLM response text."""
    # Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    if not text:
        return {}
    # Extract from ```json blocks
    json_blocks = re.findall(r"```json\s*(.*?)```", text, re.DOTALL)
    for block in json_blocks:
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue
    # Find JSON object by brace matching
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
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    return {}


def _summarize_input(input_data: dict) -> str:
    """Short summary of tool input for logging."""
    if "url" in input_data:
        url = input_data["url"]
        if len(url) > 60:
            url = url[:57] + "..."
        return url
    if "query" in input_data:
        return input_data["query"][:40]
    return str(input_data)[:40]


# --- Standalone test ---

if __name__ == "__main__":
    # Quick test
    print("Testing web_fetch...")
    result = execute_web_fetch("https://www.baidu.com/s?wd=A股+今日+要闻", max_chars=500)
    print(f"  Got {len(result)} chars")
    print(f"  Preview: {result[:200]}")
