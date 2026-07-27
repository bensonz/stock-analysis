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

# Deep-report defaults: Fable 5 writes, DeepSeek judges/cleans. These are
# deliberately LOCAL to deep reports — the daily pipeline keeps its own
# LLM_PROVIDER default. Override per-run with --provider/--verify-provider,
# or per-env with DEEP_REPORT_PROVIDER / DEEP_REPORT_VERIFY_PROVIDER;
# ANTHROPIC_MODEL (env/.env) still wins over the Fable fallback.
DEFAULT_WRITER_PROVIDER = "anthropic"
DEFAULT_VERIFY_PROVIDER = "openai"
FALLBACK_ANTHROPIC_MODEL = "claude-fable-5"


def _resolve_providers(provider: str | None, verify_provider: str | None) -> tuple:
    """(writer_provider, verify_provider), normalized, with deep-report defaults."""
    import os

    import llm_client

    writer = llm_client.normalize_llm_provider(
        provider or os.getenv("DEEP_REPORT_PROVIDER") or DEFAULT_WRITER_PROVIDER)
    verify = llm_client.normalize_llm_provider(
        verify_provider or os.getenv("DEEP_REPORT_VERIFY_PROVIDER") or DEFAULT_VERIFY_PROVIDER)
    return writer, verify


def _provider_model(resolved: str) -> str:
    """Model name a provider resolves to (no client construction — safe for banners)."""
    import llm_client

    if resolved == "anthropic":
        return (llm_client._get_env_value("ANTHROPIC_MODEL", "CLAUDE_MODEL")
                or FALLBACK_ANTHROPIC_MODEL)
    return llm_client.OPENAI_MODEL


# --------------------------------------------------------------------------- #
# Data gathering
# --------------------------------------------------------------------------- #
def _safe(fn, label: str, errors: list):
    """Run a data-source call, recording (not raising) failures for graceful
    degradation. Logs each source with timing so long gathers aren't silent."""
    import time

    print(f"  [gather] {label} ...", file=sys.stderr, end="", flush=True)
    t0 = time.time()
    try:
        result = fn()
        print(f" ok ({time.time() - t0:.1f}s)", file=sys.stderr)
        return result
    except Exception as e:  # one flaky source must not sink the whole report
        print(f" FAILED ({e})", file=sys.stderr)
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

    # Exchange-disclosure financials for the SUBJECT (exact, current-period).
    # Peers are fetched on demand by the writer via the stock_fundamentals tool.
    import fundamentals

    data["fundamentals"] = _safe(
        lambda: fundamentals.stock_snapshot(code6, include_valuation=False, include_rps=False),
        "fundamentals", errors)

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


STOCK_FUNDAMENTALS_TOOL = {
    "name": "stock_fundamentals",
    "description": (
        "获取任意A股的交易所披露口径财务数据：最新季报/年报（营收、净利、同比、EPS、ROE、"
        "毛利率、每股经营现金流）、业绩预告/快报（含原文）、估值（PE/PB/估值分位）、RPS动量、"
        "股东户数近8期（滞后的季度末快照，含截止日/公告日——引用时必须注明截止日，"
        "并与同期股价方向联读：涨+户数降=集中，涨+户数升=分散/派发）。"
        "所有涉及A股个股财务数字（本股或同业对标）必须优先使用本工具，其返回的数字可直接引用"
        "并标注〖内部数据〗（无需外部链接）。web_search 仅用于新闻、行业、定性信息。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "6位A股代码，如 300014 或 300014.SZ",
            },
        },
        "required": ["code"],
    },
}


BASE_RATE_TOOL = {
    "name": "base_rate",
    "description": (
        "参考类基准（历史频率）计算器：在本地全市场价格库/披露数据上统计\"该形态历史上"
        "发生某结局的频率\"，含样本量、95%置信区间、样本窗口。风险提示中凡是价格路径类"
        "（回撤/杀跌）或业绩持续性类的概率，必须引用本工具的频率并标注〖内部数据〗，"
        "不得凭感觉写\"概率：中\"。configs: extended_high_momentum（RPS60≥90且跌破MA10，"
        "强势股破位形态）、high_momentum_healthy（RPS60≥90且站上MA10，对照组）、"
        "momentum_gate_pass（RPS三线全≥80，我们的可买池）、growth_persistence"
        "（高增长公司下期降速频率）。结果附带的 caveats 必须一并向读者披露。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "config": {
                "type": "string",
                "enum": ["extended_high_momentum", "high_momentum_healthy",
                         "momentum_gate_pass", "growth_persistence"],
            },
            "horizon_days": {"type": "integer", "enum": [20, 60, 120],
                             "description": "前瞻交易日数（默认60；growth_persistence 忽略）"},
            "drawdown_pct": {"type": "integer", "enum": [10, 15, 20],
                             "description": "回撤阈值%（默认15；growth_persistence 忽略）"},
        },
        "required": ["config"],
    },
}


