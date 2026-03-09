#!/usr/bin/env python3
"""
llm_client.py — Anthropic API client with tool-use loop.

Calls Claude with web_fetch/web_search tools. Executes tool calls
locally and feeds results back until the LLM returns a final text response.
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

# --- Config ---

DEFAULT_MODEL = "claude-opus-4-6"
MAX_TOOL_ROUNDS = 15  # Safety cap on tool-use loops
FETCH_TIMEOUT = 15  # seconds per web fetch
FETCH_MAX_CHARS = 8000  # max chars per fetch result

# --- Tools ---

TOOLS = [
    {
        "name": "web_fetch",
        "description": (
            "Fetch and extract readable content from a URL (HTML → text). "
            "Use for news articles, Baidu search results, stock pages. "
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
            "Search the web using Baidu. Returns search result snippets. "
            "Use for finding recent news, sector analysis, stock catalysts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query in Chinese or English.",
                },
                "maxChars": {
                    "type": "integer",
                    "description": f"Maximum characters to return (default {FETCH_MAX_CHARS}).",
                    "default": FETCH_MAX_CHARS,
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


def execute_web_search(query: str, max_chars: int = FETCH_MAX_CHARS) -> str:
    """Search via Baidu and return extracted results."""
    encoded = quote_plus(query)
    url = f"https://www.baidu.com/s?wd={encoded}"
    return execute_web_fetch(url, max_chars)


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
            max_chars=input_data.get("maxChars", FETCH_MAX_CHARS),
        )
    else:
        return f"Unknown tool: {name}"


# --- LLM call with tool loop ---

def call_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 8192,
    temperature: float = 0.3,
) -> dict:
    """Call Anthropic API with tool-use loop.

    Args:
        prompt: The full analysis prompt (ANALYST.md + data).
        model: Model name.
        max_tokens: Max tokens for LLM response.
        temperature: Sampling temperature.

    Returns:
        {
            "text": str,           # Final text response (should contain JSON)
            "tool_calls": list,    # Log of all tool calls made
            "input_tokens": int,   # Total input tokens
            "output_tokens": int,  # Total output tokens
            "rounds": int,         # Number of API calls
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
    total_input = 0
    total_output = 0
    start_time = time.time()

    for round_num in range(1, MAX_TOOL_ROUNDS + 1):
        print(f"  LLM round {round_num}...", file=sys.stderr, end="", flush=True)

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=TOOLS,
            messages=messages,
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        # Check if we got tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]

        if not tool_use_blocks:
            # No tools — final response
            final_text = "\n".join(b.text for b in text_blocks)
            print(f" done ({total_input}+{total_output} tokens)", file=sys.stderr)
            return {
                "text": final_text,
                "tool_calls": tool_log,
                "input_tokens": total_input,
                "output_tokens": total_output,
                "rounds": round_num,
                "duration_sec": round(time.time() - start_time, 1),
            }

        # Execute tool calls
        # First, add assistant message with all content blocks
        messages.append({"role": "assistant", "content": response.content})

        # Then add tool results
        tool_results = []
        for tool_block in tool_use_blocks:
            tool_name = tool_block.name
            tool_input = tool_block.input
            print(f" → {tool_name}({_summarize_input(tool_input)})", file=sys.stderr, end="", flush=True)

            result_text = execute_tool(tool_name, tool_input)
            tool_log.append({
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
        print("", file=sys.stderr)  # newline after tool calls

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

    return {
        "text": final_text,
        "tool_calls": tool_log,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "rounds": MAX_TOOL_ROUNDS,
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
