#!/usr/bin/env python3
"""
Deep-report citation verification — mechanical claim extraction + verify pipeline.

Every number in a deep report must be either:
  - a `linked` claim: inline markdown link on the number, [43.14亿](https://…)
  - an `internal` claim: tagged 〖内部数据〗 (RPS/MA/klines from our own price DB)
Anything else with an ASCII digit (outside the allowlist: dates, stock codes,
评级 N/5, ordinals, indicator names…) is a `naked` claim and fails verification.

Extraction is pure python (regex) so it is deterministic and unit-testable; the
LLM is only used to judge whether a fetched page supports the numbers citing it.
See agents/DEEP_VERIFY.md for the judge spec and docs/deep_report_verify/ for
the implementation plan.
"""
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

TAG = "〖内部数据〗"
VERIFY_FETCH_MAX_CHARS = 20000  # verifier fetches more than the drafter's 8000
JUDGE_MAX_TOKENS = 8192
JUDGE_TEMPERATURE = 0.0
# Max claims per judge call. The 300037 run sent 23 internal claims in one
# batch: the verdict JSON truncated at max_tokens, parse failed twice, and all
# 23 correct numbers were scrubbed. Small batches keep each response parseable.
JUDGE_BATCH = int(os.getenv("DEEP_VERIFY_JUDGE_BATCH", "20"))

# --------------------------------------------------------------------------- #
# Regexes
# --------------------------------------------------------------------------- #
LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.S)
FOOTER_RE = re.compile(r"^数据核验[:：].*$", re.M)

# A number token: digits with optional decimals/commas, optional range tail,
# optional unit suffix. Used for display + cache keys, not arithmetic.
NUM_TOKEN_RE = re.compile(
    r"[0-9][0-9,，]*(?:\.[0-9]+)?"
    r"(?:\s*[–\-—~～至]\s*[0-9][0-9,，]*(?:\.[0-9]+)?)?"
    r"\s*(?:%|％|万亿|亿元|亿股|亿|万元|万股|万|元|倍|pp|bp|个百分点|天|日|家|店|股|吨|人|次|席)?"
)

# Numbers that need NO citation. Order-independent; all matches become covered
# spans. Tuned against reports/002832|002602|301345-2026-07-22-deep.md.
_YEAR = r"(?:19|20)\d{2}"
ALLOWLIST_RES = [re.compile(p) for p in [
    rf"{_YEAR}\s*[–\-—~～/]\s*(?:{_YEAR})?\s*年?",          # 2011–2025, 2024/2025年
    rf"{_YEAR}\s*年?(?:[QH][1-4])?",                        # 2025年, 2026Q1, 2026H1, bare 2026
    rf"{_YEAR}-\d{{1,2}}-\d{{1,2}}",                        # ISO date
    r"\d{1,2}月(?:\d{1,2}日)?",                              # 7月21日, 8月
    r"\d{1,2}日(?![0-9])",                                   # …日 leftovers
    # slash dates 7/21, 7/16–17 (month 1-12 / day 1-31, not part of a number)
    r"(?<![0-9.])(?:1[0-2]|0?[1-9])/(?:3[01]|[12]?[0-9])(?:\s*[–\-~～]\s*\d{1,2})?(?![0-9/])",
    r"\d{1,2}\s*个月(?![0-9])",                               # （9个月）duration
    r"(?<![A-Za-z0-9])FY\d{2,4}",                            # FY2026
    r"(?<![A-Za-z0-9])[QH][1-4](?![0-9])",                   # Q1 / H2 alone
    r"\d{6}\.(?:SZ|SH|BJ|HK)",                               # 002832.SZ
    r"[（(]\d{6}[）)]",                                       # （002832）
    # bare 6-digit stock code (table cells, prose): not part of a larger/decimal
    # number and not followed by a unit — real quantities carry 亿/万/元 etc.
    r"(?<![0-9.，,])\d{6}(?![0-9.%％亿万元倍股])",
    r"评级\s*[1-5]\s*[/／]\s*5",                              # 评级 4/5
    r"(?<![0-9.])[1-5]\s*[/／]\s*5(?![0-9])",                 # bare 4/5
    r"(?<![A-Za-z0-9])(?:RPS|MA|rps|ma)\s?\d{2,3}(?![0-9.=＝%％])",  # indicator names
    r"RPS\s*[≥>＞=]{1,2}\s*\d{2,3}",                          # RPS≥80 gate mentions
    # indicator-with-threshold comparisons: RPS60≥90, rps120>85 — the digits
    # name a screen condition, not a measured quantity
    r"(?<![A-Za-z0-9])(?:RPS|rps)\s*\d{2,3}\s*[≥≤>＞<＜]=?\s*\d{1,3}(?![0-9.%％])",
    r"近\s*\d+\s*(?:个)?(?:日|周|月|年|季|交易日)",             # 近1月
    r"\d+\s*(?:个)?交易日",                                    # 5个交易日
    r"[①②③④⑤⑥⑦⑧⑨⑩]",
]]
ALLOWLIST_LINE_RES = [re.compile(p, re.M) for p in [
    r"^\s{0,3}#{1,6}\s*\d+[.、]?",                            # "### 3. 风险提示"
    r"^\s*\d+[.、）)]",                                        # list ordinals
]]

