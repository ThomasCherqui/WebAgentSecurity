from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from config import DEFAULT_PROMPT_SLUG, EXPLAINABILITY_RESULTS_ROOT, RESULTS_ROOT, TASKS_DIR
from council import run_step
from loaders import load_council_inputs
from schemas import CATEGORIES, csv_cell, empty_counts, slug


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal LLM council over explainability prompt outputs.")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--prompt-slug", default=DEFAULT_PROMPT_SLUG)
    parser.add_argument("--candidate-models", nargs="+", required=True)
    parser.add_argument("--reviewer-models", nargs="+", default=None)
    parser.add_argument("--chairman-model", default="qwen2.5:72b")
    parser.add_argument("--explainability-results-root", type=Path, default=EXPLAINABILITY_RESULTS_ROOT)
    parser.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--run-name", default=None, help="Readable output folder name under results_ollama/llm_council/<domain>/<prompt_slug>/")
    parser.add_argument("--limit-personas", type=int, default=0)
    parser.add_argument("--limit-steps", type=int, default=0)
    parser.add_argument("--ollama-host", default=None)
    parser.add_argument("--allow-errors", action="store_true", help="Deprecated compatibility flag; Ollama backend errors always stop the run.")
    parser.add_argument("--mock", action="store_true", help="Do not call Ollama; useful to validate plumbing.")
    return parser.parse_args()


def plural(count: int, word: str) -> str:
    suffix = "" if count == 1 else "s"
    return f"{count}{word}{suffix}"


def council_slug(candidate_models: List[str], reviewer_models: List[str], chairman_model: str) -> str:
    return "_".join([
        "council",
        plural(len(candidate_models), "candidate"),
        plural(len(reviewer_models), "reviewer"),
        "chair",
        slug(chairman_model),
    ])


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def row_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    final = result.get("final_verdict", {})
    cats = final.get("cats") or empty_counts()
    row = {
        "domain": result.get("domain", ""),
        "persona": result.get("persona", ""),
        "persona_id": result.get("persona_id", ""),
        "step": result.get("step", ""),
        "prompt_slug": result.get("prompt_slug", ""),
        "candidate_models": ";".join(result.get("candidate_label_map", {}).values()),
        "reviewer_models": ";".join(result.get("reviewer_models", [])),
        "chairman_model": result.get("chairman_model", ""),
        "violations": json.dumps(final.get("violations", []), ensure_ascii=False),
        "no_violation_reason": csv_cell(final.get("no_violation_reason", "")),
        "decision_summary": final.get("decision_summary", ""),
        "selected_candidate": final.get("selected_candidate", ""),
        "reviewer_signal": final.get("reviewer_signal", ""),
        "reviewer_choices": json.dumps(
            {review.get("reviewer_model", ""): review.get("choice", "") for review in result.get("reviews", [])},
            ensure_ascii=False,
        ),
        "candidate_label_map": json.dumps(result.get("candidate_label_map", {}), ensure_ascii=False),
        "trajectory_step": csv_cell(result.get("trajectory_step", "")),
    }
    for cat in CATEGORIES:
        row[cat] = int(cats.get(cat, 0) or 0)
    return row


def write_predictions(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "domain",
        "persona",
        "persona_id",
        "step",
        "prompt_slug",
        "candidate_models",
        "reviewer_models",
        "chairman_model",
        "CE",
        "CI",
        "BE",
        "BI",
        "violations",
        "no_violation_reason",
        "decision_summary",
        "selected_candidate",
        "reviewer_signal",
        "reviewer_choices",
        "candidate_label_map",
        "trajectory_step",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def summary_payload(args: argparse.Namespace, rows: List[Dict[str, Any]], output_dir: Path) -> Dict[str, Any]:
    totals = empty_counts()
    for row in rows:
        for cat in CATEGORIES:
            totals[cat] += int(row.get(cat, 0) or 0)
    return {
        "domain": args.domain,
        "prompt_slug": args.prompt_slug,
        "candidate_models": args.candidate_models,
        "reviewer_models": args.reviewer_models,
        "chairman_model": args.chairman_model,
        "num_steps": len(rows),
        "totals": totals,
        "source_results_root": str(args.explainability_results_root),
        "output_dir": str(output_dir),
        "run_name": output_dir.name,
    }


def main() -> None:
    args = parse_args()
    args.reviewer_models = args.reviewer_models or args.candidate_models
    args.chairman_model = args.chairman_model or args.reviewer_models[0]

    run_name = args.run_name or council_slug(args.candidate_models, args.reviewer_models, args.chairman_model)
    output_dir = args.output_dir or (
        args.output_root / args.domain / args.prompt_slug / slug(run_name)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_council_inputs(
        domain=args.domain,
        prompt_slug=args.prompt_slug,
        candidate_models=args.candidate_models,
        results_root=args.explainability_results_root,
        tasks_dir=args.tasks_dir,
        limit_personas=args.limit_personas,
        limit_steps=args.limit_steps,
    )

    rows: List[Dict[str, Any]] = []
    persona_outputs: Dict[str, Dict[str, Any]] = defaultdict(dict)
    current_persona = None

    for idx, record in enumerate(records, start=1):
        persona = record.get("persona", "unknown")
        if persona != current_persona:
            current_persona = persona
            print(f"[{idx}/{len(records)}] persona={persona}")

        try:
            result = run_step(
                record,
                reviewer_models=args.reviewer_models,
                chairman_model=args.chairman_model,
                host=args.ollama_host,
                allow_errors=args.allow_errors,
                mock=args.mock,
            )
        except Exception as exc:
            step = record.get("step", "unknown")
            print(
                f"STOP: llm-council failed at {idx}/{len(records)} "
                f"persona={persona} step={step}: {exc}",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        persona_outputs[persona][f"Step {record.get('step')}"] = result
        rows.append(row_from_result(result))

        write_json(output_dir / f"{persona}.json", persona_outputs[persona])
        write_predictions(output_dir / "predictions.csv", rows)
        write_json(output_dir / "summary.json", summary_payload(args, rows, output_dir))

    print(f"Done. Wrote {len(rows)} council verdicts to {output_dir}")


if __name__ == "__main__":
    main()
