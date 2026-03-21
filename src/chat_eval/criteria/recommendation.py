"""Product recommendation quality criteria."""

from chat_eval.criteria.base import Criterion

RECOMMENDATION_EN = Criterion(
    name="recommendation",
    description="Quality of product/service recommendations in conversation",
    language="en",
    prompt="""\
Evaluate the quality of product/service recommendations in this conversation.

Scoring rubric (0-10):
- 9-10: Excellent recommendations. Precisely matches user needs, provides
  relevant comparisons, explains trade-offs clearly, and guides the user
  toward a well-informed decision without being pushy.
- 7-8: Good recommendations. Mostly relevant suggestions with adequate
  explanation. Minor gaps in personalization or comparison.
- 5-6: Adequate recommendations. Suggestions are reasonable but generic.
  Limited personalization or missing key details the user would need.
- 3-4: Poor recommendations. Suggestions don't align well with stated needs,
  or the assistant pushes options without understanding preferences.
- 1-2: Very poor. Random or irrelevant suggestions, no attempt to understand
  user needs, or misleading information.
- 0: No recommendations provided when clearly requested.

Consider these factors:
1. Need understanding: Did the assistant correctly identify what the user wants?
2. Relevance: Are recommended items appropriate for the user's stated needs/constraints?
3. Explanation: Are pros/cons and key differentiators clearly communicated?
4. Personalization: Are recommendations tailored to the specific user, not generic?
5. Honesty: Does the assistant acknowledge limitations or trade-offs?
6. Conversational guidance: Does it help narrow down choices through dialogue?
""",
)

RECOMMENDATION_JA = Criterion(
    name="recommendation",
    description="商品・サービス推薦の品質評価",
    language="ja",
    prompt="""\
この会話における商品・サービス推薦の品質を評価してください。

採点基準（0〜10点）：
- 9-10: 優れた推薦。ユーザーのニーズに正確にマッチし、適切な比較を提供し、
  トレードオフを明確に説明し、押し付けがましくなく十分な情報に基づく
  意思決定に導いている。
- 7-8: 良い推薦。おおむね適切な提案で十分な説明がある。
  パーソナライゼーションや比較に軽微な不足がある。
- 5-6: まあまあの推薦。提案は妥当だが一般的。
  パーソナライゼーションが限られているか、重要な詳細が不足している。
- 3-4: 不十分な推薦。提案がユーザーのニーズと合っていないか、
  好みを理解せずに選択肢を押し付けている。
- 1-2: 非常に不十分。ランダムまたは無関係な提案、ユーザーのニーズを
  理解しようとしていない、または誤解を招く情報がある。
- 0: 明確に求められているのに推薦が提供されていない。

以下の要素を考慮してください：
1. ニーズの理解：ユーザーが何を求めているかを正確に把握しているか？
2. 関連性：推薦された項目がユーザーのニーズや制約に適切か？
3. 説明：長所・短所や主な差別化要因が明確に伝えられているか？
4. パーソナライゼーション：推薦が一般的ではなく特定のユーザー向けか？
5. 誠実さ：制限やトレードオフを認めているか？
6. 会話による導き：対話を通じて選択肢を絞り込む手助けをしているか？
""",
)

RECOMMENDATION_ZH = Criterion(
    name="recommendation",
    description="评估商品/服务推荐的质量",
    language="zh",
    prompt="""\
评估本次对话中商品/服务推荐的质量。

评分标准（0-10分）：
- 9-10: 优秀的推荐。精确匹配用户需求，提供相关比较，\
  清晰解释权衡，引导用户做出充分知情的决策而不强硬推销。
- 7-8: 良好的推荐。建议大体相关，解释充分。\
  在个性化或比较方面存在轻微不足。
- 5-6: 尚可的推荐。建议合理但泛泛而谈。\
  个性化有限或缺少用户需要的关键细节。
- 3-4: 较差的推荐。建议与用户需求不太匹配，\
  或在未了解偏好的情况下强推选项。
- 1-2: 很差。随机或无关的建议，未尝试了解用户需求，或提供误导信息。
- 0: 明确要求推荐时未提供任何推荐。

请考虑：
1. 需求理解：助手是否正确识别了用户想要什么？
2. 相关性：推荐的项目是否适合用户陈述的需求/约束？
3. 解释：优缺点和主要差异是否清晰传达？
4. 个性化：推荐是否针对特定用户而非泛泛而谈？
5. 诚实：是否承认了局限性或权衡？
6. 对话引导：是否通过对话帮助缩小选择范围？
""",
)
