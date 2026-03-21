"""Test case loading from YAML files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TestCase:
    """A single evaluation test case."""

    id: str
    name: str
    language: str  # "en" or "ja"
    category: str  # "naturalness", "recommendation", etc.
    description: str = ""
    conversation: list[dict[str, str]] = field(default_factory=list)
    # For live evaluation: only user turns, assistant responses are generated
    user_turns: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def is_static(self) -> bool:
        """Whether this is a static (pre-recorded) evaluation case."""
        return len(self.conversation) > 0

    @property
    def is_live(self) -> bool:
        """Whether this requires live interaction with a target service."""
        return len(self.user_turns) > 0 and len(self.conversation) == 0


def load_case_from_yaml(path: Path) -> TestCase:
    """Load a single test case from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return TestCase(
        id=data.get("id", path.stem),
        name=data.get("name", path.stem),
        language=data.get("language", "en"),
        category=data.get("category", "naturalness"),
        description=data.get("description", ""),
        conversation=data.get("conversation", []),
        user_turns=data.get("user_turns", []),
        criteria=data.get("criteria", []),
        tags=data.get("tags", []),
        metadata=data.get("metadata", {}),
    )


def load_cases(
    cases_dir: str | Path,
    categories: list[str] | None = None,
    languages: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[TestCase]:
    """Load test cases from a directory structure.

    Directory structure:
        cases_dir/
          category/
            language/
              case_file.yaml

    Or flat:
        cases_dir/
          case_file.yaml  (category/language specified in YAML)
    """
    cases_dir = Path(cases_dir)
    if not cases_dir.exists():
        return []

    cases: list[TestCase] = []
    for yaml_path in sorted(cases_dir.rglob("*.yaml")):
        try:
            case = load_case_from_yaml(yaml_path)
        except Exception as e:
            print(f"Warning: Failed to load {yaml_path}: {e}")
            continue

        # Infer category/language from directory structure if not specified
        rel = yaml_path.relative_to(cases_dir)
        parts = rel.parts
        if len(parts) >= 3 and not case.category:
            case.category = parts[0]
        if len(parts) >= 3 and case.language == "en":
            possible_lang = parts[1] if len(parts) >= 3 else None
            if possible_lang in ("en", "ja"):
                case.language = possible_lang

        # Apply filters
        if categories and case.category not in categories:
            continue
        if languages and case.language not in languages:
            continue
        if tags and not any(t in case.tags for t in tags):
            continue

        cases.append(case)

    return cases
