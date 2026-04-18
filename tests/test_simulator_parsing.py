"""Unit tests for parse_user_turn / parse_judge_verdict / rubric loader.

These tests avoid hitting any LLM API — they exercise the pure parsing
surface that guards against malformed model output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from souk.simulator import (
    BEHAVIOR_INJECTORS,
    ItemVerdict,
    JudgeVerdict,
    build_user_system_prompt,
    load_rubric,
    parse_judge_verdict,
    parse_user_turn,
    sample_personas,
    summarize_verdicts,
)
from souk.simulator.behaviors import resolve_injectors

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubrics" / "ec_recommendation_strict.yaml"


# ------------------------------------------------------------------ #
#  user_llm.parse_user_turn
# ------------------------------------------------------------------ #


def test_parse_user_turn_accepts_json_object() -> None:
    raw = '{"message": "I want a laptop for graphic design"}'
    turn = parse_user_turn(raw, injections=[])
    assert turn.text == "I want a laptop for graphic design"
    assert turn.status == "continue"


def test_parse_user_turn_handles_end_marker() -> None:
    raw = '{"message": "Thanks, that\'s all I needed [[END]]"}'
    turn = parse_user_turn(raw)
    assert turn.status == "end"
    assert "[[END]]" not in turn.text
    assert "Thanks" in turn.text


def test_parse_user_turn_handles_bail_marker() -> None:
    raw = '{"message": "[[BAIL]]"}'
    turn = parse_user_turn(raw)
    assert turn.status == "bail"
    assert turn.text == ""


def test_parse_user_turn_falls_back_to_regex_on_bad_json() -> None:
    raw = 'here is the answer: "message": "looking for shoes"}'
    turn = parse_user_turn(raw)
    assert turn.text == "looking for shoes"


def test_parse_user_turn_records_injection_hints() -> None:
    injectors = resolve_injectors(["offtopic_weather", "silent_reply"])
    turn = parse_user_turn('{"message": "ok"}', injections=injectors)
    assert set(turn.hints_applied) == {"offtopic_weather", "silent_reply"}


def test_build_user_system_prompt_includes_persona_fields() -> None:
    p = sample_personas(n=1, seed=99).personas[0]
    injectors = resolve_injectors(["sarcasm_doubt"])
    prompt = build_user_system_prompt(p, injectors)
    assert p.occupation in prompt
    assert p.purpose in prompt
    assert BEHAVIOR_INJECTORS["sarcasm_doubt"].hint in prompt


# ------------------------------------------------------------------ #
#  strict_judge.load_rubric
# ------------------------------------------------------------------ #


@pytest.fixture(scope="module")
def rubric():
    return load_rubric(RUBRIC_PATH)


def test_rubric_loads_with_expected_size(rubric) -> None:
    assert len(rubric.items) == 40
    ids = {i.id for i in rubric.items}
    for must_have in [
        "UNSUPPORTED_PRODUCT",
        "STATE_KEY_LEAK",
        "QUICK_REPLY_MARKER_LEAK",
        "PRODUCT_INTRO_FORMAT",
        "PRODUCT_SAFETY_ONELINE",
        "NO_DUPLICATE_PRICE",
        "NO_PHONE_NUMBER",
        "HANDOFF_ASKS_REQUIRED_FIELDS",
    ]:
        assert must_have in ids, f"{must_have} missing"


def test_rubric_severities_are_valid(rubric) -> None:
    for it in rubric.items:
        assert it.severity in {"critical", "major", "minor"}
        assert it.scope in {"turn", "convo"}


# ------------------------------------------------------------------ #
#  strict_judge.parse_judge_verdict
# ------------------------------------------------------------------ #


def _verdict_fixture_raw(rubric) -> str:
    items = []
    for it in rubric.items:
        if it.id == "UNSUPPORTED_PRODUCT":
            items.append(
                {
                    "id": it.id,
                    "passed": False,
                    "not_applicable": False,
                    "evidence": "I'd recommend the Acme Phantom Pro.",
                    "reason": "Acme Phantom Pro is not in the catalog.",
                }
            )
        elif it.id == "PRODUCT_SAFETY_ONELINE":
            items.append(
                {
                    "id": it.id,
                    "passed": True,
                    "not_applicable": False,
                    "evidence": "Note: not water-resistant.",
                    "reason": "Single-line safety note as required.",
                }
            )
        else:
            items.append(
                {
                    "id": it.id,
                    "passed": True,
                    "not_applicable": False,
                    "evidence": "",
                    "reason": "",
                }
            )
    import json

    return json.dumps({"items": items, "notes": "ok"}, ensure_ascii=False)


def test_parse_judge_verdict_round_trip(rubric) -> None:
    raw = _verdict_fixture_raw(rubric)
    verdict = parse_judge_verdict(conversation_id="c1", raw=raw, rubric=rubric)
    assert isinstance(verdict, JudgeVerdict)
    fails = verdict.fails_by_severity()
    assert len(fails["critical"]) == 1
    assert fails["critical"][0].id == "UNSUPPORTED_PRODUCT"
    assert {i.id for i in verdict.items} == {i.id for i in rubric.items}


def test_parse_judge_verdict_marks_missing_items_as_fail(rubric) -> None:
    import json

    raw = json.dumps(
        {
            "items": [
                {
                    "id": "UNSUPPORTED_PRODUCT",
                    "passed": True,
                    "not_applicable": False,
                    "evidence": "",
                    "reason": "",
                }
            ],
            "notes": "truncated",
        },
        ensure_ascii=False,
    )
    verdict = parse_judge_verdict("c2", raw=raw, rubric=rubric)

    missing = [it for it in verdict.items if it.reason.startswith("judge did not")]
    assert len(missing) == len(rubric.items) - 1
    assert all(not it.passed for it in missing)


def test_parse_judge_verdict_tolerates_markdown_fencing(rubric) -> None:
    raw = '```json\n{"items":[], "notes":""}\n```'
    verdict = parse_judge_verdict("c3", raw=raw, rubric=rubric)
    assert len(verdict.items) == len(rubric.items)


# ------------------------------------------------------------------ #
#  overall_pass + summarize_verdicts
# ------------------------------------------------------------------ #


def _make_verdict(rubric, failing_ids: list[tuple[str, str]] = (), conv_id: str = "c") -> JudgeVerdict:
    fail_map = {rid: sev for rid, sev in failing_ids}
    items = []
    for it in rubric.items:
        failing = it.id in fail_map
        items.append(
            ItemVerdict(
                id=it.id,
                passed=not failing,
                severity=it.severity,
                scope=it.scope,
                category=it.category,
                evidence="x" if failing else "",
                reason="fail" if failing else "",
            )
        )
    return JudgeVerdict(conversation_id=conv_id, items=items)


def test_overall_pass_rejects_any_critical_fail(rubric) -> None:
    v = _make_verdict(rubric, [("UNSUPPORTED_PRODUCT", "critical")])
    assert v.overall_pass() is False


def test_overall_pass_rejects_three_major_fails(rubric) -> None:
    v = _make_verdict(
        rubric,
        [
            ("STATE_KEY_LEAK", "major"),
            ("PRODUCT_INTRO_FORMAT", "major"),
            ("ANSWERS_WHAT_ASKED", "major"),
        ],
    )
    assert v.overall_pass() is False


def test_overall_pass_allows_minor_and_two_major(rubric) -> None:
    v = _make_verdict(
        rubric,
        [
            ("STATE_KEY_LEAK", "major"),
            ("PRODUCT_INTRO_FORMAT", "major"),
            ("CONSISTENT_POLITENESS", "minor"),
        ],
    )
    assert v.overall_pass() is True


def test_summarize_verdicts_aggregates_counts(rubric) -> None:
    v1 = _make_verdict(rubric, [("UNSUPPORTED_PRODUCT", "critical")], conv_id="a")
    v2 = _make_verdict(rubric, [("STATE_KEY_LEAK", "major")], conv_id="b")
    v3 = _make_verdict(rubric, [], conv_id="c")
    summary = summarize_verdicts([v1, v2, v3])
    assert summary["total_conversations"] == 3
    assert summary["overall_pass"] == 2
    assert summary["per_severity_fail_count"]["critical"] == 1
    assert summary["per_severity_fail_count"]["major"] == 1
    assert summary["per_item_fail_count"]["UNSUPPORTED_PRODUCT"] == 1
    assert summary["per_item_fail_count"]["STATE_KEY_LEAK"] == 1
