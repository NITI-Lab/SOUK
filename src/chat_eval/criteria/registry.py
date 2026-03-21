"""Criterion registry."""

from __future__ import annotations

from chat_eval.criteria.base import Criterion

_REGISTRY: dict[str, dict[str, Criterion]] = {}  # name -> {lang -> Criterion}


def register_criterion(criterion: Criterion) -> None:
    """Register a criterion."""
    if criterion.name not in _REGISTRY:
        _REGISTRY[criterion.name] = {}
    _REGISTRY[criterion.name][criterion.language] = criterion


def get_criterion(name: str, language: str = "en") -> Criterion:
    """Get a criterion by name and language, falling back to English."""
    if name not in _REGISTRY:
        raise ValueError(f"Unknown criterion: '{name}'. Available: {list(_REGISTRY.keys())}")
    lang_map = _REGISTRY[name]
    return lang_map.get(language) or lang_map.get("en") or next(iter(lang_map.values()))


def list_criteria() -> list[str]:
    """List all registered criterion names."""
    return list(_REGISTRY.keys())


def _register_defaults() -> None:
    """Register built-in criteria."""
    from chat_eval.criteria.coherence import COHERENCE_EN, COHERENCE_JA, COHERENCE_ZH
    from chat_eval.criteria.hallucination import HALLUCINATION_EN, HALLUCINATION_JA, HALLUCINATION_ZH
    from chat_eval.criteria.helpfulness import HELPFULNESS_EN, HELPFULNESS_JA, HELPFULNESS_ZH
    from chat_eval.criteria.naturalness import NATURALNESS_EN, NATURALNESS_JA, NATURALNESS_ZH
    from chat_eval.criteria.recommendation import RECOMMENDATION_EN, RECOMMENDATION_JA, RECOMMENDATION_ZH
    from chat_eval.criteria.security import (
        INFO_LEAKAGE_EN,
        INFO_LEAKAGE_JA,
        INFO_LEAKAGE_ZH,
        PII_HANDLING_EN,
        PII_HANDLING_JA,
        PII_HANDLING_ZH,
        PROMPT_INJECTION_EN,
        PROMPT_INJECTION_JA,
        PROMPT_INJECTION_ZH,
        ROLE_BOUNDARY_EN,
        ROLE_BOUNDARY_JA,
        ROLE_BOUNDARY_ZH,
    )
    from chat_eval.criteria.toxicity import TOXICITY_EN, TOXICITY_JA, TOXICITY_ZH

    for c in [
        # Quality
        NATURALNESS_EN,
        NATURALNESS_JA,
        NATURALNESS_ZH,
        RECOMMENDATION_EN,
        RECOMMENDATION_JA,
        RECOMMENDATION_ZH,
        COHERENCE_EN,
        COHERENCE_JA,
        COHERENCE_ZH,
        HALLUCINATION_EN,
        HALLUCINATION_JA,
        HALLUCINATION_ZH,
        HELPFULNESS_EN,
        HELPFULNESS_JA,
        HELPFULNESS_ZH,
        TOXICITY_EN,
        TOXICITY_JA,
        TOXICITY_ZH,
        # Security
        PROMPT_INJECTION_EN,
        PROMPT_INJECTION_JA,
        PROMPT_INJECTION_ZH,
        INFO_LEAKAGE_EN,
        INFO_LEAKAGE_JA,
        INFO_LEAKAGE_ZH,
        ROLE_BOUNDARY_EN,
        ROLE_BOUNDARY_JA,
        ROLE_BOUNDARY_ZH,
        PII_HANDLING_EN,
        PII_HANDLING_JA,
        PII_HANDLING_ZH,
    ]:
        register_criterion(c)


# Auto-register on import
_register_defaults()
