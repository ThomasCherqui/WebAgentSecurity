#!/usr/bin/env python3
"""Launcher for explainability prompt/model sweeps.

This stage generates raw per-judge outputs only. Aggregation is intentionally
handled by the downstream aggregation pipeline.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "")).strip("_") or "run"


def main():
    # Compute SPILLage-main root by searching upward for a folder named 'SPILLage-main'
    p = Path(__file__).resolve()
    project_root = None
    for ancestor in [p] + list(p.parents):
        if ancestor.name == "SPILLage-main":
            project_root = ancestor
            break
    if project_root is None:
        # fallback to two directories up (previous behavior)
        project_root = p.parents[2]

    script = Path(__file__).resolve().parent / "scripts" / "llm_jury_browseruse.py"
    if not script.exists():
        raise SystemExit(f"Baseline judge script not found: {script}")

    # sensible defaults (use data/input by default)
    default_domain = "shopping_Amazon_chat"
    default_trajectories = str(project_root / "data" / "input" / "trajectories" / "browseruse_gpt4o_parsed")
    default_tasks = str(project_root / "data" / "input" / "tasks" / "less_sensitive")

    p = argparse.ArgumentParser(description="Generate raw explainability outputs for judge prompts/models")
    p.add_argument("--domain", default=default_domain)
    p.add_argument("--trajectories-dir", default=default_trajectories)
    p.add_argument("--tasks-dir", default=default_tasks)
    p.add_argument("--model", default="gemma4:31b", help="Single Ollama judge model")
    p.add_argument("--models", nargs="+", default=None, help="Deprecated alias; pass exactly one model")
    p.add_argument("--limit-personas", type=int, default=0, help="0 means no limit")
    p.add_argument("--limit-steps", type=int, default=0, help="0 means no limit")
    p.add_argument("--resume-existing", action="store_true", help="Reuse existing predictions and process only missing personas")
    p.add_argument("--mock", action="store_true", help="Run deterministic mock judge (no Ollama)")
    p.add_argument("--prompt-template", default="violations_only_fewshot.md", help="Prompt .md filename under prompts/ or an absolute path")
    args = p.parse_args()

    model_names = args.models or [args.model]
    if len(model_names) != 1:
        raise SystemExit("This launcher runs exactly one model at a time. Use --model once, or run the batch script to loop over models.")
    model = model_names[0]
    prompt_slug = slug(os.path.splitext(os.path.basename(args.prompt_template))[0])
    model_slug = slug(model)
    out_dir = Path(__file__).resolve().parent / "results_ollama" / args.domain / prompt_slug / model_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Quick fix: if tasks file <domain>.json missing but <domain>_modified.json exists,
    # create a symlink named <domain>.json pointing to it (inline, minimal change).
    tasks_dir = Path(args.tasks_dir)
    expected = tasks_dir / f"{args.domain}.json"
    if not expected.exists():
        candidate = tasks_dir / f"{args.domain}_modified.json"
        if candidate.exists():
            try:
                # create symlink in the same tasks_dir
                expected.symlink_to(candidate)
                print(f"Created symlink {expected} -> {candidate}")
            except FileExistsError:
                pass
            except Exception as e:
                print(f"Could not create symlink {expected} -> {candidate}: {e}")

    cmd = [sys.executable, str(script), "--domain", args.domain, "--trajectories-dir", args.trajectories_dir, "--tasks-dir", args.tasks_dir]
    cmd += ["--model", model]
    if args.limit_personas and args.limit_personas > 0:
        cmd += ["--limit-personas", str(args.limit_personas)]
    if args.limit_steps and args.limit_steps > 0:
        cmd += ["--limit-steps", str(args.limit_steps)]
    if args.resume_existing:
        cmd += ["--resume-existing"]
    cmd += ["--allow-judge-errors", "--prompt-template", args.prompt_template]

    print("\n>>", " ".join(cmd))

    rc = subprocess.run(cmd)
    if rc.returncode != 0:
        print("Judge exited with code", rc.returncode)
        raise SystemExit(rc.returncode)
    print("Raw judge output generation finished. Results are in:", out_dir)


if __name__ == "__main__":
    main()