_SEG_BOUNDARY_RE = re.compile(r"[。；;！？!?\n|]")


def _has_ascii_digit(s: str) -> bool:
    return any("0" <= ch <= "9" for ch in s)


_FW_TABLE = str.maketrans("０１２３４５６７８９％，．～", "0123456789%,.~")


def normalize_number(tok: str) -> str:
    """Canonical form for matching/caching: full-width→ASCII, strip separators."""
    return tok.translate(_FW_TABLE).replace(",", "").replace(" ", "")


def token_number_parts(tok: str) -> list:
    """Constituent numbers of a token, for part-wise mechanical matching.

    NUM_TOKEN_RE can produce compound tokens — "38.1–39.9" (range),
    "11442，95%" (sentence comma gluing two numbers), "2025-04" (dates) —
    whose normalize_number() form will never sit in the corpus as one string.
    Split them: a comma is treated as a thousands separator only in the
    strict 3-digit-groups form ("1,234"); otherwise it separates numbers.
    """
    parts = []
    for m in re.finditer(r"[0-9][0-9,]*(?:\.[0-9]+)?", tok.translate(_FW_TABLE)):
        p = m.group(0)
        if "," in p:
            segs = p.split(",")
            if all(len(s) == 3 for s in segs[1:]) and "." not in "".join(segs[:-1]):
                parts.append(p.replace(",", ""))
            else:
                parts.extend(s for s in segs if s)
        else:
            parts.append(p)
    return parts


def _allowlist_spans(text: str) -> list:
    spans = []
    for rx in ALLOWLIST_RES:
        spans.extend(m.span() for m in rx.finditer(text))
    for rx in ALLOWLIST_LINE_RES:
        spans.extend(m.span() for m in rx.finditer(text))
    return spans


def _merge_spans(spans: list) -> list:
    if not spans:
        return []
    spans = sorted(spans)
    out = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def _in_spans(pos: int, spans: list) -> bool:
    return any(s <= pos < e for s, e in spans)


def _context(text: str, start: int, end: int, radius: int = 80) -> str:
    return text[max(0, start - radius):min(len(text), end + radius)].replace("\n", " ")


_IND_NAME_PREFIX_RE = re.compile(r"(?:RPS|MA|rps|ma)\s?$")


def _is_indicator_name_digits(text: str, tok_start: int) -> bool:
    """True if the digit run at tok_start belongs to an indicator name (RPS60, MA20)."""
    return bool(_IND_NAME_PREFIX_RE.search(text[max(0, tok_start - 4):tok_start]))


def _claim_numbers(segment: str) -> list:
    """Number tokens in a claim segment, minus indicator-name digits."""
    return [m.group(0).strip() for m in NUM_TOKEN_RE.finditer(segment)
            if not _is_indicator_name_digits(segment, m.start())]


def _numbers_in(text: str, base_offset: int, covered: list) -> list:
    """Number tokens in `text` whose absolute position is not covered."""
    out = []
    for m in NUM_TOKEN_RE.finditer(text):
        if _in_spans(base_offset + m.start(), covered):
            continue
        if _is_indicator_name_digits(text, m.start()):
            continue
        out.append(m.group(0).strip())
    return out


# --------------------------------------------------------------------------- #
# Table analysis
# --------------------------------------------------------------------------- #
def _table_lines(text: str) -> list:
    """Return [(line_start, line_end, line, caption)] for markdown table rows."""
    rows = []
    lines = text.split("\n")
    pos = 0
    prev_nonempty = ""
    block_caption = ""
    in_table = False
    for line in lines:
        start, end = pos, pos + len(line)
        stripped = line.strip()
        if stripped.startswith("|"):
            if not in_table:
                block_caption = prev_nonempty
                in_table = True
            rows.append((start, end, line, block_caption))
        else:
            in_table = False
            if stripped:
                prev_nonempty = line
        pos = end + 1
    return rows


