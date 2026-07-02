#!/usr/bin/env python3
"""Orchestrator: run judge, build dataset, compare to golden, compare baseline.

Usage: edit the CONFIG below or run with --dry-run to print commands without executing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys


# ---- CONFIG: edit these paths/params as needed ----
CONFIG = {
    "domain": "shopping_Amazon_chat",
    "models": "qwen3.6:35b gemma4:31b nemotron-cascade-2:latest",
    "trajectories_dir": "llm_jury_eval_v3/trajectories/browseruse_gpt4o_parsed",
    "tasks_dir": "llm_jury_eval_v3/tasks/less_sensitive",
    "results_dir": "llm_jury_eval_v3/results_ollama/shopping_Amazon_chat",
    "limit_personas": 2,  # 0 means no limit
    "gold_csv": "llm_jury_eval_v3/golden_dataset_browseruse_o4_chat/trajectories_browseruser_gpt4o_enriched.csv",
    # baseline produced from existing_results
    "baseline_csv": "llm_jury_eval_v3/results_ollama/shopping_Amazon_chat/baseline_existing_results_shopping_Amazon_chat.csv",
}


def run_cmd(cmd, dry_run=False):
    print("\n>>", " ".join(cmd))
    if dry_run:
        return 0
    res = subprocess.run(cmd, check=False)
    return res.returncode


def main(dry_run: bool):
    repo_root = Path(__file__).resolve().parent.parent
    script_dir = Path(__file__).resolve().parent

    # Resolve config paths relative to repo root if not absolute
    def resolve(p):
        pp = Path(p)
        return pp if pp.is_absolute() else (repo_root / pp)

    trajectories_src = resolve(CONFIG.get("trajectories_dir"))
    tasks_dir = resolve(CONFIG.get("tasks_dir"))
    results_dir = resolve(CONFIG.get("results_dir"))
    gold_csv = resolve(CONFIG.get("gold_csv"))
    baseline_csv = resolve(CONFIG.get("baseline_csv"))

    domain = CONFIG.get("domain")

    # parse models: accept comma/space-separated string or list
    raw_models = CONFIG.get("models")
    if isinstance(raw_models, str):
        models = [m.strip() for part in raw_models.split() for m in part.split(",") if m.strip()]
    elif isinstance(raw_models, (list, tuple)):
        models = list(raw_models)
    else:
        models = []

    judge_script = script_dir / "scripts" / "llm_jury_browseruse_reliance_reduced.py"
    exporter = script_dir / "tools" / "trajectory_to_dataframe.py"
    compare_script = script_dir / "scripts" / "compare_predictions_to_golden.py"

    # If trajectories_src doesn't contain domain subfolder but contains persona jsons,
    # create a temporary dir with the expected structure <tmp>/<domain> and symlink files.
    tmp_dir = None
    trajectories_to_pass = None
    try:
        expected = trajectories_src / domain
        if expected.exists() and expected.is_dir():
            trajectories_to_pass = str(trajectories_src)
        else:
            # check if trajectories_src has JSON persona files
            if trajectories_src.exists() and any(str(f).endswith('.json') for f in trajectories_src.iterdir()):
                import tempfile, shutil
                tmp_dir = Path(tempfile.mkdtemp(prefix=f"traj_for_{domain}_"))
                dest = tmp_dir / domain
                dest.mkdir(parents=True, exist_ok=True)
                # symlink or copy
                for f in trajectories_src.iterdir():
                    if f.is_file() and f.suffix == '.json':
                        try:
                            (dest / f.name).symlink_to(f.resolve())
                        except Exception:
                            shutil.copy(f, dest / f.name)
                trajectories_to_pass = str(tmp_dir)
                print(f"Created temporary trajectories folder {tmp_dir} with domain subfolder for judge")
            else:
                # No suitable trajectories; fallback to original path (will likely error)
                trajectories_to_pass = str(trajectories_src)

        # Run judge (single run over models string joined) — pass models as separate args
        judge_cmd = [sys.executable, str(judge_script), "--domain", domain]
        if models:
            judge_cmd += ["--models"] + models
        judge_cmd += ["--trajectories-dir", trajectories_to_pass, "--tasks-dir", str(tasks_dir)]
        if CONFIG.get("limit_personas") and CONFIG["limit_personas"] > 0:
            judge_cmd += ["--limit-personas", str(CONFIG["limit_personas"])]

        print("STEP 1: running judge (may take long)\n")
        rc = run_cmd(judge_cmd, dry_run=dry_run)
        if rc != 0 and not dry_run:
            print("Judge failed (rc=%s), continuing but outputs may be incomplete" % rc)

        # 2) build dataset from results (export trajectories -> CSV)
        pred_csv = results_dir / f"trajectories_{Path(trajectories_src).name}.csv"
        exporter_cmd = [sys.executable, str(exporter), "--input", str(results_dir), "--output", str(pred_csv)]
        print("STEP 2: building predictions CSV from results\n")
        rc = run_cmd(exporter_cmd, dry_run=dry_run)
        if rc != 0 and not dry_run:
            print("Exporter failed (rc=%s)" % rc)

        # 3) compare predictions -> gold
        compare_outdir = results_dir / "compare_results"
        compare_cmd = [sys.executable, str(compare_script), "--pred", str(pred_csv), "--gold", str(gold_csv), "--outdir", str(compare_outdir)]
        print("STEP 3: comparing predictions to golden\n")
        rc = run_cmd(compare_cmd, dry_run=dry_run)
        if rc != 0 and not dry_run:
            print("Compare (pred vs gold) failed (rc=%s)" % rc)

        # 4) compare baseline -> gold
        compare_outdir_baseline = results_dir / "compare_results_baseline_cs"
        compare_baseline_cmd = [sys.executable, str(compare_script), "--pred", str(baseline_csv), "--gold", str(gold_csv), "--outdir", str(compare_outdir_baseline)]
        print("STEP 4: comparing baseline to golden\n")
        rc = run_cmd(compare_baseline_cmd, dry_run=dry_run)
        if rc != 0 and not dry_run:
            print("Compare (baseline vs gold) failed (rc=%s)" % rc)

        # 5) diff the two reports (report.json files)
        report1 = compare_outdir / "report.json"
        report2 = compare_outdir_baseline / "report.json"
        print("STEP 5: diffing metric reports (predictions vs baseline)\n")
        if dry_run:
            print(f"Would diff {report1} vs {report2}")
            return

        try:
            r1 = json.load(open(report1)) if report1.exists() else None
            r2 = json.load(open(report2)) if report2.exists() else None
        except Exception as e:
            print('Could not read report.json:', e)
            return

        # simple diff summary
        summary = {"domain": domain}
        if r1 is None:
            summary["pred_vs_gold"] = "missing"
        else:
            summary["pred_vs_gold"] = {"rows_compared": r1.get("rows_compared"), "score_correlation": r1.get("score_correlation"), "metrics": {k: v.get("f1") for k, v in r1.get("metrics", {}).items()}}
        if r2 is None:
            summary["baseline_vs_gold"] = "missing"
        else:
            summary["baseline_vs_gold"] = {"rows_compared": r2.get("rows_compared"), "score_correlation": r2.get("score_correlation"), "metrics": {k: v.get("f1") for k, v in r2.get("metrics", {}).items()}}

        # compute simple deltas if both present
        if r1 and r2:
            deltas = {}
            for k in set(r1.get("metrics", {}).keys()) | set(r2.get("metrics", {}).keys()):
                f1_1 = r1.get("metrics", {}).get(k, {}).get("f1")
                f1_2 = r2.get("metrics", {}).get(k, {}).get("f1")
                try:
                    deltas[k] = (float(f1_1 or 0) - float(f1_2 or 0))
                except Exception:
                    deltas[k] = None
            summary["f1_delta_pred_minus_baseline"] = deltas

        out_summary = results_dir / "comparison_summary.json"
        json.dump(summary, open(out_summary, "w"), indent=2)
        print("Wrote summary to", out_summary)
    finally:
        # cleanup temp dir if created
        if 'tmp_dir' in locals() and tmp_dir and tmp_dir.exists():
            try:
                import shutil
                shutil.rmtree(tmp_dir)
                print(f"Removed temporary trajectories folder {tmp_dir}")
            except Exception:
                pass


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = p.parse_args()
    main(dry_run=args.dry_run)
