#!/usr/bin/env python3
"""Offline aggregation for raw explainability judge outputs.

This stage reads the raw per-judge outputs produced by
jury_explainability_and_prompts and applies aggregation methods without
calling any judge model again.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "scripts"))
from ollama_jury_common import CATEGORIES, aggregate, compute_weights, empty_counts, majority_threshold


StepRecord = Dict[str, Any]
RunRecord = Dict[str, Any]


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("_") or "run"


def csv_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def raw_persona_files(raw_run: Path) -> List[Path]:
    ignored = {"raw_judge_outputs_summary.json", "jury_results_fixed.json", "summary.json"}
    return sorted(path for path in raw_run.glob("*.json") if path.name not in ignored)


def step_number(step_key: str, fallback: int) -> int:
    match = re.search(r"\d+", step_key or "")
    return int(match.group()) if match else fallback


def normalize_votes(votes: Dict[str, Any]) -> Dict[str, int]:
    return {cat: int((votes or {}).get(cat, 0) or 0) for cat in CATEGORIES}


def infer_judge_models(summary: Dict[str, Any], runs: List[RunRecord]) -> Dict[str, str]:
    judge_models = summary.get("judge_models") if isinstance(summary, dict) else None
    if isinstance(judge_models, dict) and judge_models:
        return {str(k): str(v) for k, v in judge_models.items()}

    inferred: Dict[str, str] = {}
    for run in runs:
        for step in run["steps"]:
            for judge_id, judge_data in step["judges"].items():
                inferred[judge_id] = str(judge_data.get("model") or judge_id)
        if inferred:
            break
    return inferred


def load_raw_run(raw_run: Path) -> Tuple[Dict[str, Any], List[RunRecord], List[str], Dict[str, str]]:
    if not raw_run.is_dir():
        raise SystemExit(f"Raw run directory not found: {raw_run}")

    summary_path = raw_run / "raw_judge_outputs_summary.json"
    summary = load_json(summary_path) if summary_path.exists() else {}

    runs: List[RunRecord] = []
    for path in raw_persona_files(raw_run):
        data = load_json(path)
        steps: List[StepRecord] = []
        persona_name = path.stem
        persona_id = ""
        step_items = sorted(data.items(), key=lambda item: step_number(item[0], 10**9))
        for idx, (step_key, raw_step) in enumerate(step_items, start=1):
            judges_blob = raw_step.get("judges", {}) if isinstance(raw_step, dict) else {}
            if not isinstance(judges_blob, dict) or not judges_blob:
                continue
            normalized_judges: Dict[str, Dict[str, Any]] = {}
            for judge_id, judge_data in judges_blob.items():
                judge_data = judge_data or {}
                normalized_judges[str(judge_id)] = {
                    "model": judge_data.get("model", str(judge_id)),
                    "violations": normalize_votes(judge_data.get("violations", {})),
                    "response": judge_data.get("response", ""),
                }
            persona_name = str(raw_step.get("persona") or persona_name)
            persona_id = raw_step.get("persona_id", persona_id)
            steps.append({
                "step_key": step_key,
                "step": int(raw_step.get("step") or step_number(step_key, idx)),
                "prompt_template": raw_step.get("prompt_template", summary.get("prompt_template", "")),
                "prompt_slug": raw_step.get("prompt_slug", summary.get("prompt_slug", "")),
                "prompt_used": raw_step.get("prompt_used", ""),
                "trajectory_step": raw_step.get("trajectory_step", raw_step.get("combined_text", "")),
                "judges": normalized_judges,
            })
        if steps:
            runs.append({
                "persona": persona_name,
                "persona_id": persona_id,
                "source_file": str(path),
                "steps": sorted(steps, key=lambda s: s["step"]),
            })

    judge_models = infer_judge_models(summary, runs)
    judges = list(judge_models.keys())
    if not judges:
        raise SystemExit(f"No raw judge outputs found in: {raw_run}")

    for run in runs:
        for step in run["steps"]:
            missing = [j for j in judges if j not in step["judges"]]
            if missing:
                missing_text = ", ".join(missing)
                raise SystemExit(f"Step {step['step_key']} in {run['source_file']} is missing judges: {missing_text}")

    return summary, runs, judges, judge_models


def all_step_votes(runs: Iterable[RunRecord], judges: List[str]) -> List[Dict[str, Dict[str, int]]]:
    steps = []
    for run in runs:
        for step in run["steps"]:
            steps.append({j: step["judges"][j]["violations"] for j in judges})
    return steps


def aggregate_majority(votes: List[Dict[str, int]], judges: List[str]) -> Dict[str, int]:
    out = empty_counts()
    threshold = majority_threshold(judges)
    for cat in CATEGORIES:
        nonzero = [vote.get(cat, 0) for vote in votes if vote.get(cat, 0) > 0]
        if len(nonzero) >= threshold:
            out[cat] = min(nonzero)
    return out


def aggregate_step(method: str, step: StepRecord, judges: List[str], weights: Dict[str, float]) -> Dict[str, int]:
    votes = [step["judges"][j]["violations"] for j in judges]
    if method == "weighted":
        return aggregate(votes, weights, judges)
    if method == "majority":
        return aggregate_majority(votes, judges)
    raise ValueError(f"Unknown aggregation method: {method}")


def part_or_default(path: Path, offset: int, default: str) -> str:
    parts = path.parts
    return parts[offset] if len(parts) >= abs(offset) else default


def default_output_dir(raw_run: Path, output_root: Path, method: str, summary: Dict[str, Any]) -> Path:
    domain = summary.get("domain") or part_or_default(raw_run, -3, "domain")
    prompt_slug = summary.get("prompt_slug") or part_or_default(raw_run, -2, "prompt")
    models_slug = summary.get("models_slug") or raw_run.name
    return output_root / slug(domain) / slug(prompt_slug) / slug(models_slug) / method


def aggregate_run(raw_run: Path, output_dir: Path, method: str) -> None:
    summary, runs, judges, judge_models = load_raw_run(raw_run)
    steps_for_weights = all_step_votes(runs, judges)
    weights = compute_weights(steps_for_weights, judges) if steps_for_weights else {j: 1.0 / len(judges) for j in judges}

    totals = empty_counts()
    csv_rows: List[Dict[str, Any]] = []

    for run in runs:
        per_person_out: Dict[str, Any] = {}
        for step in run["steps"]:
            verdict = aggregate_step(method, step, judges, weights)
            for cat in CATEGORIES:
                totals[cat] += verdict[cat]

            step_out = {
                "aggregation_method": method,
                "jury_verdict": verdict,
                "weights_used": weights if method == "weighted" else {},
                "judge_models": judge_models,
                "prompt_template": step.get("prompt_template", ""),
                "prompt_slug": step.get("prompt_slug", ""),
                "trajectory_step": step.get("trajectory_step", ""),
                "raw_judges": step["judges"],
            }
            per_person_out[f"Step {step['step']}"] = step_out
            csv_rows.append({
                "persona": run["persona"],
                "persona_id": run.get("persona_id", ""),
                "step": step["step"],
                "judge_models": ";".join(judge_models[j] for j in judges),
                "prompt_template": step.get("prompt_template", ""),
                "aggregation_method": method,
                "CE": int(verdict.get("CE", 0)),
                "CI": int(verdict.get("CI", 0)),
                "BE": int(verdict.get("BE", 0)),
                "BI": int(verdict.get("BI", 0)),
                "weights": csv_cell(json.dumps(weights, sort_keys=True)) if method == "weighted" else "",
                "trajectory_step": csv_cell(step.get("trajectory_step", "")),
            })

        dump_json(output_dir / f"{run['persona']}.json", per_person_out)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "predictions.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(
            cf,
            fieldnames=[
                "persona",
                "persona_id",
                "step",
                "judge_models",
                "prompt_template",
                "aggregation_method",
                "CE",
                "CI",
                "BE",
                "BI",
                "weights",
                "trajectory_step",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    dump_json(output_dir / "summary.json", {
        "method": method,
        "source_raw_run": str(raw_run),
        "domain": summary.get("domain", ""),
        "prompt_template": summary.get("prompt_template", ""),
        "prompt_slug": summary.get("prompt_slug", ""),
        "models_slug": summary.get("models_slug", ""),
        "judge_models": judge_models,
        "weights": weights if method == "weighted" else {},
        "totals": totals,
        "num_personas": len(runs),
        "num_steps": len(csv_rows),
    })

    print(f"Aggregation method={method} written to {output_dir}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aggregate raw per-judge explainability outputs")
    p.add_argument("--raw-run", required=True, help="Directory produced by jury_explainability_and_prompts")
    p.add_argument("--method", choices=["weighted", "majority", "all"], default="weighted")
    p.add_argument("--output-dir", default=None, help="Exact output directory for a single method")
    p.add_argument("--output-root", default=str(SCRIPT_DIR / "results"), help="Root used when --output-dir is omitted")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    raw_run = Path(args.raw_run).resolve()
    output_root = Path(args.output_root).resolve()
    methods = ["weighted", "majority"] if args.method == "all" else [args.method]

    summary_path = raw_run / "raw_judge_outputs_summary.json"
    summary = load_json(summary_path) if summary_path.exists() else {}

    if args.output_dir and len(methods) > 1:
        raise SystemExit("--output-dir can only be used with one --method, not --method all")

    for method in methods:
        output_dir = Path(args.output_dir).resolve() if args.output_dir else default_output_dir(raw_run, output_root, method, summary)
        aggregate_run(raw_run, output_dir, method)


if __name__ == "__main__":
    main()
