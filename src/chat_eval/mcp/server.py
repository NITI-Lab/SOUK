"""MCP server exposing ChatEval as tools.

Run with: python -m chat_eval.mcp.server
Or configure in MCP settings as a stdio server.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except ImportError:
    print("MCP SDK not installed. Install with: pip install 'souk[mcp]'", file=sys.stderr)
    sys.exit(1)

from chat_eval.cases import load_cases
from chat_eval.config import load_config
from chat_eval.report import generate_report
from chat_eval.runner import EvalRunner

server = Server("souk")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="chateval_run",
            description=(
                "Run chat quality evaluation. Evaluates conversations using multiple "
                "AI judge models across criteria like naturalness and recommendation quality."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Path to the evaluation config YAML file",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter cases by category (e.g., 'naturalness', 'recommendation')",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter cases by language ('en' or 'ja')",
                    },
                    "case_id": {
                        "type": "string",
                        "description": "Run a specific case by ID",
                    },
                },
                "required": ["config_path"],
            },
        ),
        Tool(
            name="chateval_list_cases",
            description="List available test cases",
            inputSchema={
                "type": "object",
                "properties": {
                    "cases_dir": {
                        "type": "string",
                        "description": "Path to the cases directory",
                    },
                },
                "required": ["cases_dir"],
            },
        ),
        Tool(
            name="chateval_list_criteria",
            description="List available evaluation criteria",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="chateval_evaluate_conversation",
            description=(
                "Evaluate a single conversation inline (no YAML file needed). "
                "Provide the conversation directly as a list of messages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "config_path": {
                        "type": "string",
                        "description": "Path to config YAML (defines which judges to use)",
                    },
                    "conversation": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant"]},
                                "content": {"type": "string"},
                            },
                            "required": ["role", "content"],
                        },
                        "description": "The conversation to evaluate",
                    },
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Criteria to evaluate (default: ['naturalness'])",
                    },
                    "language": {
                        "type": "string",
                        "description": "Language of the conversation ('en' or 'ja')",
                        "default": "en",
                    },
                },
                "required": ["config_path", "conversation"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "chateval_run":
        return await _handle_run(arguments)
    elif name == "chateval_list_cases":
        return await _handle_list_cases(arguments)
    elif name == "chateval_list_criteria":
        return await _handle_list_criteria()
    elif name == "chateval_evaluate_conversation":
        return await _handle_evaluate_conversation(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _handle_run(args: dict) -> list[TextContent]:
    config = load_config(args["config_path"])
    cases = load_cases(
        config.cases_dir,
        categories=[args["category"]] if args.get("category") else None,
        languages=[args["language"]] if args.get("language") else config.languages,
    )
    if args.get("case_id"):
        cases = [c for c in cases if c.id == args["case_id"]]

    if not cases:
        return [TextContent(type="text", text="No test cases found matching filters.")]

    runner = EvalRunner(config)
    eval_run = await runner.run(cases)
    outputs = generate_report(eval_run)
    summary = eval_run.summary()

    result = json.dumps(
        {"summary": summary, "reports": {k: str(v) for k, v in outputs.items()}},
        indent=2,
        ensure_ascii=False,
    )
    return [TextContent(type="text", text=result)]


async def _handle_list_cases(args: dict) -> list[TextContent]:
    cases = load_cases(args["cases_dir"])
    result = [
        {"id": c.id, "name": c.name, "language": c.language, "category": c.category, "mode": "static" if c.is_static else "live"}
        for c in cases
    ]
    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _handle_list_criteria() -> list[TextContent]:
    from chat_eval.criteria import list_criteria, get_criterion

    result = []
    for name in list_criteria():
        c = get_criterion(name)
        result.append({"name": name, "description": c.description})
    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _handle_evaluate_conversation(args: dict) -> list[TextContent]:
    from chat_eval.cases.loader import TestCase

    config = load_config(args["config_path"])
    conversation = args["conversation"]
    criteria = args.get("criteria", ["naturalness"])
    language = args.get("language", "en")

    case = TestCase(
        id="inline",
        name="Inline Evaluation",
        language=language,
        category=criteria[0],
        conversation=conversation,
        criteria=criteria,
    )

    runner = EvalRunner(config)
    eval_run = await runner.run([case])

    if eval_run.results:
        r = eval_run.results[0]
        result = {
            "avg_score": round(r.avg_score, 2),
            "by_criterion": {k: round(v, 2) for k, v in r.avg_by_criterion().items()},
            "by_judge": {k: round(v, 2) for k, v in r.avg_by_judge().items()},
            "details": [
                {"judge": s.judge_id, "criterion": s.criterion, "score": round(s.score, 2), "reasoning": s.reasoning}
                for s in r.scores
            ],
        }
    else:
        result = {"error": "No results"}

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