def _make_report_tools(data: dict) -> tuple:
    """([tool_defs], executor) for the writer loop.

    Every fetch is stored into `data` (peer_fundamentals / base_rates) so the
    verify pipeline's DATA corpus covers it — that's what turns these numbers
    into verifiable 〖内部数据〗 claims instead of unverifiable web claims.
    """
    import base_rates
    import fundamentals

    def executor(name: str, tool_input: dict):
        if name == "stock_fundamentals":
            code6 = str(tool_input.get("code", "")).split(".")[0].strip()
            store = data.setdefault("peer_fundamentals", {})
            if code6 not in store:  # revise rounds reuse the first fetch
                store[code6] = fundamentals.stock_snapshot(code6)
            return json.dumps(store[code6], ensure_ascii=False, indent=1)
        if name == "base_rate":
            cfg = str(tool_input.get("config", ""))
            h = int(tool_input.get("horizon_days") or 60)
            dd = int(tool_input.get("drawdown_pct") or 15)
            key = f"{cfg}_{h}d_{dd}pct"
            store = data.setdefault("base_rates", {})
            if key not in store:
                try:
                    store[key] = base_rates.base_rate(cfg, h, dd)
                except ValueError as e:
                    return f"Error: {e}"
            return json.dumps(store[key], ensure_ascii=False, indent=1)
        return None  # fall through to web_search/web_fetch dispatch

    return [STOCK_FUNDAMENTALS_TOOL, BASE_RATE_TOOL], executor


PREDICTIONS_BLOCK_RE = None  # compiled lazily in extract_predictions_block


def extract_predictions_block(text: str) -> tuple:
    """Split the writer's ```predictions fenced JSON block (judgment bets)
    out of the article. Returns (records_or_[], text_without_block).

    Runs on the DRAFT before verification: the block is the writer's own
    banded bets, not claims to verify, and its numbers must not trip the
    naked-number guard."""
    import re
    global PREDICTIONS_BLOCK_RE
    if PREDICTIONS_BLOCK_RE is None:
        PREDICTIONS_BLOCK_RE = re.compile(
            r"```predictions\s*\n(.*?)\n```\s*", re.DOTALL)
    m = PREDICTIONS_BLOCK_RE.search(text)
    if not m:
        return [], text
    try:
        raw = json.loads(m.group(1))
        records = raw if isinstance(raw, list) else []
    except json.JSONDecodeError:
        records = []
    return records, text[:m.start()] + text[m.end():]


def build_auto_predictions(data: dict, made: str | None = None) -> list:
    """Mechanically derivable bets from the base_rate tool calls of this run.

    A technical base rate becomes a prediction only if the subject is
    actually in the config's state on the last covered session (the writer
    calling the tool is evidence, but we verify against the panel). The
    growth-persistence rate becomes a prediction if the subject qualifies as
    high-growth via its latest report or forecast."""
    import base_rates as br

    made = made or datetime.now().strftime("%Y-%m-%d")
    code6 = str(data.get("code6", ""))
    out = []
    for key, r in (data.get("base_rates") or {}).items():
        cfg = r.get("config")
        if r.get("frequency_pct") is None:
            continue
        if cfg in br.TECHNICAL_CONFIGS:
            state = br.stock_in_config(code6, cfg)
            if not state["in_class"] or state["close_adj"] is None:
                continue
            h = int(key.rsplit("_", 2)[-2].rstrip("d") or 60)
            dd = int(key.rsplit("_", 2)[-1].rstrip("pct") or 15)
            out.append({
                "id": f"{code6}-{made}-{key}",
                "code": code6, "made": made, "kind": "price_drawdown",
                "event": f"进入{cfg}形态后{h}个交易日内最大回撤≥{dd}%",
                "params": {"horizon_sessions": h, "drawdown_pct": dd},
                "entry_adj": state["close_adj"], "entry_as_of": state["as_of"],
                "p": round(r["frequency_pct"] / 100, 4),
                "source": f"base_rate:{cfg}", "status": "open",
            })
        elif cfg == "growth_persistence":
            target = _growth_target_period(data)
            if target is None:
                continue
            out.append({
                "id": f"{code6}-{made}-growth_persistence_{target}",
                "code": code6, "made": made, "kind": "earnings_decel",
                "event": f"{target}期累计归母净利同比降速至20%以下",
                "params": {"target_period": target, "decel_below_pct": 20},
                "p": round(r["frequency_pct"] / 100, 4),
                "source": "base_rate:growth_persistence", "status": "open",
            })
    return out


