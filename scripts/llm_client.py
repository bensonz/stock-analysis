#!/usr/bin/env python3
"""
llm_client.py — LLM orchestration for the daily analysis pipeline.

Supported provider modes:
- openai: GPT-5.4 only, full prompt + tool loop + JSON refine
- hybrid: Claude research/tool pass, then GPT-5.4 final decision
- anthropic: Claude only, full prompt + tool loop + JSON refine

Tools: web_search (Tavily), web_fetch (direct HTTP)
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

ENV_FILE = Path(__file__).parent.parent / ".env"
CLAUDE_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"


def _read_env_file(env_file: Path | None = None) -> dict[str, str]:
    """Read simple KEY=VALUE pairs from `.env`."""
    env_path = env_file or ENV_FILE
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _read_claude_settings_env(settings_file: Path | None = None) -> dict[str, str]:
    """Read env values from `~/.claude/settings.json` if present."""
    config_path = settings_file or CLAUDE_SETTINGS_FILE
    if not config_path.exists():
        return {}

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return {}

    env_values = payload.get("env")
    if not isinstance(env_values, dict):
        return {}

    result: dict[str, str] = {}
    for key, value in env_values.items():
        if isinstance(key, str) and isinstance(value, (str, int, float, bool)):
            result[key] = str(value).strip()
    return result


def _load_env_defaults() -> None:
    """Populate missing env vars from Claude settings, then project `.env`."""
    for source in (_read_claude_settings_env(), _read_env_file()):
        for key, value in source.items():
            os.environ.setdefault(key, value)


def _get_env_value(*names: str, default: str | None = None) -> str | None:
    """Read from process env first, then `.env`, then Claude settings."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()

    file_values = _read_env_file()
    for name in names:
        value = file_values.get(name)
        if value:
            return value.strip()

    settings_values = _read_claude_settings_env()
    for name in names:
        value = settings_values.get(name)
        if value:
            return value.strip()

    return default


_load_env_defaults()

# --- Config ---

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = _get_env_value("ANTHROPIC_MODEL", "CLAUDE_MODEL", default="claude-opus-4-6") or "claude-opus-4-6"
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

