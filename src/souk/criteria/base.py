"""Base criterion definition."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Criterion:
    """An evaluation criterion with rubric."""

    name: str
    description: str
    prompt: str  # Full evaluation prompt sent to judges
    weight: float = 1.0
    language: str = "en"  # "en", "ja", or "any"