# --------------------------------------------------------------------------- #
# Claim extraction
# --------------------------------------------------------------------------- #
def extract_claims(markdown: str) -> list:
    """Extract linked / internal / naked claims from a report draft.

    Returns claim dicts sorted by span start:
      {id, kind, numbers, context, url, span, status, reason, fallback_text}
    """
    text = markdown
    covered = []          # spans exempt from the naked scan
    claims = []

    # 0. Structural exemptions
    covered.extend(m.span() for m in FENCE_RE.finditer(text))
    covered.extend(m.span() for m in FOOTER_RE.finditer(text))
    allow = _allowlist_spans(text)
    covered.extend(allow)
    covered = _merge_spans(covered)

    # 1. Tables: a row is covered by its first link (all row numbers → that URL)
    #    or by 〖内部数据〗 in the row or the table caption.
    table_row_spans = []
    for start, end, line, caption in _table_lines(text):
        link = LINK_RE.search(line)
        tagged = TAG in line or TAG in caption
        row_nums = _numbers_in(line, start, _merge_spans(allow))
        if link and _has_ascii_digit(line):
            claims.append({
                "kind": "linked", "url": link.group(2),
                "numbers": row_nums or [link.group(1)],
                "span": (start, end), "context": line.strip()[:200],
            })
            table_row_spans.append((start, end))
        elif tagged and _has_ascii_digit(line):
            claims.append({
                "kind": "internal", "url": None, "numbers": row_nums,
                "span": (start, end), "context": line.strip()[:200],
            })
            table_row_spans.append((start, end))
        elif not _has_ascii_digit(line):
            table_row_spans.append((start, end))  # header/separator rows
    covered = _merge_spans(covered + table_row_spans)

    # 2. Inline links (outside covered table rows)
    for m in LINK_RE.finditer(text):
        if _in_spans(m.start(), covered):
            continue
        label, url = m.group(1), m.group(2)
        if _has_ascii_digit(label):
            claims.append({
                "kind": "linked", "url": url,
                "numbers": _claim_numbers(label),
                "span": m.span(), "context": _context(text, m.start(), m.end()),
            })
        # digit-free labels create no claim, but the whole link (incl. URL
        # digits) is exempt from the naked scan either way
        covered = _merge_spans(covered + [m.span()])

    # 3. 〖内部数据〗 segments (outside covered table rows)
    link_spans = [lm.span() for lm in LINK_RE.finditer(text)]
    for m in re.finditer(re.escape(TAG), text):
        if _in_spans(m.start(), covered):
            continue
        seg_start = 0
        for b in _SEG_BOUNDARY_RE.finditer(text, max(0, m.start() - 80), m.start()):
            seg_start = b.end()
        seg_start = max(seg_start, m.start() - 80)
        # never start mid-link: a segment that cuts a [label](url) in half
        # would later mangle the link when its span gets replaced
        for ls, le in link_spans:
            if ls < seg_start < le:
                seg_start = le
        segment = text[seg_start:m.start()]
        claims.append({
            "kind": "internal", "url": None,
            "numbers": _claim_numbers(segment),
            "span": (seg_start, m.end()), "context": segment.strip()[:200],
        })
        covered = _merge_spans(covered + [(seg_start, m.end())])

    # 4. Naked numbers: anything left with an ASCII digit
    for m in NUM_TOKEN_RE.finditer(text):
        if _in_spans(m.start(), covered):
            continue
        claims.append({
            "kind": "naked", "url": None, "numbers": [m.group(0).strip()],
            "span": m.span(), "context": _context(text, m.start(), m.end()),
        })

    claims.sort(key=lambda c: c["span"][0])
    for i, c in enumerate(claims, 1):
        c["id"] = f"c{i:03d}"
        c.setdefault("status", "pending")
        c.setdefault("reason", "")
        c.setdefault("fallback_text", None)
    return claims


def covered_spans(markdown: str) -> list:
    """Expose the exempt spans (fences, footer, allowlist) — for tests."""
    spans = [m.span() for m in FENCE_RE.finditer(markdown)]
    spans += [m.span() for m in FOOTER_RE.finditer(markdown)]
    spans += _allowlist_spans(markdown)
    return _merge_spans(spans)


# --------------------------------------------------------------------------- #
# Internal-data matching
# --------------------------------------------------------------------------- #
def flatten_data_numbers(data: dict) -> set:
    """All numeric values in the DATA block, as normalized string variants."""
    out = set()

    def _add(v: float):
        if v != v:  # NaN
            return
        out.add(normalize_number(repr(v)))
        out.add(normalize_number(f"{v:.1f}"))
        out.add(normalize_number(f"{v:.2f}"))
        if float(v).is_integer():
            out.add(normalize_number(str(int(v))))

    def _walk(node):
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            _add(float(node))
        elif isinstance(node, str):
            # simple digit runs (NOT the range-aware token regex — each range
            # endpoint must land in the set separately, e.g. "55~60亿" → 55, 60)
            for t in re.finditer(r"[0-9][0-9,，]*(?:\.[0-9]+)?", node):
                out.add(normalize_number(t.group(0)))
        elif isinstance(node, dict):
            for k, v in node.items():
                # key digits too: "wilson95_pct"/"rps60" label the values a
                # writer restates alongside them ("95%CI", "RPS60")
                if isinstance(k, str):
                    for t in re.finditer(r"[0-9][0-9]*(?:\.[0-9]+)?", k):
                        out.add(normalize_number(t.group(0)))
                _walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                _walk(v)

    _walk(data)
    return out


