#!/usr/bin/env python3
"""Convert go-abroad conversation_eval_cases.json to ChatEval YAML format.

Usage:
    python scripts/convert_eval_cases.py \
        ../agent-core/tests/conversation_eval_cases.json \
        cases/go-abroad/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


def convert(input_path: str, output_dir: str) -> None:
    with open(input_path) as f:
        data = json.load(f)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for case in data["cases"]:
        chateval_case = {
            "id": case["id"],
            "name": case.get("description", case["id"]),
            "language": "ja",
            "category": _infer_category(case),
            "description": case.get("context", case.get("description", "")),
            "criteria": ["naturalness", "coherence"],
            "tags": ["go-abroad", "converted"],
            "user_turns": case["messages"],
        }

        # Add recommendation criterion for school-related cases
        if any(kw in case["id"] for kw in ["school", "recommendation", "product"]):
            chateval_case["criteria"].append("recommendation")

        filename = f"{case['id']}.yaml"
        with open(out / filename, "w") as f:
            yaml.dump(chateval_case, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"  Created: {out / filename}")

    print(f"\nConverted {len(data['cases'])} cases to {output_dir}")


def _infer_category(case: dict) -> str:
    case_id = case["id"]
    if any(kw in case_id for kw in ["school", "recommendation", "product", "alternate"]):
        return "recommendation"
    return "naturalness"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.json> <output_dir>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
