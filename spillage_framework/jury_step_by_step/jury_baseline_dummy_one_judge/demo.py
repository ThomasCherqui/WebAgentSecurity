#!/usr/bin/env python3
"""Small, readable demo for the one-judge baseline.

Default mode is safe: it explains the workflow and inspects existing outputs.
Use --run to actually launch a tiny judge run.
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


def project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "data" / "input").exists():
            return parent
    return here.parents[2]


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


def print_card(title: str, lines: list[str]) -> None:
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


def preview_inputs_and_prompt(args: argparse.Namespace, root: Path) -> None:
    base_dir = Path(__file__).resolve().parent
    scripts_dir = base_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    from llm_jury_browseruse import (
        build_prompt,
        extract_persona,
        find_trajectory_files,
        load_personas,
        load_steps,
        step_text,
    )

    trajectories_root = root / "data" / "input" / "trajectories" / "browseruse_gpt4o_parsed"
    trajectories_dir = trajectories_root / args.domain
    tasks_file = root / "data" / "input" / "tasks" / "less_sensitive" / f"{args.domain}.json"

    files = find_trajectory_files(str(trajectories_dir))
    if not files:
        print_card("Input example", [f"No trajectory files found in {trajectories_dir}"])
        return

    candidates = []
    for file_name in files:
        sample_pid, sample_name = extract_persona(Path(file_name).name)
        if isinstance(sample_pid, int):
            candidates.append((sample_pid, sample_name, Path(file_name)))
    if not candidates:
        print_card("Input example", [f"No persona trajectory files found in {trajectories_dir}"])
        return

    sample = None
    for sample_pid, sample_name, path in sorted(candidates):
        with path.open(encoding="utf-8") as f:
            trajectory = json.load(f)
        steps = load_steps(trajectory)
        for step_number, step in enumerate(steps, start=1):
            if step_text(step):
                sample = (sample_pid, sample_name, path, step_number, step)
                break
        if sample:
            break

    if sample is None:
        sample_pid, sample_name, path = sorted(candidates)[0]
        with path.open(encoding="utf-8") as f:
            trajectory = json.load(f)
        steps = load_steps(trajectory)
        if not steps:
            print_card("Input example", [f"No steps found in {path}"])
            return
        sample = (sample_pid, sample_name, path, 1, steps[0])

    pid, persona_name, sample_file, sample_step_number, sample_step = sample
    personas = load_personas(str(tasks_file))
    pdetail = personas.get(str(pid)) or personas.get(persona_name) or {}
    irrelevant = pdetail.get("irrelevant_attributes", []) or []
    prompt = build_prompt(pdetail, sample_step)
    task_text = short(pdetail.get("task"), 360)
    irrelevant_text = short(", ".join(irrelevant), 360)

    print_card(
        "Input example",
        [
            f"Persona: {persona_name}",
            f"Task: {task_text}",
            f"Irrelevant attributes: {irrelevant_text}",
            f"Trajectory file: {sample_file}",
            f"Step {sample_step_number} text: {short(step_text(sample_step), 520)}",
        ],
    )
    print_block("Prompt example", prompt, 1800)


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
    parser.add_argument("--sleep", type=float, default=2.0, help="Seconds to pause between demo sections")
    args = parser.parse_args()

    root = project_root()
    base_dir = Path(__file__).resolve().parent
    model_slug = args.model.replace(":", "_").replace("/", "_")
    results_dir = base_dir / "results_ollama_demo" / args.domain / model_slug
    predictions_csv = results_dir / "predictions.csv"

    print(color("One-judge baseline demo", "32;1"))
    print(f"Project root: {root}")
    print(f"Domain: {args.domain}")
    print(f"Model: {args.model}")
    print(f"Small demo limits: personas={args.limit_personas}, steps={args.limit_steps}")
    pause(args.sleep)

    print_step(1, "What this baseline does")
    print("For each Browser-Use trajectory step, the script builds one privacy prompt.")
    print("It asks one Ollama judge model to return JSON violations in four categories:")
    print("  CE = direct content leak")
    print("  CI = indirect content leak")
    print("  BE = direct behavioral leak")
    print("  BI = indirect behavioral leak")
    pause(args.sleep)

    print_step(2, "Inputs")
    print(f"Trajectories: {root / 'data' / 'input' / 'trajectories' / 'browseruse_gpt4o_parsed' / args.domain}")
    print(f"Persona tasks: {root / 'data' / 'input' / 'tasks' / 'less_sensitive' / (args.domain + '.json')}")
    pause(args.sleep)

    print_step(3, "Input and prompt examples")
    preview_inputs_and_prompt(args, root)
    pause(args.sleep)

    print_step(4, "Command")
    cmd = build_command(args, root)
    print(" ".join(cmd))
    if not args.run:
        print("\nDry run only. Add --run to execute this tiny demo.")
    else:
        print("\nRunning the tiny demo now...")
        rc = subprocess.run(cmd)
        print(f"Judge process exited with code: {rc.returncode}")

    pause(args.sleep)

    print_step(5, "Outputs")
    print(f"Results directory: {results_dir}")
    print("Expected files:")
    print("  predictions.csv       one row per persona x step")
    print("  <Persona>.json        raw response + parsed categories per step")

    pause(args.sleep)

    print_step(6, "Output preview")
    preview_csv(predictions_csv)
    preview_persona_json(results_dir)

    print()
    print(color("Demo complete.", "32;1"))


if __name__ == "__main__":
    main()
