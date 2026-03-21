"""Tests for case loading."""

from pathlib import Path

from chat_eval.cases.loader import load_cases

CASES_DIR = Path(__file__).parent.parent / "cases"


def test_load_all_cases():
    cases = load_cases(CASES_DIR)
    assert len(cases) > 0
    for case in cases:
        assert case.id
        assert case.name
        assert case.language in ("en", "ja")
        assert case.is_static or case.is_live


def test_load_cases_filter_language():
    en_cases = load_cases(CASES_DIR, languages=["en"])
    ja_cases = load_cases(CASES_DIR, languages=["ja"])
    all_cases = load_cases(CASES_DIR)
    assert len(en_cases) + len(ja_cases) == len(all_cases)
    assert all(c.language == "en" for c in en_cases)
    assert all(c.language == "ja" for c in ja_cases)


def test_load_cases_filter_category():
    nat_cases = load_cases(CASES_DIR, categories=["naturalness"])
    rec_cases = load_cases(CASES_DIR, categories=["recommendation"])
    assert len(nat_cases) > 0
    assert len(rec_cases) > 0
    assert all(c.category == "naturalness" for c in nat_cases)
    assert all(c.category == "recommendation" for c in rec_cases)


def test_static_case_has_conversation():
    cases = load_cases(CASES_DIR, categories=["naturalness"], languages=["en"])
    static = [c for c in cases if c.is_static]
    assert len(static) > 0
    for case in static:
        assert len(case.conversation) >= 2
        roles = [m["role"] for m in case.conversation]
        assert "user" in roles
        assert "assistant" in roles


def test_live_case_has_user_turns():
    cases = load_cases(CASES_DIR)
    live = [c for c in cases if c.is_live]
    assert len(live) > 0
    for case in live:
        assert len(case.user_turns) >= 1
        assert len(case.conversation) == 0
