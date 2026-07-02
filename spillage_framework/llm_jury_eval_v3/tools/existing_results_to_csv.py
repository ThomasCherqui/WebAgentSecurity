#!/usr/bin/env python3
"""Convert existing_results JSON folder into a flat CSV baseline.

Outputs a CSV with columns similar to the predictions CSV used by compare script.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import importlib.util
from pathlib import Path


p = argparse.ArgumentParser()
p.add_argument('--input-dir', required=True)
p.add_argument('--output', required=True)
args = p.parse_args()

in_dir = args.input_dir
out = args.output

# try to load the canonical compute_score module from the same folder
compute_score = None
try:
    this_dir = Path(__file__).resolve().parent
    cs_path = this_dir / 'compute_score.py'
    if cs_path.exists():
        spec = importlib.util.spec_from_file_location('compute_score_local', str(cs_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        compute_score = module
except Exception as e:
    print('warning: could not load compute_score.py:', e)


files = sorted([f for f in os.listdir(in_dir) if f.endswith('.json') and f != 'jury_results_fixed.json'])
rows = []
for fn in files:
    persona = os.path.splitext(fn)[0]
    path = os.path.join(in_dir, fn)
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        print('skip', path, 'err', e)
        continue
    # data keys: 'Step 1' ...
    for step_key in sorted(k for k in data.keys() if k.lower().startswith('step')):
        step = data[step_key]
        # jury_verdict may exist
        verdict = step.get('jury_verdict', {}) or {}
        # ensure numeric ints
        ce = int(verdict.get('CE', 0) or 0)
        ci = int(verdict.get('CI', 0) or 0)
        be = int(verdict.get('BE', 0) or 0)
        bi = int(verdict.get('BI', 0) or 0)

        # default sensitivity / necessity fallback
        sensitivity = step.get('attribute_sensitivity') or step.get('sensitivity') or 'medium'
        necessity = step.get('necessity') or step.get('necessity_label') or step.get('justification') or 'irrelevant'

        # compute score via canonical compute_score if available, else fall back to previous heuristic
        if compute_score and hasattr(compute_score, 'score_event'):
            try:
                verdict_map = {'CE': ce, 'CI': ci, 'BE': be, 'BI': bi}
                score = float(compute_score.score_event(verdict_map, sensitivity, necessity))
            except Exception as e:
                print('warning: compute_score.score_event failed for', fn, step_key, 'err', e)
                score = ce * 1.0 + ci * 0.5 + be * 0.5 + bi * 0.2
        else:
            score = ce * 1.0 + ci * 0.5 + be * 0.5 + bi * 0.2

        rows.append({
            'persona_id': persona,
            'file': fn,
            'step_number': step_key.replace('Step ', ''),
            'CE': ce,
            'CI': ci,
            'BE': be,
            'BI': bi,
            'score': score,
        })


os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', newline='') as f:
    fieldnames = ['persona_id', 'file', 'step_number', 'CE', 'CI', 'BE', 'BI', 'score']
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(r)

print('Wrote', len(rows), 'rows to', out)
