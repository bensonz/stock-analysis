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
VERIFY_SPEC_FILE = PROJECT_ROOT / "agents" / "DEEP_VERIFY.md"

MAX_TOKENS = 16384
TEMPERATURE = 0.5
MAX_VERIFY_ROUNDS = 2


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
    # Gate floor kept in sync with data_collector.RPS_GATE_MIN (uniform 80).
    gate_min = 80
    data["rps_gate"] = {
        "threshold": gate_min,
        "rps60": r60,
        "rps120": r120,
        "rps250": r250,
        "passes_all_ge_80": (all(v >= gate_min for v in (r60, r120, r250)) if have_all else None),
        "note": "Our momentum screen requires rps60/rps120/rps250 all >= 80.",
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


def _provider_ctx(resolved: str) -> tuple:
    """Client + model for a normalized provider name."""
    import llm_client

    if resolved == "anthropic":
        return llm_client._build_anthropic_client(), llm_client.DEFAULT_MODEL
    # openai (default) and hybrid both use the OpenAI tool loop for free-form output.
    return llm_client._build_openai_client(), llm_client.OPENAI_MODEL


def _run_writer_pass(client, model, resolved, messages, tool_log, label) -> tuple:
    """One tool-loop pass (draft or revise). Returns (text, tin, tout, rounds)."""
    import llm_client

    if resolved == "anthropic":
        return llm_client._run_tool_loop(
            client, messages, model, MAX_TOKENS, TEMPERATURE, tool_log, label=label)
    return llm_client._run_openai_tool_loop(
        client, messages, model, MAX_TOKENS, TEMPERATURE, tool_log, label=label)


def _make_runners(resolved, client, model, tool_log, totals) -> tuple:
    """(revise_runner, judge_runner, cleanup_runner) for deep_verify.run_pipeline.

    Judge/cleanup are single no-tools calls (the _call_hybrid Pass-2 pattern);
    revise gets the full tool loop so it can re-search for better sources.
    All accumulate into `totals` so generate() can aggregate token counts.
    """
    import deep_verify
    import llm_client

    def revise_runner(prompt: str):
        t, i, o, r = _run_writer_pass(
            client, model, resolved, [{"role": "user", "content": prompt}],
            tool_log, label="verify-revise ")
        totals["in"] += i
        totals["out"] += o
        totals["rounds"] += r
        return t, i, o, r

    def _text_once(prompt: str, label: str, max_tokens: int):
        if resolved == "anthropic":
            t, i, o, _ = llm_client._run_anthropic_text_once(
                client, [{"role": "user", "content": prompt}], model,
                max_tokens, deep_verify.JUDGE_TEMPERATURE, label=label)
        else:
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                temperature=deep_verify.JUDGE_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
                timeout=llm_client.GPT_TIMEOUT,
            )
            usage = resp.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
            t, i, o = resp.choices[0].message.content or "", usage.prompt_tokens, usage.completion_tokens
        totals["in"] += i
        totals["out"] += o
        totals["rounds"] += 1
        return t, i, o

    # Judge emits small JSON verdicts; cleanup must re-emit a FULL report, so it
    # gets the writer budget — 4096 would truncate it into uselessness.
    return (revise_runner,
            lambda p: _text_once(p, "verify-judge ", deep_verify.JUDGE_MAX_TOKENS),
            lambda p: _text_once(p, "verify-cleanup ", MAX_TOKENS))


def generate(code: str, provider: str | None = None, data: dict | None = None,
             verify: bool = True, max_verify_rounds: int = MAX_VERIFY_ROUNDS) -> dict:
    """Draft the article, then (unless verify=False) run the citation-verify
    pipeline: every number must be inline-linked and confirmed at its source,
    or tagged 〖内部数据〗 and matched against DATA. See agents/DEEP_VERIFY.md.
    """
    import llm_client

    resolved = llm_client.normalize_llm_provider(provider)  # None -> env LLM_PROVIDER -> openai
    spec = SPEC_FILE.read_text(encoding="utf-8")
    if data is None:
        data = gather_data(code)
    prompt = build_prompt(spec, code, data)
    messages = [{"role": "user", "content": prompt}]
    tool_log: list = []

    client, model = _provider_ctx(resolved)
    text, tin, tout, rounds = _run_writer_pass(
        client, model, resolved, messages, tool_log, label="deep_report ")

    verify_audit = None
    verify_rounds = 0
    if verify:
        import deep_verify

        spec_verify = VERIFY_SPEC_FILE.read_text(encoding="utf-8")
        totals = {"in": 0, "out": 0, "rounds": 0}
        revise_runner, judge_runner, cleanup_runner = _make_runners(
            resolved, client, model, tool_log, totals)
        text, verify_audit = deep_verify.run_pipeline(
            text, data,
            spec_writer=spec, spec_verify=spec_verify,
            max_rounds=max_verify_rounds,
            judge_runner=judge_runner, revise_runner=revise_runner,
            cleanup_runner=cleanup_runner,
            log=lambda m: print(f"  [verify] {m}", file=sys.stderr),
        )
        verify_rounds = len(verify_audit["rounds"])
        tin += totals["in"]
        tout += totals["out"]
        rounds += totals["rounds"]

    return {
        "text": text,
        "tool_calls": tool_log,
        "input_tokens": tin,
        "output_tokens": tout,
        "rounds": rounds,
        "provider": resolved,
        "model": model,
        "data": data,
        "verify_audit": verify_audit,
        "verify_rounds": verify_rounds,
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


def write_verify_audit(code: str, audit: dict, output_dir=None) -> Path:
    """Write the citation-verification audit JSON next to the report."""
    import report_generator

    code6 = str(code).split(".")[0]
    date = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path(output_dir) if output_dir else report_generator.REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{code6}-{date}-deep-verify.json"
    out.write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
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
            "[--output-dir DIR] [--human] [--no-verify] [--max-verify-rounds N]",
            file=sys.stderr,
        )
        sys.exit(2)

    code = args[0]
    provider = _arg_value(args, "--provider")
    output_dir = _arg_value(args, "--output-dir")
    human = "--human" in args
    verify = "--no-verify" not in args
    mvr = _arg_value(args, "--max-verify-rounds")

    print(f"[deep_report] gathering data for {code} ...", file=sys.stderr)
    result = generate(code, provider=provider, verify=verify,
                      max_verify_rounds=int(mvr) if mvr else MAX_VERIFY_ROUNDS)
    out = write_report(code, result["text"], output_dir=output_dir)

    if result.get("verify_audit"):
        audit_path = write_verify_audit(code, result["verify_audit"], output_dir=output_dir)
        f = result["verify_audit"]["final"]
        print(
            f"[deep_report] verify: {f['verified_linked'] + f['verified_internal']}"
            f"/{f['total']} verified ({f['verified_linked']} linked/"
            f"{f['verified_internal']} internal), {f['rewritten_qualitative']} rewritten"
            f", rounds={result['verify_rounds']} | audit {audit_path}",
            file=sys.stderr,
        )

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