def _anthropic_messages_create(client: anthropic.Anthropic, **kwargs):
    """Wrap Anthropic calls with a clearer model-availability error."""
    try:
        return client.messages.create(**kwargs)
    except anthropic.InternalServerError as exc:
        message = str(exc)
        if "No available Claude accounts support the requested model" in message:
            model = kwargs.get("model")
            raise ValueError(
                f"Anthropic model {model!r} is unavailable on the current relay. "
                "Set ANTHROPIC_MODEL in .env to a supported model."
            ) from exc
        raise


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

        response = _anthropic_messages_create(client,
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


def _run_anthropic_text_once(
    client: anthropic.Anthropic,
    messages: list,
    model: str,
    max_tokens: int,
    temperature: float,
    label: str = "",
) -> tuple[str, int, int, int]:
    """Run a single Anthropic response without tools."""
    print(f"  {label}round 1...", file=sys.stderr, end="", flush=True)
    response = _anthropic_messages_create(client,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    final_text = "\n".join(getattr(block, "text", "") for block in response.content if getattr(block, "type", "") == "text")
    print(f" done ({response.usage.input_tokens}+{response.usage.output_tokens} tokens)", file=sys.stderr)
    return final_text, response.usage.input_tokens, response.usage.output_tokens, 1


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


def normalize_llm_provider(provider: str | None = None) -> str:
    """Normalize provider aliases to one of: openai, hybrid, anthropic."""
    raw = (provider or _get_env_value("LLM_PROVIDER", default=DEFAULT_PROVIDER) or DEFAULT_PROVIDER).strip().lower()
    aliases = {
        "gpt": "openai",
        "gpt-5.4": "openai",
        "openai": "openai",
        "hybrid": "hybrid",
        "claude+gpt": "hybrid",
        "anthropic": "anthropic",
        "claude": "anthropic",
    }
    normalized = aliases.get(raw)
    if not normalized:
        valid = ", ".join(sorted(set(aliases.values())))
        raise ValueError(f"Unknown LLM provider: {provider!r}. Use one of: {valid}")
    return normalized


def _build_anthropic_client() -> anthropic.Anthropic:
    api_key = _get_env_value("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "No Anthropic API key found. Set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY, "
            "or provide them in ~/.claude/settings.json."
        )
    base_url = _get_env_value(
        "ANTHROPIC_API_URL",
        "ANTHROPIC_BASE_URL",
        default="https://api.anthropic.com",
    )
    return anthropic.Anthropic(base_url=base_url, api_key=api_key)


def _build_openai_client() -> openai.OpenAI:
    api_key = _get_env_value("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No OpenAI API key found. Set OPENAI_API_KEY.")
    base_url = _get_env_value("OPENAI_BASE_URL", default="https://api.openai.com/v1")
    return openai.OpenAI(api_key=api_key, base_url=base_url)


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
    """Condense phase1 data (~250KB) into ~5-10KB for GPT.

    Handles both the actual Phase 1 schema (dict indices, {top5,bottom5} sectors,
    'positions' key, 'price' in position_prices, structured iv_sentiment) and
    any future normalized schema.
    """
    sections = []

    def _format_iv_proxy(proxy: dict | None) -> str:
        if not isinstance(proxy, dict):
            return ""
        name = proxy.get("primary_name") or proxy.get("primary_underlying")
        rank = proxy.get("iv_rank")
        sizing = proxy.get("sizing")
        if not name or rank in (None, ""):
            return ""
        return f", iv_proxy={name} IVR={float(rank)*100:.1f}% ({sizing})"

    # Portfolio snapshot (may be None in raw Phase 1 — built later by run_daily)
    pf = phase1_data.get("portfolio") or {}
    if pf:
        sections.append(
            "## Portfolio Snapshot\n"
            f"- Equity: {pf.get('totalEquity', '?'):,} / Cash: {pf.get('cash', '?'):,} ({pf.get('cashPct', '?')}%)\n"
            f"- Positions: {pf.get('positionsUsed', 0)}/{pf.get('positionsMax', 10)}\n"
            f"- Unrealized P&L: {pf.get('unrealizedPnl', 0):,} | Realized: {pf.get('realizedPnl', 0):,}\n"
            f"- Total return: {pf.get('totalReturnPct', 0)}%"
        )

    # Market indices — dict (actual) or list
    market = phase1_data.get("market") or {}
    indices = market.get("indices") or {}
    if indices:
        idx_lines = ["## Market Indices"]
        if isinstance(indices, dict):
            for name, info in indices.items():
                if isinstance(info, dict):
                    idx_lines.append(f"- {name}: {info.get('close', '?')} ({info.get('change_pct', '?')}%)")
        elif isinstance(indices, list):
            for idx in indices:
                name = idx.get("name", idx.get("code", "?"))
                idx_lines.append(f"- {name}: {idx.get('close', '?')} ({idx.get('change_pct', '?')}%)")
        sections.append("\n".join(idx_lines))

    # Breadth
    breadth = market.get("breadth") or {}
    if breadth:
        up = breadth.get("up", 0)
        down = breadth.get("down", 0)
        ratio = f"{up/down:.1f}:1" if down > 0 else "N/A"
        sections.append(f"## Breadth\n- Up: {up} / Down: {down} / Ratio: {ratio}")

    # Sectors — {top5, bottom5} (actual) or flat list
    sector_data = market.get("sectors") or {}
    if sector_data:
        lines = ["## Sectors"]
        if isinstance(sector_data, dict):
            for label in ("top5", "bottom5"):
                items = sector_data.get(label, [])
                if items:
                    lines.append(f"\n**{label}:**")
                    for s in items:
                        name = s.get("板块名称", s.get("name", "?"))
                        chg = s.get("涨跌幅", s.get("change_pct", "?"))
                        lines.append(f"- {name}: {chg}%")
        elif isinstance(sector_data, list):
            for s in sector_data[:10]:
                lines.append(f"- {s.get('name', '?')}: {s.get('change_pct', '?')}%")
        sections.append("\n".join(lines))

    # Strategy pool — compact table
    pool = (phase1_data.get("strategy_pool") or {}).get("stocks", [])
    if pool:
        lines = ["## Strategy Pool", "| Code | Name | RPS120 | RPS20 | PE | MCap |", "|---|---|---|---|---|---|"]
        for s in pool:
            lines.append(
                f"| {s.get('code', '?')} | {s.get('name', '?')} "
                f"| {s.get('rps120', '?')} | {s.get('rps20', '?')} "
                f"| {s.get('pe', '?')} | {s.get('market_cap', '?')} |"
            )
        sections.append("\n".join(lines))

    # Enriched candidates — try both keys
    enriched = phase1_data.get("enriched") or phase1_data.get("enriched_candidates") or []
    if enriched:
        lines = ["## Enriched Candidates"]
        for c in enriched:
            # Get sector from industries list if present
            sector = c.get("sector", "?")
            if sector == "?" and c.get("industries"):
                industries = c["industries"]
                sector = industries[0].get("name", "?") if industries else "?"
            iv_proxy = _format_iv_proxy(c.get("iv_proxy"))
            lines.append(
                f"- **{c.get('code', '?')} {c.get('name', '?')}**: "
                f"PE={c.get('pe', '?')}, "
                f"dist_ma5={c.get('dist_ma5_pct', '?')}%, "
                f"dist_ma10={c.get('dist_ma10_pct', '?')}%, "
                f"dist_ma20={c.get('dist_ma20_pct', '?')}%, "
                f"sector={sector}{iv_proxy}"
            )
        sections.append("\n".join(lines))

    # Positions — try both keys
    positions = phase1_data.get("positions") or phase1_data.get("active_positions") or []
    if positions:
        lines = ["## Active Positions"]
        for p in positions:
            iv_proxy = _format_iv_proxy(p.get("iv_proxy"))
            lines.append(
                f"- **{p.get('code', '?')} {p.get('name', '?')}**: "
                f"entry={p.get('entryPrice', '?')} on {p.get('entryDate', '?')}, "
                f"stop={p.get('stopLoss', '?')}, target={p.get('targetPrice', '?')}, "
                f"sector={p.get('sector', '?')}{iv_proxy}"
            )
        sections.append("\n".join(lines))

    # Position prices — handle both 'price' and 'current_price'
    pos_prices = phase1_data.get("position_prices") or {}
    if pos_prices:
        lines = ["## Position Prices (live)"]
        for code, info in pos_prices.items():
            if isinstance(info, dict):
                price = info.get("price", info.get("current_price", "?"))
                chg = info.get("change_pct", "?")
                lines.append(f"- {code} ({info.get('name', '')}): {price} ({chg}%)")
            else:
                lines.append(f"- {code}: {info}")
        sections.append("\n".join(lines))

    # IV Sentiment — structured format
    iv = phase1_data.get("iv_sentiment") or {}
    if iv:
        lines = ["## IV Sentiment"]
        overall = iv.get("overall_sentiment")
        if isinstance(overall, dict):
            based_on = overall.get("based_on") or []
            basket = f", Core Basket: {','.join(based_on)}" if based_on else ""
            lines.append(
                f"- Signal: {overall.get('signal', '?')}, "
                f"Avg IV Rank: {overall.get('avg_iv_rank', '?')}, "
                f"Avg IV Percentile: {overall.get('avg_iv_percentile', '?')}{basket}"
            )
            if overall.get("implication"):
                lines.append(f"- Implication: {overall['implication']}")
        etf_data = iv.get("etf_iv_data", [])
        if etf_data:
            for etf in etf_data:
                if isinstance(etf, dict):
                    lines.append(
                        f"- {etf.get('name', etf.get('underlying', '?'))}: "
                        f"IV={etf.get('current_iv', '?')}, "
                        f"IVRank={etf.get('iv_rank', '?')}, "
                        f"{etf.get('interpretation', '')}"
                    )
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _call_anthropic_only(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16384,
    temperature: float = 0.3,
    output_dir: Path | None = None,
) -> dict:
    """Claude-only path: full prompt + tools + JSON refine."""
    client = _build_anthropic_client()
    messages = [{"role": "user", "content": prompt}]
    tool_log = []
    start_time = time.time()

    print("  [Pass 1] Claude analysis...", file=sys.stderr)
    pass1_text, in1, out1, rounds1 = _run_tool_loop(
        client, messages, model, max_tokens, temperature, tool_log, label="P1 "
    )
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "claude_response.txt").write_text(pass1_text, encoding="utf-8")

    claude_json = _parse_json_from_text(pass1_text)
    primary_text = pass1_text
    total_input = in1
    total_output = out1
    total_rounds = rounds1

    if not claude_json:
        print("  [Pass 1b] Claude JSON refine...", file=sys.stderr)
        messages.append({"role": "user", "content": REFINE_PROMPT})
        fb_text, fb_in, fb_out, fb_rounds = _run_anthropic_text_once(
            client, messages, model, max_tokens, temperature, label="P1b "
        )
        if output_dir:
            (output_dir / "claude_refine.txt").write_text(fb_text, encoding="utf-8")
        claude_json = _parse_json_from_text(fb_text)
        total_input += fb_in
        total_output += fb_out
        total_rounds += fb_rounds
        if claude_json:
            primary_text = fb_text
            print("  Claude JSON extracted", file=sys.stderr)
        else:
            print("  WARNING: Claude produced no valid JSON", file=sys.stderr)

    return {
        "text": primary_text,
        "claude_memo": pass1_text,
        "claude_json": claude_json,
        "gpt_json": {},
        "fallback_used": not bool(claude_json),
        "tool_calls": tool_log,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "rounds": total_rounds,
        "duration_sec": round(time.time() - start_time, 1),
        "provider": "anthropic",
        "decision_source": "Claude primary",
        "primary_model": model,
    }


def _call_openai_only(
    prompt: str,
    max_tokens: int = 16384,
    temperature: float = 0.3,
    output_dir: Path | None = None,
) -> dict:
    """GPT-only path: full prompt + tools + JSON refine."""
    client = _build_openai_client()
    messages = [{"role": "user", "content": prompt}]
    tool_log = []
    start_time = time.time()

    print("  [Pass 1] GPT-5.4 analysis...", file=sys.stderr)
    pass1_text, in1, out1, rounds1 = _run_openai_tool_loop(
        client, messages, OPENAI_MODEL, max_tokens, temperature, tool_log, label="P1 "
    )
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "gpt_response.txt").write_text(pass1_text, encoding="utf-8")

    gpt_json = _parse_json_from_text(pass1_text)
    primary_text = pass1_text
    total_input = in1
    total_output = out1
    total_rounds = rounds1

    if not gpt_json:
        print("  [Pass 1b] GPT-5.4 JSON refine...", file=sys.stderr)
        messages.append({"role": "user", "content": REFINE_PROMPT})
        refine_text, refine_in, refine_out, refine_rounds = _run_openai_tool_loop(
            client, messages, OPENAI_MODEL, max_tokens, temperature, tool_log, label="P1b "
        )
        if output_dir:
            (output_dir / "gpt_refine.txt").write_text(refine_text, encoding="utf-8")
        gpt_json = _parse_json_from_text(refine_text)
        total_input += refine_in
        total_output += refine_out
        total_rounds += refine_rounds
        if gpt_json:
            primary_text = refine_text
            print("  GPT JSON extracted", file=sys.stderr)
        else:
            print("  WARNING: GPT produced no valid JSON", file=sys.stderr)

    return {
        "text": primary_text,
        "claude_memo": "",
        "claude_json": {},
        "gpt_json": gpt_json,
        "fallback_used": not bool(gpt_json),
        "tool_calls": tool_log,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "rounds": total_rounds,
        "duration_sec": round(time.time() - start_time, 1),
        "provider": "openai",
        "decision_source": "GPT primary",
        "primary_model": OPENAI_MODEL,
    }


