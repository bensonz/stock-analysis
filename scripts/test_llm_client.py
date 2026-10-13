import os
from pathlib import Path

import llm_client


def test_normalize_llm_provider_aliases():
    assert llm_client.normalize_llm_provider("openai") == "openai"
    assert llm_client.normalize_llm_provider("gpt") == "openai"
    assert llm_client.normalize_llm_provider("hybrid") == "hybrid"
    assert llm_client.normalize_llm_provider("claude") == "anthropic"
    assert llm_client.normalize_llm_provider("anthropic") == "anthropic"


def test_normalize_llm_provider_invalid():
    try:
        llm_client.normalize_llm_provider("bogus")
    except ValueError as exc:
        assert "Unknown LLM provider" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid provider")


def test_read_env_file_strips_quotes(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'OPENAI_API_KEY="abc123"\nANTHROPIC_API_KEY=\'xyz789\'\n# comment\n',
        encoding="utf-8",
    )
    values = llm_client._read_env_file(env_file)
    assert values["OPENAI_API_KEY"] == "abc123"
    assert values["ANTHROPIC_API_KEY"] == "xyz789"


def test_parse_json_prefers_dict_over_earlier_list_block():
    """Regression: 2026-07-13 afternoon run failed because the model emitted a
    standalone ``new_learnings`` array in its own ```json block *before* the
    full decision object. The parser must skip the list and return the dict."""
    text = (
        "## Research Memo\n\nSome prose.\n\n"
        "```json\n"
        '[{"text": "a learning", "type": "heuristic"}]\n'
        "```\n\n"
        "More prose.\n\n"
        "```json\n"
        '{"market_call": "恐慌", "new_positions": [], '
        '"new_learnings": [{"text": "a learning"}]}\n'
        "```\n"
    )
    result = llm_client._parse_json_from_text(text)
    assert isinstance(result, dict)
    assert result["market_call"] == "恐慌"
    assert result["new_positions"] == []


def test_parse_json_direct_list_is_not_accepted():
    """A top-level JSON list is never a valid decision object -> {}."""
    assert llm_client._parse_json_from_text('[{"text": "x"}]') == {}


def test_get_env_value_prefers_process_env_over_file(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('OPENAI_API_KEY=file_value\n', encoding="utf-8")
    monkeypatch.setattr(llm_client, "ENV_FILE", env_file)
    monkeypatch.setenv("OPENAI_API_KEY", "process_value")
    assert llm_client._get_env_value("OPENAI_API_KEY") == "process_value"


def test_get_env_value_falls_back_to_file(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('TAVILY_API_KEY=file_value\n', encoding="utf-8")
    monkeypatch.setattr(llm_client, "ENV_FILE", env_file)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    assert llm_client._get_env_value("TAVILY_API_KEY") == "file_value"


def test_read_claude_settings_env(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        '{"env": {"ANTHROPIC_AUTH_TOKEN": "token123", "ANTHROPIC_BASE_URL": "http://example.com/api", "name": "profile"}}',
        encoding="utf-8",
    )
    values = llm_client._read_claude_settings_env(settings_file)
    assert values["ANTHROPIC_AUTH_TOKEN"] == "token123"
    assert values["ANTHROPIC_BASE_URL"] == "http://example.com/api"
    assert values["name"] == "profile"


def test_get_env_value_falls_back_to_claude_settings(tmp_path: Path, monkeypatch):
    settings_file = tmp_path / "settings.json"
    settings_file.write_text(
        '{"env": {"ANTHROPIC_AUTH_TOKEN": "settings_token", "ANTHROPIC_BASE_URL": "http://settings.example/api"}}',
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text('', encoding="utf-8")
    monkeypatch.setattr(llm_client, "CLAUDE_SETTINGS_FILE", settings_file)
    monkeypatch.setattr(llm_client, "ENV_FILE", env_file)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    assert llm_client._get_env_value("ANTHROPIC_AUTH_TOKEN") == "settings_token"
    assert llm_client._get_env_value("ANTHROPIC_API_URL", "ANTHROPIC_BASE_URL") == "http://settings.example/api"


# --------------------------------------------------------------------------- #
# Truncation signal (2026-10-13: a cut-off deep-report revision was returned as
# a finished answer — the loop treated "no tool calls" as "done").
# --------------------------------------------------------------------------- #
from types import SimpleNamespace


def _openai_client(finish_reason):
    msg = SimpleNamespace(content="报告正文", tool_calls=None)
    resp = SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish_reason)],
                           usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))
    return SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=lambda **k: resp)))


def test_openai_loop_reports_a_cut_off_reply():
    meta = {}
    llm_client._run_openai_tool_loop(_openai_client("length"), [], "m", 100, 0, [], meta=meta)
    assert meta == {"stop_reason": "length", "truncated": True}


def test_openai_loop_reports_a_complete_reply():
    meta = {}
    llm_client._run_openai_tool_loop(_openai_client("stop"), [], "m", 100, 0, [], meta=meta)
    assert meta["truncated"] is False


def test_openai_loop_without_meta_still_returns_the_text():
    text, *_ = llm_client._run_openai_tool_loop(_openai_client("length"), [], "m", 100, 0, [])
    assert text == "报告正文"


def test_anthropic_loop_reports_a_cut_off_reply(monkeypatch):
    block = SimpleNamespace(type="text", text="报告正文", model_dump=lambda: {"type": "text", "text": "报告正文"})
    resp = SimpleNamespace(content=[block], stop_reason="max_tokens",
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))
    monkeypatch.setattr(llm_client, "_anthropic_messages_create", lambda client, **k: resp)
    meta = {}
    llm_client._run_tool_loop(object(), [], "m", 100, 0, [], meta=meta)
    assert meta["truncated"] is True
