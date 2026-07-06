#!/usr/bin/env python3
"""Generate single-model explainability outputs for Browser-Use trajectories.

This script focuses on prompt/model sweeps. It:
 - reads parsed trajectories from a domain folder (persona_*_parsed.json)
 - reads the tasks persona JSON to get persona metadata
 - for each step, builds an explainability prompt and calls safe_judge_ollama()
 - writes one model's raw explainability outputs; aggregation is handled downstream

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
from ollama_jury_common import empty_counts, parse_json, parse_models, safe_judge_ollama

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


def normalize_violation(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        return {"category": "", "attribute": "", "evidence": "", "explanation": ""}
    return {
        "category": str(value.get("category") or ""),
        "attribute": str(value.get("attribute") or ""),
        "evidence": str(value.get("evidence") or ""),
        "explanation": str(value.get("explanation") or ""),
    }


def parsed_response_fields(response: str) -> Dict[str, Any]:
    parsed = parse_json(response)
    violations_raw = parsed.get("violations", [])
    violations = [normalize_violation(v) for v in violations_raw] if isinstance(violations_raw, list) else []
    evidence = "; ".join(v["evidence"] for v in violations if v.get("evidence"))
    explanation = "; ".join(v["explanation"] for v in violations if v.get("explanation"))
    return {
        "violations": violations,
        "evidence": evidence,
        "explanation": explanation,
        "no_violation_reason": str(parsed.get("no_violation_reason") or ""),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--domain", required=True)
    p.add_argument("--trajectories-dir", required=True, help="Folder containing persona_*_parsed.json")
    p.add_argument("--tasks-dir", required=True, help="Folder containing <domain>.json persona tasks")
    p.add_argument("--model", default="llama3.1:8b", help="Single Ollama judge model")
    p.add_argument("--models", nargs="+", default=None, help=argparse.SUPPRESS)
    p.add_argument("--ollama-host", default=None)
    p.add_argument("--limit-personas", type=int, default=None)
    p.add_argument("--limit-steps", type=int, default=None)
    p.add_argument("--allow-judge-errors", action="store_true")
    p.add_argument("--resume-existing", action="store_true", help="Reuse existing per-persona JSON/predictions.csv and process only missing personas")
    p.add_argument("--prompt-template", default="violations_only_fewshot.md", help="Prompt .md filename under prompts/ or an absolute path")
    args = p.parse_args()

    model_names = parse_models(args.models or [args.model])
    if len(model_names) != 1:
        raise SystemExit("This explainability stage runs exactly one model at a time. Use --model once, or launch separate runs.")
    model = model_names[0]

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
    prompt_slug = slug(os.path.splitext(os.path.basename(args.prompt_template))[0])
    model_slug = slug(model)
    out_dir = os.path.join(SCRIPT_DIR, "..", "results_ollama", args.domain, prompt_slug, model_slug)
    out_dir = os.path.normpath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    print(f"Using prompt template: {args.prompt_template}")
    print(f"Judge model: {model}")

    fieldnames = [
        "domain",
        "persona",
        "persona_id",
        "step",
        "model",
        "prompt_template",
        "prompt_slug",
        "CE",
        "CI",
        "BE",
        "BI",
        "violations",
        "evidence",
        "explanation",
        "no_violation_reason",
        "response",
        "trajectory_step",
    ]
    csv_path = os.path.join(out_dir, "predictions.csv")
    csv_rows = []
    totals = empty_counts()
    completed_personas = set()

    if args.resume_existing and os.path.isfile(csv_path):
        try:
            with open(csv_path, newline="", encoding="utf-8") as cf:
                for row in csv.DictReader(cf):
                    csv_rows.append(row)
                    if row.get("persona"):
                        completed_personas.add(row["persona"])
                    for cat in totals:
                        try:
                            totals[cat] += int(row.get(cat, 0) or 0)
                        except Exception:
                            pass
            print(f"Resume enabled: loaded {len(csv_rows)} existing rows for {len(completed_personas)} personas")
        except Exception as e:
            print(f"Resume warning: could not load existing CSV {csv_path}: {e}")
            csv_rows = []
            totals = empty_counts()
            completed_personas = set()

    def write_csv() -> None:
        with open(csv_path, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in csv_rows:
                writer.writerow(row)

    def write_summary() -> None:
        with open(os.path.join(out_dir, "summary.json"), "w") as jf:
            json.dump({
                "method": "ollama_single_judge_explainability",
                "domain": args.domain,
                "model": model,
                "model_slug": model_slug,
                "prompt_template": args.prompt_template,
                "prompt_slug": prompt_slug,
                "totals": totals,
                "aggregation": "none",
                "num_personas_completed": len({row["persona"] for row in csv_rows}),
                "num_steps": len(csv_rows),
            }, jf, indent=2)

    print(f"Running {model}")
    write_csv()
    write_summary()

    for pid, pname, path in personas:
        if args.resume_existing and pname in completed_personas and os.path.isfile(os.path.join(out_dir, f"{pname}.json")):
            print(f"Skip existing persona: {pname}")
            continue
        print(f"Persona: {pname}")
        with open(path) as f:
            data = json.load(f)
        steps = load_steps(data)
        if args.limit_steps:
            steps = steps[: args.limit_steps]
        pdetail = personas_lookup.get(str(pid)) or personas_lookup.get(pname) or {}
        per_person_out = {}

        for i, step in enumerate(steps):
            prompt = build_prompt(pdetail, step, prompt_template)
            trajectory_step = step_text(step)
            resp, cats = safe_judge_ollama(prompt, model, host=args.ollama_host, allow_errors=args.allow_judge_errors)
            parsed_fields = parsed_response_fields(resp)
            step_out = {
                "domain": args.domain,
                "persona": pname,
                "persona_id": pdetail.get("id", ""),
                "step": i + 1,
                "judge_model": model,
                "prompt_template": args.prompt_template,
                "prompt_slug": prompt_slug,
                "cats": cats,
                "violations": parsed_fields["violations"],
                "evidence": parsed_fields["evidence"],
                "explanation": parsed_fields["explanation"],
                "no_violation_reason": parsed_fields["no_violation_reason"],
                "response": resp,
                "trajectory_step": trajectory_step,
            }
            per_person_out[f"Step {i+1}"] = step_out
            for c in totals:
                totals[c] += cats[c]
            csv_rows.append({
                "domain": args.domain,
                "persona": pname,
                "persona_id": pdetail.get("id", ""),
                "step": i + 1,
                "model": model,
                "prompt_template": args.prompt_template,
                "prompt_slug": prompt_slug,
                "CE": int(cats.get("CE", 0)),
                "CI": int(cats.get("CI", 0)),
                "BE": int(cats.get("BE", 0)),
                "BI": int(cats.get("BI", 0)),
                "violations": csv_cell(json.dumps(parsed_fields["violations"], ensure_ascii=False)),
                "evidence": csv_cell(parsed_fields["evidence"]),
                "explanation": csv_cell(parsed_fields["explanation"]),
                "no_violation_reason": csv_cell(parsed_fields["no_violation_reason"]),
                "response": csv_cell(resp),
                "trajectory_step": csv_cell(trajectory_step),
            })

        with open(os.path.join(out_dir, f"{pname}.json"), "w") as pf:
            json.dump(per_person_out, pf, indent=2)
        completed_personas.add(pname)
        write_csv()
        write_summary()
        print(f"Saved persona output: {os.path.join(out_dir, f'{pname}.json')}")

    print(f"Explainability outputs written to {out_dir}")
    print("Aggregation disabled for this stage; use the aggregation pipeline downstream.")


if __name__ == "__main__":
    main()
