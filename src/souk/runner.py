"""Evaluation runner - orchestrates judges, cases, and criteria."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from souk.cases.loader import TestCase
from souk.config import EvalConfig, TargetConfig
from souk.criteria import get_criterion
from souk.judges import create_judge
from souk.judges.base import JudgeBase, JudgeResult
from souk.target import TargetClient


def _create_target_client(target_config: TargetConfig) -> TargetClient:
    """Create the appropriate target client for a single target config."""
    if target_config.provider == "agentcore":
        from souk.targets.agentcore import AgentCoreTarget

        return AgentCoreTarget(target_config)  # type: ignore[return-value]
    if target_config.provider == "agentcore-local":
        from souk.targets.agentcore_local import AgentCoreLocalTarget

        return AgentCoreLocalTarget(target_config)  # type: ignore[return-value]
    return TargetClient(target_config)


def _create_target(config: EvalConfig) -> TargetClient | None:
    """Create target client from legacy single-target config (backward compat)."""
    if not config.target:
        return None
    return _create_target_client(config.target)


@dataclass
class CaseResult:
    """Results for a single test case across all judges and criteria."""

    case_id: str
    case_name: str
    language: str
    category: str
    target_id: str = ""
    scores: list[JudgeResult] = field(default_factory=list)
    conversation: list[dict[str, str]] = field(default_factory=list)
    response_times: list[float] = field(default_factory=list)  # per-turn seconds
    error: str | None = None

    @property
    def total_response_time(self) -> float:
        return sum(self.response_times)

    @property
    def avg_response_time(self) -> float:
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def avg_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores) / len(self.scores)

    def avg_by_criterion(self) -> dict[str, float]:
        by_criterion: dict[str, list[float]] = {}
        for s in self.scores:
            by_criterion.setdefault(s.criterion, []).append(s.score)
        return {k: sum(v) / len(v) for k, v in by_criterion.items()}

    def avg_by_judge(self) -> dict[str, float]:
        by_judge: dict[str, list[float]] = {}
        for s in self.scores:
            by_judge.setdefault(s.judge_id, []).append(s.score)
        return {k: sum(v) / len(v) for k, v in by_judge.items()}


@dataclass
class EvalRun:
    """Complete evaluation run results."""

    config: EvalConfig
    results: list[CaseResult] = field(default_factory=list)
    started_at: float = 0.0
    finished_at: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def is_multi_target(self) -> bool:
        target_ids = {r.target_id for r in self.results if r.target_id}
        return len(target_ids) > 1

    @property
    def target_ids(self) -> list[str]:
        seen: dict[str, None] = {}
        for r in self.results:
            if r.target_id and r.target_id not in seen:
                seen[r.target_id] = None
        return list(seen.keys())

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def total_evaluations(self) -> int:
        return sum(len(r.scores) for r in self.results)

    def summary(self) -> dict:
        """Generate summary statistics."""
        all_scores = [s for r in self.results for s in r.scores]

        by_judge: dict[str, list[float]] = {}
        by_criterion: dict[str, list[float]] = {}
        by_category: dict[str, list[float]] = {}
        by_target: dict[str, list[float]] = {}

        for s in all_scores:
            by_judge.setdefault(s.judge_id, []).append(s.score)
            by_criterion.setdefault(s.criterion, []).append(s.score)
        for r in self.results:
            for s in r.scores:
                by_category.setdefault(r.category, []).append(s.score)
                if r.target_id:
                    by_target.setdefault(r.target_id, []).append(s.score)

        result = {
            "overall_avg": sum(s.score for s in all_scores) / len(all_scores) if all_scores else 0,
            "by_judge": {k: sum(v) / len(v) for k, v in by_judge.items()},
            "by_criterion": {k: sum(v) / len(v) for k, v in by_criterion.items()},
            "by_category": {k: sum(v) / len(v) for k, v in by_category.items()},
            "total_cases": self.total_cases,
            "total_evaluations": self.total_evaluations,
            "duration_seconds": self.duration_seconds,
        }

        if by_target:
            result["by_target"] = {k: sum(v) / len(v) for k, v in by_target.items()}

            # Cross-tabulation: target × criterion
            target_criterion: dict[str, dict[str, list[float]]] = {}
            for r in self.results:
                if not r.target_id:
                    continue
                for s in r.scores:
                    target_criterion.setdefault(r.target_id, {}).setdefault(s.criterion, []).append(s.score)
            result["by_target_criterion"] = {
                tid: {crit: sum(vals) / len(vals) for crit, vals in crits.items()}
                for tid, crits in target_criterion.items()
            }

        # Response time stats by target
        target_times: dict[str, list[float]] = {}
        for r in self.results:
            if r.target_id and r.response_times:
                target_times.setdefault(r.target_id, []).extend(r.response_times)
        if target_times:
            result["response_times"] = {
                tid: {
                    "avg_per_turn": sum(ts) / len(ts),
                    "total": sum(ts),
                    "turns": len(ts),
                }
                for tid, ts in target_times.items()
            }

        return result


class EvalRunner:
    """Orchestrates the evaluation process."""

    def __init__(self, config: EvalConfig) -> None:
        self.config = config
        self.console = Console()
        self.judges: list[JudgeBase] = [create_judge(jc) for jc in config.judges]
        # Legacy single-target support
        self.target = _create_target(config)

    async def run(self, cases: list[TestCase]) -> EvalRun:
        """Run evaluation on all cases.

        If multiple targets are configured, runs each case against all targets.
        """
        targets = self.config.get_targets()

        if len(targets) > 1:
            return await self._run_multi_target(cases, targets)
        else:
            return await self._run_single(cases)

    async def _run_single(self, cases: list[TestCase]) -> EvalRun:
        """Single-target evaluation (original behavior)."""
        run = EvalRun(config=self.config, started_at=time.time())
        target_id = ""
        targets = self.config.get_targets()
        if targets:
            target_id = targets[0].id

        self.console.print(f"\n[bold]SOUK[/bold] - Evaluating {len(cases)} cases with {len(self.judges)} judges\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Evaluating...", total=len(cases))

            sem = asyncio.Semaphore(self.config.concurrency)

            async def eval_case(case: TestCase) -> CaseResult:
                async with sem:
                    result = await self._evaluate_case(case, self.target, target_id)
                    progress.advance(task)
                    return result

            run.results = await asyncio.gather(*[eval_case(c) for c in cases])

        run.finished_at = time.time()
        run.errors = [r.error for r in run.results if r.error]
        return run

    async def _run_multi_target(self, cases: list[TestCase], targets: list[TargetConfig]) -> EvalRun:
        """Multi-target round-robin evaluation."""
        run = EvalRun(config=self.config, started_at=time.time())
        total = len(cases) * len(targets)

        self.console.print(
            f"\n[bold]SOUK[/bold] - Round-robin: {len(cases)} cases "
            f"× {len(targets)} targets × {len(self.judges)} judges\n"
        )

        target_names = ", ".join(t.id for t in targets)
        self.console.print(f"  Targets: [cyan]{target_names}[/cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Evaluating...", total=total)

            sem = asyncio.Semaphore(self.config.concurrency)
            all_results: list[CaseResult] = []

            # Process targets sequentially (each target may have session state),
            # cases within a target can run concurrently if concurrency > 1
            for target_config in targets:
                target_client = _create_target_client(target_config)

                self.console.print(
                    f"  [bold]{target_config.id}[/bold] ...",
                    end=" ",
                )

                async def eval_case(case: TestCase, tc: TargetClient, tid: str) -> CaseResult:
                    async with sem:
                        result = await self._evaluate_case(case, tc, tid)
                        progress.advance(task)
                        return result

                target_results = await asyncio.gather(*[eval_case(c, target_client, target_config.id) for c in cases])

                # Compute average for this target
                target_scores = [s.score for r in target_results for s in r.scores]
                avg = sum(target_scores) / len(target_scores) if target_scores else 0
                all_times = [t for r in target_results for t in r.response_times]
                avg_time = sum(all_times) / len(all_times) if all_times else 0
                self.console.print(f"avg={avg:.1f}/10  ({avg_time:.1f}s/turn)")

                all_results.extend(target_results)

            run.results = all_results

        run.finished_at = time.time()
        run.errors = [r.error for r in run.results if r.error]
        return run

    async def _evaluate_case(self, case: TestCase, target: TargetClient | None, target_id: str = "") -> CaseResult:
        """Evaluate a single test case."""
        result = CaseResult(
            case_id=case.id,
            case_name=case.name,
            language=case.language,
            category=case.category,
            target_id=target_id,
        )

        try:
            # Get the conversation to evaluate
            if case.is_static:
                conversation = case.conversation
            elif case.is_live and target:
                system_prompt = getattr(target, "system_prompt", None)
                if system_prompt is None and hasattr(target, "config"):
                    system_prompt = target.config.system_prompt
                t0 = time.time()
                conversation = await target.run_conversation(case.user_turns, system_prompt=system_prompt)
                elapsed = time.time() - t0
                # Store per-turn average and total
                n_turns = len(case.user_turns)
                result.response_times = [elapsed / n_turns] * n_turns
            else:
                result.error = (
                    "Live case requires a target endpoint in config"
                    if case.is_live
                    else "Case has no conversation or user_turns"
                )
                return result

            result.conversation = conversation

            # Determine which criteria to evaluate
            criteria_names = case.criteria or [case.category]

            # Run all judges x criteria in parallel
            eval_tasks = []
            for judge in self.judges:
                for criterion_name in criteria_names:
                    criterion = get_criterion(criterion_name, case.language)
                    eval_tasks.append(self._run_judge(judge, conversation, criterion.prompt, criterion_name))

            judge_results = await asyncio.gather(*eval_tasks, return_exceptions=True)
            for jr in judge_results:
                if isinstance(jr, Exception):
                    result.error = str(jr)
                else:
                    result.scores.append(jr)

        except Exception as e:
            result.error = str(e)

        return result

    async def _run_judge(
        self,
        judge: JudgeBase,
        conversation: list[dict[str, str]],
        criterion_prompt: str,
        criterion_name: str,
    ) -> JudgeResult:
        """Run a single judge evaluation with error handling."""
        try:
            return await judge.evaluate(conversation, criterion_prompt, criterion_name)
        except Exception as e:
            return JudgeResult(
                judge_id=judge.id,
                criterion=criterion_name,
                score=0.0,
                reasoning=f"Error: {e}",
                metadata={"error": True},
            )
