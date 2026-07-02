#!/usr/bin/env python3
"""
Read Ollama result JSON files (per-persona) and compute oversharing scores
per step using the existing compute_score module. Writes per-persona score
JSON files and prints summaries.

This is the tools/ copy used in the cleaned layout.
"""
from __future__ import annotations

import argparse
import json
import os
import glob
from typing import Dict, Any

import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from compute_score import score_event, aggregate_scores


def read_persona_file(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        return json.load(f)


def extract_verdict_from_step(step: Dict[str, Any]) -> Dict[str, int]:
    # Prefer 'jury_verdict' if present
    if 'jury_verdict' in step and isinstance(step['jury_verdict'], dict):
        return {k: int(step['jury_verdict'].get(k, 0)) for k in ('CE', 'CI', 'BE', 'BI')}
    # Fallback: sum judge individual 'violations' dicts if available
    counts = {'CE': 0, 'CI': 0, 'BE': 0, 'BI': 0}
    for k, v in step.items():
        if k.startswith('judge_') and isinstance(v, dict):
            viol = v.get('violations')
            if isinstance(viol, dict):
                for c in counts:
                    counts[c] += int(viol.get(c, 0))
    return counts


def process_file(path: str, sensitivity: str, necessity: str, aggregate_method: str, out_dir: str):
    data = read_persona_file(path)
    steps = [k for k in data.keys() if k.lower().startswith('step')]
    steps = sorted(steps, key=lambda s: int(''.join(filter(str.isdigit, s)) or 0))

    per_step_scores = {}
    scores_list = []

    for s in steps:
        step = data[s]
        verdict = extract_verdict_from_step(step)
        sc = score_event(verdict, sensitivity, necessity)
        per_step_scores[s] = {
            'verdict': verdict,
            'score': sc,
        }
        scores_list.append(sc)

    agg = aggregate_scores(scores_list, aggregate_method)

    out = {
        'persona_file': os.path.basename(path),
        'num_steps': len(steps),
        'per_step': per_step_scores,
        'scores': scores_list,
        'aggregate': agg,
        'sensitivity': sensitivity,
        'necessity': necessity,
        'aggregate_method': aggregate_method,
    }

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.basename(path) + '.scores.json')
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)

    print(f"Processed {path}: steps={len(steps)} aggregate={agg:.3f} -> {out_path}")
    return out_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True, help='Path to a persona JSON file or a directory of persona files')
    p.add_argument('--sensitivity', default='medium', help='Attribute sensitivity (low|medium|high or numeric)')
    p.add_argument('--necessity', default='irrelevant', help='Necessity label')
    p.add_argument('--aggregate', default='sum', choices=('sum', 'mean', 'max'))
    p.add_argument('--out-dir', default='scored_results', help='Directory to write per-persona score outputs')
    args = p.parse_args()

    paths = []
    if os.path.isdir(args.input):
        paths = glob.glob(os.path.join(args.input, '*.json'))
    elif os.path.isfile(args.input):
        paths = [args.input]
    else:
        raise SystemExit(f'Input not found: {args.input}')

    for pth in paths:
        process_file(pth, args.sensitivity, args.necessity, args.aggregate, args.out_dir)


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""Tools shim for score_ollama_results: keeps compatibility with scripts/ imports.
"""
from __future__ import annotations
import sys
import os
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.normpath(os.path.join(TOOLS_DIR, '..', 'scripts'))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from score_ollama_results import *
