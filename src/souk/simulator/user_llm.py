"""LLM-driven simulated-user turn generator.

Given a persona + conversation history + optional behaviour-injection hints,
produces the user's next message in English by default. The generator is
designed to be cheap (gpt-5.4-mini by default) since it runs per-turn for
every conversation in a large batch.

The generator also returns a lightweight ``status`` flag so the runner can
detect when the simulated user has disengaged (explicit end-of-session,
the model chose to bail). This avoids burning turns after the conversation
should have ended.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Literal

from openai import AsyncOpenAI

from souk.simulator._openai_compat import _chat_create_compat
from souk.simulator.behaviors import BehaviorInjector
from souk.simulator.persona import Persona

UserTurnStatus = Literal["continue", "end", "bail"]


@dataclass
class UserTurn:
    text: str
    status: UserTurnStatus = "continue"
    raw: str = ""
    hints_applied: list[str] = field(default_factory=list)


_SYSTEM_TEMPLATE = """You are role-playing a fictional shopper testing an \
EC product-recommendation chat assistant. Embody the persona below and write \
the **next single user message** in response to the assistant's most recent turn.

## Persona
- Occupation: {occupation}
- Purchase purpose: {purpose}
- Top priority when choosing a product: {priorities}
- Communication style: {comm_style}
- Domain knowledge: {knowledge_level}
- Budget signal: {budget_hint}

## Rules
1. Reply with a single message only (no multi-turn replies, no preambles, no meta-commentary).
2. Stay in persona. Polite personas use formal phrasing; casual personas use slang.
3. Keep messages short — chat-style, minimal line breaks.
4. If the assistant offers numbered choices, pick whichever is naturally consistent with your persona.
5. When the conversation has clearly wrapped up (the assistant confirmed handoff to a human, \
or said something like "an order specialist will reach out"), append `[[END]]` to your final message.
6. If you genuinely cannot figure out what to say, append `[[BAIL]]` and stop.
{injection_block}
## Output format
Return exactly one JSON object:
{{"message": "<your reply. when ending, include [[END]] / [[BAIL]] inline>"}}"""


_INJECTION_HEADER = """
## Extra behavior to weave into THIS turn (do it naturally)
"""


def build_user_system_prompt(persona: Persona, injections: list[BehaviorInjector]) -> str:
    if injections:
        lines = [f"- [{inj.label}] {inj.hint}" for inj in injections]
        injection_block = _INJECTION_HEADER + "\n".join(lines) + "\n"
    else:
        injection_block = ""
    return _SYSTEM_TEMPLATE.format(
        occupation=persona.occupation,
        purpose=persona.purpose,
        priorities=persona.priorities,
        comm_style=persona.comm_style,
        knowledge_level=persona.knowledge_level,
        budget_hint=persona.budget_hint,
        injection_block=injection_block,
    )


@dataclass
class UserLLMConfig:
    model: str = "gpt-5.4-mini"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    temperature: float = 0.8
    max_output_tokens: int = 300
    timeout: float = 30.0


class SimulatedUserLLM:
    """Generates simulated-user turns with a small OpenAI-compatible model."""

    def __init__(self, config: UserLLMConfig | None = None) -> None:
        self.config = config or UserLLMConfig()
        key = os.environ.get(self.config.api_key_env, "")
        if not key:
            raise RuntimeError(f"{self.config.api_key_env} is not set; cannot run simulated user.")
        self._client = AsyncOpenAI(api_key=key, base_url=self.config.base_url)

    async def generate_turn(
        self,
        persona: Persona,
        history: list[dict[str, str]],
        injections: list[BehaviorInjector],
    ) -> UserTurn:
        """Produce the user's next message given conversation history so far.

        ``history`` follows the OpenAI messages schema from the *agent's*
        perspective: user turns are role=user, bot turns are role=assistant.
        For the simulated user we invert these.
        """
        system = build_user_system_prompt(persona, injections)

        flipped: list[dict[str, str]] = []
        for msg in history:
            if msg["role"] == "assistant":
                flipped.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "user":
                flipped.append({"role": "assistant", "content": msg["content"]})

        if not flipped:
            flipped.append(
                {
                    "role": "user",
                    "content": "(Start the conversation. You send the first message.)",
                }
            )

        messages = [{"role": "system", "content": system}] + flipped

        resp = await _chat_create_compat(
            self._client,
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            timeout=self.config.timeout,
            json_mode=True,
        )

        raw = (resp.choices[0].message.content or "").strip()
        return parse_user_turn(raw, injections)


def parse_user_turn(raw: str, injections: list[BehaviorInjector] | None = None) -> UserTurn:
    """Extract message text and status from a raw LLM response string."""
    text = raw
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "message" in parsed:
            text = str(parsed["message"]).strip()
    except json.JSONDecodeError:
        match = re.search(r'"message"\s*:\s*"([^"]*)"', raw)
        if match:
            text = match.group(1).strip()

    status: UserTurnStatus = "continue"
    if "[[END]]" in text:
        status = "end"
        text = text.replace("[[END]]", "").strip()
    elif "[[BAIL]]" in text:
        status = "bail"
        text = text.replace("[[BAIL]]", "").strip()

    hints_applied = [inj.id for inj in (injections or [])]
    return UserTurn(text=text, status=status, raw=raw, hints_applied=hints_applied)
