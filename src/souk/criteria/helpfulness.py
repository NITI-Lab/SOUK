"""Helpfulness and task completion criteria."""

from souk.criteria.base import Criterion

HELPFULNESS_EN = Criterion(
    name="helpfulness",
    description="Whether the assistant effectively helps the user achieve their goal",
    language="en",
    prompt="""\
Evaluate whether the assistant effectively helps the user achieve their goal.

Scoring rubric (0-10):
- 9-10: Highly helpful. Directly addresses the user's needs, provides \
  actionable information, moves the conversation toward resolution, and \
  anticipates follow-up needs without over-explaining.
- 7-8: Helpful. Addresses the main request adequately with minor gaps \
  in completeness or actionability.
- 5-6: Somewhat helpful. Provides relevant information but misses key \
  aspects of the request, or adds unnecessary friction to the interaction.
- 3-4: Minimally helpful. Responds to the user but fails to meaningfully \
  advance their goal. May be evasive, overly generic, or off-target.
- 1-2: Unhelpful. Ignores the user's request, provides irrelevant \
  information, or creates confusion.
- 0: Counterproductive. Makes the situation worse or blocks the user.

Consider:
1. Does the assistant directly answer the user's question?
2. Is the information actionable (can the user act on it)?
3. Does it advance the conversation toward the user's goal?
4. Does it ask useful clarifying questions when needed?
5. Does it avoid unnecessary steps, repetition, or bureaucratic friction?
6. Does it proactively surface relevant information the user didn't ask for but would benefit from?
""",
)

HELPFULNESS_JA = Criterion(
    name="helpfulness",
    description="ユーザーの目的達成を効果的に支援しているか",
    language="ja",
    prompt="""\
アシスタントがユーザーの目的達成を効果的に支援しているかを評価してください。

採点基準（0〜10点）：
- 9-10: 非常に有用。ユーザーのニーズに直接対応し、\
  実行可能な情報を提供し、解決に向けて会話を進め、\
  過剰な説明なしにフォローアップのニーズを予測している。
- 7-8: 有用。主要なリクエストに十分に対応しているが、\
  完全性や実行可能性に軽微な不足がある。
- 5-6: やや有用。関連情報を提供しているが、リクエストの\
  重要な側面を見落としているか、不必要な摩擦を追加している。
- 3-4: 最小限の有用性。ユーザーに応答しているが、\
  目的の達成に実質的に貢献していない。回避的、一般的すぎる、\
  または的外れな場合がある。
- 1-2: 有用でない。ユーザーのリクエストを無視し、\
  無関係な情報を提供するか、混乱を招いている。
- 0: 逆効果。状況を悪化させたり、ユーザーをブロックしている。

以下を考慮してください：
1. ユーザーの質問に直接答えているか？
2. 情報は実行可能か（ユーザーがそれに基づいて行動できるか）？
3. ユーザーの目的に向けて会話を前進させているか？
4. 必要な時に有用な確認質問をしているか？
5. 不必要なステップ、繰り返し、手続き的な摩擦を避けているか？
6. ユーザーが聞いていないが有益な関連情報を積極的に提供しているか？
""",
)

HELPFULNESS_ZH = Criterion(
    name="helpfulness",
    description="助手是否有效地帮助用户实现其目标",
    language="zh",
    prompt="""\
评估助手是否有效地帮助用户实现其目标。

评分标准（0-10分）：
- 9-10: 非常有帮助。直接满足用户需求，提供可操作的信息，\
  推动对话朝着解决方案方向发展，并在不过度解释的情况下\
  预见后续需求。
- 7-8: 有帮助。充分回应了主要请求，在完整性或\
  可操作性方面存在轻微不足。
- 5-6: 有一定帮助。提供了相关信息，但遗漏了请求的关键方面，\
  或给交互增加了不必要的阻力。
- 3-4: 帮助极少。回应了用户但未能实质性地推进其目标。\
  可能过于回避、泛泛而谈或偏离主题。
- 1-2: 没有帮助。忽视用户请求，提供无关信息，或造成混乱。
- 0: 适得其反。使情况恶化或阻碍用户。

请考虑：
1. 助手是否直接回答了用户的问题？
2. 信息是否可操作（用户能否据此采取行动）？
3. 是否推动了对话朝用户目标方向发展？
4. 需要时是否提出了有用的澄清问题？
5. 是否避免了不必要的步骤、重复或流程上的阻力？
6. 是否主动提供了用户未询问但会受益的相关信息？
""",
)
