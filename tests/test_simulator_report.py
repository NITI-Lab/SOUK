"""Unit tests for report aggregation (pure, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from souk.simulator import (
    ConversationRunResult,
    ItemVerdict,
    JudgeVerdict,
    Persona,
    load_rubric,
)
from souk.simulator.report import write_run

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubrics" / "ec_recommendation_strict.yaml"


def _persona(tag: str, **overrides) -> Persona:
    base = dict(
        id=tag,
        occupation="student",
        purpose="first_purchase",
        priorities="lowest_price",
        comm_style="concise",
        knowledge_level="novice",
        budget_hint="vague",
        injections=[],
        notes="",
    )
    base.update(overrides)
    return Persona(**base)


def _result(
    persona: Persona,
    rubric,
    failing_ids: list[str],
    *,
    turns: int = 3,
    error: str | None = None,
) -> ConversationRunResult:
    items = []
    for it in rubric.items:
        failing = it.id in failing_ids
        items.append(
            ItemVerdict(
                id=it.id,
                passed=not failing,
                severity=it.severity,
                scope=it.scope,
                category=it.category,
                evidence=f"fixture evidence for {it.id}" if failing else "",
                reason="fixture fail" if failing else "",
            )
        )
    verdict = (
        None
        if error
        else JudgeVerdict(
            conversation_id=f"conv-{persona.id}",
            items=items,
        )
    )
    conversation: list[dict[str, str]] = []
    for t in range(turns):
        conversation.append({"role": "user", "content": f"u{t}"})
        conversation.append({"role": "assistant", "content": f"a{t}"})
    return ConversationRunResult(
        conversation_id=f"conv-{persona.id}",
        persona=persona,
        conversation=conversation,
        user_turns=[],
        turn_latencies_sec=[0.5] * turns,
        end_reason="max_turns" if not error else "error",
        verdict=verdict,
        error=error,
    )


def test_write_run_produces_expected_artifacts(tmp_path) -> None:
    rubric = load_rubric(RUBRIC_PATH)

    results = [
        _result(_persona("p1"), rubric, failing_ids=["UNSUPPORTED_PRODUCT"]),  # critical fail
        _result(
            _persona("p2", occupation="young_professional"),
            rubric,
            failing_ids=[
                "STATE_KEY_LEAK",
                "PRODUCT_INTRO_FORMAT",
                "ANSWERS_WHAT_ASKED",
            ],  # 3 major -> overall fail
        ),
        _result(_persona("p3"), rubric, failing_ids=[]),  # clean pass
        _result(_persona("p4"), rubric, failing_ids=[], error="boom"),  # judge skipped
    ]

    summary = write_run(results, tmp_path)

    # File layout
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "results.csv").exists()
    assert (tmp_path / "REPORT.md").exists()
    assert (tmp_path / "conversations" / "conv-p1.json").exists()

    # Summary totals
    assert summary["total_conversations"] == 4
    assert summary["judged"] == 3  # p4 had error -> no verdict
    assert summary["overall_pass"] == 1  # only p3
    assert summary["errors"] == 1
    assert summary["per_severity_fail"]["critical"] == 1
    assert summary["per_severity_fail"]["major"] == 3

    top_fail_ids = {row["id"] for row in summary["per_item_rates"] if row["fail"] > 0}
    assert {
        "UNSUPPORTED_PRODUCT",
        "STATE_KEY_LEAK",
        "PRODUCT_INTRO_FORMAT",
        "ANSWERS_WHAT_ASKED",
    }.issubset(top_fail_ids)

    occ = {row["value"]: row for row in summary["per_attr_rates"]["occupation"]}
    assert occ["student"]["convos"] == 2
    assert occ["student"]["convo_fails"] == 1
    assert occ["young_professional"]["convos"] == 1
    assert occ["young_professional"]["convo_fails"] == 1

    md = (tmp_path / "REPORT.md").read_text(encoding="utf-8")
    assert "Worst" in md
    assert "UNSUPPORTED_PRODUCT" in md or "STATE_KEY_LEAK" in md


def test_per_conversation_json_includes_persona_and_verdict(tmp_path) -> None:
    rubric = load_rubric(RUBRIC_PATH)
    res = _result(_persona("p-demo"), rubric, failing_ids=["PRODUCT_SAFETY_ONELINE"])
    write_run([res], tmp_path)
    payload = json.loads((tmp_path / "conversations" / "conv-p-demo.json").read_text(encoding="utf-8"))
    assert payload["persona"]["id"] == "p-demo"
    assert payload["verdict"] is not None
    failed = [it for it in payload["verdict"]["items"] if not it["passed"] and not it["not_applicable"]]
    assert len(failed) == 1
    assert failed[0]["id"] == "PRODUCT_SAFETY_ONELINE"
