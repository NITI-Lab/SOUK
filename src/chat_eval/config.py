"""Configuration management for ChatEval."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class JudgeConfig(BaseModel):
    """Configuration for a judge model."""

    id: str
    provider: str  # "openai", "anthropic", "google", "endpoint"
    model: str
    api_key: str | None = None  # Falls back to env var
    base_url: str | None = None  # For custom endpoints
    temperature: float = 0.0
    max_tokens: int = 2048
    extra: dict[str, Any] = Field(default_factory=dict)

    def resolve_api_key(self) -> str:
        """Resolve API key from config or environment."""
        if self.api_key:
            return self.api_key
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = env_map.get(self.provider, f"{self.provider.upper()}_API_KEY")
        key = os.environ.get(env_var, "")
        if not key:
            raise ValueError(
                f"API key not found for judge '{self.id}'. "
                f"Set {env_var} or provide api_key in config."
            )
        return key


class TargetConfig(BaseModel):
    """Configuration for the target service being evaluated."""

    id: str = "target"
    provider: str = "endpoint"  # "openai", "anthropic", "google", "endpoint"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)

    def resolve_api_key(self) -> str | None:
        """Resolve API key, returning None if not needed."""
        if self.api_key:
            return self.api_key
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = env_map.get(self.provider, f"{self.provider.upper()}_API_KEY")
        return os.environ.get(env_var)


class ReportConfig(BaseModel):
    """Configuration for report generation."""

    output_dir: str = "./reports"
    formats: list[str] = Field(default_factory=lambda: ["html", "json"])
    title: str = "ChatEval Report"


class EvalConfig(BaseModel):
    """Top-level evaluation configuration."""

    judges: list[JudgeConfig]
    target: TargetConfig | None = None
    criteria: list[str] = Field(default_factory=lambda: ["naturalness"])
    cases_dir: str = "./cases"
    report: ReportConfig = Field(default_factory=ReportConfig)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    concurrency: int = 5


def load_config(path: str | Path) -> EvalConfig:
    """Load configuration from a YAML file."""
    path = Path(path)
    with open(path) as f:
        raw = yaml.safe_load(f)
    return EvalConfig(**raw)
