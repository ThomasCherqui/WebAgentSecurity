#!/usr/bin/env python3
"""Generate per-judge explainability outputs for Browser-Use trajectories.

This script focuses on prompt/model sweeps. It:
 - reads parsed trajectories from a domain folder (persona_*_parsed.json)
 - reads the tasks persona JSON to get persona metadata
 - for each step, builds an explainability prompt and calls safe_judge_ollama()
 - writes raw per-judge outputs only; aggregation is handled downstream

Usage (example):
  python llm_jury_browseruse.py --domain shopping_Amazon_chat \
      --trajectories-dir /path/to/trajectories/browseruse_gpt4o_parsed \
      --tasks-dir /path/to/tasks/less_sensitive \
      --model llama3.1:8b --limit-personas 10 --limit-steps 5 --allow-judge-errors
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
from typing import List, Dict, Any

# import common utilities from this package
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from ollama_jury_common import (
    empty_counts,
    make_judges,
    parse_models,
    safe_judge_ollama,
)

PROMPTS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "prompts"))


def load_personas(tasks_file: str) -> Dict[str, Dict[str, Any]]:
    with open(tasks_file) as f:
        data = json.load(f)
    lookup: Dict[str, Dict[str, Any]] = {}
    for p in data.get("personas", []):
        pid = p.get("id")
        name = p.get("name")
        if pid is not None:
            lookup[str(pid)] = p
        if name:
            lookup[name] = p
    return lookup


def find_trajectory_files(traj_dir: str) -> List[str]:
    p = os.path.abspath(traj_dir)
    if not os.path.isdir(p):
        raise SystemExit(f"Trajectory dir not found: {p}")
    return sorted(glob.glob(os.path.join(p, "persona_*_parsed.json")) + glob.glob(os.path.join(p, "persona_*_eval.json")))


def extract_persona(basename: str):
    m = re.search(r"persona_(\d+)_(.*?)_(?:parsed|eval)\.json$", basename)
    if not m:
        return basename, basename
    return int(m.group(1)), m.group(2).replace("_", " ")


def step_text(step: Any) -> str:
    if isinstance(step, dict):
        return " ".join(str(step.get(k) or "") for k in ("action", "evaluation", "memory_update", "next_goal", "thinking")).strip()
    return str(step or "").strip()


def load_steps(data: Dict[str, Any]) -> List[Any]:
    if isinstance(data.get("steps"), list):
        return data["steps"]
    keys = sorted((k for k in data if re.match(r"step_?\d+$", k, re.I)), key=lambda k: int(re.search(r"\d+", k).group()))
    return [data[k] for k in keys]


def csv_cell(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("_") or "run"


def load_prompt_template(template_name: str) -> str:
    path = template_name if os.path.isabs(template_name) else os.path.join(PROMPTS_DIR, template_name)
    if not os.path.isfile(path):
        raise SystemExit(f"Prompt template not found: {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def render_template(template: str, values: Dict[str, Any]) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value or ""))
    return template


def build_prompt(pdetail: Dict[str, Any], step: Any, template: str) -> str:
    values = {
        "task_goal": pdetail.get("task", "the user's task"),
        "full_user_prompt": pdetail.get("prompt", ""),
        "relevant_attributes": ", ".join(pdetail.get("relevant_attributes", []) or []),
        "irrelevant_attributes": ", ".join(pdetail.get("irrelevant_attributes", []) or []),
        "trajectory_step": step_text(step),
    }
    return render_template(template, values)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--domain", required=True)
    p.add_argument("--trajectories-dir", required=True, help="Folder containing persona_*_parsed.json")
    p.add_argument("--tasks-dir", required=True, help="Folder containing <domain>.json persona tasks")
    p.add_argument("--model", default="llama3.1:8b", help="Single model string for baseline/backward compatibility")
    p.add_argument("--models", nargs="+", default=None, help="One or more Ollama judge models; overrides --model")
    p.add_argument("--ollama-host", default=None)
    p.add_argument("--limit-personas", type=int, default=None)
    p.add_argument("--limit-steps", type=int, default=None)
    p.add_argument("--allow-judge-errors", action="store_true")
    p.add_argument("--prompt-template", default="balanced_fewshot.md", help="Prompt .md filename under prompts/ or an absolute path")
    args = p.parse_args()

    traj_domain_dir = os.path.join(args.trajectories_dir, args.domain)
    tasks_file = os.path.join(args.tasks_dir, f"{args.domain}.json")
    if not os.path.isfile(tasks_file):
        raise SystemExit(f"Persona file not found: {tasks_file}")

    personas_lookup = load_personas(tasks_file)
    files = find_trajectory_files(traj_domain_dir)
    personas = []
    for f in files:
        bn = os.path.basename(f)
        pid, pname = extract_persona(bn)
        if isinstance(pid, int):
            personas.append((pid, pname, f))
    personas = sorted(personas)
    if args.limit_personas:
        personas = personas[: args.limit_personas]

    prompt_template = load_prompt_template(args.prompt_template)
    model_names = parse_models(args.models or [args.model])
    judge_specs = make_judges(model_names)
    judges = [jid for jid, _ in judge_specs]
    prompt_slug = slug(os.path.splitext(os.path.basename(args.prompt_template))[0])
    models_slug = slug("__".join(model_names))
    out_dir = os.path.join(SCRIPT_DIR, "..", "results_ollama", args.domain, prompt_slug, models_slug)
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Using prompt template: {args.prompt_template}")
    print("Judge models: " + ", ".join(model_names))

    persona_runs = []
    for pid, pname, path in personas:
        with open(path) as f:
            data = json.load(f)
        steps = load_steps(data)
        if args.limit_steps:
            steps = steps[: args.limit_steps]
        pdetail = personas_lookup.get(str(pid)) or personas_lookup.get(pname) or {}
        persona_runs.append({
            "pname": pname,
            "pdetail": pdetail,
            "steps": steps,
            "step_results": [
                {
                    "responses": {},
                    "trajectory_step": step_text(step),
                    "prompt_used": build_prompt(pdetail, step, prompt_template),
                }
                for step in steps
            ],
        })

    for judge_name, model in judge_specs:
        print(f"Running {judge_name} ({model})")
        for run_data in persona_runs:
            for i, step in enumerate(run_data["steps"]):
                sd = run_data["step_results"][i]
                prompt = sd["prompt_used"]
                resp, cats = safe_judge_ollama(prompt, model, host=args.ollama_host, allow_errors=args.allow_judge_errors)
                sd[judge_name] = cats
                sd["responses"][judge_name] = resp

    raw_csv_rows = []
    judge_models = {j: m for j, m in judge_specs}
    judge_totals = {j: empty_counts() for j in judges}

    for run_data in persona_runs:
        pname = run_data["pname"]
        pdetail = run_data["pdetail"]
        per_person_out = {}
        for i, sd in enumerate(run_data["step_results"]):
            step_out = {
                "domain": args.domain,
                "persona": pname,
                "persona_id": pdetail.get("id", ""),
                "step": i + 1,
                "judge_models": judge_models,
                "prompt_template": args.prompt_template,
                "prompt_slug": prompt_slug,
                "prompt_used": sd["prompt_used"],
                "trajectory_step": sd["trajectory_step"],
                "judges": {},
            }
            for j in judges:
                step_out["judges"][j] = {
                    "model": judge_models[j],
                    "violations": sd[j],
                    "response": sd["responses"][j],
                }
                for c in judge_totals[j]:
                    judge_totals[j][c] += sd[j][c]
                raw_csv_rows.append({
                    "domain": args.domain,
                    "persona": pname,
                    "persona_id": pdetail.get("id", ""),
                    "step": i + 1,
                    "judge_id": j,
                    "judge_model": judge_models[j],
                    "prompt_template": args.prompt_template,
                    "prompt_slug": prompt_slug,
                    "CE": int(sd[j].get("CE", 0)),
                    "CI": int(sd[j].get("CI", 0)),
                    "BE": int(sd[j].get("BE", 0)),
                    "BI": int(sd[j].get("BI", 0)),
                    "response": csv_cell(sd["responses"][j]),
                    "trajectory_step": csv_cell(sd["trajectory_step"]),
                })
            per_person_out[f"Step {i+1}"] = step_out

        with open(os.path.join(out_dir, f"{pname}.json"), "w") as pf:
            json.dump(per_person_out, pf, indent=2)

    with open(os.path.join(out_dir, "raw_judge_outputs_summary.json"), "w") as jf:
        json.dump({
            "method": "ollama_multi_judge_explainability_raw",
            "domain": args.domain,
            "judge_models": judge_models,
            "prompt_template": args.prompt_template,
            "prompt_slug": prompt_slug,
            "prompt_text": prompt_template,
            "models_slug": models_slug,
            "judge_totals": judge_totals,
            "aggregation": "none",
        }, jf, indent=2)

    csv_path = os.path.join(out_dir, "raw_predictions_by_judge.csv")
    if raw_csv_rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(
                cf,
                fieldnames=[
                    "domain",
                    "persona",
                    "persona_id",
                    "step",
                    "judge_id",
                    "judge_model",
                    "prompt_template",
                    "prompt_slug",
                    "CE",
                    "CI",
                    "BE",
                    "BI",
                    "response",
                    "trajectory_step",
                ],
                lineterminator="\n",
            )
            writer.writeheader()
            for r in raw_csv_rows:
                writer.writerow(r)

    print(f"Raw judge outputs written to {out_dir}")
    print("Aggregation disabled for this stage; use the aggregation pipeline downstream.")


if __name__ == "__main__":
    main()