def _growth_target_period(data: dict):
    """Next report period to test for deceleration, if the subject qualifies
    as high-growth (>=40% YoY in its latest report, annual, or forecast)."""
    f = data.get("fundamentals") or {}
    _PERIODS = {"一季报": "0331", "中报": "0630", "三季报": "0930", "年报": "1231"}

    def _parse(label):  # "2026一季报" -> ("2026", "0331")
        for name, mmdd in _PERIODS.items():
            if label and label.endswith(name):
                return label[:-len(name)], mmdd
        return None

    candidates = []
    for block, val_key in (("latest_report", "net_profit_yoy_pct"),
                           ("annual_report", "net_profit_yoy_pct")):
        b = f.get(block) or {}
        if (b.get(val_key) or 0) >= 40 and _parse(b.get("period")):
            candidates.append(_parse(b.get("period")))
    for fc in f.get("forecast") or []:
        if (fc.get("change_pct") or 0) >= 40:
            per = str(fc.get("period", ""))  # "2026H1" style
            mmdd = {"Q1": "0331", "H1": "0630", "Q1-Q3": "0930", "全年": "1231"}.get(per[4:])
            if mmdd:
                candidates.append((per[:4], mmdd))
    if not candidates:
        return None
    year, mmdd = max(candidates, key=lambda c: c[0] + c[1])
    order = ["0331", "0630", "0930", "1231"]
    i = order.index(mmdd)
    return f"{year}{order[i + 1]}" if i < 3 else f"{int(year) + 1}0331"


def _provider_ctx(resolved: str) -> tuple:
    """Client + model for a normalized provider name."""
    import llm_client

    if resolved == "anthropic":
        return llm_client._build_anthropic_client(), _provider_model("anthropic")
    # openai (default) and hybrid both use the OpenAI tool loop for free-form output.
    return llm_client._build_openai_client(), llm_client.OPENAI_MODEL


def _run_writer_pass(client, model, resolved, messages, tool_log, label,
                     extra_tools=None, tool_executor=None) -> tuple:
    """One tool-loop pass (draft or revise). Returns (text, tin, tout, rounds)."""
    import llm_client

    if resolved == "anthropic":
        return llm_client._run_tool_loop(
            client, messages, model, MAX_TOKENS, TEMPERATURE, tool_log, label=label,
            extra_tools=extra_tools, tool_executor=tool_executor)
    return llm_client._run_openai_tool_loop(
        client, messages, model, MAX_TOKENS, TEMPERATURE, tool_log, label=label,
        extra_tools=extra_tools, tool_executor=tool_executor)


