"""Tests for judge response parsing."""

from chat_eval.config import JudgeConfig
from chat_eval.judges.base import JudgeBase, JudgeResult


class MockJudge(JudgeBase):
    """Concrete judge for testing parse logic."""

    async def evaluate(self, conversation, criterion_prompt, criterion_name):
        return JudgeResult(judge_id="mock", criterion=criterion_name, score=5.0, reasoning="test")


def _make_judge():
    config = JudgeConfig(id="mock", provider="openai", model="test", api_key="fake")
    return MockJudge(config)


def test_parse_valid_json():
    judge = _make_judge()
    raw = '{"score": 8.5, "reasoning": "Very natural conversation"}'
    score, reasoning = judge._parse_result(raw, "naturalness")
    assert score == 8.5
    assert reasoning == "Very natural conversation"


def test_parse_json_with_surrounding_text():
    judge = _make_judge()
    raw = 'Here is my evaluation:\n{"score": 7.0, "reasoning": "Good flow"}\nEnd.'
    score, reasoning = judge._parse_result(raw, "naturalness")
    assert score == 7.0
    assert reasoning == "Good flow"


def test_parse_score_clamping():
    judge = _make_judge()
    raw = '{"score": 15, "reasoning": "test"}'
    score, _ = judge._parse_result(raw, "naturalness")
    assert score == 10.0

    raw = '{"score": -5, "reasoning": "test"}'
    score, _ = judge._parse_result(raw, "naturalness")
    assert score == 0.0


def test_parse_fallback_number():
    judge = _make_judge()
    raw = "I would rate this conversation a 6.5 out of 10."
    score, _ = judge._parse_result(raw, "naturalness")
    assert score == 6.5
