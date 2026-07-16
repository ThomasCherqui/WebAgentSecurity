#!/usr/bin/env python3
"""Small, readable demo for the llm_council aggregation layer.

Default mode is safe: it explains the workflow, previews existing
explainability outputs, and shows the command that would be run.

Use --run to actually launch a tiny council run. By default that run uses
--mock so it does not call Ollama; pass --real if you want live model calls.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List

from config import BASE_DIR, EXPLAINABILITY_RESULTS_ROOT, TASKS_DIR
from council import label_candidates, load_template, prompt_context, render, run_step
from loaders import load_council_inputs
from schemas import slug


DEFAULT_CANDIDATES = {
    "shopping_Amazon_chat": ["gemma4:31b-cloud", "gpt-oss:20b-cloud", "nemotron-3-nano:30b-cloud"],
    "shopping_ebay_chat": ["gemma4:31b", "gpt-oss:20b", "nemotron-cascade-2:latest"],
}


def color(text: str, code: str) -> str:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"


def pause(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def short(text: object, limit: int = 520) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def print_card(title: str, lines: List[str]) -> None:
    print(color(f"\n-- {title} --", "36;1"))
    for line in lines:
        print(f"  {line}")


def print_block(title: str, text: object, limit: int = 1800) -> None:
    value = str(text or "")
    if len(value) > limit:
        value = value[: limit - 3] + "..."
    print(color(f"\n-- {title} --", "36;1"))
    for raw_line in value.splitlines() or [""]:
        for line in textwrap.wrap(raw_line, width=96) or [""]:
            print(f"  {line}")


def print_step(number: int, title: str) -> None:
    print()
    print(color("=" * 72, "35"))
    print(color(f"STEP {number}: {title}", "35;1"))
    print(color("=" * 72, "35"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Explain and optionally run a small llm_council demo")
    parser.add_argument("--domain", default="shopping_Amazon_chat")
    parser.add_argument("--prompt-slug", default="comparative_counterexamples_fewshot")
    parser.add_argument("--candidate-models", nargs="+", default=None)
    parser.add_argument("--reviewer-models", nargs="+", default=None)
    parser.add_argument("--chairman-model", default="qwen2.5:72b")
    parser.add_argument("--limit-personas", type=int, default=1)
    parser.add_argument("--limit-steps", type=int, default=1)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--ollama-host", default=None)
    parser.add_argument("--run", action="store_true", help="Actually run the small council demo")
    parser.add_argument("--real", action="store_true", help="Call real reviewer/chairman models instead of --mock")
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to pause between demo sections")
    return parser.parse_args()


def resolved_models(args: argparse.Namespace) -> tuple[List[str], List[str]]:
    candidate_models = list(args.candidate_models or DEFAULT_CANDIDATES.get(args.domain, ["gemma4:31b"]))
    reviewer_models = list(args.reviewer_models or candidate_models)
    return candidate_models, reviewer_models


def demo_run_name(args: argparse.Namespace) -> str:
    if args.run_name:
        return args.run_name
    return f"demo_{args.prompt_slug}_{slug(args.chairman_model)}"


def demo_output_dir(args: argparse.Namespace) -> Path:
    return BASE_DIR / "results_demo" / args.domain / args.prompt_slug / demo_run_name(args)


def preview_record(domain: str, prompt_slug: str, candidate_models: List[str]) -> Dict[str, Any]:
    records = load_council_inputs(
        domain=domain,
        prompt_slug=prompt_slug,
        candidate_models=candidate_models,
        results_root=EXPLAINABILITY_RESULTS_ROOT,
        tasks_dir=TASKS_DIR,
        limit_personas=1,
        limit_steps=1,
    )
    if not records:
        raise SystemExit("No council input records found for this configuration")
    return records[0]


def print_candidate_preview(record: Dict[str, Any]) -> None:
    lines = [
        f"Persona: {record.get('persona', '')}",
        f"Task goal: {short(record.get('task_goal', ''), 320)}",
        f"Trajectory step: {short(record.get('trajectory_step', ''), 520)}",
        f"Relevant attributes: {short(', '.join(record.get('relevant_attributes', []) or []), 220)}",
        f"Irrelevant attributes: {short(', '.join(record.get('irrelevant_attributes', []) or []), 220)}",
    ]
    print_card("Sample council input", lines)

    for index, (model, candidate) in enumerate(record.get("candidates", {}).items(), start=1):
        cats = candidate.get("cats", {})
        violations = candidate.get("violations", []) or []
        no_violation_reason = short(candidate.get("no_violation_reason", ""), 220)
        print_card(
            f"Candidate {index}",
            [
                f"Model: {model}",
                f"Counts: CE={cats.get('CE', 0)} CI={cats.get('CI', 0)} BE={cats.get('BE', 0)} BI={cats.get('BI', 0)}",
                f"Violations extracted: {len(violations)}",
                f"No-violation reason: {no_violation_reason or '(empty)'}",
            ],
        )


def preview_prompts_and_mock_decision(record: Dict[str, Any], reviewer_models: List[str], chairman_model: str) -> None:
    label_map, labelled = label_candidates(record.get("candidates", {}))
    review_prompt = render(load_template("review_verdict.md"), prompt_context(record, labelled))
    print_card(
        "Candidate label map",
        [f"{label} -> {model}" for label, model in label_map.items()],
    )
    print_block("Reviewer prompt preview", review_prompt, 1800)

    mock_result = run_step(
        record,
        reviewer_models=reviewer_models,
        chairman_model=chairman_model,
        mock=True,
    )
    final_verdict = mock_result.get("final_verdict", {})
    print_card(
        "Mock council decision",
        [
            f"Selected candidate label: {final_verdict.get('selected_candidate', '(mock chairman uses top reviewed candidate)')}",
            f"Decision summary: {short(final_verdict.get('decision_summary', ''), 320)}",
            "Final counts: "
            f"CE={final_verdict.get('cats', {}).get('CE', 0)} "
            f"CI={final_verdict.get('cats', {}).get('CI', 0)} "
            f"BE={final_verdict.get('cats', {}).get('BE', 0)} "
            f"BI={final_verdict.get('cats', {}).get('BI', 0)}",
        ],
    )


def build_command(args: argparse.Namespace, candidate_models: List[str], reviewer_models: List[str]) -> List[str]:
    script = BASE_DIR / "main.py"
    cmd = [
        sys.executable,
        str(script),
        "--domain",
        args.domain,
        "--prompt-slug",
        args.prompt_slug,
        "--candidate-models",
        *candidate_models,
        "--reviewer-models",
        *reviewer_models,
        "--chairman-model",
        args.chairman_model,
        "--limit-personas",
        str(args.limit_personas),
        "--limit-steps",
        str(args.limit_steps),
        "--output-root",
        str(BASE_DIR / "results_demo"),
        "--run-name",
        demo_run_name(args),
    ]
    if args.ollama_host:
        cmd += ["--ollama-host", args.ollama_host]
    if not args.real:
        cmd += ["--mock"]
    return cmd


def preview_csv(path: Path, max_rows: int = 5) -> None:
    if not path.exists():
        print(f"No predictions.csv found yet at: {path}")
        return

    print(f"Found predictions.csv: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"Rows: {len(rows)}")
    for row in rows[:max_rows]:
        print(
            "  "
            f"persona={row.get('persona')} "
            f"step={row.get('step')} "
            f"CE={row.get('CE')} CI={row.get('CI')} "
            f"BE={row.get('BE')} BI={row.get('BI')} "
            f"chair={row.get('chairman_model')}"
        )


def preview_persona_json(results_dir: Path) -> None:
    files = sorted(p for p in results_dir.glob("*.json") if p.name != "summary.json")
    if not files:
        print(f"No per-person JSON files found yet in: {results_dir}")
        return

    sample = files[0]
    print(f"\nExample per-person JSON: {sample}")
    with sample.open(encoding="utf-8") as f:
        data = json.load(f)

    first_key = sorted(data.keys())[0] if data else None
    if not first_key:
        print("JSON is empty.")
        return

    step = data[first_key]
    final_verdict = step.get("final_verdict", {})
    print(f"Example key: {first_key}")
    print(f"Candidate label map: {step.get('candidate_label_map')}")
    print(f"Reviewer models: {step.get('reviewer_models')}")
    print(f"Chairman model: {step.get('chairman_model')}")
    print(f"Final cats: {final_verdict.get('cats')}")
    print(f"Decision summary: {short(final_verdict.get('decision_summary', ''), 260)}")


def main() -> None:
    args = parse_args()
    candidate_models, reviewer_models = resolved_models(args)
    results_dir = demo_output_dir(args)
    predictions_csv = results_dir / "predictions.csv"

    print(color("LLM council demo", "32;1"))
    print(f"Explainability source root: {EXPLAINABILITY_RESULTS_ROOT}")
    print(f"Domain: {args.domain}")
    print(f"Prompt slug: {args.prompt_slug}")
    print(f"Candidate models: {', '.join(candidate_models)}")
    print(f"Reviewer models: {', '.join(reviewer_models)}")
    print(f"Chairman model: {args.chairman_model}")
    print(f"Small demo limits: personas={args.limit_personas}, steps={args.limit_steps}")
    print(f"Run mode: {'real models' if args.real else 'mock only'}")
    pause(args.sleep)

    print_step(1, "What llm_council does")
    print("It reuses explainability outputs that already exist for several candidate models.")
    print("Reviewer models compare those candidate verdicts for one trajectory step.")
    print("A chairman model then writes the final council verdict for that step.")
    print("This means llm_council is an aggregation layer on top of explainability, not a new trajectory judge.")
    pause(args.sleep)

    print_step(2, "Inputs reused from explainability")
    print(f"Expected explainability inputs: {EXPLAINABILITY_RESULTS_ROOT / args.domain / args.prompt_slug}")
    print(f"Persona metadata: {TASKS_DIR / (args.domain + '.json')}")
    record = preview_record(args.domain, args.prompt_slug, candidate_models)
    print_candidate_preview(record)
    pause(args.sleep)

    print_step(3, "Prompting and council behavior")
    preview_prompts_and_mock_decision(record, reviewer_models, args.chairman_model)
    pause(args.sleep)

    print_step(4, "Command")
    cmd = build_command(args, candidate_models, reviewer_models)
    print(" ".join(cmd))
    if not args.run:
        print("\nDry run only. Add --run to execute this tiny council demo.")
        if not args.real:
            print("By default the command includes --mock, so it is safe for a supervisor demo.")
        else:
            print("You asked for --real, so a run would call the reviewer and chairman models.")
    else:
        print("\nRunning the tiny council demo now...")
        rc = subprocess.run(cmd, cwd=BASE_DIR)
        print(f"Council process exited with code: {rc.returncode}")

    pause(args.sleep)

    print_step(5, "Outputs")
    print(f"Demo output directory: {results_dir}")
    print("Expected files:")
    print("  predictions.csv       one row per persona x step with the final council verdict")
    print("  <Persona>.json        candidate verdicts, reviewer choices, chairman response")
    print("  summary.json          small run summary")
    pause(args.sleep)

    print_step(6, "Output preview")
    preview_csv(predictions_csv)
    preview_persona_json(results_dir)

    print()
    print(color("Demo complete.", "32;1"))


if __name__ == "__main__":
    main()
