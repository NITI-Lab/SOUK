"""Google/Gemini judge implementation."""

from __future__ import annotations

from souk.config import JudgeConfig
from souk.judges.base import JudgeBase, JudgeResult


class GoogleJudge(JudgeBase):
    """Judge using Google Generative AI API (Gemini)."""

    def __init__(self, config: JudgeConfig) -> None:
        super().__init__(config)
        import google.generativeai as genai

        genai.configure(api_key=config.resolve_api_key())
        self._genai = genai
        self.model = genai.GenerativeModel(
            config.model,
            generation_config=genai.GenerationConfig(
                temperature=config.temperature,
                max_output_tokens=config.max_tokens,
            ),
        )

    async def evaluate(
        self,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
        criterion_name: str,
    ) -> JudgeResult:
        messages = self._build_eval_messages(conversation, criterion_prompt)
        # Gemini combines system + user into a single prompt
        full_prompt = f"{messages[0]['content']}\n\n{messages[1]['content']}"

        response = await self.model.generate_content_async(full_prompt)
        raw = response.text or ""
        score, reasoning = self._parse_result(raw, criterion_name)
        return JudgeResult(
            judge_id=self.id,
            criterion=criterion_name,
            score=score,
            reasoning=reasoning,
            raw_response=raw,
            metadata={"model": self.config.model, "provider": "google"},
        )