def internal_numbers_match(numbers: list, data_numbers: set) -> bool:
    """Mechanical check: every numeric token appears in the DATA block.

    Compound tokens (ranges, comma-glued pairs, partial dates) match part-wise:
    EVERY constituent number must be in the corpus — "38.1–39.9" needs both
    endpoints present, not just the first.
    """
    for tok in numbers:
        if normalize_number(tok) in data_numbers:
            continue
        parts = token_number_parts(tok)
        if not parts:  # no digits at all — nothing to verify
            continue
        if all(p in data_numbers for p in parts):
            continue
        return False
    return True


# --------------------------------------------------------------------------- #
# Verification round
# --------------------------------------------------------------------------- #
GENERIC_FALLBACK = "（数据未核实，略）"
_FETCH_ERROR_PREFIXES = ("HTTP ", "Timeout", "Error", "Tavily")
_MIN_PAGE_CHARS = 200
# Per-URL fetch+judge fan-out. Each unique URL is independent (own fetch, own
# judge call, own claim group), so verify wall-clock ≈ slowest URL, not the sum.
VERIFY_MAX_WORKERS = int(os.getenv("DEEP_VERIFY_MAX_WORKERS", "6"))


def _numsig(claim: dict) -> tuple:
    return tuple(sorted(normalize_number(t) for t in claim["numbers"]))


def parse_verdicts(text: str) -> dict | None:
    """Extract {"verdicts": {id: {...}}} from judge output; None on failure."""
    import llm_client
    try:
        obj = llm_client._parse_json_from_text(text)
    except Exception:
        return None
    verdicts = obj.get("verdicts") if isinstance(obj, dict) else None
    return verdicts if isinstance(verdicts, dict) else None


def _judge_with_retry(judge_runner, prompt: str):
    """One retry on unparseable JSON. Returns (verdicts|None, tin, tout)."""
    tin = tout = 0
    for _ in range(2):
        text, i, o = judge_runner(prompt)
        tin += i
        tout += o
        verdicts = parse_verdicts(text)
        if verdicts is not None:
            return verdicts, tin, tout
    return None, tin, tout


def _apply_verdict(claim: dict, v: dict | None):
    # Missing/unparseable verdict is a JUDGE outage, not a verdict on the
    # claim. judge_error claims are re-judged next round and, if the outage
    # persists, KEPT with a footer disclosure — never scrubbed. (Scrubbing
    # correct numbers because the verify service hiccuped is the wrong
    # failure direction; see the 300037 post-mortem.)
    if not isinstance(v, dict) or v.get("verdict") not in ("supported", "not_found", "contradicted"):
        claim["status"] = "judge_error"
        claim["reason"] = "核验服务输出缺失或无法解析（数字保留，未复核）"
        return
    if v["verdict"] == "supported":
        claim["status"] = "verified"
    else:
        claim["status"] = "failed"
        claim["reason"] = v.get("reason", v["verdict"])
        claim["fallback_text"] = v.get("fallback_text")


def build_judge_prompt(spec_verify: str, url: str, page_text: str, claims: list) -> str:
    items = [{"id": c["id"], "numbers": c["numbers"], "context": c["context"]} for c in claims]
    return (
        spec_verify
        + "\n\n---\n\n# 模式\n外部页面核验\n"
        + f"\n# 页面URL\n{url}\n"
        + "\n# 页面文本（可能被截断，只依据在场内容判断）\n"
        + page_text
        + "\n\n# 待核验条目 (JSON)\n```json\n"
        + json.dumps(items, ensure_ascii=False, indent=1)
        + "\n```\n\n只输出JSON verdicts，不要任何其他文字。\n"
    )


def build_internal_judge_prompt(spec_verify: str, data: dict, claims: list) -> str:
    slim = {k: data.get(k)
            for k in ("technicals", "rps_gate", "margin",
                      "fundamentals", "peer_fundamentals", "base_rates")
            if k in data}
    items = [{"id": c["id"], "numbers": c["numbers"], "context": c["context"]} for c in claims]
    return (
        spec_verify
        + "\n\n---\n\n# 模式\n内部DATA核验（数值须可由DATA直接得到或简单推导）\n"
        + "\n# DATA (JSON)\n```json\n"
        + json.dumps(slim, ensure_ascii=False, indent=1)
        + "\n```\n\n# 待核验条目 (JSON)\n```json\n"
        + json.dumps(items, ensure_ascii=False, indent=1)
        + "\n```\n\n只输出JSON verdicts，不要任何其他文字。\n"
    )


