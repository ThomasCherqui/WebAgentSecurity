#!/usr/bin/env python3
"""Small, readable demo for the one-judge baseline.

Default mode is safe: it explains the workflow and inspects existing outputs.
Use --run to actually launch a tiny judge run.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "data" / "input").exists():
            return parent
    return here.parents[2]


def print_step(number: int, title: str) -> None:
    print()
    print("=" * 72)
    print(f"STEP {number}: {title}")
    print("=" * 72)


def preview_csv(path: Path, max_rows: int = 5) -> None:
    if not path.exists():
        print(f"No predictions.csv found yet at: {path}")
        return

    print(f"Found predictions.csv: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Rows: {len(rows)}")
    if not rows:
        return

    print("\nFirst rows:")
    for row in rows[:max_rows]:
        print(
            "  "
            f"persona={row.get('persona')} "
            f"step={row.get('step')} "
            f"CE={row.get('CE')} CI={row.get('CI')} "
            f"BE={row.get('BE')} BI={row.get('BI')}"
        )


def preview_persona_json(results_dir: Path) -> None:
    files = sorted(p for p in results_dir.glob("*.json") if p.name != "jury_results_fixed.json")
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
    print(f"Example key: {first_key}")
    print(f"Judge model: {step.get('judge_model')}")
    print(f"Parsed cats: {step.get('cats')}")
    combined = str(step.get("combined_text", "")).replace("\n", " ")
    print(f"Step text preview: {combined[:220]}")


def build_command(args: argparse.Namespace, root: Path) -> list[str]:
    base_dir = Path(__file__).resolve().parent
    script = base_dir / "scripts" / "llm_jury_browseruse.py"
    trajectories_dir = root / "data" / "input" / "trajectories" / "browseruse_gpt4o_parsed"
    tasks_dir = root / "data" / "input" / "tasks" / "less_sensitive"
    cmd = [
        sys.executable,
        str(script),
        "--domain",
        args.domain,
        "--trajectories-dir",
        str(trajectories_dir),
        "--tasks-dir",
        str(tasks_dir),
        "--model",
        args.model,
        "--limit-personas",
        str(args.limit_personas),
        "--limit-steps",
        str(args.limit_steps),
        "--allow-judge-errors",
        "--results-root",
        "results_ollama_demo",
    ]
    if args.ollama_host:
        cmd += ["--ollama-host", args.ollama_host]
    return cmd


def main() -> None:
    parser = argparse.ArgumentParser(description="Explain and optionally run the one-judge baseline demo")
    parser.add_argument("--domain", default="shopping_Amazon_chat")
    parser.add_argument("--model", default="gemma4:31b")
    parser.add_argument("--limit-personas", type=int, default=1)
    parser.add_argument("--limit-steps", type=int, default=2)
    parser.add_argument("--ollama-host", default=None)
    parser.add_argument("--run", action="store_true", help="Actually run the small demo judge job")
    args = parser.parse_args()

    root = project_root()
    base_dir = Path(__file__).resolve().parent
    model_slug = args.model.replace(":", "_").replace("/", "_")
    results_dir = base_dir / "results_ollama_demo" / args.domain / model_slug
    predictions_csv = results_dir / "predictions.csv"

    print("One-judge baseline demo")
    print(f"Project root: {root}")
    print(f"Domain: {args.domain}")
    print(f"Model: {args.model}")
    print(f"Small demo limits: personas={args.limit_personas}, steps={args.limit_steps}")

    print_step(1, "What this baseline does")
    print("For each Browser-Use trajectory step, the script builds one privacy prompt.")
    print("It asks one Ollama judge model to return JSON violations in four categories:")
    print("  CE = direct content leak")
    print("  CI = indirect content leak")
    print("  BE = direct behavioral leak")
    print("  BI = indirect behavioral leak")

    print_step(2, "Inputs")
    print(f"Trajectories: {root / 'data' / 'input' / 'trajectories' / 'browseruse_gpt4o_parsed' / args.domain}")
    print(f"Persona tasks: {root / 'data' / 'input' / 'tasks' / 'less_sensitive' / (args.domain + '.json')}")

    print_step(3, "Command")
    cmd = build_command(args, root)
    print(" ".join(cmd))
    if not args.run:
        print("\nDry run only. Add --run to execute this tiny demo.")
    else:
        print("\nRunning the tiny demo now...")
        rc = subprocess.run(cmd)
        print(f"Judge process exited with code: {rc.returncode}")

    print_step(4, "Outputs")
    print(f"Results directory: {results_dir}")
    print("Expected files:")
    print("  predictions.csv       one row per persona x step")
    print("  <Persona>.json        raw response + parsed categories per step")

    print_step(5, "Output preview")
    preview_csv(predictions_csv)
    preview_persona_json(results_dir)

    print()
    print("Demo complete.")


if __name__ == "__main__":
    main()