def _make_runners(resolved, client, model, tool_log, totals,
                  verify_resolved=None, verify_client=None, verify_model=None,
                  extra_tools=None, tool_executor=None) -> tuple:
    """(revise_runner, judge_runner, cleanup_runner) for deep_verify.run_pipeline.

    Judge/cleanup are single no-tools calls (the _call_hybrid Pass-2 pattern);
    revise gets the full tool loop so it can re-search for better sources.
    All accumulate into `totals` so generate() can aggregate token counts.

    The verify_* trio lets judge/cleanup run on a DIFFERENT (fast/cheap) model
    than the writer — e.g. Kimi as the brain, DeepSeek as the verify agent.
    Defaults to the writer's provider when not given.
    """
    if verify_resolved is None:
        verify_resolved, verify_client, verify_model = resolved, client, model
    import threading

    import deep_verify
    import llm_client

    # judge_runner is called concurrently (per-URL fan-out) — guard the counters
    lock = threading.Lock()

    def _add(i: int, o: int, r: int):
        with lock:
            totals["in"] += i
            totals["out"] += o
            totals["rounds"] += r

    def revise_runner(prompt: str):
        t, i, o, r = _run_writer_pass(
            client, model, resolved, [{"role": "user", "content": prompt}],
            tool_log, label="verify-revise ",
            extra_tools=extra_tools, tool_executor=tool_executor)
        _add(i, o, r)
        return t, i, o, r

    def _text_once(prompt: str, label: str, max_tokens: int):
        if verify_resolved == "anthropic":
            t, i, o, _ = llm_client._run_anthropic_text_once(
                verify_client, [{"role": "user", "content": prompt}], verify_model,
                max_tokens, deep_verify.JUDGE_TEMPERATURE, label=label)
        else:
            resp = verify_client.chat.completions.create(
                model=verify_model,
                max_tokens=max_tokens,
                temperature=deep_verify.JUDGE_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
                timeout=llm_client.GPT_TIMEOUT,
            )
            usage = resp.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
            t, i, o = resp.choices[0].message.content or "", usage.prompt_tokens, usage.completion_tokens
        _add(i, o, 1)
        return t, i, o

    # Judge emits small JSON verdicts; cleanup must re-emit a FULL report, so it
    # gets the writer budget — 4096 would truncate it into uselessness.
    return (revise_runner,
            lambda p: _text_once(p, "verify-judge ", deep_verify.JUDGE_MAX_TOKENS),
            lambda p: _text_once(p, "verify-cleanup ", MAX_TOKENS))


def generate(code: str, provider: str | None = None, data: dict | None = None,
             verify: bool = True, max_verify_rounds: int = MAX_VERIFY_ROUNDS,
             verify_provider: str | None = None) -> dict:
    """Draft the article, then (unless verify=False) run the citation-verify
    pipeline: every number must be inline-linked and confirmed at its source,
    or tagged 〖内部数据〗 and matched against DATA. See agents/DEEP_VERIFY.md.

    verify_provider lets the judge/cleanup passes run on a different (fast/cheap)
    model than the writer — e.g. --provider anthropic (Kimi brain) with
    --verify-provider openai (DeepSeek verify agent). Default: same as writer.
    """
    import llm_client

    resolved, default_verify = _resolve_providers(provider, verify_provider)
    if verify_provider is None:
        verify_provider = default_verify
    spec = SPEC_FILE.read_text(encoding="utf-8")
    if data is None:
        data = gather_data(code)
    prompt = build_prompt(spec, code, data)
    messages = [{"role": "user", "content": prompt}]
    tool_log: list = []

    client, model = _provider_ctx(resolved)
    extra_tools, tool_executor = _make_report_tools(data)
    text, tin, tout, rounds = _run_writer_pass(
        client, model, resolved, messages, tool_log, label="deep_report ",
        extra_tools=extra_tools, tool_executor=tool_executor)
    judgment_bets, text = extract_predictions_block(text)

    verify_audit = None
    verify_rounds = 0
    if verify:
        import deep_verify

        spec_verify = VERIFY_SPEC_FILE.read_text(encoding="utf-8")
        totals = {"in": 0, "out": 0, "rounds": 0}
        v_resolved = v_client = v_model = None
        if verify_provider:
            v_resolved = llm_client.normalize_llm_provider(verify_provider)
            if v_resolved == resolved:
                v_client, v_model = client, model
            else:
                v_client, v_model = _provider_ctx(v_resolved)
            print(f"  [verify] judge/cleanup on {v_resolved}/{v_model}", file=sys.stderr)
        revise_runner, judge_runner, cleanup_runner = _make_runners(
            resolved, client, model, tool_log, totals,
            verify_resolved=v_resolved, verify_client=v_client, verify_model=v_model,
            extra_tools=extra_tools, tool_executor=tool_executor)
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

    # The prediction ledger: auto bets from base_rate calls (verified against
    # the subject's actual state) + the writer's judgment bets from the
    # ```predictions block. Caller decides whether to log (main() does).
    made = datetime.now().strftime("%Y-%m-%d")
    code6 = str(data.get("code6", ""))
    predictions = build_auto_predictions(data, made)
    for i, j in enumerate(judgment_bets, 1):
        if not isinstance(j, dict) or not j.get("event"):
            continue
        rec = {"id": f"{code6}-{made}-j{i}", "code": code6, "made": made,
               "kind": "manual", "event": str(j["event"]),
               "expires": str(j.get("expires", "")), "source": "judgment",
               "status": "open"}
        if j.get("p") is not None:
            rec["p"] = float(j["p"])
        elif j.get("p_low") is not None and j.get("p_high") is not None:
            rec["p_low"], rec["p_high"] = float(j["p_low"]), float(j["p_high"])
        else:
            continue  # a bet without a probability is not a bet
        predictions.append(rec)

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
        "predictions": predictions,
    }


