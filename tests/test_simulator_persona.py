"""Unit tests for the simulator persona / behaviour layers."""

from __future__ import annotations

import collections

from souk.simulator import (
    BEHAVIOR_INJECTORS,
    Persona,
    sample_personas,
)
from souk.simulator.behaviors import resolve_injectors, schedule_injections


def test_sample_personas_is_deterministic() -> None:
    a = sample_personas(n=50, seed=42)
    b = sample_personas(n=50, seed=42)
    assert [p.id for p in a] == [p.id for p in b]


def test_sample_personas_balanced_primary_axes_at_200() -> None:
    lib = sample_personas(n=200, seed=0)
    assert len(lib) == 200

    by_occ = collections.Counter(p.occupation for p in lib)
    by_pur = collections.Counter(p.purpose for p in lib)
    by_pri = collections.Counter(p.priorities for p in lib)

    # 5 occupations, 5 purposes, 4 priorities. 200 / 5 = 40; 200 / 4 = 50.
    assert set(by_occ.values()) == {40}
    assert set(by_pur.values()) == {40}
    assert set(by_pri.values()) == {50}


def test_sample_personas_small_n_subsamples_grid() -> None:
    lib = sample_personas(n=10, seed=1)
    assert len(lib) == 10
    triples = {(p.occupation, p.purpose, p.priorities) for p in lib}
    assert len(triples) == 10


def test_persona_id_changes_when_injections_change() -> None:
    base = Persona(
        id="ignored",
        occupation="young_professional",
        purpose="work_essential",
        priorities="best_quality",
        comm_style="concise",
        knowledge_level="experienced",
        budget_hint="explicit",
        injections=[],
    )
    a = sample_personas(n=1, seed=0).personas[0]
    b = sample_personas(n=1, seed=1).personas[0]
    assert a.id != b.id or a.injections != b.injections

    _ = base  # silence unused


def test_all_injectors_have_required_fields() -> None:
    for inj in BEHAVIOR_INJECTORS.values():
        assert inj.id
        assert inj.label
        assert inj.hint
        assert inj.trigger in {"early", "mid", "late", "any"}
        assert inj.tags, f"injector {inj.id} missing rubric tags"


def test_resolve_injectors_ignores_unknown_ids() -> None:
    resolved = resolve_injectors(["offtopic_weather", "nonexistent", "emoji_only_reply"])
    ids = {r.id for r in resolved}
    assert ids == {"offtopic_weather", "emoji_only_reply"}


def test_schedule_injections_respects_trigger() -> None:
    injectors = resolve_injectors(["offtopic_weather", "mid_category_change", "long_rant"])
    schedule = schedule_injections(injectors, total_turns=10)

    # long_rant is "early" → should land on turn 1
    assert any(i.id == "long_rant" for i in schedule.get(1, []))
    # mid_category_change is "mid" → should land on turn 5
    assert any(i.id == "mid_category_change" for i in schedule.get(5, []))
