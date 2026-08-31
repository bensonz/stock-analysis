"""web_fetch escalates husks to a headless browser — bounded, loud, optional.

August measurement that motivated this: 39 web_fetches, 6 under 600 chars —
JS search wrappers and anti-bot shells. The model asked for evidence, got 7
characters, and kept reasoning on air. requests stays the first attempt; the
crawl4ai browser (separate torch-heavy venv, subprocessed) is the escalation.

Non-negotiables pinned here:
- the browser is OPTIONAL: venv missing / crash / timeout degrades to the thin
  text WITH a loud note, never an exception — this runs unattended on launchd;
- escalation is BUDGETED per process, so a pathological page list cannot add
  minutes of browser spin-up to Phase 2;
- provenance is visible: escalated results are prefixed, so tool_call logs and
  later audits can tell rendered content from plain fetches;
- web_screenshot exists ONLY in the Anthropic tool list. The daily decision
  model (DeepSeek, openai path) is text-only; an image block in its tool_result
  would be rejected. Keeping the tool out of TOOLS is the guarantee.

All tests fake `_crawl4ai_run` — the subprocess seam llm_client owns. No
browser, no network.
"""
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import llm_client as lc


class _Resp:
    status_code = 200
    reason = "OK"

    def __init__(self, text):
        self.text = text
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"


@pytest.fixture(autouse=True)
def _fresh_budget(monkeypatch):
    monkeypatch.setattr(lc, "_crawl4ai_used", 0)


def _fetch(monkeypatch, page_text, crawl=(True, "# rendered markdown " * 50)):
    calls = []

    def fake_crawl(url, mode):
        calls.append((url, mode))
        return crawl

    monkeypatch.setattr(lc.requests, "get", lambda *a, **k: _Resp(page_text))
    monkeypatch.setattr(lc, "_crawl4ai_run", fake_crawl)
    out = lc.execute_web_fetch("http://x.test/page")
    return out, calls


def test_a_healthy_page_never_touches_the_browser(monkeypatch):
    body = "<p>" + "real article text " * 100 + "</p>"
    out, calls = _fetch(monkeypatch, body)
    assert calls == [], "escalated despite a full-bodied response"
    assert "crawl4ai" not in out


def test_a_husk_escalates_and_carries_provenance(monkeypatch):
    """The 28-char baidu wrapper case: thin text → rendered markdown, marked."""
    out, calls = _fetch(monkeypatch, "<div id=app></div>")
    assert calls == [("http://x.test/page", "markdown")]
    assert out.startswith("[via crawl4ai headless-browser fallback")
    assert "rendered markdown" in out


def test_a_request_error_also_escalates(monkeypatch):
    def boom(*a, **k):
        raise requests.Timeout()
    monkeypatch.setattr(lc.requests, "get", boom)
    monkeypatch.setattr(lc, "_crawl4ai_run", lambda u, m: (True, "rescued content " * 40))
    out = lc.execute_web_fetch("http://x.test/page")
    assert "rescued content" in out


def test_browser_failure_degrades_to_the_thin_text_loudly(monkeypatch):
    """launchd host: a broken Chromium must never take the run down, and must
    never be silent either — the thin text comes back with the reason."""
    out, _ = _fetch(monkeypatch, "<div id=app></div>",
                    crawl=(False, "crawl4ai venv not found at /nope"))
    assert "crawl4ai fallback failed" in out
    assert "venv not found" in out
    assert "treat as unverified" in out


def test_the_budget_caps_escalations_per_process(monkeypatch):
    monkeypatch.setattr(lc, "CRAWL4AI_MAX_PER_RUN", 2)
    n = 0

    def counting(url, mode):
        nonlocal n
        n += 1
        return True, "x" * 2000

    monkeypatch.setattr(lc.requests, "get", lambda *a, **k: _Resp("thin"))
    monkeypatch.setattr(lc, "_crawl4ai_run", counting)
    for _ in range(5):
        out = lc.execute_web_fetch("http://x.test/page")
    assert n == 2, "budget did not cap browser launches"
    assert "budget" in out, "post-budget result did not say why it is thin"


def test_escalated_output_respects_max_chars(monkeypatch):
    out, _ = _fetch(monkeypatch, "thin", crawl=(True, "y" * 50_000))
    assert len(out) < 10_000


# --- the screenshot tool ----------------------------------------------------

def test_screenshot_returns_image_and_text_blocks(monkeypatch):
    monkeypatch.setattr(lc, "_crawl4ai_run", lambda u, m: (True, "aGVsbG8="))
    got = lc.execute_web_screenshot("http://x.test/dash")
    assert isinstance(got, list)
    kinds = [b["type"] for b in got]
    assert kinds == ["image", "text"]
    assert got[0]["source"]["media_type"] == "image/png"
    assert got[0]["source"]["data"] == "aGVsbG8="


def test_screenshot_failure_returns_plain_text_advice(monkeypatch):
    monkeypatch.setattr(lc, "_crawl4ai_run", lambda u, m: (False, "boom"))
    got = lc.execute_web_screenshot("http://x.test/dash")
    assert isinstance(got, str) and "web_fetch" in got


def test_an_oversize_screenshot_is_refused_not_sent(monkeypatch):
    """The API hard-rejects >5MB images; refusing with advice beats a 400 that
    kills the whole tool round."""
    monkeypatch.setattr(lc, "_crawl4ai_run", lambda u, m: (True, "z" * (5 * 1024 * 1024)))
    got = lc.execute_web_screenshot("http://x.test/dash")
    assert isinstance(got, str) and "too large" in got


def test_the_text_only_provider_never_sees_the_tool():
    """THE provider-safety guarantee. web_screenshot must live only in
    ANTHROPIC_ONLY_TOOLS; if it leaks into TOOLS, the DeepSeek loop will offer
    it, the model will call it, and an image block lands in a text-only API."""
    assert all(t["name"] != "web_screenshot" for t in lc.TOOLS)
    assert any(t["name"] == "web_screenshot" for t in lc.ANTHROPIC_ONLY_TOOLS)


def test_dispatch_routes_the_screenshot_tool(monkeypatch):
    monkeypatch.setattr(lc, "_crawl4ai_run", lambda u, m: (True, "aGVsbG8="))
    got = lc.execute_tool("web_screenshot", {"url": "http://x.test"})
    assert isinstance(got, list) and got[0]["type"] == "image"
