"""Judge registry - maps provider names to judge classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chat_eval.judges.base import JudgeBase

if TYPE_CHECKING:
    from chat_eval.config import JudgeConfig

JUDGE_REGISTRY: dict[str, type[JudgeBase]] = {}


def _register_defaults() -> None:
    from chat_eval.judges.anthropic_judge import AnthropicJudge
    from chat_eval.judges.bedrock_judge import BedrockJudge
    from chat_eval.judges.endpoint_judge import EndpointJudge
    from chat_eval.judges.google_judge import GoogleJudge
    from chat_eval.judges.openai_judge import OpenAIJudge

    JUDGE_REGISTRY.update(
        {
            "openai": OpenAIJudge,
            "anthropic": AnthropicJudge,
            "google": GoogleJudge,
            "endpoint": EndpointJudge,
            "bedrock": BedrockJudge,
        }
    )


def create_judge(config: JudgeConfig) -> JudgeBase:
    """Create a judge instance from config."""
    if not JUDGE_REGISTRY:
        _register_defaults()

    judge_class = JUDGE_REGISTRY.get(config.provider)
    if judge_class is None:
        raise ValueError(f"Unknown judge provider: '{config.provider}'. Available: {list(JUDGE_REGISTRY.keys())}")
    return judge_class(config)
