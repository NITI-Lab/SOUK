"""Aggregate a batch of conversation verdicts into tabular + markdown reports.

The reports answer three operational questions after a 200-conversation run:

1. **Did the agent regress?** — per-severity fail counts + overall_pass rate.
2. **Which rubric items hurt the most?** — per-item fail rate, sortable.
3. **Which personas hit trouble?** — cross of persona attributes × overall
   fail, and a worst-N surface that quotes the offending evidence so an
   engineer can triage quickly.

Outputs are written to a run directory; index files (CSV + Markdown) are
plain-text so they diff nicely in CI.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from souk.simulator.conversation_runner import ConversationRunResult


def _verdict_row(result: ConversationRunResult) -> dict:
    v = result.verdict
    persona = result.persona
    if v is None:
        return {
            "conversation_id": result.conversation_id,
            "persona_id": persona.id,
            "occupation": persona.occupation,
            "purpose": persona.purpose,
            "priorities": persona.priorities,
            "comm_style": persona.comm_style,
            "injections": ",".join(persona.injections),
            "turns": len(result.conversation) // 2,
            "end_reason": result.end_reason,
            "error": result.error or "",
            "overall_pass": "",
            "critical_fails": "",
            "major_fails": "",
            "minor_fails": "",
            "failed_items": "",
        }
    fails = v.fails_by_severity()
    return {
        "conversation_id": result.conversation_id,
        "persona_id": persona.id,
        "occupation": persona.occupation,
        "purpose": persona.purpose,
        "priorities": persona.priorities,
        "comm_style": persona.comm_style,
        "injections": ",".join(persona.injections),
        "turns": len(result.conversation) // 2,
        "end_reason": result.end_reason,
        "error": result.error or "",
        "overall_pass": v.overall_pass(),
        "critical_fails": len(fails["critical"]),
        "major_fails": len(fails["major"]),
        "minor_fails": len(fails["minor"]),
        "failed_items": ";".join(
            f"{it.id}[{it.severity}]" for it in v.items if not it.passed and not it.not_applicable
        ),
    }


def write_run(
    results: list[ConversationRunResult],
    out_dir: str | Path,
) -> dict:
    """Write CSV, per-conversation JSON, and Markdown summary to ``out_dir``.

    Returns a summary dict that callers can use for CI exit codes.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # --- per-conversation JSON dumps -------------------------------------- #
    (out / "conversations").mkdir(exist_ok=True)
    for r in results:
        payload = {
            "conversation_id": r.conversation_id,
            "persona": r.persona.to_dict(),
            "conversation": r.conversation,
            "turn_latencies_sec": r.turn_latencies_sec,
            "end_reason": r.end_reason,
            "error": r.error,
            "user_turns": [
                {
                    "text": t.text,
                    "status": t.status,
                    "hints_applied": t.hints_applied,
                }
                for t in r.user_turns
            ],
            "verdict": None
            if r.verdict is None
            else {
                "notes": r.verdict.notes,
                "items": [asdict(it) for it in r.verdict.items],
            },
        }
        with (out / "conversations" / f"{r.conversation_id}.json").open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    # --- flat CSV --------------------------------------------------------- #
    rows = [_verdict_row(r) for r in results]
    csv_path = out / "results.csv"
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    # --- aggregate summary ------------------------------------------------ #
    summary = _aggregate(results)
    with (out / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    md = _render_markdown(results, summary)
    with (out / "REPORT.md").open("w", encoding="utf-8") as f:
        f.write(md)

    return summary


def _aggregate(results: list[ConversationRunResult]) -> dict:
    total = len(results)
    total_with_verdict = sum(1 for r in results if r.verdict is not None)
    overall_pass = sum(1 for r in results if r.verdict is not None and r.verdict.overall_pass())
    errors = sum(1 for r in results if r.error)
    end_reasons = Counter(r.end_reason for r in results)

    per_item_fail: Counter[str] = Counter()
    per_item_total: Counter[str] = Counter()
    per_item_na: Counter[str] = Counter()
    per_severity_fail: Counter[str] = Counter()
    per_category_fail: Counter[str] = Counter()

    per_attr_fail: dict[str, Counter[str]] = defaultdict(Counter)
    per_attr_total: dict[str, Counter[str]] = defaultdict(Counter)
    injection_item_fail: dict[str, Counter[str]] = defaultdict(Counter)

    for r in results:
        if r.verdict is None:
            continue
        attrs = {
            "occupation": r.persona.occupation,
            "purpose": r.persona.purpose,
            "priorities": r.persona.priorities,
            "comm_style": r.persona.comm_style,
        }
        for k, v in attrs.items():
            per_attr_total[k][v] += 1

        convo_has_fail = False
        for it in r.verdict.items:
            per_item_total[it.id] += 1
            if it.not_applicable:
                per_item_na[it.id] += 1
                continue
            if not it.passed:
                per_item_fail[it.id] += 1
                per_severity_fail[it.severity] += 1
                per_category_fail[it.category] += 1
                convo_has_fail = True
                for inj in r.persona.injections:
                    injection_item_fail[inj][it.id] += 1

        if convo_has_fail:
            for k, v in attrs.items():
                per_attr_fail[k][v] += 1

    # Build per-item rates (fail / (total - na)).
    per_item_rates: list[dict] = []
    for item_id, total_count in per_item_total.items():
        na = per_item_na.get(item_id, 0)
        denom = total_count - na
        fail = per_item_fail.get(item_id, 0)
        rate = (fail / denom) if denom else 0.0
        per_item_rates.append(
            {
                "id": item_id,
                "fail": fail,
                "total_applicable": denom,
                "not_applicable": na,
                "fail_rate": rate,
            }
        )
    per_item_rates.sort(key=lambda row: (-row["fail_rate"], -row["fail"]))

    per_attr_rates: dict[str, list[dict]] = {}
    for k, totals in per_attr_total.items():
        per_attr_rates[k] = []
        for value, total_count in totals.items():
            fails = per_attr_fail[k].get(value, 0)
            per_attr_rates[k].append(
                {
                    "value": value,
                    "convos": total_count,
                    "convo_fails": fails,
                    "fail_rate": (fails / total_count) if total_count else 0.0,
                }
            )
        per_attr_rates[k].sort(key=lambda row: -row["fail_rate"])

    return {
        "total_conversations": total,
        "judged": total_with_verdict,
        "errors": errors,
        "overall_pass": overall_pass,
        "overall_pass_rate": (overall_pass / total_with_verdict) if total_with_verdict else 0.0,
        "end_reasons": dict(end_reasons),
        "per_severity_fail": dict(per_severity_fail),
        "per_category_fail": dict(per_category_fail),
        "per_item_rates": per_item_rates,
        "per_attr_rates": per_attr_rates,
        "injection_item_fail": {k: dict(v) for k, v in injection_item_fail.items()},
    }


# ---------------------------------------------------------------------- #
#  Markdown rendering
# ---------------------------------------------------------------------- #


def _render_markdown(results: list[ConversationRunResult], summary: dict, worst_n: int = 10) -> str:
    total = summary["total_conversations"]
    judged = summary["judged"]
    pass_rate = summary["overall_pass_rate"] * 100
    lines: list[str] = []
    lines.append(f"# Chat Eval Report — {total} conversations")
    lines.append("")
    lines.append(f"- Judged: **{judged}** / {total}  (errors: {summary['errors']})")
    lines.append(f"- Overall pass rate: **{pass_rate:.1f}%**")
    lines.append("")

    lines.append("## Fail counts by severity")
    sev = summary["per_severity_fail"]
    lines.append("| severity | fail count |")
    lines.append("|---|---|")
    for s in ("critical", "major", "minor"):
        lines.append(f"| {s} | {sev.get(s, 0)} |")
    lines.append("")

    lines.append("## Top failing rubric items")
    lines.append("| rubric id | fail | applicable | fail rate |")
    lines.append("|---|---|---|---|")
    for row in summary["per_item_rates"][:20]:
        if row["fail"] == 0:
            continue
        lines.append(f"| `{row['id']}` | {row['fail']} | {row['total_applicable']} | {row['fail_rate'] * 100:.1f}% |")
    lines.append("")

    lines.append("## Persona-attribute fail rates")
    for attr, rows in summary["per_attr_rates"].items():
        lines.append(f"### by {attr}")
        lines.append("| value | convos | fails | fail rate |")
        lines.append("|---|---|---|---|")
        for row in rows:
            lines.append(f"| {row['value']} | {row['convos']} | {row['convo_fails']} | {row['fail_rate'] * 100:.1f}% |")
        lines.append("")

    # Worst conversations — sort by (critical fails, major fails)
    scored: list[tuple[tuple[int, int, int], ConversationRunResult]] = []
    for r in results:
        if r.verdict is None:
            continue
        fails = r.verdict.fails_by_severity()
        score = (len(fails["critical"]), len(fails["major"]), len(fails["minor"]))
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)

    lines.append(f"## Worst {worst_n} conversations")
    for score, r in scored[:worst_n]:
        if score == (0, 0, 0):
            break
        c, m, mi = score
        lines.append(f"### `{r.conversation_id}` — {r.persona.summary()}  (critical={c}, major={m}, minor={mi})")
        for it in r.verdict.items if r.verdict else []:
            if it.passed or it.not_applicable:
                continue
            lines.append(f"- **{it.id}** [{it.severity}] — `{(it.evidence or '')[:200]}` — {it.reason}")
        lines.append("")

    return "\n".join(lines) + "\n"
