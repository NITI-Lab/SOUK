"""Behavior injectors for simulated users.

Each injector carries:
    id       — stable identifier used in Persona.injections
    label    — short human label for reporting
    hint     — instruction snippet appended to the user-simulator prompt
    trigger  — heuristic for when (turn index) to fire
    tags     — rubric ids this injector specifically probes, so the
               aggregated report can prove coverage per rubric item.

The simulator prompt stitches ``hint`` into the system message when an
injection is scheduled for the current turn.

Defaults target an EC product-recommendation chat. Replace this dict to
target a different domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TurnTiming = Literal["early", "mid", "late", "any"]


@dataclass(frozen=True)
class BehaviorInjector:
    id: str
    label: str
    hint: str
    trigger: TurnTiming
    tags: tuple[str, ...]


BEHAVIOR_INJECTORS: dict[str, BehaviorInjector] = {
    inj.id: inj
    for inj in (
        BehaviorInjector(
            id="mid_category_change",
            label="switch product category mid-conversation",
            hint=(
                "After the assistant has narrowed in on one product category, "
                "abruptly switch to a different category (e.g. laptops -> headphones). "
                "Phrase it naturally, like 'actually, on second thought I want X instead'."
            ),
            trigger="mid",
            tags=("RECOGNIZE_CORRECTION",),
        ),
        BehaviorInjector(
            id="mid_purpose_change",
            label="switch purchase purpose mid-conversation",
            hint=(
                "Just before the assistant gives a recommendation, change the "
                "purpose you stated earlier (e.g. 'wait, this is actually a gift' "
                "or 'I changed my mind, it's for work, not personal use')."
            ),
            trigger="mid",
            tags=("RECOGNIZE_CORRECTION",),
        ),
        BehaviorInjector(
            id="ambiguous_number_reply",
            label="answer numbered choice with vague free text",
            hint=(
                "When the assistant offers numbered choices, do NOT reply with a "
                "number. Reply with vague free text such as 'hmm, hard to say', "
                "'either is fine', or 'I haven't decided yet'."
            ),
            trigger="early",
            tags=("BARE_NUMBER_INTERPRETED", "KEYWORD_ONLY_INTERCEPT"),
        ),
        BehaviorInjector(
            id="offtopic_origin_country",
            label="ask about country of origin",
            hint=(
                "At some point ask 'where is this made?', 'is it made domestically?', "
                "or 'I'd prefer something not made in country X'."
            ),
            trigger="any",
            tags=("KEYWORD_ONLY_INTERCEPT",),
        ),
        BehaviorInjector(
            id="offtopic_payment_method",
            label="ask about payment options",
            hint=(
                "At some point ask about payment options: 'can I pay in installments?', "
                "'do you accept credit cards?', 'how many payments can I split this into?'."
            ),
            trigger="any",
            tags=("KEYWORD_ONLY_INTERCEPT",),
        ),
        BehaviorInjector(
            id="offtopic_shipping",
            label="ask about shipping",
            hint=(
                "At some point ask about shipping: 'is shipping included?', "
                "'how much is delivery?', 'can it be expedited?'."
            ),
            trigger="any",
            tags=("KEYWORD_ONLY_INTERCEPT",),
        ),
        BehaviorInjector(
            id="offtopic_warranty",
            label="ask about warranty / returns",
            hint=(
                "At some point ask about warranty or returns: 'what's the return policy?', "
                "'is there a warranty?', 'what if it breaks?'."
            ),
            trigger="any",
            tags=("KEYWORD_ONLY_INTERCEPT",),
        ),
        BehaviorInjector(
            id="offtopic_weather",
            label="completely off-topic question",
            hint=(
                "Drop in one completely unrelated question (today's weather, "
                "a movie recommendation, your hobbies, etc.)."
            ),
            trigger="any",
            tags=("OFFTOPIC_GRACEFUL",),
        ),
        BehaviorInjector(
            id="multi_question",
            label="multiple questions in one message",
            hint=(
                "Pack 2-3 questions into a single message. Example: "
                "'how much is it? does it ship in time? and any reviews you trust?'"
            ),
            trigger="any",
            tags=("ANSWERS_WHAT_ASKED",),
        ),
        BehaviorInjector(
            id="sarcasm_doubt",
            label="skeptical / sarcastic",
            hint=("React to the recommendation with skepticism: 'really?', 'sounds fishy', 'is this an ad?', etc."),
            trigger="mid",
            tags=("EMPATHY_ON_ANXIETY", "NO_HALLUCINATED_OFFER"),
        ),
        BehaviorInjector(
            id="silent_reply",
            label="near-silent ('yes' / 'ok' / 'sure')",
            hint=(
                "When asked questions, give the smallest possible reply: 'yes', 'ok', "
                "'sure', 'right'. Volunteer nothing extra."
            ),
            trigger="any",
            tags=("ANSWERS_WHAT_ASKED", "MOVES_FLOW_FORWARD"),
        ),
        BehaviorInjector(
            id="emoji_only_reply",
            label="emoji-only reply",
            hint=("Reply with emoji only (🤔 / 👍 / ✨ / 🥺)."),
            trigger="any",
            tags=("ANSWERS_WHAT_ASKED",),
        ),
        BehaviorInjector(
            id="typo_reply",
            label="typos and abbreviations",
            hint=("Use frequent typos ('headfones', 'lapptop') and abbreviations ('mbp', 'tldr', 'asap')."),
            trigger="any",
            tags=("KEYWORD_ONLY_INTERCEPT",),
        ),
        BehaviorInjector(
            id="code_switch",
            label="mixed language",
            hint=(
                "Mix English and another language naturally inside one message, "
                "e.g. 'cheap な laptop で please' or 'budget は about $500'."
            ),
            trigger="any",
            tags=("KEYWORD_ONLY_INTERCEPT",),
        ),
        BehaviorInjector(
            id="long_rant",
            label="long verbose rant",
            hint=(
                "At some point, dump 200+ characters explaining your situation, "
                "anxieties, and background in one message. Multiple wishes mixed "
                "together is fine."
            ),
            trigger="early",
            tags=("EMPATHY_ON_ANXIETY", "ANSWERS_WHAT_ASKED"),
        ),
    )
}


def resolve_injectors(ids: list[str]) -> list[BehaviorInjector]:
    """Return injectors by id, skipping unknown ids."""
    out: list[BehaviorInjector] = []
    for iid in ids:
        inj = BEHAVIOR_INJECTORS.get(iid)
        if inj is not None:
            out.append(inj)
    return out


def schedule_injections(injectors: list[BehaviorInjector], total_turns: int) -> dict[int, list[BehaviorInjector]]:
    """Assign each injector to a turn index based on its trigger window."""
    if total_turns <= 0:
        return {}
    schedule: dict[int, list[BehaviorInjector]] = {}
    for inj in injectors:
        if inj.trigger == "early":
            turn = max(0, min(total_turns - 1, 1))
        elif inj.trigger == "mid":
            turn = total_turns // 2
        elif inj.trigger == "late":
            turn = max(0, total_turns - 2)
        else:  # "any"
            turn = total_turns // 2
        schedule.setdefault(turn, []).append(inj)
    return schedule
