"""Strict rubric-based judge.

Reads a rubric YAML, asks a high-capability LLM to score each item with
pass/fail + evidence quote + short reason, and aggregates a per-conversation
verdict (critical_fails, major_fails, minor_fails, overall_pass).

The judge scores the full conversation in a single call to keep cost bounded
at ~1 request / conversation. The prompt is deliberately adversarial
("assume every response is a bug unless proven otherwise") so the judge
flags borderline cases rather than glossing over them.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml
from openai import AsyncOpenAI

from souk.simulator._openai_compat import _chat_create_compat
from souk.simulator.ground_truth import GroundTruth
from souk.simulator.persona import Persona

Severity = Literal["critical", "major", "minor"]
Scope = Literal["turn", "convo"]


@dataclass
class RubricItem:
    id: str
    category: str
    severity: Severity
    scope: Scope
    description: str


@dataclass
class Rubric:
    version: float
    domain: str
    language: str
    items: list[RubricItem]

    def by_id(self) -> dict[str, RubricItem]:
        return {i.id: i for i in self.items}


def load_rubric(path: str | Path) -> Rubric:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    items: list[RubricItem] = []
    for cat_name, cat_body in (data.get("categories") or {}).items():
        for it in cat_body.get("items", []):
            items.append(
                RubricItem(
                    id=it["id"],
                    category=cat_name,
                    severity=it["severity"],
                    scope=it["scope"],
                    description=it["description"],
                )
            )
    return Rubric(
        version=float(data.get("rubric_version", 0)),
        domain=str(data.get("domain", "")),
        language=str(data.get("language", "en")),
        items=items,
    )


@dataclass
class ItemVerdict:
    id: str
    passed: bool
    severity: Severity
    scope: Scope
    category: str
    evidence: str = ""  # quoted fragment from the conversation
    reason: str = ""  # short rationale from the judge
    not_applicable: bool = False  # true when the item cannot be evaluated in this convo


@dataclass
class JudgeVerdict:
    conversation_id: str
    items: list[ItemVerdict]
    notes: str = ""
    raw_response: str = ""
    persona_summary: str = ""
    metadata: dict = field(default_factory=dict)

    def fails_by_severity(self) -> dict[Severity, list[ItemVerdict]]:
        out: dict[Severity, list[ItemVerdict]] = {
            "critical": [],
            "major": [],
            "minor": [],
        }
        for it in self.items:
            if not it.passed and not it.not_applicable:
                out[it.severity].append(it)
        return out

    def overall_pass(self) -> bool:
        fails = self.fails_by_severity()
        # Any critical fail, or 3+ major fails, counts as overall fail.
        if fails["critical"]:
            return False
        if len(fails["major"]) >= 3:
            return False
        return True


@dataclass
class StrictJudgeConfig:
    model: str = "gpt-5.4"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str | None = None
    temperature: float = 0.0
    max_output_tokens: int = 4000
    timeout: float = 90.0


class StrictJudge:
    """Single-shot per-conversation rubric judge."""

    def __init__(
        self,
        rubric: Rubric,
        config: StrictJudgeConfig | None = None,
        ground_truth: GroundTruth | None = None,
    ) -> None:
        self.rubric = rubric
        self.config = config or StrictJudgeConfig()
        self.ground_truth = ground_truth
        key = os.environ.get(self.config.api_key_env, "")
        if not key:
            raise RuntimeError(f"{self.config.api_key_env} is not set; cannot run strict judge.")
        self._client = AsyncOpenAI(api_key=key, base_url=self.config.base_url)

    async def evaluate(
        self,
        conversation_id: str,
        conversation: list[dict[str, str]],
        persona: Persona | None = None,
    ) -> JudgeVerdict:
        if not conversation:
            return JudgeVerdict(conversation_id=conversation_id, items=[])

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(conversation, persona)

        resp = await _chat_create_compat(
            self._client,
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_output_tokens,
            timeout=self.config.timeout,
            json_mode=True,
        )

        raw = (resp.choices[0].message.content or "").strip()
        return parse_judge_verdict(
            conversation_id=conversation_id,
            raw=raw,
            rubric=self.rubric,
            persona=persona,
        )

    # ------------------------------------------------------------------ #
    #  Prompt construction
    # ------------------------------------------------------------------ #

    def _build_system_prompt(self) -> str:
        return (
            "You are a strict quality reviewer for an EC product-recommendation chat "
            "assistant. Imagine you are an end-user shopping through this assistant. "
            "Audit the conversation log and ruthlessly flag any behavior that hurts "
            "the user or any unnatural / inappropriate response.\n\n"
            "## Ground rules\n"
            "- Treat suspicious responses as fail (passed=false). When in doubt, fail.\n"
            "- evidence MUST be a short verbatim quote from the conversation log.\n"
            "- reason is 1-2 short sentences in English.\n"
            "- For items that cannot be evaluated because the relevant content never "
            "appeared (e.g. PRODUCT_INTRO_FORMAT in a conversation that never reached a "
            "product introduction), set not_applicable=true.\n"
            "- When a reference data block is supplied, treat it as ground truth: any "
            "product / URL / specification not present there is potential hallucination. "
            "When no reference data is supplied, only fail clear fabrications "
            "(implausible names, impossible prices, etc.); otherwise pass.\n"
            "- Do not import preferences that are not in the rubric.\n"
        )

    def _format_rubric_items_for_prompt(self) -> str:
        lines: list[str] = []
        for it in self.rubric.items:
            lines.append(f"- {it.id} [{it.severity}/{it.scope}/{it.category}]: {it.description}")
        return "\n".join(lines)

    def _build_user_prompt(
        self,
        conversation: list[dict[str, str]],
        persona: Persona | None,
    ) -> str:
        convo_text = _format_conversation(conversation)
        persona_text = persona.summary() if persona else "(no persona supplied)"
        rubric_text = self._format_rubric_items_for_prompt()
        schema_hint = _JUDGE_OUTPUT_SCHEMA_HINT.format(
            ids=json.dumps([i.id for i in self.rubric.items], ensure_ascii=False),
        )
        ground_truth_block = self.ground_truth.to_prompt_block() if self.ground_truth else ""
        sections: list[str] = [
            "## Simulated user (persona)",
            persona_text,
        ]
        if ground_truth_block:
            sections += ["", ground_truth_block]
        sections += [
            "",
            "## Conversation log under review",
            convo_text,
            "",
            "## Rubric items (judge every one of them)",
            rubric_text,
            "",
            "## Output format",
            schema_hint,
        ]
        return "\n".join(sections)


_JUDGE_OUTPUT_SCHEMA_HINT = """Return exactly one JSON object with this shape:
{{
  "items": [
    {{
      "id": "<rubric id>",
      "passed": true | false,
      "not_applicable": true | false,
      "evidence": "<short verbatim quote from the conversation; empty when passed=true>",
      "reason": "<1-2 sentences in English>"
    }},
    ...
  ],
  "notes": "<short overall comment, optional>"
}}

