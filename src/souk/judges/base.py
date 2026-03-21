"""Base judge interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from souk.config import JudgeConfig


@dataclass
class JudgeResult:
    """Result from a single judge evaluation."""

    judge_id: str
    criterion: str
    score: float  # 0.0 - 10.0
    reasoning: str
    raw_response: str = ""
    metadata: dict = field(default_factory=dict)


class JudgeBase(ABC):
    """Abstract base class for judge models."""

    def __init__(self, config: JudgeConfig) -> None:
        self.config = config
        self.id = config.id

    @abstractmethod
    async def evaluate(
        self,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
        criterion_name: str,
    ) -> JudgeResult:
        """Evaluate a conversation against a criterion.

        Args:
            conversation: List of {"role": "user"|"assistant", "content": "..."} messages.
            criterion_prompt: The full evaluation prompt including rubric.
            criterion_name: Name of the criterion being evaluated.

        Returns:
            JudgeResult with score and reasoning.
        """

    def _build_system_prompt(self, criterion_prompt: str) -> str:
        """Build the system prompt for evaluation."""
        return (
            "You are an expert conversation quality evaluator. "
            "You will be given a conversation and a specific evaluation criterion. "
            "Evaluate the conversation and provide:\n"
            "1. A score from 0 to 10 (use decimals for precision)\n"
            "2. A brief reasoning for your score\n\n"
            "Respond in this exact JSON format:\n"
            '{"score": <number>, "reasoning": "<string>"}\n\n'
            f"Criterion:\n{criterion_prompt}"
        )

    def _build_eval_messages(
        self,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
    ) -> list[dict[str, str]]:
        """Build messages for the evaluation request."""
        conv_text = "\n".join(f"[{m['role'].upper()}]: {m['content']}" for m in conversation)
        return [
            {"role": "system", "content": self._build_system_prompt(criterion_prompt)},
            {
                "role": "user",
                "content": f"Evaluate this conversation:\n\n{conv_text}",
            },
        ]

    def _parse_result(self, raw: str, criterion_name: str) -> tuple[float, str]:
        """Parse score and reasoning from judge response."""
        import json
        import re

        # Try to extract JSON from the response
        json_match = re.search(r"\{[^}]+\}", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                score = float(data.get("score", 0))
                reasoning = data.get("reasoning", "")
                return min(max(score, 0.0), 10.0), reasoning
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: try to find a number
        numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", raw)
        score = float(numbers[0]) if numbers else 5.0
        return min(max(score, 0.0), 10.0), raw