def verify_claims(claims: list, data_numbers: set, data: dict, *, spec_verify: str,
                  judge_runner, fetch, cache: dict) -> dict:
    """Mutate claim statuses in place. Returns round record for the audit."""
    fetches = []
    judge_in = judge_out = 0

    # Naked numbers: a number whose values all match the internal DATA corpus
    # is an internal claim missing its tag — a formatting lapse, not a lie.
    # Verify it as internal (2026-08-07: the 601168 run hard-failed 58 such
    # claims, overloaded the revise pass into degenerate output, and the
    # cleanup scrubbed the report into adjectives); the missing tag itself is
    # added mechanically by _tag_naked_data_numbers at pipeline end. Numbers
    # matching nothing still fail mechanically.
    for c in claims:
        if c["kind"] == "naked":
            if c["numbers"] and internal_numbers_match(c["numbers"], data_numbers):
                c["kind"] = "internal"
            else:
                c["status"] = "failed"
                c["reason"] = "数字缺少引用链接或〖内部数据〗标注"

    # Internal: mechanical match first — BEFORE the cache. The DATA corpus can
    # grow mid-pipeline (revise passes fetch peer fundamentals via the
    # stock_fundamentals tool), so a claim that failed in round 1 may match
    # mechanically in round 2; a stale cached "failed" must not pin it.
    unmatched = []
    for c in (c for c in claims if c["kind"] == "internal"):
        key = ("__internal__", _numsig(c))
        cached = cache.get(key)
        if internal_numbers_match(c["numbers"], data_numbers):
            c["status"] = "verified"
            cache[key] = ("verified", "", None)
        elif cached is not None and cached[0] != "judge_error":
            # a judge_error is an outage marker, not a verdict — re-judge it
            c["status"], c["reason"], c["fallback_text"] = cached
        else:
            unmatched.append(c)
    # Judge in small batches: one oversized call that truncates loses verdicts
    # for the WHOLE batch; chunking bounds the blast radius of any one failure.
    for start in range(0, len(unmatched), JUDGE_BATCH):
        chunk = unmatched[start:start + JUDGE_BATCH]
        verdicts, i, o = _judge_with_retry(
            judge_runner, build_internal_judge_prompt(spec_verify, data, chunk))
        judge_in += i
        judge_out += o
        for c in chunk:
            _apply_verdict(c, (verdicts or {}).get(c["id"]))
            cache[("__internal__", _numsig(c))] = (c["status"], c["reason"], c["fallback_text"])

    # Linked: one fetch per unique URL, one batched judge call per URL.
    # URLs are independent — fan out (wall-clock ≈ slowest URL, not the sum).
    groups: dict = {}
    for c in (c for c in claims if c["kind"] == "linked"):
        key = (c["url"], _numsig(c))
        cached = cache.get(key)
        if cached is not None and cached[0] != "judge_error":
            c["status"], c["reason"], c["fallback_text"] = cached
        else:
            groups.setdefault(c["url"], []).append(c)

    lock = threading.Lock()

    def _verify_url_group(url: str, cs: list) -> tuple:
        page = fetch(url)
        ok = bool(page) and not page.startswith(_FETCH_ERROR_PREFIXES) and len(page) >= _MIN_PAGE_CHARS
        rec = {"url": url, "ok": ok, "chars": len(page or "")}
        if not ok:
            with lock:
                for c in cs:
                    c["status"] = "unreachable"
                    c["reason"] = "来源无法访问或内容过短，请更换可访问的来源（优先巨潮资讯/东方财富/官方公告）"
                    cache[(url, _numsig(c))] = (c["status"], c["reason"], None)
            return rec, 0, 0
        ti = to = 0
        for start in range(0, len(cs), JUDGE_BATCH):
            chunk = cs[start:start + JUDGE_BATCH]
            verdicts, i, o = _judge_with_retry(
                judge_runner, build_judge_prompt(spec_verify, url, page, chunk))
            ti += i
            to += o
            with lock:
                for c in chunk:
                    _apply_verdict(c, (verdicts or {}).get(c["id"]))
                    cache[(url, _numsig(c))] = (c["status"], c["reason"], c["fallback_text"])
        return rec, ti, to

    if groups:
        with ThreadPoolExecutor(max_workers=min(VERIFY_MAX_WORKERS, len(groups))) as ex:
            futures = [ex.submit(_verify_url_group, url, cs) for url, cs in groups.items()]
            for fut in as_completed(futures):
                rec, i, o = fut.result()
                fetches.append(rec)
                judge_in += i
                judge_out += o

    counts = {
        "linked": sum(1 for c in claims if c["kind"] == "linked"),
        "internal": sum(1 for c in claims if c["kind"] == "internal"),
        "naked": sum(1 for c in claims if c["kind"] == "naked"),
        "verified": sum(1 for c in claims if c["status"] == "verified"),
        "failed": sum(1 for c in claims if c["status"] == "failed"),
        "unreachable": sum(1 for c in claims if c["status"] == "unreachable"),
        "judge_error": sum(1 for c in claims if c["status"] == "judge_error"),
    }
    return {
        "claims": [dict(c, span=list(c["span"])) for c in claims],
        "fetches": fetches,
        "counts": counts,
        "judge_tokens": {"in": judge_in, "out": judge_out},
    }


