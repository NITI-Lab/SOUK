"""Target service client for live evaluation."""

from __future__ import annotations

from openai import AsyncOpenAI

from souk.config import TargetConfig

_EXTRA_META_KEYS = {"api_key_env", "tenant_id", "timeout"}


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
        # Filter out meta keys that shouldn't be passed to the API
        self._api_extra = {k: v for k, v in config.extra.items() if k not in _EXTRA_META_KEYS}

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
                **self._api_extra,
            )
            assistant_msg = response.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": assistant_msg})

        # Return without system prompt
        return [m for m in messages if m["role"] != "system"]
