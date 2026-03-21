"""AWS Bedrock judge implementation (for Claude models via AWS)."""

from __future__ import annotations

import json

import boto3

from chat_eval.config import JudgeConfig
from chat_eval.judges.base import JudgeBase, JudgeResult


class BedrockJudge(JudgeBase):
    """Judge using AWS Bedrock (Claude, etc.).

    Config example:
        - id: claude-haiku-bedrock
          provider: bedrock
          model: anthropic.claude-haiku-4-5-20251001-v1:0
          extra:
            region: us-west-2
    """

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        region = config.extra.get("region", "us-west-2")
        self.client = boto3.client("bedrock-runtime", region_name=region)

    async def evaluate(
        self,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
        criterion_name: str,
    ) -> JudgeResult:
        messages = self._build_eval_messages(conversation, criterion_prompt)
        system_msg = messages[0]["content"]
        user_msgs = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages[1:]]

        # Bedrock converse API (synchronous, but wrapped in async context)
        import asyncio

        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.converse(
                modelId=self.config.model,
                system=[{"text": system_msg}],
                messages=user_msgs,
                inferenceConfig={
                    "temperature": self.config.temperature,
                    "maxTokens": self.config.max_tokens,
                },
            ),
        )

        raw = ""
        if response.get("output", {}).get("message", {}).get("content"):
            raw = response["output"]["message"]["content"][0].get("text", "")

        score, reasoning = self._parse_result(raw, criterion_name)
        return JudgeResult(
            judge_id=self.id,
            criterion=criterion_name,
            score=score,
            reasoning=reasoning,
            raw_response=raw,
            metadata={"model": self.config.model, "provider": "bedrock"},
        )
