#!/usr/bin/env python3
"""
llm_client.py — Anthropic API client with two-pass tool-use loop.

Pass 1: Full prompt → LLM researches (web_search/web_fetch) and drafts analysis
Pass 2: Same conversation, repeat instruction → LLM refines

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


REFINE_PROMPT = (
    "请根据以上数据进行分析，按照 Required Output JSON 格式返回你的决策。"
    "注意：skip_list 中只能引用输入数据中实际存在的价格和指标，不要编造。"
)


def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 8192,
    temperature: float = 0.3,
    output_dir: Path | None = None,
) -> dict:
    """Call Anthropic API with two-pass approach.

    Pass 1: Full prompt (ANALYST.md + data) → LLM researches and drafts analysis
    Pass 2: Same conversation, just the instruction → LLM refines with full context

    Args:
        prompt: The full analysis prompt.
        model: Model name.
        max_tokens: Max tokens per response.
        temperature: Sampling temperature.
        output_dir: If set, save pass1_response.txt and pass2_response.txt here.

    Returns:
        {
            "text": str,           # Final text response from pass 2 (should contain JSON)
            "pass1_text": str,     # First pass response (for debugging)
            "tool_calls": list,    # Log of all tool calls made
            "input_tokens": int,   # Total input tokens
            "output_tokens": int,  # Total output tokens
            "rounds": int,         # Total number of API calls
            "duration_sec": float, # Total wall time
        }
    """
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        raise ValueError("No API key found. Set ANTHROPIC_AUTH_TOKEN or ANTHROPIC_API_KEY.")

    client = anthropic.Anthropic(
        base_url=base_url,
        api_key=api_key,
    )

    messages = [{"role": "user", "content": prompt}]
    tool_log = []
    start_time = time.time()

    # Pass 1: Full prompt — LLM researches and produces initial analysis
    print("  [Pass 1] Full analysis...", file=sys.stderr)
    pass1_text, in1, out1, rounds1 = _run_tool_loop(
        client, messages, model, max_tokens, temperature, tool_log, label="P1 "
    )

    # Save pass 1 response
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "pass1_response.txt").write_text(pass1_text, encoding="utf-8")

    # Pass 2: Same conversation, repeat instruction — LLM refines
    print("  [Pass 2] Refine...", file=sys.stderr)
    messages.append({"role": "user", "content": REFINE_PROMPT})
    pass2_text, in2, out2, rounds2 = _run_tool_loop(
        client, messages, model, max_tokens, temperature, tool_log, label="P2 "
    )

    # Save pass 2 response
    if output_dir:
        (output_dir / "pass2_response.txt").write_text(pass2_text, encoding="utf-8")

    total_input = in1 + in2
    total_output = out1 + out2
    total_rounds = rounds1 + rounds2

    return {
        "text": pass2_text,
        "pass1_text": pass1_text,
        "tool_calls": tool_log,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "rounds": total_rounds,
        "duration_sec": round(time.time() - start_time, 1),
    }


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
