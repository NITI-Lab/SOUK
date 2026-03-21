"""Tests for criteria registry."""

from chat_eval.criteria import get_criterion, list_criteria

ALL_CRITERIA = [
    "naturalness",
    "recommendation",
    "coherence",
    "hallucination",
    "helpfulness",
    "toxicity",
    "prompt_injection",
    "info_leakage",
    "role_boundary",
    "pii_handling",
]

ALL_LANGUAGES = ["en", "ja", "zh"]


def test_list_criteria():
    names = list_criteria()
    for c in ALL_CRITERIA:
        assert c in names, f"Missing criterion: {c}"


def test_all_criteria_have_all_languages():
    for name in ALL_CRITERIA:
        for lang in ALL_LANGUAGES:
            c = get_criterion(name, lang)
            assert c.language == lang, f"Criterion '{name}' missing language '{lang}' (got '{c.language}' via fallback)"


def test_get_criterion_fallback():
    # Unknown language falls back to English
    c = get_criterion("naturalness", "fr")
    assert c.language == "en"


def test_naturalness_zh():
    c = get_criterion("naturalness", "zh")
    assert c.language == "zh"
    assert "自然" in c.prompt


def test_hallucination_all_langs():
    en = get_criterion("hallucination", "en")
    ja = get_criterion("hallucination", "ja")
    zh = get_criterion("hallucination", "zh")
    assert "hallucination" in en.prompt.lower()
    assert "ハルシネーション" in ja.prompt
    assert "幻觉" in zh.prompt


def test_helpfulness_all_langs():
    en = get_criterion("helpfulness", "en")
    ja = get_criterion("helpfulness", "ja")
    zh = get_criterion("helpfulness", "zh")
    assert "helpful" in en.prompt.lower()
    assert "有用" in ja.prompt
    assert "帮助" in zh.prompt


def test_toxicity_all_langs():
    en = get_criterion("toxicity", "en")
    ja = get_criterion("toxicity", "ja")
    zh = get_criterion("toxicity", "zh")
    assert "toxic" in en.prompt.lower() or "harmful" in en.prompt.lower()
    assert "有害" in ja.prompt
    assert "有害" in zh.prompt


def test_security_criteria_all_langs():
    for name in ["prompt_injection", "info_leakage", "role_boundary", "pii_handling"]:
        for lang in ALL_LANGUAGES:
            c = get_criterion(name, lang)
            assert c.language == lang, f"{name}/{lang} missing"
            assert len(c.prompt) > 100, f"{name}/{lang} prompt too short"
