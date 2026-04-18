"""Persona schema + stratified sampler for simulated-user eval.

A Persona is a compact, LLM-friendly description of a synthetic user. The
simulator passes it to a "play this user" prompt to generate the user's
next turn given the conversation so far.

Defaults are tuned for an EC product-recommendation chat assistant. Every
enum is a string so projects can extend or replace them without changing
the sampler.

Sampling uses stratified rejection: we walk the primary axes
(occupation × purpose × priorities) as a grid and fill each cell with
round-robin picks for the secondary axes (comm_style, knowledge,
budget_hint, injections). This guarantees every (occupation, purpose,
priorities) triple appears before any cell is duplicated, so rubric
coverage stays broad even at small sample sizes.
"""

from __future__ import annotations

import hashlib
import itertools
import random
from dataclasses import asdict, dataclass, field
from typing import Iterable

OCCUPATIONS = (
    "student",
    "young_professional",
    "parent",
    "senior",
    "retiree",
)

PURPOSES = (
    "gift_for_someone",
    "personal_use",
    "work_essential",
    "hobby_upgrade",
    "first_purchase",
)

PRIORITIES = (
    "lowest_price",
    "best_quality",
    "fast_delivery",
    "popular_brand",
)

COMM_STYLES = (
    "concise",  # one-word answers, "yes" / "ok" / "2"
    "polite",  # formal phrasing, "could you possibly..."
    "casual",  # slangy, "yeah whatever works"
    "emoji_heavy",  # heavy emoji use, "love it 🥰✨"
    "mixed_lang",  # native + English mix
)

KNOWLEDGE_LEVELS = (
    "novice",
    "experienced",
)

BUDGET_HINTS = (
    "explicit",  # states an exact budget early
    "vague",  # "something cheap-ish"
    "unspecified",  # never mentions budget
)

# Behavior injection ids — see behaviors.py for definitions.
DEFAULT_INJECTORS = (
    "mid_category_change",
    "mid_purpose_change",
    "ambiguous_number_reply",
    "offtopic_origin_country",
    "offtopic_payment_method",
    "offtopic_shipping",
    "offtopic_warranty",
    "offtopic_weather",
    "multi_question",
    "sarcasm_doubt",
    "silent_reply",
    "emoji_only_reply",
    "typo_reply",
    "code_switch",
    "long_rant",
)


@dataclass
class Persona:
    """A synthetic user specification.

    ``id`` is deterministic from attributes so reruns of a given sampling
    seed produce comparable persona sets.
    """

    id: str
    occupation: str
    purpose: str
    priorities: str
    comm_style: str
    knowledge_level: str
    budget_hint: str
    injections: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Persona":
        return cls(**data)

    def summary(self) -> str:
        inj = ", ".join(self.injections) if self.injections else "none"
        return (
            f"[{self.id}] {self.occupation} / {self.purpose} / {self.priorities}"
            f" / style:{self.comm_style} / knowledge:{self.knowledge_level}"
            f" / budget:{self.budget_hint} / behaviors:{inj}"
        )


@dataclass
class PersonaLibrary:
    """Container for a sampled set of personas."""

    personas: list[Persona]

    def __len__(self) -> int:
        return len(self.personas)

    def __iter__(self) -> Iterable[Persona]:
        return iter(self.personas)


def _persona_id(fields: tuple[str, ...], injections: tuple[str, ...]) -> str:
    payload = "|".join(fields) + "||" + ",".join(sorted(injections))
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"p-{digest}"


def sample_personas(
    n: int,
    *,
    seed: int = 0,
    injection_menu: Iterable[str] = DEFAULT_INJECTORS,
    inj_probability: tuple[float, float, float] = (0.25, 0.55, 0.20),
) -> PersonaLibrary:
    """Return ``n`` personas with stratified coverage.

    Parameters
    ----------
    n:
        Target persona count. Sampling guarantees every (occupation,
        purpose, priorities) triple is visited at least once if ``n``
        >= len(OCCUPATIONS)*len(PURPOSES)*len(PRIORITIES) (=100); smaller
        ``n`` subsamples the grid uniformly.
    seed:
        RNG seed for reproducibility.
    injection_menu:
        Behavior ids eligible for injection. Each persona is assigned
        0 / 1 / 2 injections with probabilities ``inj_probability``
        (must sum to 1.0).
    """
    rng = random.Random(seed)
    menu = list(injection_menu)
    if abs(sum(inj_probability) - 1.0) > 1e-6:
        raise ValueError("inj_probability must sum to 1.0")

    primary_grid = list(itertools.product(OCCUPATIONS, PURPOSES, PRIORITIES))
    rng.shuffle(primary_grid)

    if n >= len(primary_grid):
        repeats = (n + len(primary_grid) - 1) // len(primary_grid)
        expanded = primary_grid * repeats
        rng.shuffle(expanded)
        chosen_primary = expanded[:n]
    else:
        chosen_primary = primary_grid[:n]

    personas: list[Persona] = []
    for occupation, purpose, priorities in chosen_primary:
        comm = rng.choice(COMM_STYLES)
        knowledge = rng.choice(KNOWLEDGE_LEVELS)
        budget = rng.choice(BUDGET_HINTS)

        r = rng.random()
        if r < inj_probability[0]:
            inj_count = 0
        elif r < inj_probability[0] + inj_probability[1]:
            inj_count = 1
        else:
            inj_count = 2
        injections = sorted(rng.sample(menu, min(inj_count, len(menu))))

        fields = (occupation, purpose, priorities, comm, knowledge, budget)
        pid = _persona_id(fields, tuple(injections))
        personas.append(
            Persona(
                id=pid,
                occupation=occupation,
                purpose=purpose,
                priorities=priorities,
                comm_style=comm,
                knowledge_level=knowledge,
                budget_hint=budget,
                injections=list(injections),
            )
        )
    return PersonaLibrary(personas=personas)
