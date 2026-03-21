"""Generic HTTP endpoint judge (OpenAI-compatible API)."""

from __future__ import annotations

from openai import AsyncOpenAI

from souk.config import JudgeConfig
from souk.judges.base import JudgeBase, JudgeResult


class EndpointJudge(JudgeBase):
    """Judge using any OpenAI-compatible HTTP endpoint.

    Works with vLLM, Ollama, LiteLLM, Azure OpenAI, or any service
    that implements the OpenAI chat completions API.
    """

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        if not config.base_url:
            raise ValueError(f"EndpointJudge '{config.id}' requires base_url in config.")
        self.client = AsyncOpenAI(
            api_key=config.api_key or "not-needed",
            base_url=config.base_url,
        )

    async def evaluate(
        self,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
        criterion_name: str,
    ) -> JudgeResult:
        messages = self._build_eval_messages(conversation, criterion_prompt)
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            **self.config.extra,
        )
        raw = response.choices[0].message.content or ""
        score, reasoning = self._parse_result(raw, criterion_name)
        return JudgeResult(
            judge_id=self.id,
            criterion=criterion_name,
            score=score,
            reasoning=reasoning,
            raw_response=raw,
            metadata={
                "model": self.config.model,
                "provider": "endpoint",
                "base_url": self.config.base_url,
            },
        )
