"""CLI entry point for SOUK."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from souk.cases import load_cases
from souk.config import load_config
from souk.report import generate_report
from souk.runner import EvalRunner


def _load_dotenv() -> None:
    """Load .env file from current directory if it exists."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if not os.environ.get(key):
                os.environ[key] = value


console = Console()


@click.group()
@click.version_option(package_name="souk")
def main() -> None:
    """SOUK - EC product recommendation chat benchmark."""
    _load_dotenv()


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--category", "-c", multiple=True, help="Filter by category")
@click.option("--language", "-l", multiple=True, help="Filter by language (en, ja)")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--output", "-o", type=click.Path(), help="Output directory for reports")
@click.option("--case-id", help="Run a specific case by ID")
@click.option("--judge", "-j", multiple=True, help="Override judges. Format: provider:model (e.g., openai:gpt-5.4)")
def run(
    config_path: str,
    category: tuple[str, ...],
    language: tuple[str, ...],
    tag: tuple[str, ...],
    output: str | None,
    case_id: str | None,
    judge: tuple[str, ...],
) -> None:
    """Run evaluation with the given config."""
    config = load_config(config_path)

    # Override judges from CLI if specified
    if judge:
        from souk.config import JudgeConfig

        config.judges = []
        for j in judge:
            provider, _, model = j.partition(":")
            extra = {}
            if provider == "bedrock":
                extra["region"] = "us-west-2"
            config.judges.append(
                JudgeConfig(
                    id=f"{provider}-{model.split('.')[-1][:20]}",
                    provider=provider,
                    model=model,
                    extra=extra,
                )
            )

    cases = load_cases(
        config.cases_dir,
        categories=list(category) or None,
        languages=list(language) or config.languages,
        tags=list(tag) or None,
    )

    if case_id:
        cases = [c for c in cases if c.id == case_id]

    if not cases:
        console.print("[red]No test cases found.[/red]")
        sys.exit(1)

    console.print(f"Loaded [bold]{len(cases)}[/bold] test cases")

    runner = EvalRunner(config)
    eval_run = asyncio.run(runner.run(cases))

    # Print summary table
    summary = eval_run.summary()
    _print_summary(summary)

    # Generate reports
    outputs = generate_report(eval_run, output)
    for fmt, path in outputs.items():
        console.print(f"  {fmt}: [cyan]{path}[/cyan]")


@main.command()
@click.argument("cases_dir", type=click.Path(exists=True))
@click.option("--language", "-l", multiple=True, help="Filter by language")
@click.option("--category", "-c", multiple=True, help="Filter by category")
def list_cases(cases_dir: str, language: tuple[str, ...], category: tuple[str, ...]) -> None:
    """List available test cases."""
    cases = load_cases(
        cases_dir,
        languages=list(language) or None,
        categories=list(category) or None,
    )
    table = Table(title="Test Cases")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Lang")
    table.add_column("Category")
    table.add_column("Mode")
    table.add_column("Criteria")

    for c in cases:
        mode = "static" if c.is_static else "live" if c.is_live else "?"
        table.add_row(c.id, c.name, c.language, c.category, mode, ", ".join(c.criteria))

    console.print(table)


@main.command()
def list_criteria_cmd() -> None:
    """List available evaluation criteria."""
    from souk.criteria import get_criterion, list_criteria

    table = Table(title="Evaluation Criteria")
    table.add_column("Name")
    table.add_column("Languages")
    table.add_column("Description")

    for name in list_criteria():
        langs = []
        for lang in ("en", "ja", "zh"):
            try:
                c = get_criterion(name, lang)
                if c.language == lang:
                    langs.append(lang)
            except ValueError:
                pass
        table.add_row(name, ", ".join(langs), get_criterion(name).description)

    console.print(table)


@main.command()
@click.option(
    "--provider",
    "-p",
    multiple=True,
    help="Provider to check (openai, google, bedrock). Default: auto-detect from env vars.",
)
@click.option("--filter", "-f", "name_filter", default=None, help="Filter model names (substring match)")
def models(provider: tuple[str, ...], name_filter: str | None) -> None:
    """List available models from each provider's API."""
    from souk.model_discovery import discover_models

    providers = list(provider) or None
    results = discover_models(providers)

    for prov, model_list in results.items():
        table = Table(title=f"{prov} models")
        table.add_column("Model ID")
        if any("name" in m for m in model_list):
            table.add_column("Name")
        has_type = any("type" in m for m in model_list)
        if has_type:
            table.add_column("Type")

        for m in model_list:
            if "error" in m:
                console.print(f"[red]{prov}: {m['error']}[/red]")
                break
            model_id = m["id"]
            if name_filter and name_filter.lower() not in model_id.lower():
                name = m.get("name", "")
                if name_filter.lower() not in name.lower():
                    continue
            row = [model_id]
            if any("name" in mm for mm in model_list):
                row.append(m.get("name", ""))
            if has_type:
                row.append(m.get("type", ""))
            table.add_row(*row)

        console.print(table)
        console.print()


def _print_summary(summary: dict) -> None:
    """Print evaluation summary to console."""
    console.print(f"\n[bold]Overall Score: {summary['overall_avg']:.1f}/10[/bold]")
    evals = summary["total_evaluations"]
    dur = summary["duration_seconds"]
    console.print(f"Cases: {summary['total_cases']} | Evaluations: {evals} | Duration: {dur:.1f}s\n")

    if summary.get("by_judge"):
        table = Table(title="By Judge")
        table.add_column("Judge")
        table.add_column("Avg Score")
        for judge, score in summary["by_judge"].items():
            table.add_row(judge, f"{score:.1f}")
        console.print(table)

    if summary.get("by_criterion"):
        table = Table(title="By Criterion")
        table.add_column("Criterion")
        table.add_column("Avg Score")
        for criterion, score in summary["by_criterion"].items():
            table.add_row(criterion, f"{score:.1f}")
        console.print(table)


if __name__ == "__main__":
    main()
