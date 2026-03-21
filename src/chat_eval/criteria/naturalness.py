"""Chat naturalness evaluation criteria."""

from chat_eval.criteria.base import Criterion

NATURALNESS_EN = Criterion(
    name="naturalness",
    description="How natural and human-like the conversation feels",
    language="en",
    prompt="""\
Evaluate the naturalness of the assistant's responses in this conversation.

Scoring rubric (0-10):
- 9-10: Indistinguishable from a skilled human. Natural flow, appropriate tone,
  contextually aware responses with no awkward phrasing.
- 7-8: Very natural. Minor issues that wouldn't bother most users.
  Good conversational rhythm and appropriate register.
- 5-6: Acceptable but noticeably AI-like. Some robotic phrasing,
  unnecessary formality, or slightly off-tone responses.
- 3-4: Clearly artificial. Frequent awkward constructions, repetitive patterns,
  or inappropriate tone shifts.
- 1-2: Very unnatural. Reads like a template or form letter.
  Poor flow, irrelevant responses, or broken conversational logic.
- 0: Completely incoherent or non-responsive.

Consider these factors:
1. Conversational flow: Do responses connect naturally to previous messages?
2. Tone consistency: Is the register appropriate and consistent?
3. Conciseness: Are responses appropriately sized (not over-explaining)?
4. Empathy: Does the assistant acknowledge the user's emotions/context?
5. Filler avoidance: Does it avoid unnecessary AI phrases like "Great question!" or "I'd be happy to help"?
""",
)

NATURALNESS_JA = Criterion(
    name="naturalness",
    description="会話の自然さの評価",
    language="ja",
    prompt="""\
この会話におけるアシスタントの応答の自然さを評価してください。

採点基準（0〜10点）：
- 9-10: 熟練した人間と区別がつかない。自然な流れ、適切なトーン、
  文脈を踏まえた応答で、不自然な表現がない。
- 7-8: 非常に自然。ほとんどのユーザーが気にならない程度の軽微な問題。
  良い会話リズムと適切な言葉遣い。
- 5-6: 許容範囲だが、AI的な印象がある。やや機械的な言い回し、
  不必要な丁寧さ、やや的外れなトーンの応答がある。
- 3-4: 明らかに人工的。不自然な構文、繰り返しパターン、
  不適切なトーンの変化が頻繁にある。
- 1-2: 非常に不自然。テンプレートのように読める。
  流れが悪く、無関係な応答や会話ロジックの破綻がある。
- 0: 完全に意味不明または無応答。

以下の要素を考慮してください：
1. 会話の流れ：応答が前のメッセージに自然につながっているか？
2. トーンの一貫性：言葉遣いが適切で一貫しているか？
3. 簡潔さ：応答の長さが適切か（過剰な説明をしていないか）？
4. 共感性：ユーザーの感情や状況を認識しているか？
5. 定型句の回避：「素晴らしい質問ですね！」のような不要なAI的フレーズを避けているか？
6. 敬語の適切さ：敬語のレベルが会話の文脈に合っているか？
""",
)

NATURALNESS_ZH = Criterion(
    name="naturalness",
    description="评估对话的自然程度",
    language="zh",
    prompt="""\
评估助手在本次对话中回复的自然程度。

评分标准（0-10分）：
- 9-10: 与熟练的人类无法区分。自然的对话流程、恰当的语气、\
  具有上下文意识的回复，没有生硬的措辞。
- 7-8: 非常自然。大多数用户不会在意的轻微问题。\
  良好的对话节奏和恰当的语域。
- 5-6: 可以接受但明显有AI感。有些机械化的措辞、\
  不必要的正式感或略有偏差的语气。
- 3-4: 明显人工化。频繁出现生硬的表达、重复模式或不恰当的语气变化。
- 1-2: 非常不自然。读起来像模板或表格信。\
  对话流程差、回复无关或对话逻辑断裂。
- 0: 完全不连贯或无回应。

请考虑以下因素：
1. 对话流畅度：回复是否自然地衔接了之前的消息？
2. 语气一致性：语域是否恰当且一致？
3. 简洁性：回复长度是否合适（是否过度解释）？
4. 共情能力：是否识别了用户的情感和处境？
5. 避免套话：是否避免了"好问题！"或"很高兴为您服务"等不必要的AI套话？
6. 语域适当性：敬语/口语的程度是否符合对话的语境？
""",
)
