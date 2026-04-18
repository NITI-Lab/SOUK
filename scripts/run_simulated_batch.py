#!/usr/bin/env python3
"""Run a batch of simulated conversations against a target chat agent.

Examples
--------
    # Smoke (5 conversations, fast feedback loop)
    AGENTCORE_API_KEY=... OPENAI_API_KEY=... python scripts/run_simulated_batch.py \\
        --personas personas/default_200.yaml \\
        --base-url https://example.com/agent \\
        --limit 5 --concurrency 2 --out reports/smoke

    # Full 200-run
    AGENTCORE_API_KEY=... OPENAI_API_KEY=... python scripts/run_simulated_batch.py \\
        --personas personas/default_200.yaml \\
        --base-url https://example.com/agent \\
        --concurrency 8 --out reports/run_$(date +%Y%m%d_%H%M)

Environment
-----------
    AGENTCORE_API_KEY  — API Gateway key for the target agent
    OPENAI_API_KEY     — user-simulator + judge API key
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
import time
from pathlib import Path

import yaml


def _setup_path() -> None:
    src = Path(__file__).resolve().parent.parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _load_personas(path: Path, limit: int | None):
    from souk.simulator import Persona

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = data.get("personas", [])
    if limit:
        entries = entries[:limit]
    return [Persona.from_dict(e) for e in entries]


async def _run(args: argparse.Namespace) -> int:
    _setup_path()
    from souk.simulator import (
        AgentTargetConfig,
        SimulatedUserLLM,
        StrictJudge,
        StrictJudgeConfig,
        UserLLMConfig,
        load_ground_truth_from_products,
        load_rubric,
        run_many_conversations,
    )
    from souk.simulator.report import write_run

    personas = _load_personas(Path(args.personas), args.limit)
    rubric = load_rubric(Path(args.rubric))

    api_key = os.environ.get("AGENTCORE_API_KEY", "")
    if not api_key:
        print("ERROR: AGENTCORE_API_KEY not set", file=sys.stderr)
        return 2

    target_cfg = AgentTargetConfig(
        base_url=args.base_url,
        api_key=api_key,
        tenant_id=args.tenant_id,
        model_id=args.agent_model_id,
        timeout=args.target_timeout,
    )
    user_llm = SimulatedUserLLM(
        UserLLMConfig(
            model=args.user_model,
            temperature=args.user_temperature,
        )
    )
    ground_truth = None
    if args.products_json:
        ground_truth = load_ground_truth_from_products(args.products_json)
    judge = StrictJudge(
        rubric,
        StrictJudgeConfig(
            model=args.judge_model,
            temperature=0.0,
        ),
        ground_truth=ground_truth,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = out_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    logger = logging.getLogger("batch")

    logger.info(
        "Starting batch: personas=%d concurrency=%d target=%s user_model=%s judge_model=%s",
        len(personas),
        args.concurrency,
        args.base_url,
        args.user_model,
        args.judge_model,
    )

    started = time.time()
    progress_state = {"done": 0, "pass": 0, "fail": 0, "err": 0}

    def _on_progress(done: int, total: int, result) -> None:
        progress_state["done"] = done
        if result.error:
            progress_state["err"] += 1
        elif result.verdict is not None and result.verdict.overall_pass():
            progress_state["pass"] += 1
        else:
            progress_state["fail"] += 1
        if done % max(1, args.progress_every) == 0 or done == total:
            elapsed = time.time() - started
            eta = (total - done) * (elapsed / done) if done else 0
            logger.info(
                "progress %d/%d  pass=%d fail=%d err=%d  elapsed=%.0fs eta=%.0fs",
                done,
                total,
                progress_state["pass"],
                progress_state["fail"],
                progress_state["err"],
                elapsed,
                eta,
            )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass

    results = await run_many_conversations(
        personas=personas,
        agent_cfg=target_cfg,
        user_llm=user_llm,
        judge=judge,
        concurrency=args.concurrency,
        max_turns=args.max_turns,
        kickoff_message=args.kickoff,
        progress_cb=_on_progress,
    )

    logger.info("writing report to %s", out_dir)
    summary = write_run(results, out_dir)

    logger.info(
        "DONE  overall_pass=%d/%d (%.1f%%)  critical=%d major=%d minor=%d",
        summary["overall_pass"],
        summary["judged"],
        summary["overall_pass_rate"] * 100,
        summary["per_severity_fail"].get("critical", 0),
        summary["per_severity_fail"].get("major", 0),
        summary["per_severity_fail"].get("minor", 0),
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--personas", required=True, help="persona YAML")
    ap.add_argument(
        "--rubric",
        default=str(Path(__file__).resolve().parent.parent / "rubrics" / "ec_recommendation_strict.yaml"),
    )
    ap.add_argument("--base-url", required=True, help="target agent base URL")
    ap.add_argument("--tenant-id", default="default")
    ap.add_argument("--agent-model-id", default=None)
    ap.add_argument("--user-model", default="gpt-5.4-mini")
    ap.add_argument("--user-temperature", type=float, default=0.8)
    ap.add_argument("--judge-model", default="gpt-5.4")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-turns", type=int, default=10)
    ap.add_argument("--target-timeout", type=float, default=90.0)
    ap.add_argument("--limit", type=int, default=None, help="subsample first N personas")
    ap.add_argument("--kickoff", default=None, help="optional fixed first user message")
    ap.add_argument("--progress-every", type=int, default=5)
    ap.add_argument(
        "--products-json",
        default=None,
        help="path to a tenant products.json for hallucination-grounding (optional)",
    )
    ap.add_argument("--out", required=True, help="report output directory")
    args = ap.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