def _stock_name(code6: str) -> str | None:
    """Chinese name from the local stocks table; None when unavailable."""
    try:
        import pricedb

        con = sqlite3.connect(str(pricedb.DB_PATH))
        try:
            row = con.execute("SELECT name FROM stocks WHERE code=?", (code6,)).fetchone()
        finally:
            con.close()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def _report_group_dir(code6: str) -> Path:
    """Per-stock report folder: reports/<code6>-<中文名> (name-less fallback:
    just the code). Explicit --output-dir bypasses grouping entirely."""
    import re

    import report_generator

    name = re.sub(r"[*/\\\s]", "", _stock_name(code6) or "")
    return report_generator.REPORTS_DIR / (f"{code6}-{name}" if name else code6)


def _report_out_dir(code6: str, output_dir) -> Path:
    out_dir = Path(output_dir) if output_dir else _report_group_dir(code6)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_report(code: str, text: str, output_dir=None) -> Path:
    code6 = str(code).split(".")[0]
    date = datetime.now().strftime("%Y-%m-%d")
    out = _report_out_dir(code6, output_dir) / f"{code6}-{date}-deep.md"
    out.write_text(text, encoding="utf-8")
    return out


def write_verify_audit(code: str, audit: dict, output_dir=None) -> Path:
    """Write the citation-verification audit JSON next to the report."""
    code6 = str(code).split(".")[0]
    date = datetime.now().strftime("%Y-%m-%d")
    out = _report_out_dir(code6, output_dir) / f"{code6}-{date}-deep-verify.json"
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
            "[--output-dir DIR] [--human] [--no-verify] [--max-verify-rounds N] "
            "[--verify-provider anthropic|openai]",
            file=sys.stderr,
        )
        sys.exit(2)

    code = args[0]
    provider = _arg_value(args, "--provider")
    output_dir = _arg_value(args, "--output-dir")
    human = "--human" in args
    verify = "--no-verify" not in args
    mvr = _arg_value(args, "--max-verify-rounds")
    verify_provider = _arg_value(args, "--verify-provider")

    import time
    t0 = time.time()
    w, v = _resolve_providers(provider, verify_provider)
    rounds_planned = int(mvr) if mvr else MAX_VERIFY_ROUNDS
    print("=" * 62, file=sys.stderr)
    print(f"[deep_report] {code}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"  writer : {w}/{_provider_model(w)}", file=sys.stderr)
    if verify:
        print(f"  verify : {v}/{_provider_model(v)}  (max {rounds_planned} rounds)", file=sys.stderr)
    else:
        print("  verify : OFF (--no-verify) — numbers will be unverified", file=sys.stderr)
    print("  stages : gather → draft (tools) → claim-verify → revise → cleanup", file=sys.stderr)
    print("=" * 62, file=sys.stderr)

    result = generate(code, provider=provider, verify=verify,
                      max_verify_rounds=rounds_planned,
                      verify_provider=verify_provider)
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

    if result.get("predictions"):
        import prediction_log

        n_new = prediction_log.append(result["predictions"])
        print(
            f"[deep_report] predictions: {len(result['predictions'])} bets "
            f"({n_new} new) → {prediction_log.PRED_FILE}",
            file=sys.stderr,
        )

    print(
        f"[deep_report] {result['provider']}/{result['model']} | {result['rounds']} rounds "
        f"| {len(result['tool_calls'])} tool calls "
        f"| {result['input_tokens']}+{result['output_tokens']} tok",
        file=sys.stderr,
    )
    print(f"[deep_report] wrote {out} ({(time.time() - t0) / 60:.1f} min total)", file=sys.stderr)

    if human:
        print(result["text"])
    else:
        print(str(out))


if __name__ == "__main__":
    main()
