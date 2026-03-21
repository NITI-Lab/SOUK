"""Report generator - produces HTML and JSON reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from chat_eval.runner import EvalRun

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_report(run: EvalRun, output_dir: str | Path | None = None) -> dict[str, Path]:
    """Generate reports from an evaluation run.

    Returns a dict of format -> output path.
    """
    output_dir = Path(output_dir or run.config.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outputs: dict[str, Path] = {}

    report_data = _build_report_data(run)

    if "json" in run.config.report.formats:
        json_path = output_dir / f"chateval_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        outputs["json"] = json_path

    if "html" in run.config.report.formats:
        html_path = output_dir / f"chateval_{timestamp}.html"
        html_content = _render_html(report_data, run.config.report.title)
        with open(html_path, "w") as f:
            f.write(html_content)
        outputs["html"] = html_path

    return outputs


def _build_report_data(run: EvalRun) -> dict:
    """Build the full report data structure."""
    summary = run.summary()
    cases = []
    for r in run.results:
        cases.append({
            "id": r.case_id,
            "name": r.case_name,
            "language": r.language,
            "category": r.category,
            "avg_score": round(r.avg_score, 2),
            "by_criterion": {k: round(v, 2) for k, v in r.avg_by_criterion().items()},
            "by_judge": {k: round(v, 2) for k, v in r.avg_by_judge().items()},
            "scores": [
                {
                    "judge_id": s.judge_id,
                    "criterion": s.criterion,
                    "score": round(s.score, 2),
                    "reasoning": s.reasoning,
                }
                for s in r.scores
            ],
            "conversation": r.conversation,
            "error": r.error,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            k: round(v, 2) if isinstance(v, float) else v
            for k, v in summary.items()
            if k not in ("by_judge", "by_criterion", "by_category")
        },
        "by_judge": {k: round(v, 2) for k, v in summary["by_judge"].items()},
        "by_criterion": {k: round(v, 2) for k, v in summary["by_criterion"].items()},
        "by_category": {k: round(v, 2) for k, v in summary["by_category"].items()},
        "cases": cases,
        "errors": run.errors,
    }


def _render_html(data: dict, title: str) -> str:
    """Render HTML report from template."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html")
    return template.render(data=data, title=title, data_json=json.dumps(data, ensure_ascii=False))
