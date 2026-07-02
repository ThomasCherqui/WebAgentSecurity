#!/usr/bin/env python3
"""Build a CSV (one row per step) from raw parsed trajectories and tasks persona file.

Inputs:
  --trajectories-dir /path/to/trajectories/<domain>/  (folder containing persona_*_parsed.json)
  --tasks-file /path/to/tasks/less_sensitive/<domain>.json
  --output out.csv

This script does NOT call any judge. It only extracts the fields we feed to the LLM:
  action, evaluation, memory_update, next_goal, combined_text
and persona-level metadata from the tasks file: task, prompt, relevant_attributes, irrelevant_attributes.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from typing import Dict, Any


def load_tasks(tasks_file: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(tasks_file) as f:
            data = json.load(f)
    except Exception as e:
        raise SystemExit(f"Could not read tasks file {tasks_file}: {e}")
    lookup: Dict[str, Dict[str, Any]] = {}
    for p in data.get("personas", []):
        pid = p.get("id")
        name = p.get("name")
        if pid is not None:
            lookup[str(pid)] = p
        if name:
            lookup[str(name)] = p
    return lookup


def collect_parsed_files(traj_dir: str):
    p = Path(traj_dir)
    if not p.exists() or not p.is_dir():
        raise SystemExit(f"Trajectories dir not found: {traj_dir}")
    files = sorted([str(x) for x in p.glob("persona_*_parsed.json") if x.is_file()])
    return files


def extract_persona_info_from_filename(basename: str):
    m = re.search(r"persona_(\d+)_(.*?)_parsed\.json$", basename)
    if m:
        return int(m.group(1)), m.group(2).replace("_", " ")
    # fallback: use whole basename
    return basename, basename


def read_json(path: str):
    with open(path) as f:
        return json.load(f)


def build_rows(files, persona_lookup):
    rows = []
    for path in files:
        basename = os.path.basename(path)
        pid, pname = extract_persona_info_from_filename(basename)
        pdata = persona_lookup.get(str(pid)) or persona_lookup.get(pname) or {}
        task_text = pdata.get("task", "")
        full_prompt = pdata.get("prompt", "")
        relevant = pdata.get("relevant_attributes", []) or []
        irrelevant = pdata.get("irrelevant_attributes", []) or []
        try:
            data = read_json(path)
        except Exception as e:
            print("Skipping", path, "read error:", e)
            continue
        steps = data.get("steps", [])
        for s in steps:
            action = s.get("action", "")
            evaluation = s.get("evaluation", "")
            memory_update = s.get("memory_update", "")
            next_goal = s.get("next_goal", "")
            combined = " ".join([str(x).strip() for x in (action, evaluation, memory_update, next_goal) if x])
            row = {
                "persona_id": pid,
                "persona_name": pname,
                "persona_task": task_text,
                "persona_prompt": full_prompt,
                "relevant_attributes": ", ".join(relevant),
                "irrelevant_attributes": ", ".join(irrelevant),
                "file": basename,
                "step_number": s.get("step_number") or s.get("index") or "",
                "action": action,
                "evaluation": evaluation,
                "memory_update": memory_update,
                "next_goal": next_goal,
                "combined_text": combined,
            }
            rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trajectories-dir", required=True, help="Folder containing persona_*_parsed.json")
    p.add_argument("--tasks-file", required=True, help="Persona tasks JSON file (e.g. tasks/less_sensitive/<domain>.json)")
    p.add_argument("--output", required=True, help="Output CSV path")
    args = p.parse_args()

    persona_lookup = load_tasks(args.tasks_file)
    files = collect_parsed_files(args.trajectories_dir)
    if not files:
        raise SystemExit(f"No parsed persona files found in {args.trajectories_dir}")
    rows = build_rows(files, persona_lookup)
    fieldnames = [
        "persona_id", "persona_name", "persona_task", "persona_prompt", "relevant_attributes", "irrelevant_attributes",
        "file", "step_number", "action", "evaluation", "memory_update", "next_goal", "combined_text"
    ]
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    print(f"Wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
