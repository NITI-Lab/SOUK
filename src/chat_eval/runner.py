"""Evaluation runner - orchestrates judges, cases, and criteria."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from chat_eval.cases.loader import TestCase
from chat_eval.config import EvalConfig
from chat_eval.criteria import get_criterion
from chat_eval.judges import create_judge
from chat_eval.judges.base import JudgeBase, JudgeResult
from chat_eval.target import TargetClient


def _create_target(config: EvalConfig) -> TargetClient | None:
    """Create the appropriate target client based on config."""
    if not config.target:
        return None
    if config.target.provider == "agentcore":
        from chat_eval.targets.agentcore import AgentCoreTarget
        return AgentCoreTarget(config.target)  # type: ignore[return-value]
    return TargetClient(config.target)


@dataclass
class CaseResult:
    """Results for a single test case across all judges and criteria."""

    case_id: str
    case_name: str
    language: str
    category: str
    scores: list[JudgeResult] = field(default_factory=list)
    conversation: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None

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

        for s in all_scores:
            by_judge.setdefault(s.judge_id, []).append(s.score)
            by_criterion.setdefault(s.criterion, []).append(s.score)
        for r in self.results:
            for s in r.scores:
                by_category.setdefault(r.category, []).append(s.score)

        return {
            "overall_avg": sum(s.score for s in all_scores) / len(all_scores) if all_scores else 0,
            "by_judge": {k: sum(v) / len(v) for k, v in by_judge.items()},
            "by_criterion": {k: sum(v) / len(v) for k, v in by_criterion.items()},
            "by_category": {k: sum(v) / len(v) for k, v in by_category.items()},
            "total_cases": self.total_cases,
            "total_evaluations": self.total_evaluations,
            "duration_seconds": self.duration_seconds,
        }


class EvalRunner:
    """Orchestrates the evaluation process."""

    def __init__(self, config: EvalConfig) -> None:
        self.config = config
        self.console = Console()
        self.judges: list[JudgeBase] = [create_judge(jc) for jc in config.judges]
        self.target = _create_target(config)

    async def run(self, cases: list[TestCase]) -> EvalRun:
        """Run evaluation on all cases."""
        run = EvalRun(config=self.config, started_at=time.time())

        self.console.print(
            f"\n[bold]ChatEval[/bold] - Evaluating {len(cases)} cases "
            f"with {len(self.judges)} judges\n"
        )

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
                    result = await self._evaluate_case(case)
                    progress.advance(task)
                    return result

            run.results = await asyncio.gather(
                *[eval_case(c) for c in cases]
            )

        run.finished_at = time.time()
        run.errors = [r.error for r in run.results if r.error]
        return run

    async def _evaluate_case(self, case: TestCase) -> CaseResult:
        """Evaluate a single test case."""
        result = CaseResult(
            case_id=case.id,
            case_name=case.name,
            language=case.language,
            category=case.category,
        )

        try:
            # Get the conversation to evaluate
            if case.is_static:
                conversation = case.conversation
            elif case.is_live and self.target:
                conversation = await self.target.run_conversation(case.user_turns)
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
                    eval_tasks.append(
                        self._run_judge(judge, conversation, criterion.prompt, criterion_name)
                    )

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
