"""Target service client for live evaluation."""

from __future__ import annotations

from openai import AsyncOpenAI

from chat_eval.config import TargetConfig


class TargetClient:
    """Client for interacting with the target service being evaluated.

    Supports OpenAI-compatible endpoints. For non-standard APIs,
    subclass and override run_conversation().
    """

    def __init__(self, config: TargetConfig) -> None:
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.resolve_api_key() or "not-needed",
            base_url=config.base_url,
        )

    async def run_conversation(
        self,
        user_turns: list[str],
        system_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Send user turns to the target and collect responses.

        Returns the full conversation as a list of messages.
        """
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        for user_msg in user_turns:
            messages.append({"role": "user", "content": user_msg})

            response = await self.client.chat.completions.create(
                model=self.config.model or "default",
                messages=messages,  # type: ignore[arg-type]
                **self.config.extra,
            )
            assistant_msg = response.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": assistant_msg})

        # Return without system prompt
        return [m for m in messages if m["role"] != "system"]