def _call_hybrid(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16384,
    temperature: float = 0.3,
    output_dir: Path | None = None,
    phase1_data: dict | None = None,
) -> dict:
    """Claude research + GPT final decision."""
    client = _build_anthropic_client()
    messages = [{"role": "user", "content": prompt}]
    tool_log = []
    start_time = time.time()

    print("  [Pass 1] Claude research...", file=sys.stderr)
    pass1_text, in1, out1, rounds1 = _run_tool_loop(
        client, messages, model, max_tokens, temperature, tool_log, label="P1 "
    )
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "claude_memo.txt").write_text(pass1_text, encoding="utf-8")

    claude_json = _parse_json_from_text(pass1_text)
    if not claude_json:
        print("  [Pass 1b] Claude fallback JSON...", file=sys.stderr)
        messages.append({"role": "user", "content": REFINE_PROMPT})
        fb_text, fb_in, fb_out, fb_rounds = _run_anthropic_text_once(
            client, messages, model, max_tokens, temperature, label="P1b "
        )
        claude_json = _parse_json_from_text(fb_text)
        in1 += fb_in
        out1 += fb_out
        rounds1 += fb_rounds
        if output_dir:
            (output_dir / "claude_fallback.txt").write_text(fb_text, encoding="utf-8")
        if claude_json:
            print("  Claude fallback JSON extracted", file=sys.stderr)
        else:
            print("  WARNING: Claude fallback also produced no valid JSON", file=sys.stderr)

    total_input = in1
    total_output = out1
    total_rounds = rounds1
    gpt_text = ""
    gpt_json = {}
    fallback_used = False

    openai_key = _get_env_value("OPENAI_API_KEY")
    if openai_key and phase1_data:
        try:
            oai_client = _build_openai_client()
            analyst_md = (Path(__file__).parent.parent / "agents" / "ANALYST.md").read_text(encoding="utf-8")
            summary = build_summary(phase1_data)
            gpt_prompt = build_gpt_prompt(analyst_md, summary, pass1_text)

            print("  [Pass 2] GPT-5.4 decision...", file=sys.stderr)
            print(f"    GPT prompt: ~{len(gpt_prompt)//1000}KB", file=sys.stderr)

            response = oai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": gpt_prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
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
        print("  [Skip] No OPENAI_API_KEY — Claude-only fallback within hybrid mode", file=sys.stderr)
    elif not phase1_data:
        print("  [Skip] No phase1_data — Claude-only fallback within hybrid mode", file=sys.stderr)

    if gpt_json:
        primary_text = gpt_text
        decision_source = "GPT primary"
        fallback_used = False
    else:
        primary_text = pass1_text
        decision_source = "Claude fallback"
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
        "provider": "hybrid",
        "decision_source": decision_source,
        "primary_model": OPENAI_MODEL if gpt_json else model,
    }


