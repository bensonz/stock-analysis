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
