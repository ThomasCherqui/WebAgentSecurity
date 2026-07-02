#!/usr/bin/env python3
"""
Offline smoke test for the Ollama v2 implicit AutoGen evaluator.

No API keys, no Ollama server, no network. The script monkey-patches
implicit_eval_autogen.safe_judge_ollama with a deterministic fake.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import implicit_eval_autogen as ie  # noqa: E402


def fake_safe_judge(prompt, model, host=None, temperature=0.0, max_tokens=2048, allow_errors=False):
    response = json.dumps({
        "violations": [
            {"category": "indirect_content"},
            {"category": "indirect_behavioral"},
        ]
    })
    return response, {"CE": 0, "CI": 1, "BE": 0, "BI": 1}


def main():
    p = argparse.ArgumentParser(description="Offline smoke test for Ollama implicit_eval_autogen.py")
    p.add_argument("--domain", default="shopping_ebay_generic")
    p.add_argument("--backbone", default="o4-mini")
    p.add_argument("--models", nargs="+", default=["fake-a", "fake-b", "fake-c"])
    args = p.parse_args()

    tmp = tempfile.mkdtemp(prefix="implicit_eval_v2_smoketest_")
    real_root = ie.ROOT
    ie.ROOT = tmp
    ie.safe_judge_ollama = fake_safe_judge

    traj_subdir = ie.BACKBONE_DIR_MAP.get(args.backbone, "autogen_%s_processed" % args.backbone)
    src_traj = os.path.join(real_root, "trajectories", traj_subdir, args.domain)
    dst_traj = os.path.join(tmp, "trajectories", traj_subdir, args.domain)
    os.makedirs(os.path.dirname(dst_traj), exist_ok=True)
    shutil.copytree(src_traj, dst_traj)

    src_task = os.path.join(real_root, "tasks", "less_sensitive", "%s.json" % args.domain)
    dst_task = os.path.join(tmp, "tasks", "less_sensitive", "%s.json" % args.domain)
    os.makedirs(os.path.dirname(dst_task), exist_ok=True)
    shutil.copy2(src_task, dst_task)

    print("Running implicit_eval_autogen with fake Ollama judges...")
    ie.run(
        args.domain,
        args.backbone,
        models=args.models,
        limit_personas=1,
        limit_steps=2,
    )

    results_root = (
        "results_autogen_ollama_implicit"
        if args.backbone == "gpt-4o"
        else "results_autogen_ollama_implicit_%s" % args.backbone
    )
    out_path = os.path.join(tmp, results_root, args.domain, "jury_results_fixed.json")
    if not os.path.isfile(out_path):
        sys.exit("FAIL: expected output not produced at %s" % out_path)

    out = json.load(open(out_path))
    failures = []

    def check(cond, msg):
        print("[%s] %s" % ("PASS" if cond else "FAIL", msg))
        if not cond:
            failures.append(msg)

    check(out.get("method") == "implicit_only_ollama_n_model_weighted_average", "method tag is v2 Ollama implicit")
    check(out.get("judge_backend") == "ollama", "judge backend is ollama")
    check(len(out.get("judge_models", {})) == len(args.models), "all fake models registered")
    check(out["totals"]["jury"]["CE"] == 0 and out["totals"]["jury"]["BE"] == 0, "explicit categories zeroed")
    check(
        out["totals"]["jury"]["CI"] > 0 or out["totals"]["jury"]["BI"] > 0,
        "implicit CI or BI populated",
    )

    if failures:
        print("FAILED; temp output preserved: %s" % tmp)
        sys.exit(1)

    shutil.rmtree(tmp, ignore_errors=True)
    print("OK - implicit_eval_autogen v2 smoke test passed.")


if __name__ == "__main__":
    main()