# --------------------------------------------------------------------------- #
# Revise / cleanup / mechanical guarantee
# --------------------------------------------------------------------------- #
def _failed(claims: list) -> list:
    return [c for c in claims if c["status"] in ("failed", "unreachable")]


def _failed_items_json(failed: list) -> str:
    items = [{"id": c["id"], "kind": c["kind"], "numbers": c["numbers"],
              "context": c["context"], "url": c["url"],
              "status": c["status"], "reason": c["reason"]} for c in failed]
    return json.dumps(items, ensure_ascii=False, indent=1)


def build_revise_prompt(spec_writer: str, draft: str, failed: list,
                        data_slim: dict, round_no: int, max_rounds: int) -> str:
    return (
        spec_writer
        + f"\n\n---\n\n# 修订任务（第{round_no}/{max_rounds}轮核验后）\n"
        + "下面是你此前的报告草稿，以及未通过数据核验的条目清单。对每一条，你必须三选一：\n"
        + "①把数字改为与所引来源一致；②用 web_search/web_fetch 找到真正包含该数字的页面并"
        + "更换链接（优先巨潮资讯/东方财富/官方公告，避免需登录的页面）；③改写为不含具体数字"
        + "的定性表述（如\"定位高端\"）或删除该句。\n"
        + "严格要求：输出**完整**修订后报告；不得改动未被列出的部分；已通过核验的链接原样保留；"
        + "不得新增任何没有链接或〖内部数据〗标注的数字。\n"
        + "\n# 当前草稿\n"
        + draft
        + "\n\n# 核验失败清单 (JSON)\n```json\n"
        + _failed_items_json(failed)
        + "\n```\n\n# DATA（内部数据，供〖内部数据〗标注修正）\n```json\n"
        + json.dumps(data_slim, ensure_ascii=False, indent=1)
        + "\n```\n"
    )


def _seg_start_for(text: str, pos: int) -> int:
    """Segment start exactly as extract_claims computes it for a tag at pos."""
    seg_start = 0
    for b in _SEG_BOUNDARY_RE.finditer(text, max(0, pos - 80), pos):
        seg_start = b.end()
    return max(seg_start, pos - 80)


def _tag_naked_data_numbers(text: str, data_numbers: set) -> tuple:
    """Mechanically append 〖内部数据〗 after naked numbers whose values all
    match the internal DATA corpus (2026-08-07: labeling lapses must not get
    true numbers scrubbed). A tag is only inserted when EVERY naked number in
    the segment it would cover also matches — no smuggling an unverified
    neighbour under a true tag. Returns (text, tags_inserted)."""
    total = 0
    for _ in range(4):  # insertions shift offsets → re-extract until stable
        claims = extract_claims(text)
        naked = [c for c in claims if c["kind"] == "naked"]
        matched = {id(c) for c in naked
                   if c["numbers"] and internal_numbers_match(c["numbers"], data_numbers)}
        candidates = [c for c in naked if id(c) in matched]
        if not candidates:
            break
        inserted = []
        claimed_from = None  # left edge of the last (rightmost-first) segment
        for c in sorted(candidates, key=lambda c: -c["span"][1]):
            pos = c["span"][1]
            if claimed_from is not None and pos > claimed_from:
                continue  # already covered by a tag scheduled to its right
            seg = _seg_start_for(text, pos)
            in_seg = [o for o in naked if seg <= o["span"][0] and o["span"][1] <= pos]
            if any(id(o) not in matched for o in in_seg):
                continue  # an unverified number would ride under this tag
            inserted.append(pos)
            claimed_from = seg
        if not inserted:
            break
        for pos in inserted:  # already descending
            text = text[:pos] + TAG + text[pos:]
        total += len(inserted)
    return text, total


def build_cleanup_prompt(draft: str, failed: list) -> str:
    return (
        "你是报告清理器。下面报告中列出的条目未通过数据核验。把每一条改写为不含具体数字的"
        "定性表述，或删除整句。禁止新增任何数字、任何链接。输出完整报告，其余部分逐字保留。\n"
        + "\n# 报告\n"
        + draft
        + "\n\n# 未通过核验条目 (JSON)\n```json\n"
        + _failed_items_json(failed)
        + "\n```\n"
    )


