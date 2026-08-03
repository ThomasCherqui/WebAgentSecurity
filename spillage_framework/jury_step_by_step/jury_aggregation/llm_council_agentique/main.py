from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


AGGREGATION_DIR = Path(__file__).resolve().parent.parent
if str(AGGREGATION_DIR) not in sys.path:
    sys.path.insert(0, str(AGGREGATION_DIR))
LEGACY_COUNCIL_DIR = AGGREGATION_DIR / "llm_council"
if str(LEGACY_COUNCIL_DIR) not in sys.path:
    sys.path.append(str(LEGACY_COUNCIL_DIR))

from loaders import load_council_inputs  # noqa: E402
from schemas import CATEGORIES, csv_cell, empty_counts, slug  # noqa: E402

from config import (  # noqa: E402
    DEFAULT_PROMPT_SLUG,
    EXPLAINABILITY_RESULTS_ROOT,
    RESULTS_ROOT,
    TASKS_DIR,
)
from council import run_step  # noqa: E402


StepKey = Tuple[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic, evidence-grounded LLM council for SPILLage.")
    parser.add_argument("--domain", required=True)
    parser.add_argument("--prompt-slug", default=DEFAULT_PROMPT_SLUG)
    parser.add_argument("--candidate-models", nargs="+", required=True)
    parser.add_argument("--content-model", default="qwen2.5:72b")
    parser.add_argument("--behavior-model", default="qwen2.5:72b")
    parser.add_argument("--verifier-model", default="qwen2.5:72b")
    parser.add_argument("--chairman-model", default="qwen2.5:72b")
    parser.add_argument("--explainability-results-root", type=Path, default=EXPLAINABILITY_RESULTS_ROOT)
    parser.add_argument("--tasks-dir", type=Path, default=TASKS_DIR)
    parser.add_argument("--output-root", type=Path, default=RESULTS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--limit-personas", type=int, default=0)
    parser.add_argument("--limit-steps", type=int, default=0)
    parser.add_argument("--ollama-host", default=None)
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--mock", action="store_true", help="Validate the complete workflow without calling Ollama.")
    return parser.parse_args()


def agentic_slug(args: argparse.Namespace) -> str:
    models = [args.content_model, args.behavior_model, args.verifier_model, args.chairman_model]
    return "agentic_" + "__".join(slug(model) for model in models)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json_object(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    return value if isinstance(value, dict) else {}


def write_predictions(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "domain", "persona", "persona_id", "step", "prompt_slug", "candidate_models",
        "content_model", "behavior_model", "verifier_model", "chairman_model",
        "CE", "CI", "BE", "BI", "violations", "no_violation_reason",
        "decision_summary", "disputed_categories", "trajectory_step",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def row_from_result(result: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    final = result.get("final_verdict", {})
    cats = final.get("cats") or empty_counts()
    row = {
        "domain": result.get("domain", ""),
        "persona": result.get("persona", ""),
        "persona_id": result.get("persona_id", ""),
        "step": result.get("step", ""),
        "prompt_slug": result.get("prompt_slug", ""),
        "candidate_models": ";".join(args.candidate_models),
        "content_model": args.content_model,
        "behavior_model": args.behavior_model,
        "verifier_model": args.verifier_model,
        "chairman_model": args.chairman_model,
        "violations": json.dumps(final.get("violations", []), ensure_ascii=False),
        "no_violation_reason": csv_cell(final.get("no_violation_reason", "")),
        "decision_summary": csv_cell(final.get("decision_summary", "")),
        "disputed_categories": ";".join(result.get("disputed_categories", [])),
        "trajectory_step": csv_cell(result.get("trajectory_step", "")),
    }
    for cat in CATEGORIES:
        row[cat] = int(cats.get(cat, 0) or 0)
    return row


def load_existing_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def normalize_step(value: Any) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group()) if match else 0


def row_key(row: Dict[str, Any]) -> StepKey:
    return str(row.get("persona", "")), normalize_step(row.get("step", 0))


def summary_payload(args: argparse.Namespace, rows: List[Dict[str, Any]], output_dir: Path) -> Dict[str, Any]:
    totals = empty_counts()
    disputes = 0
    for row in rows:
        disputes += int(bool(row.get("disputed_categories")))
        for cat in CATEGORIES:
            totals[cat] += int(row.get(cat, 0) or 0)
    return {
        "domain": args.domain,
        "prompt_slug": args.prompt_slug,
        "candidate_models": args.candidate_models,
        "agents": {
            "content": args.content_model,
            "behavior": args.behavior_model,
            "verifier": args.verifier_model,
            "chairman": args.chairman_model,
        },
        "num_steps": len(rows),
        "steps_with_candidate_disagreement": disputes,
        "totals": totals,
        "output_dir": str(output_dir),
    }


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or args.output_root / args.domain / args.prompt_slug / slug(args.run_name or agentic_slug(args))
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
    predictions_path = output_dir / "predictions.csv"
    rows = load_existing_rows(predictions_path) if args.resume_existing else []
    completed: Set[StepKey] = {row_key(row) for row in rows}
    persona_outputs: Dict[str, Dict[str, Any]] = defaultdict(dict)

    for index, record in enumerate(records, start=1):
        key = str(record.get("persona", "")), normalize_step(record.get("step", 0))
        if key in completed:
            continue
        print(f"[{index}/{len(records)}] persona={key[0]} step={key[1]}")
        result = run_step(
            record,
            content_model=args.content_model,
            behavior_model=args.behavior_model,
            verifier_model=args.verifier_model,
            chairman_model=args.chairman_model,
            host=args.ollama_host,
            mock=args.mock,
        )
        if not persona_outputs[key[0]] and args.resume_existing:
            persona_outputs[key[0]] = read_json_object(output_dir / f"{key[0]}.json")
        persona_outputs[key[0]][f"Step {key[1]}"] = result
        rows.append(row_from_result(result, args))
        completed.add(key)

        write_json(output_dir / f"{key[0]}.json", persona_outputs[key[0]])
        write_predictions(predictions_path, rows)
        write_json(output_dir / "summary.json", summary_payload(args, rows, output_dir))

    print(f"Done. Wrote {len(rows)} agentic council verdicts to {output_dir}")


if __name__ == "__main__":
    main()

