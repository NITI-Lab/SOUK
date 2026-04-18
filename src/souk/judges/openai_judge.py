"""OpenAI/ChatGPT judge implementation."""

from __future__ import annotations

from openai import AsyncOpenAI

from souk.config import JudgeConfig
from souk.judges.base import JudgeBase, JudgeResult


class OpenAIJudge(JudgeBase):
    """Judge using OpenAI API (GPT-5.x, GPT-4o, o-series)."""

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.resolve_api_key(),
            base_url=config.base_url,
        )

    async def evaluate(
        self,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
        criterion_name: str,
    ) -> JudgeResult:
        messages = self._build_eval_messages(conversation, criterion_prompt)
        # GPT-5+ uses max_completion_tokens instead of max_tokens
        token_param = (
            "max_completion_tokens"
            if self.config.model.startswith("gpt-5") or self.config.model.startswith("o")
            else "max_tokens"
        )
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self.config.temperature,
            **{token_param: self.config.max_tokens},
        )
        raw = response.choices[0].message.content or ""
        score, reasoning = self._parse_result(raw, criterion_name)
        return JudgeResult(
            judge_id=self.id,
            criterion=criterion_name,
            score=score,
            reasoning=reasoning,
            raw_response=raw,
            metadata={"model": self.config.model, "provider": "openai"},
        )
