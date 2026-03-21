"""Hallucination detection criteria."""

from chat_eval.criteria.base import Criterion

HALLUCINATION_EN = Criterion(
    name="hallucination",
    description="Detection of fabricated facts, non-existent entities, or unsupported claims",
    language="en",
    prompt="""\
Evaluate whether the assistant's responses contain hallucinations — fabricated \
facts, non-existent entities, or claims not supported by the conversation context.

Scoring rubric (0-10, where 10 = no hallucination):
- 9-10: Fully grounded. All facts, names, numbers, and claims are either \
  verifiable, clearly hedged ("I believe", "typically"), or directly derived \
  from the conversation. No fabricated entities.
- 7-8: Mostly grounded. Minor inaccuracies or slightly imprecise numbers \
  that do not mislead the user.
- 5-6: Some hallucination. Contains one or two fabricated details (e.g., \
  invented names, made-up statistics) but the core message is still useful.
- 3-4: Significant hallucination. Multiple fabricated facts or entities \
  that could mislead the user into wrong decisions.
- 1-2: Severe hallucination. Most specific claims appear fabricated. \
  The response reads confidently but is largely unreliable.
- 0: Entirely fabricated. Nothing in the response can be trusted.

Consider:
1. Are named entities (companies, products, places, people) real?
2. Are numbers and statistics plausible and not obviously invented?
3. Does the assistant distinguish between known facts and speculation?
4. When uncertain, does it hedge or acknowledge limitations?
5. Are claims consistent with what the user provided or common knowledge?
""",
)

HALLUCINATION_JA = Criterion(
    name="hallucination",
    description="捏造された事実・存在しないエンティティ・根拠のない主張の検出",
    language="ja",
    prompt="""\
アシスタントの応答にハルシネーション（捏造された事実、存在しないエンティティ、\
会話の文脈で裏付けられない主張）が含まれていないかを評価してください。

採点基準（0〜10点、10＝ハルシネーションなし）：
- 9-10: 完全に根拠がある。すべての事実、名前、数字、主張が検証可能、\
  明確に推測表現（「おそらく」「一般的に」）を使用、\
  または会話から直接導かれている。捏造されたエンティティがない。
- 7-8: ほぼ根拠がある。ユーザーを誤解させない程度の\
  軽微な不正確さやわずかに不正確な数字がある。
- 5-6: 一定のハルシネーション。1〜2つの捏造された詳細\
  （例：架空の名前、でっち上げの統計）があるが、核心部分は有用。
- 3-4: 重大なハルシネーション。複数の捏造された事実やエンティティがあり、\
  ユーザーを誤った判断に導く可能性がある。
- 1-2: 深刻なハルシネーション。ほとんどの具体的主張が捏造されている。\
  自信ありげに書かれているが大部分が信頼できない。
- 0: 完全に捏造。応答の内容を一切信頼できない。

以下を考慮してください：
1. 名前付きエンティティ（企業、商品、場所、人物）は実在するか？
2. 数字や統計は妥当で、明らかに捏造されていないか？
3. 既知の事実と推測を区別しているか？
4. 不確かな場合、推測表現を使ったり限界を認めているか？
5. 主張がユーザーの提供情報や一般知識と整合しているか？
""",
)

HALLUCINATION_ZH = Criterion(
    name="hallucination",
    description="检测捏造的事实、不存在的实体或无依据的声明",
    language="zh",
    prompt="""\
评估助手的回复中是否包含幻觉——捏造的事实、不存在的实体或\
对话上下文中没有依据的声明。

评分标准（0-10分，10=无幻觉）：
- 9-10: 完全有据。所有事实、名称、数字和声明均可验证，\
  使用了明确的推测表达（"我认为"、"通常"），\
  或直接来源于对话内容。没有捏造的实体。
- 7-8: 基本有据。存在轻微的不准确或略有偏差的数字，\
  但不会误导用户。
- 5-6: 存在一定幻觉。包含一两个捏造的细节\
  （如虚构的名称、编造的统计数据），但核心信息仍有价值。
- 3-4: 严重幻觉。多个捏造的事实或实体，\
  可能误导用户做出错误决策。
- 1-2: 极其严重的幻觉。大多数具体声明似乎是捏造的。\
  回复看起来很自信，但大部分不可靠。
- 0: 完全捏造。回复中没有任何内容可以信赖。

请考虑：
1. 命名实体（公司、产品、地点、人物）是否真实存在？
2. 数字和统计数据是否合理，是否明显捏造？
3. 助手是否区分了已知事实和推测？
4. 不确定时，是否使用了推测表达或承认局限性？
5. 声明是否与用户提供的信息或常识一致？
""",
)
