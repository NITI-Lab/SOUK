"""Simulated-user framework for large-scale conversation evaluation."""

from souk.simulator.behaviors import (
    BEHAVIOR_INJECTORS,
    BehaviorInjector,
)
from souk.simulator.conversation_runner import (
    AgentSession,
    AgentTargetConfig,
    ConversationRunResult,
    run_many_conversations,
    run_single_conversation,
)
from souk.simulator.ground_truth import (
    GroundTruth,
    load_ground_truth_from_products,
)
from souk.simulator.persona import (
    Persona,
    PersonaLibrary,
    sample_personas,
)
from souk.simulator.strict_judge import (
    ItemVerdict,
    JudgeVerdict,
    Rubric,
    RubricItem,
    StrictJudge,
    StrictJudgeConfig,
    load_rubric,
    parse_judge_verdict,
    summarize_verdicts,
)
from souk.simulator.user_llm import (
    SimulatedUserLLM,
    UserLLMConfig,
    UserTurn,
    build_user_system_prompt,
    parse_user_turn,
)

__all__ = [
    # persona
    "Persona",
    "PersonaLibrary",
    "sample_personas",
    # behaviors
    "BEHAVIOR_INJECTORS",
    "BehaviorInjector",
    # user LLM
    "SimulatedUserLLM",
    "UserLLMConfig",
    "UserTurn",
    "build_user_system_prompt",
    "parse_user_turn",
    # judge
    "JudgeVerdict",
    "Rubric",
    "RubricItem",
    "StrictJudge",
    "StrictJudgeConfig",
    "ItemVerdict",
    "load_rubric",
    "parse_judge_verdict",
    "summarize_verdicts",
    # conversation runner
    "AgentSession",
    "AgentTargetConfig",
    "ConversationRunResult",
    "run_many_conversations",
    "run_single_conversation",
    # ground truth
    "GroundTruth",
    "load_ground_truth_from_products",
]