- The items array MUST include every id below (any order): {ids}
- Match the id values exactly.
- No extra keys, no preamble, no code fences.
"""


def _format_conversation(conversation: list[dict[str, str]]) -> str:
    lines: list[str] = []
    turn_no = 0
    for msg in conversation:
        role = msg.get("role", "user").lower()
        content = msg.get("content", "")
        if role == "user":
            turn_no += 1
            lines.append(f"[T{turn_no}][USER] {content}")
        else:
            lines.append(f"[T{turn_no}][BOT]  {content}")
    return "\n".join(lines)


def parse_judge_verdict(
    conversation_id: str,
    raw: str,
    rubric: Rubric,
    persona: Persona | None = None,
) -> JudgeVerdict:
    """Parse the JSON emitted by the judge, tolerating minor format slips."""
    data: dict[str, Any] = {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = {}

    by_id = rubric.by_id()
    items: list[ItemVerdict] = []
    seen_ids: set[str] = set()
    for entry in data.get("items", []) or []:
        rid = str(entry.get("id", ""))
        spec = by_id.get(rid)
        if not spec:
            continue
        seen_ids.add(rid)
        items.append(
            ItemVerdict(
                id=rid,
                passed=bool(entry.get("passed", False)),
                severity=spec.severity,
                scope=spec.scope,
                category=spec.category,
                evidence=str(entry.get("evidence", "") or "").strip(),
                reason=str(entry.get("reason", "") or "").strip(),
                not_applicable=bool(entry.get("not_applicable", False)),
            )
        )

    # Any rubric item the judge forgot: mark as fail with a specific reason so
    # missing checks surface in the report rather than silently disappearing.
    for rid, spec in by_id.items():
        if rid in seen_ids:
            continue
        items.append(
            ItemVerdict(
                id=rid,
                passed=False,
                severity=spec.severity,
                scope=spec.scope,
                category=spec.category,
                evidence="",
                reason="judge did not return verdict for this item",
                not_applicable=False,
            )
        )

    notes = str(data.get("notes", "") or "").strip()
    return JudgeVerdict(
        conversation_id=conversation_id,
        items=items,
        notes=notes,
        raw_response=raw,
        persona_summary=(persona.summary() if persona else ""),
    )


def summarize_verdicts(verdicts: Iterable[JudgeVerdict]) -> dict[str, Any]:
    """Aggregate per-item fail rates across a batch of verdicts."""
    total = 0
    convo_pass = 0
    per_item_fail: dict[str, int] = {}
    per_item_na: dict[str, int] = {}
    per_item_total: dict[str, int] = {}
    per_severity_fail: dict[str, int] = {"critical": 0, "major": 0, "minor": 0}

    for v in verdicts:
        total += 1
        if v.overall_pass():
            convo_pass += 1
        for it in v.items:
            per_item_total[it.id] = per_item_total.get(it.id, 0) + 1
            if it.not_applicable:
                per_item_na[it.id] = per_item_na.get(it.id, 0) + 1
                continue
            if not it.passed:
                per_item_fail[it.id] = per_item_fail.get(it.id, 0) + 1
                per_severity_fail[it.severity] = per_severity_fail.get(it.severity, 0) + 1

    return {
        "total_conversations": total,
        "overall_pass": convo_pass,
        "overall_pass_rate": (convo_pass / total) if total else 0.0,
        "per_severity_fail_count": per_severity_fail,
        "per_item_fail_count": per_item_fail,
        "per_item_na_count": per_item_na,
        "per_item_total": per_item_total,
    }
