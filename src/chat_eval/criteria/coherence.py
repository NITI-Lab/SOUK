"""Conversation coherence criteria."""

from chat_eval.criteria.base import Criterion

COHERENCE_EN = Criterion(
    name="coherence",
    description="Logical consistency and flow across conversation turns",
    language="en",
    prompt="""\
Evaluate the coherence and logical consistency of the assistant's responses.

Scoring rubric (0-10):
- 9-10: Perfectly coherent. Every response logically follows from the conversation
  context. No contradictions, maintains all prior commitments, and references
  earlier information accurately.
- 7-8: Very coherent. Occasional minor lapses but overall strong logical flow.
  Maintains context well across turns.
- 5-6: Mostly coherent. Some disconnects between turns or minor contradictions
  that don't severely impact understanding.
- 3-4: Poor coherence. Frequently contradicts itself, forgets prior context,
  or provides responses that don't logically follow.
- 1-2: Very incoherent. Major contradictions, context loss, or non-sequiturs.
- 0: Completely incoherent.

Consider:
1. Context retention: Does the assistant remember what was discussed earlier?
2. Consistency: Are there any contradictions across responses?
3. Logical flow: Does each response follow logically from the conversation?
4. Reference accuracy: When referring to earlier statements, is it accurate?
""",
)

COHERENCE_JA = Criterion(
    name="coherence",
    description="会話ターン間の論理的一貫性と流れ",
    language="ja",
    prompt="""\
アシスタントの応答の一貫性と論理的整合性を評価してください。

採点基準（0〜10点）：
- 9-10: 完全に一貫している。すべての応答が会話の文脈から論理的に続いている。
  矛盾がなく、以前の内容を正確に参照している。
- 7-8: 非常に一貫している。時折軽微な失敗があるが、全体的に強い論理的流れ。
- 5-6: おおむね一貫している。ターン間にやや断絶があるか、
  理解に大きく影響しない程度の軽微な矛盾がある。
- 3-4: 一貫性が低い。頻繁に矛盾したり、以前の文脈を忘れたり、
  論理的に続かない応答を提供している。
- 1-2: 非常に一貫性がない。大きな矛盾、文脈の喪失、脈絡のない応答。
- 0: 完全に支離滅裂。

以下を考慮してください：
1. 文脈の保持：以前に話した内容を覚えているか？
2. 一貫性：応答間に矛盾がないか？
3. 論理的な流れ：各応答が会話から論理的に続いているか？
4. 参照の正確さ：以前の発言に言及する際、正確か？
""",
)

COHERENCE_ZH = Criterion(
    name="coherence",
    description="对话轮次间的逻辑一致性和流畅度",
    language="zh",
    prompt="""\
评估助手回复的连贯性和逻辑一致性。

评分标准（0-10分）：
- 9-10: 完全连贯。每个回复都合乎逻辑地承接对话上下文。\
  没有矛盾，保持所有先前承诺，准确引用之前的信息。
- 7-8: 非常连贯。偶有轻微失误但整体逻辑流畅。跨轮次保持上下文良好。
- 5-6: 基本连贯。轮次间有些断裂或不严重影响理解的轻微矛盾。
- 3-4: 连贯性差。频繁自相矛盾、遗忘之前的上下文或提供逻辑不通的回复。
- 1-2: 非常不连贯。存在重大矛盾、上下文丢失或前后不搭。
- 0: 完全不连贯。

请考虑：
1. 上下文保持：助手是否记得之前讨论的内容？
2. 一致性：回复之间是否存在矛盾？
3. 逻辑流程：每个回复是否合乎逻辑地承接对话？
4. 引用准确性：引用之前的陈述时是否准确？
""",
)