def apply_mechanical_fallback(text: str, failed: list) -> tuple:
    """Deterministically replace failed claim spans. Returns (text, count).

    Two hazards handled here (both produced mangled output in live runs):
    - a claim span may start/end MID-LINK (the internal-segment scan caps at 80
      chars and URLs contain no sentence boundaries) → snap the span outward to
      whole-link boundaries so no half-URL survives as naked digits;
    - spans may overlap/nest (two 〖内部数据〗 tags in one sentence) → merge
      overlapping spans and replace once, never with stale offsets.
    """
    links = [m.span() for m in LINK_RE.finditer(text)]

    def _snap(s: int, e: int) -> tuple:
        for ls, le in links:
            if ls < s < le:
                s = ls
            if ls < e < le:
                e = le
        return s, e

    scheduled = []  # non-overlapping (start, end, repl), ascending
    for c in sorted(failed, key=lambda c: (c["span"][0], -c["span"][1])):
        s, e = _snap(*c["span"])
        repl = c.get("fallback_text") or GENERIC_FALLBACK
        if _has_ascii_digit(repl):  # a fallback may not smuggle numbers back in
            repl = GENERIC_FALLBACK
        if scheduled and s <= scheduled[-1][1]:
            ps, pe, prepl = scheduled[-1]
            scheduled[-1] = (ps, max(pe, e), prepl)  # merge into the earlier span
        else:
            scheduled.append((s, e, repl))

    for s, e, repl in reversed(scheduled):
        text = text[:s] + repl + text[e:]
    return text, len(scheduled)


def strip_preamble(text: str) -> str:
    """Cut writer chatter ("Now I have all the verified data…") before the report.

    The report proper starts at the first markdown H1. Only strips when the H1
    appears within the first 2000 chars — a missing H1 means degenerate output,
    which the caller's length guard handles.
    """
    m = re.search(r"^# ", text, re.M)
    if m and 0 < m.start() <= 2000:
        return text[m.start():]
    return text


