"""Thin compatibility wrapper around AsyncOpenAI.chat.completions.create.

The OpenAI API split ``max_tokens`` into ``max_completion_tokens`` for
GPT-5.x models, and GPT-5.x also rejects ``temperature!=1`` in some
deployments. We don't know the target model's capabilities a priori
(users may plug in gpt-5.4-mini, gpt-4o-mini, or an Azure deployment),
so this helper tries the newest parameter shape first and gracefully
retries on ``BadRequestError`` so a single call site works across both
generations.
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI, BadRequestError


async def _chat_create_compat(
    client: AsyncOpenAI,
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_output_tokens: int,
    timeout: float,
    json_mode: bool,
) -> Any:
    """Issue a chat.completions.create call, adapting to model quirks.

    Tries, in order:
        1. GPT-5.x shape: max_completion_tokens + response_format
        2. GPT-5.x without response_format (older SDKs)
        3. Legacy shape: max_tokens + response_format
        4. Legacy shape without response_format
    For each shape, if ``temperature`` is rejected, retries omitting it.
    """
    base: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
    }

    shapes: list[dict[str, Any]] = []
    # GPT-5.x preferred shape
    shapes.append({**base, "max_completion_tokens": max_output_tokens, "response_format": {"type": "json_object"}})
    shapes.append({**base, "max_completion_tokens": max_output_tokens})
    # Legacy GPT-4.x / gpt-4o shape
    shapes.append({**base, "max_tokens": max_output_tokens, "response_format": {"type": "json_object"}})
    shapes.append({**base, "max_tokens": max_output_tokens})

    last_error: Exception | None = None
    for shape in shapes:
        attempts = [
            {**shape, "temperature": temperature},
            shape,  # retry without temperature for GPT-5.x
        ]
        for payload in attempts:
            try:
                return await client.chat.completions.create(**payload)
            except BadRequestError as exc:
                last_error = exc
                msg = str(exc).lower()
                # If it's a different kind of BadRequest, don't bother retrying
                # the whole shape cascade — try next shape once.
                if (
                    "max_tokens" in msg
                    or "max_completion_tokens" in msg
                    or "response_format" in msg
                    or "temperature" in msg
                ):
                    continue
                raise
            except TypeError as exc:
                last_error = exc
                # Typically means SDK too old for response_format or
                # max_completion_tokens; try the next shape.
                continue
    assert last_error is not None
    raise last_error
