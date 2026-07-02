#!/usr/bin/env python3
"""Minimal launcher for the baseline-only judge.

This launcher is intentionally tiny so you can run `python main.py` and get
quick, deterministic outputs for development. It defaults paths to the
project's `llm_jury_eval_v3` locations and enables mock mode when invoked
without CLI arguments (safe, no Ollama required).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


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

    p = argparse.ArgumentParser(description="Minimal launcher for baseline judge")
    p.add_argument("--domain", default=default_domain)
    p.add_argument("--trajectories-dir", default=default_trajectories)
    p.add_argument("--tasks-dir", default=default_tasks)
    p.add_argument("--model", default="gemma4:31b", help="Single model string (optional)")
    p.add_argument("--limit-personas", type=int, default=0, help="0 means no limit")
    p.add_argument("--limit-steps", type=int, default=0, help="0 means no limit")
    p.add_argument("--mock", action="store_true", help="Run deterministic mock judge (no Ollama)")
    args = p.parse_args()

    out_dir = Path(__file__).resolve().parent / "results_ollama" / args.domain
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
    if args.model:
        cmd += ["--model", args.model]
    if args.limit_personas and args.limit_personas > 0:
        cmd += ["--limit-personas", str(args.limit_personas)]
    if args.limit_steps and args.limit_steps > 0:
        cmd += ["--limit-steps", str(args.limit_steps)]
    cmd += ["--allow-judge-errors"]

    print("\n>>", " ".join(cmd))

    rc = subprocess.run(cmd)
    if rc.returncode != 0:
        print("Judge exited with code", rc.returncode)
    else:
        print("Judge finished. Results (if any) are in:", out_dir)


if __name__ == "__main__":
    main()