def verification_footer(final: dict) -> str:
    line = (
        "\n\n---\n数据核验："
        f"{final['total']}处数字，"
        f"{final['verified_linked'] + final['verified_internal']}处已核验"
        f"（{final['verified_linked']}外链/{final['verified_internal']}内部），"
        f"{final['rewritten_qualitative']}处已改写为定性表述。"
    )
    if final.get("kept_unreviewed"):
        line += f"⚠️ {final['kept_unreviewed']}处因核验服务异常未复核（数字按原样保留）。"
    return line + "\n"


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def run_pipeline(draft_text: str, data: dict, *, spec_writer: str, spec_verify: str,
                 max_rounds: int, judge_runner, revise_runner, cleanup_runner,
                 fetch=None, log=None) -> tuple:
    """draft → (verify → revise)* → cleanup → mechanical guarantee.

    All LLM access goes through the injected runners:
      judge_runner(prompt)   -> (text, tin, tout)          no tools
      revise_runner(prompt)  -> (text, tin, tout, rounds)  with tools
      cleanup_runner(prompt) -> (text, tin, tout)          no tools
    Returns (final_text_with_footer, audit).
    """
    if fetch is None:
        import llm_client
        fetch = lambda url: llm_client.execute_web_fetch(url, VERIFY_FETCH_MAX_CHARS)  # noqa: E731
    log = log if log is not None else (lambda msg: None)

    def _slim(d: dict) -> dict:
        s = {k: v for k, v in d.items() if k not in ("intro", "valuation_history")}
        if isinstance(s.get("technicals"), dict):
            s["technicals"] = {k: v for k, v in s["technicals"].items() if k != "klines"}
        return s

    cache: dict = {}
    audit = {"max_rounds": max_rounds, "rounds": [],
             "cleanup": {"used": False, "mechanical_fallbacks": 0}}
    text = strip_preamble(draft_text)
    claims: list = []

    for rnd in range(1, max_rounds + 1):
        # Recomputed per round: revise passes can grow `data` (the
        # stock_fundamentals tool stores peer snapshots into it), and new
        # 〖内部数据〗 claims must verify against the grown corpus.
        data_numbers = flatten_data_numbers(data)
        claims = extract_claims(text)
        log(f"verify round {rnd}: {len(claims)} claims")
        rec = verify_claims(claims, data_numbers, data, spec_verify=spec_verify,
                            judge_runner=judge_runner, fetch=fetch, cache=cache)
        rec["round"] = rnd
        audit["rounds"].append(rec)
        failed = _failed(claims)
        errored = [c for c in claims if c["status"] == "judge_error"]
        log(f"verify round {rnd}: {rec['counts']['verified']} verified, "
            f"{len(failed)} failed, {len(errored)} judge-errored")
        if not failed and not errored:
            break
        if rnd == max_rounds:
            break
        if not failed:
            # judge outage only — there is nothing for the writer to fix.
            # judge_error is never cache-pinned, so looping re-judges them.
            log(f"verify round {rnd}: judge errors only — re-judging next round")
            continue
        revised, _tin, _tout, _rr = revise_runner(
            build_revise_prompt(spec_writer, text, failed, _slim(data), rnd, max_rounds))
        revised = strip_preamble(revised or "")
        if not revised or len(revised) < 0.4 * len(text):
            # One retry on a fresh conversation before giving up — a single
            # truncated/empty revision must not condemn the report to the
            # qualitative scrubber (2026-08-07, 601168).
            log("revise pass degenerate — retrying once")
            revised, _tin, _tout, _rr = revise_runner(
                build_revise_prompt(spec_writer, text, failed, _slim(data), rnd, max_rounds))
            revised = strip_preamble(revised or "")
        if revised and len(revised) >= 0.4 * len(text):
            text = revised
        else:  # garbage/empty revision twice: keep draft, skip to cleanup
            log("revise pass returned degenerate output; skipping to cleanup")
            break

    # Mechanical tag guard: DATA-backed naked numbers get their missing
    # 〖内部数据〗 tag appended, then re-verify (cache + mechanical match —
    # no writer involvement) so downstream spans see the final text.
    data_numbers = flatten_data_numbers(data)
    text, tagged = _tag_naked_data_numbers(text, data_numbers)
    if tagged:
        log(f"tag guard: annotated {tagged} DATA-backed naked numbers")
        audit["cleanup"]["tag_guard"] = tagged
        claims = extract_claims(text)
        rec = verify_claims(claims, data_numbers, data, spec_verify=spec_verify,
                            judge_runner=judge_runner, fetch=fetch, cache=cache)
        rec["round"] = "tag_guard"
        audit["rounds"].append(rec)

    failed = _failed(claims)
    if failed:
        data_numbers = flatten_data_numbers(data)  # corpus may have grown in the last revise
        audit["cleanup"]["used"] = True
        cleaned, _i, _o = cleanup_runner(build_cleanup_prompt(text, failed))
        cleaned = strip_preamble(cleaned or "")
        if cleaned and len(cleaned) >= 0.4 * len(text):
            text = cleaned
        # Post-cleanup: cache-verified claims pass; anything else unverified is
        # mechanically replaced. Iterate until no residual remains — a single
        # pass is not enough because replacing one span can expose neighbours
        # (e.g. a snapped span deleting a link changes what is naked around it).
        def _classify(cs: list) -> list:
            residual = []
            for c in cs:
                if c["kind"] == "naked":
                    residual.append(c)
                elif c["kind"] == "internal":
                    st = cache.get(("__internal__", _numsig(c)), ("",))[0]
                    if st == "verified" or \
                            internal_numbers_match(c["numbers"], data_numbers):
                        c["status"] = "verified"
                    elif st == "judge_error":
                        c["status"] = "judge_error"  # kept; disclosed in footer
                    else:
                        residual.append(c)
                else:
                    st = cache.get((c["url"], _numsig(c)), ("",))[0]
                    if st == "verified":
                        c["status"] = "verified"
                    elif st == "judge_error":
                        c["status"] = "judge_error"  # kept; disclosed in footer
                    else:
                        residual.append(c)
            return residual

        total_fallbacks = 0
        for _pass in range(4):
            # cleanup output can reintroduce naked-but-DATA-backed numbers;
            # tag them rather than scrub them
            text, t2 = _tag_naked_data_numbers(text, data_numbers)
            if t2:
                audit["cleanup"]["tag_guard"] = audit["cleanup"].get("tag_guard", 0) + t2
            claims = extract_claims(text)
            residual = _classify(claims)
            if not residual:
                break
            text, n = apply_mechanical_fallback(text, residual)
            total_fallbacks += n
            log(f"mechanical guard pass {_pass + 1}: replaced {n} spans")
        else:  # exhausted: recompute final state (residual here should be impossible)
            claims = extract_claims(text)
            if _classify(claims):
                log("WARNING: mechanical guard did not converge — unverified numbers remain")
        audit["cleanup"]["mechanical_fallbacks"] = total_fallbacks

    rewritten = sum(r["counts"]["failed"] + r["counts"]["unreachable"]
                    for r in audit["rounds"][-1:]) if audit["cleanup"]["used"] else 0
    final = {
        "total": len(claims),
        "verified_linked": sum(1 for c in claims if c["kind"] == "linked" and c["status"] == "verified"),
        "verified_internal": sum(1 for c in claims if c["kind"] == "internal" and c["status"] == "verified"),
        "rewritten_qualitative": rewritten,
        # judge outage: numbers deliberately kept, disclosed in the footer —
        # counted apart from unverified_remaining (the guarantee-violation alarm)
        "kept_unreviewed": sum(1 for c in claims if c["status"] == "judge_error"),
        "unverified_remaining": sum(1 for c in claims if c["status"] not in ("verified", "judge_error")),
    }
    audit["final"] = final
    return text + verification_footer(final), audit
