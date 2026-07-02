#!/usr/bin/env python3
"""
Tools copy of trajectory_to_dataframe.py — builds a CSV DataFrame from trajectory or Ollama result JSON files.

This file is intended to live in `tools/` for analysis utilities. It mirrors the behavior
of the scripts version and can be executed directly.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
from typing import Any, Dict, List
import sys
# ensure tools dir on path so compute_score shim (scripts/) can be imported if needed
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
try:
    from compute_score import score_event, normalize_sensitivity, normalize_necessity
except Exception:
    def score_event(verdict, attribute_sensitivity, necessity_label):
        return 0.0
    def normalize_sensitivity(s):
        return s
    def normalize_necessity(n):
        return n


def read_json(path: str) -> Dict[str, Any]:
    with open(path, 'r') as f:
        return json.load(f)


def is_trajectory(data: Dict[str, Any]) -> bool:
    return isinstance(data.get('steps'), list)


def is_ollama_result(data: Dict[str, Any]) -> bool:
    # Ollama result files have keys like 'Step 1', 'Step 2' and nested dicts
    return any(k.lower().startswith('step') for k in data.keys())


def normalize_bool(s: Any) -> str:
    if isinstance(s, bool):
        return 'yes' if s else 'no'
    if s is None:
        return ''
    st = str(s).strip().lower()
    if st in ('yes', 'y', 'true', '1'):
        return 'yes'
    if st in ('no', 'n', 'false', '0'):
        return 'no'
    return st


def process_trajectory(path: str, data: Dict[str, Any], persona_lookup: Dict[str, Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    rows = []
    header = data.get('header', {})
    # try header test_id, then filename pattern persona_<id>_<name>_parsed(.json|_annotated.json), else basename
    persona_id = header.get('test_id')
    persona_name = ''
    basename = os.path.basename(path)
    if not persona_id:
        m = re.search(r"persona_(\d+)_(.*?)_parsed(?:_annotated)?\.json", basename)
        if m:
            persona_id = int(m.group(1))
            persona_name = m.group(2).replace('_', ' ')
        else:
            persona_id = os.path.splitext(basename)[0]
    else:
        persona_name = str(header.get('name') or '')
    steps = data.get('steps', [])
    for step in steps:
        step_number = step.get('step_number')
        action = step.get('action', '')
        evaluation = step.get('evaluation', '')
        memory_update = step.get('memory_update', '')
        next_goal = step.get('next_goal', '')
        combined = ' '.join([str(x).strip() for x in (action, evaluation, memory_update, next_goal) if x])
        ann = step.get('annotation', {}) or {}
        row = {
            'persona_id': persona_id,
            'persona_name': persona_name,
            'file': os.path.basename(path),
            'step_number': step_number,
            'action': action,
            'evaluation': evaluation,
            'memory_update': memory_update,
            'next_goal': next_goal,
            'combined_text': combined,
            # persona-level fields (from tasks persona entry)
            'persona_task': '',
            'relevant_attributes': '',
            'irrelevant_attributes': '',
            'is_oversharing': ann.get('is_oversharing', ''),
            'attribute_used': ann.get('attribute_used', ''),
            'attribute_relevance': ann.get('attribute_relevance', ''),
            'sensitivity': ann.get('sensitivity', ''),
            'category_annotation': ann.get('category', ''),
            'exposure': ann.get('exposure', ''),
            'severity_human': ann.get('severity_human', ''),
            'evidence_annotation': ann.get('evidence', ''),
            'confidence': ann.get('confidence', ''),
            'CE': 0, 'CI': 0, 'BE': 0, 'BI': 0, 'jury_present': False,
            'score': '',
            'verdict_source': '',
        }
        verdict = {'CE': 0, 'CI': 0, 'BE': 0, 'BI': 0}
        if row['category_annotation'] and isinstance(row['category_annotation'], str):
            cat = row['category_annotation'].strip().upper()
            for label in ('CE', 'CI', 'BE', 'BI'):
                if label in cat:
                    verdict[label] = 1
                    row['verdict_source'] = 'annotation'
                    break
        for lab in ('CE', 'CI', 'BE', 'BI'):
            row[lab] = int(verdict.get(lab, 0) or 0)
        sens = row.get('sensitivity', '')
        nec = row.get('attribute_relevance', '')
        try:
            sc = score_event(verdict, sens or 'medium', nec or 'irrelevant')
        except Exception:
            sc = 0.0
        row['score'] = sc
        # enrich with persona-level info if available
        try:
            if persona_lookup is not None:
                lookup_key = None
                # try by id
                if isinstance(persona_id, int) or (isinstance(persona_id, str) and persona_id.isdigit()):
                    lookup_key = str(persona_id)
                # else try by name
                if lookup_key not in persona_lookup and persona_name:
                    lookup_key = persona_name
                pinfo = persona_lookup.get(lookup_key) if lookup_key is not None else None
                if pinfo:
                    row['persona_task'] = pinfo.get('task', '')
                    row['relevant_attributes'] = ', '.join(pinfo.get('relevant_attributes', []) or [])
                    row['irrelevant_attributes'] = ', '.join(pinfo.get('irrelevant_attributes', []) or [])
                    # prefer canonical name
                    if not row.get('persona_name'):
                        row['persona_name'] = pinfo.get('name', '')
        except Exception:
            pass
        rows.append(row)
    return rows


def process_ollama_result(path: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    persona = os.path.splitext(os.path.basename(path))[0]
    steps = sorted([k for k in data.keys() if k.lower().startswith('step')], key=lambda s: int(''.join(filter(str.isdigit, s)) or 0))
    for s in steps:
        step = data[s]
        verdict = step.get('jury_verdict') or {}
        row = {
            'persona_id': persona,
            'file': os.path.basename(path),
            'step_number': s,
            'action': '', 'evaluation': '', 'memory_update': '', 'next_goal': '',
            'combined_text': '',
            'is_oversharing': '',
            'attribute_used': '',
            'attribute_relevance': '',
            'sensitivity': '',
            'category_annotation': '',
            'exposure': '',
            'severity_human': '',
            'evidence_annotation': '',
            'confidence': '',
            'CE': 0, 'CI': 0, 'BE': 0, 'BI': 0,
            'jury_present': True,
            'score': '',
            'verdict_source': 'jury',
        }
        try:
            for lab in ('CE', 'CI', 'BE', 'BI'):
                try:
                    row[lab] = int(verdict.get(lab, 0) or 0)
                except Exception:
                    v = verdict.get(lab, '')
                    row[lab] = 1 if str(v).strip().lower() in ('1', 'true', 'yes') else 0
        except Exception:
            pass
        try:
            sc = score_event({'CE': int(row['CE']), 'CI': int(row['CI']), 'BE': int(row['BE']), 'BI': int(row['BI'])}, row.get('sensitivity','medium'), row.get('attribute_relevance','irrelevant'))
        except Exception:
            try:
                sc = score_event({'CE': int(verdict.get('CE',0) or 0), 'CI': int(verdict.get('CI',0) or 0), 'BE': int(verdict.get('BE',0) or 0), 'BI': int(verdict.get('BI',0) or 0)}, 'medium', 'irrelevant')
            except Exception:
                sc = 0.0
        row['score'] = sc
        rows.append(row)
    return rows


def collect_paths(input_path: str) -> List[str]:
    # tolerate surrounding quotes accidentally included in the argument
    if isinstance(input_path, str):
        input_path = input_path.strip()
        if (input_path.startswith('"') and input_path.endswith('"')) or (input_path.startswith("'") and input_path.endswith("'")):
            input_path = input_path[1:-1]
    if os.path.isdir(input_path):
        return sorted(glob.glob(os.path.join(input_path, '*.json')))
    if os.path.isfile(input_path):
        return [input_path]
    return sorted(glob.glob(input_path))


def main():
    p = argparse.ArgumentParser()
    default_input = os.path.join(os.path.dirname(__file__), '..', 'trajectories', 'browseruser_gpt4o_enriched')
    default_input = os.path.normpath(default_input)
    default_output_dir = os.path.join(os.path.dirname(__file__), '..', 'golden_dataset_browseruse_o4_chat')
    os.makedirs(default_output_dir, exist_ok=True)
    default_output = os.path.join(default_output_dir, 'trajectories_browseruser_gpt4o_enriched.csv')
    p.add_argument('--input', dest='input', default=default_input, help=f'File, directory or glob pattern of JSON files (default: {default_input})')
    p.add_argument('--domain', dest='domain', default=None, help='Optional domain name to locate persona file in tasks dir (e.g. shopping_Amazon_chat)')
    p.add_argument('--tasks-dir', dest='tasks_dir', default=os.path.join(os.path.dirname(__file__), '..', 'tasks', 'less_sensitive'), help='Directory containing persona task JSONs')
    p.add_argument('--input-dir', dest='input', help=argparse.SUPPRESS)
    p.add_argument('--output', default=default_output, help=f'Output CSV path (default: {default_output})')
    args = p.parse_args()

    paths = collect_paths(args.input)
    if not paths:
        raise SystemExit('No files found for: %s' % args.input)

    # load persona lookup if possible
    persona_lookup: Dict[str, Dict[str, Any]] | None = None
    if args.domain:
        persona_file = os.path.join(args.tasks_dir, f"{args.domain}.json")
        try:
            with open(persona_file) as pf:
                pdata = json.load(pf)
                persona_lookup = {}
                for p in pdata.get('personas', []):
                    key_id = str(p.get('id'))
                    persona_lookup[key_id] = p
                    if p.get('name'):
                        persona_lookup[str(p.get('name'))] = p
        except Exception:
            persona_lookup = None

    rows: List[Dict[str, Any]] = []
    for path in paths:
        try:
            data = read_json(path)
        except Exception as e:
            print('Skipping', path, 'read error:', e)
            continue
        if is_trajectory(data):
            rows.extend(process_trajectory(path, data, persona_lookup=persona_lookup))
        elif is_ollama_result(data):
            rows.extend(process_ollama_result(path, data))
        else:
            print('Unrecognized file format, skipping:', path)

    if not rows:
        print('No rows extracted.')
        return
    fieldnames = [
        'persona_id', 'persona_name', 'persona_task', 'file', 'step_number', 'action', 'evaluation', 'memory_update', 'next_goal', 'combined_text',
        'relevant_attributes', 'irrelevant_attributes',
        'is_oversharing', 'attribute_used', 'attribute_relevance', 'sensitivity', 'category_annotation', 'exposure',
        'severity_human', 'evidence_annotation', 'confidence', 'CE', 'CI', 'BE', 'BI', 'jury_present'
    ]
    if 'score' not in fieldnames:
        fieldnames.append('score')
    if 'verdict_source' not in fieldnames:
        fieldnames.append('verdict_source')
    with open(args.output, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            out = {k: r.get(k, '') for k in fieldnames}
            w.writerow(out)

    print('Wrote', len(rows), 'rows to', args.output)


if __name__ == '__main__':
    main()

