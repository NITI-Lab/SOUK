"""Tests for configuration loading."""

from pathlib import Path

from souk.config import EvalConfig, JudgeConfig, load_config

CONFIG_EXAMPLE = Path(__file__).parent.parent / "config.example.yaml"


def test_load_example_config():
    config = load_config(CONFIG_EXAMPLE)
    assert isinstance(config, EvalConfig)
    assert len(config.judges) >= 3
    assert "en" in config.languages
    assert "ja" in config.languages


def test_judge_config_providers():
    config = load_config(CONFIG_EXAMPLE)
    providers = {j.provider for j in config.judges}
    assert "openai" in providers
    assert "anthropic" in providers
    assert "google" in providers


def test_report_config_defaults():
    config = load_config(CONFIG_EXAMPLE)
    assert "html" in config.report.formats
    assert "json" in config.report.formats


def test_judge_config_resolve_api_key_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    jc = JudgeConfig(id="test", provider="openai", model="gpt-4o")
    assert jc.resolve_api_key() == "test-key-123"
