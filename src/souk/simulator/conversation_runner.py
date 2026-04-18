"""Drive a single persona through a live conversation with the target agent.

Given (persona, injection schedule, target, simulated-user LLM), this module:

1. Calls the simulated user to produce a turn.
2. Sends that turn to the target agent (per-persona session).
3. Repeats until max_turns, ``[[END]]``, or ``[[BAIL]]``.
4. Optionally hands the full conversation to the StrictJudge.

It is intentionally agnostic to how the batch is dispatched — the batch
runner wraps this with a semaphore + budget cap.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx

from souk.simulator.behaviors import (
    resolve_injectors,
    schedule_injections,
)
from souk.simulator.persona import Persona
from souk.simulator.strict_judge import JudgeVerdict, StrictJudge
from souk.simulator.user_llm import SimulatedUserLLM, UserTurn

logger = logging.getLogger(__name__)


@dataclass
class AgentTargetConfig:
    base_url: str
    api_key: str
    tenant_id: str = "default"
    model_id: Optional[str] = None
    timeout: float = 90.0


@dataclass
class ConversationRunResult:
    conversation_id: str
    persona: Persona
    conversation: list[dict[str, str]]
    user_turns: list[UserTurn] = field(default_factory=list)
    turn_latencies_sec: list[float] = field(default_factory=list)
    end_reason: str = ""  # "max_turns" | "end_marker" | "bail" | "error"
    verdict: Optional[JudgeVerdict] = None
    error: Optional[str] = None
    started_at: float = 0.0
    finished_at: float = 0.0


class AgentSession:
    """Single-session agent client scoped to one conversation."""

    def __init__(self, cfg: AgentTargetConfig, session_id: Optional[str] = None):
        self.cfg = cfg
        self.session_id = session_id or f"eval-{uuid.uuid4().hex[:10]}"

    async def invoke(self, client: httpx.AsyncClient, user_message: str) -> str:
        payload: dict[str, object] = {
            "action": "invoke",
            "session_id": self.session_id,
            "tenant_id": self.cfg.tenant_id,
            "message": user_message,
        }
        if self.cfg.model_id:
            payload["model_id"] = self.cfg.model_id
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.cfg.api_key,
        }
        resp = await client.post(self.cfg.base_url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return str(data.get("response", "") or "")

    async def reset(self, client: httpx.AsyncClient) -> None:
        try:
            await client.post(
                self.cfg.base_url,
                json={
                    "action": "reset_session",
                    "session_id": self.session_id,
                    "tenant_id": self.cfg.tenant_id,
                },
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.cfg.api_key,
                },
            )
        except Exception as exc:  # pragma: no cover — cleanup is best-effort
            logger.debug("reset_session failed: %s", exc)


async def run_single_conversation(
    persona: Persona,
    agent_cfg: AgentTargetConfig,
    user_llm: SimulatedUserLLM,
    judge: Optional[StrictJudge] = None,
    *,
    max_turns: int = 10,
    kickoff_message: Optional[str] = None,
) -> ConversationRunResult:
    """Run one persona through ``max_turns`` of live dialogue.

    Parameters
    ----------
    kickoff_message:
        If supplied, used verbatim as the first user message instead of asking
        the simulated user for turn 0. Useful for warm-starting common
        openings such as "I'm shopping for a laptop" or "I want a gift".
    """
    started = time.time()
    conv_id = f"{persona.id}-{int(started)}"
    conversation: list[dict[str, str]] = []
    user_turns: list[UserTurn] = []
    latencies: list[float] = []
    end_reason = "max_turns"
    error: Optional[str] = None

    injectors = resolve_injectors(persona.injections)
    injection_schedule = schedule_injections(injectors, total_turns=max_turns)
    session = AgentSession(agent_cfg)

    async with httpx.AsyncClient(timeout=agent_cfg.timeout) as client:
        try:
            for turn_idx in range(max_turns):
                injections_for_turn = injection_schedule.get(turn_idx, [])

                # ------- 1. user turn -------
                if turn_idx == 0 and kickoff_message:
                    user_text = kickoff_message
                    user_turn = UserTurn(
                        text=user_text,
                        status="continue",
                        raw="(kickoff)",
                        hints_applied=[],
                    )
                else:
                    user_turn = await user_llm.generate_turn(
                        persona=persona,
                        history=conversation,
                        injections=injections_for_turn,
                    )
                    user_text = user_turn.text.strip()

                user_turns.append(user_turn)

                if user_turn.status == "bail":
                    end_reason = "bail"
                    break
                if not user_text:
                    end_reason = "end_marker" if user_turn.status == "end" else "empty_user"
                    break

                conversation.append({"role": "user", "content": user_text})

                # ------- 2. agent response -------
                t0 = time.time()
                try:
                    bot_text = await session.invoke(client, user_text)
                except httpx.HTTPError as exc:
                    error = f"agent call failed turn={turn_idx}: {exc}"
                    end_reason = "error"
                    break
                latencies.append(time.time() - t0)
                conversation.append({"role": "assistant", "content": bot_text})

                # ------- 3. did the user signal end on THIS turn? -------
                if user_turn.status == "end":
                    end_reason = "end_marker"
                    break

            await session.reset(client)
        except Exception as exc:  # pragma: no cover — safety net
            logger.exception("run_single_conversation crashed")
            error = f"{type(exc).__name__}: {exc}"
            end_reason = "error"

    verdict: Optional[JudgeVerdict] = None
    if judge is not None and conversation and error is None:
        try:
            verdict = await judge.evaluate(
                conversation_id=conv_id,
                conversation=conversation,
                persona=persona,
            )
        except Exception as exc:
            logger.exception("judge failed")
            error = f"judge failed: {exc}"

    finished = time.time()
    return ConversationRunResult(
        conversation_id=conv_id,
        persona=persona,
        conversation=conversation,
        user_turns=user_turns,
        turn_latencies_sec=latencies,
        end_reason=end_reason,
        verdict=verdict,
        error=error,
        started_at=started,
        finished_at=finished,
    )


async def run_many_conversations(
    personas: list[Persona],
    agent_cfg: AgentTargetConfig,
    user_llm: SimulatedUserLLM,
    judge: Optional[StrictJudge] = None,
    *,
    concurrency: int = 8,
    max_turns: int = 10,
    kickoff_message: Optional[str] = None,
    progress_cb=None,
) -> list[ConversationRunResult]:
    """Run ``personas`` in parallel with a semaphore-bounded worker pool."""
    sem = asyncio.Semaphore(concurrency)
    results: list[ConversationRunResult] = [None] * len(personas)  # type: ignore[list-item]
    completed = 0
    completed_lock = asyncio.Lock()

    async def _worker(idx: int, persona: Persona) -> None:
        nonlocal completed
        async with sem:
            result = await run_single_conversation(
                persona=persona,
                agent_cfg=agent_cfg,
                user_llm=user_llm,
                judge=judge,
                max_turns=max_turns,
                kickoff_message=kickoff_message,
            )
        results[idx] = result
        if progress_cb is not None:
            async with completed_lock:
                completed += 1
                try:
                    progress_cb(completed, len(personas), result)
                except Exception:
                    logger.exception("progress callback raised")

    await asyncio.gather(*(_worker(i, p) for i, p in enumerate(personas)))
    return results  # type: ignore[return-value]
