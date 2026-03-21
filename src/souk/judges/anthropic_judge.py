"""Anthropic/Claude judge implementation."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from souk.config import JudgeConfig
from souk.judges.base import JudgeBase, JudgeResult


class AnthropicJudge(JudgeBase):
    """Judge using Anthropic API (Claude)."""

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        self.client = AsyncAnthropic(
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
        # Anthropic uses system as a separate parameter
        system_msg = messages[0]["content"]
        user_msgs = [{"role": m["role"], "content": m["content"]} for m in messages[1:]]

        response = await self.client.messages.create(
            model=self.config.model,
            system=system_msg,
            messages=user_msgs,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        raw = response.content[0].text if response.content else ""
        score, reasoning = self._parse_result(raw, criterion_name)
        return JudgeResult(
            judge_id=self.id,
            criterion=criterion_name,
            score=score,
            reasoning=reasoning,
            raw_response=raw,
            metadata={"model": self.config.model, "provider": "anthropic"},
        )
