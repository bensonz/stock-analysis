#!/usr/bin/env python3
"""
deep_report.py — Generate a CheeseForTune-style deep-research article for one A-share.

Assembles a data package (CheeseForTune financials/valuation/peers + our local RPS/MA/kline
+ margin flow), feeds it to the LLM with the web_search/web_fetch tool loop, and writes a
long-form markdown article that reaches its OWN 看多/看空/中性 verdict.

Reuses llm_client._run_tool_loop directly (NOT call_llm, which is hard-wired to the daily
decision-JSON format and would corrupt a markdown article).

Usage:
    python3 scripts/deep_report.py 000703
    python3 scripts/deep_report.py 000703 --provider anthropic --human
    python3 scripts/deep_report.py 000703.SZ --output-dir /tmp/reports
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "agents" / "DEEP_REPORT.md"

MAX_TOKENS = 16384
TEMPERATURE = 0.5


# --------------------------------------------------------------------------- #
# Data gathering
# --------------------------------------------------------------------------- #
def _safe(fn, label: str, errors: list):
    """Run a data-source call, recording (not raising) failures for graceful degradation."""
    try:
        return fn()
    except Exception as e:  # one flaky source must not sink the whole report
        errors.append(f"{label}: {e}")
        return None


def _downsample(series, keep: int = 24):
    """Thin a long daily valuation series to ~`keep` points to keep the prompt cheap."""
    if not isinstance(series, list) or len(series) <= keep:
        return series
    step = max(1, len(series) // keep)
    return series[::step]


def _trim_peers(peers, code6: str = ""):
    """Reduce industry_compare to the useful bits.

    Its `list` is a whole-market market-cap ranking (banks, 中移动, …), NOT sector
    comparables — feeding those as "peers" would mislead the model. Keep only the
    industry size, the metric names, and the target's own row (its rank/mkt-cap).
    The spec has the LLM web_search real sector peers from the classification.
    """
    if not isinstance(peers, dict):
        return peers
    target_row = None
    for row in peers.get("list") or []:
        if isinstance(row, dict) and str(row.get("code", "")).split(".")[0] == code6:
            target_row = row
            break
    return {
        "industry_total": peers.get("total"),
        "metrics": [c.get("optname") for c in (peers.get("catalog") or []) if isinstance(c, dict)],
        "target_row": target_row,
        "note": "Sector peers are NOT in this data — identify and web_search them from the industry classification.",
    }


def _recent_klines(code6: str, limit: int = 20) -> list:
    """Last `limit` daily bars from the local price DB (newest first)."""
    try:
        import pricedb
        con = sqlite3.connect(str(pricedb.DB_PATH))
        try:
            rows = con.execute(
                "SELECT date, open, high, low, close, volume FROM daily_prices "
                "WHERE code=? ORDER BY date DESC LIMIT ?",
                (code6, limit),
            ).fetchall()
        finally:
            con.close()
        return [
            {"date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
            for r in rows
        ]
    except Exception:
        return []


def gather_data(code: str) -> dict:
    """Assemble the full data package for one stock. Never raises; missing sources are omitted."""
    from cheesefortune_client import CheeseFortuneClient, normalize_code

    code6 = str(code).split(".")[0]
    full = code if "." in str(code) else normalize_code(code)
    errors: list = []
    client = CheeseFortuneClient()

    data: dict = {
        "code": full,
        "code6": code6,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data["summary"] = _safe(lambda: client.get_stock_summary(full), "summary", errors)
    data["intro"] = _safe(lambda: client.get_intro(full), "intro", errors)
    data["peers"] = _trim_peers(_safe(lambda: client.get_industry_compare(full), "peers", errors), code6)

    pepb = _safe(lambda: client.get_pepb_history(full, "5Y"), "pepb", errors)
    if isinstance(pepb, dict):
        data["valuation_history"] = {
            "msg": pepb.get("msg"),
            "newest": pepb.get("newest"),
            "series": _downsample(pepb.get("datas")),
        }

    # Local technicals (RPS / MA) + recent klines — our edge over a pure fundamental report.
    import pricedb
    import rps_calculator

    rps = _safe(
        lambda: rps_calculator.get_ma_rps_for_stocks(str(pricedb.DB_PATH), [code6]),
        "rps",
        errors,
    )
    tech = dict((rps or {}).get(code6) or {})
    tech["klines"] = _recent_klines(code6)
    data["technicals"] = tech

    r60, r120, r250 = tech.get("rps60"), tech.get("rps120"), tech.get("rps250")
    have_all = all(isinstance(v, (int, float)) for v in (r60, r120, r250))
    data["rps_gate"] = {
        "threshold": 85,
        "rps60": r60,
        "rps120": r120,
        "rps250": r250,
        "passes_all_ge_85": (all(v >= 85 for v in (r60, r120, r250)) if have_all else None),
        "note": "Our momentum screen requires rps60/rps120/rps250 all >= 85.",
    }

    from margin_flow import fetch_margin_flow

    data["margin"] = _safe(lambda: fetch_margin_flow(code6), "margin", errors)

    if errors:
        data["_gather_errors"] = errors
    return data


# --------------------------------------------------------------------------- #
# Prompt + generation
# --------------------------------------------------------------------------- #
def build_prompt(spec: str, code: str, data: dict) -> str:
    return (
        spec
        + "\n\n---\n\n# 目标个股\n"
        + str(data.get("code", code))
        + "\n\n# DATA\n```json\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
        + "\n```\n"
    )


def generate(code: str, provider: str | None = None, data: dict | None = None) -> dict:
    """Run the LLM tool loop to produce the article. Returns text + run metadata."""
    import llm_client

    resolved = llm_client.normalize_llm_provider(provider)  # None -> env LLM_PROVIDER -> openai
    spec = SPEC_FILE.read_text(encoding="utf-8")
    if data is None:
        data = gather_data(code)
    prompt = build_prompt(spec, code, data)
    messages = [{"role": "user", "content": prompt}]
    tool_log: list = []

    if resolved == "anthropic":
        client = llm_client._build_anthropic_client()
        model = llm_client.DEFAULT_MODEL
        text, tin, tout, rounds = llm_client._run_tool_loop(
            client, messages, model, MAX_TOKENS, TEMPERATURE, tool_log, label="deep_report "
        )
    else:
        # openai (default) and hybrid both use the OpenAI tool loop for free-form output.
        client = llm_client._build_openai_client()
        model = llm_client.OPENAI_MODEL
        text, tin, tout, rounds = llm_client._run_openai_tool_loop(
            client, messages, model, MAX_TOKENS, TEMPERATURE, tool_log, label="deep_report "
        )

    return {
        "text": text,
        "tool_calls": tool_log,
        "input_tokens": tin,
        "output_tokens": tout,
        "rounds": rounds,
        "provider": resolved,
        "model": model,
        "data": data,
    }


def write_report(code: str, text: str, output_dir=None) -> Path:
    import report_generator

    code6 = str(code).split(".")[0]
    date = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(output_dir) if output_dir else report_generator.REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{code6}-{date}-deep.md"
    out.write_text(text, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _arg_value(args: list, flag: str):
    return args[args.index(flag) + 1] if flag in args and args.index(flag) + 1 < len(args) else None


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(
            "usage: deep_report.py <code> [--provider anthropic|openai] "
            "[--output-dir DIR] [--human]",
            file=sys.stderr,
        )
        sys.exit(2)

    code = args[0]
    provider = _arg_value(args, "--provider")
    output_dir = _arg_value(args, "--output-dir")
    human = "--human" in args

    print(f"[deep_report] gathering data for {code} ...", file=sys.stderr)
    result = generate(code, provider=provider)
    out = write_report(code, result["text"], output_dir=output_dir)

    print(
        f"[deep_report] {result['provider']}/{result['model']} | {result['rounds']} rounds "
        f"| {len(result['tool_calls'])} tool calls "
        f"| {result['input_tokens']}+{result['output_tokens']} tok",
        file=sys.stderr,
    )
    print(f"[deep_report] wrote {out}", file=sys.stderr)

    if human:
        print(result["text"])
    else:
        print(str(out))


if __name__ == "__main__":
    main()