def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16384,
    temperature: float = 0.3,
    output_dir: Path | None = None,
    phase1_data: dict | None = None,
    provider: str | None = None,
) -> dict:
    """Run the configured LLM provider path and return normalized metadata."""
    selected = normalize_llm_provider(provider)
    if selected == "openai":
        return _call_openai_only(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            output_dir=output_dir,
        )
    if selected == "anthropic":
        return _call_anthropic_only(
            prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            output_dir=output_dir,
        )
    return _call_hybrid(
        prompt,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        output_dir=output_dir,
        phase1_data=phase1_data,
    )


REFINE_PROMPT = (
    "现在请直接输出最终 JSON 决策。不要输出任何解释文字、markdown标记或代码块，"
    "直接从 { 开始输出纯 JSON。确保 JSON 完整（所有括号闭合）。"
    "注意：skip_list 中只能引用输入数据中实际存在的价格和指标，不要编造。"
)


def call_llm_v1(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 16384,
    temperature: float = 0.3,
    output_dir: Path | None = None,
) -> dict:
    """Legacy 4-pass approach. Use --legacy-llm flag to activate."""
    client = _build_anthropic_client()
    messages = [{"role": "user", "content": prompt}]
    tool_log = []
    start_time = time.time()

    print("  [P1] Claude analysis...", file=sys.stderr)
    p1, in1, out1, r1 = _run_tool_loop(client, messages, model, max_tokens, temperature, tool_log, label="P1 ")
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "pass1_response.txt").write_text(p1, encoding="utf-8")

    print("  [P2] Claude refine...", file=sys.stderr)
    messages.append({"role": "user", "content": REFINE_PROMPT})
    p2, in2, out2, r2 = _run_anthropic_text_once(client, messages, model, max_tokens, temperature, label="P2 ")
    if output_dir:
        (output_dir / "pass2_response.txt").write_text(p2, encoding="utf-8")

    ti, to, tr = in1 + in2, out1 + out2, r1 + r2
    p3 = p4 = ""
    oai_key = _get_env_value("OPENAI_API_KEY")
    if oai_key:
        try:
            oc = _build_openai_client()
            om = [{"role": "user", "content": prompt}]
            print("  [P3] GPT analysis...", file=sys.stderr)
            p3, i3, o3, r3 = _run_openai_tool_loop(oc, om, OPENAI_MODEL, max_tokens, temperature, tool_log, label="P3 ")
            ti += i3; to += o3; tr += r3
            if output_dir:
                (output_dir / "pass3_response.txt").write_text(p3, encoding="utf-8")
            print("  [P4] GPT refine...", file=sys.stderr)
            om.append({"role": "user", "content": REFINE_PROMPT})
            p4, i4, o4, r4 = _run_openai_tool_loop(oc, om, OPENAI_MODEL, max_tokens, temperature, tool_log, label="P4 ")
            ti += i4; to += o4; tr += r4
            if output_dir:
                (output_dir / "pass4_response.txt").write_text(p4, encoding="utf-8")
        except Exception as e:
            print(f"  WARNING: GPT failed: {e}", file=sys.stderr)

    return {
        "text": p2, "pass1_text": p1, "pass3_text": p3, "pass4_text": p4,
        "tool_calls": tool_log, "input_tokens": ti, "output_tokens": to,
        "rounds": tr, "duration_sec": round(time.time() - start_time, 1),
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
