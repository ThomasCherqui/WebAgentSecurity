#!/usr/bin/env python3
"""Compare predictions CSV to golden dataset CSV/JSON.

This file was moved to tools/ during repo cleanup. It injects the
parent `scripts/` directory into sys.path so it can import the
compatibility shim `scripts/compute_score.py` if needed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict

import math
import csv
import sys

# ensure scripts/ directory is importable (for compute_score shim)
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.normpath(os.path.join(TOOLS_DIR, '..', 'scripts'))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    import pandas as pd
    import numpy as np
except Exception:
    pd = None
    np = None

# try to import sklearn metrics, but provide fallbacks when unavailable
try:
    from sklearn.metrics import precision_recall_fscore_support, confusion_matrix  # type: ignore
except Exception:
    precision_recall_fscore_support = None
    confusion_matrix = None


def _fallback_prf(y_true, y_pred):
    y_true = list(map(int, y_true))
    y_pred = list(map(int, y_pred))
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return prec, rec, f1, None


def load_df(path: str):
    if pd is None:
        raise RuntimeError('pandas required for this script')
    return pd.read_csv(path)


def safe_mkdir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)


def binarize_labels(df, prefix=''):
    # expects CE/CI/BE/BI columns as ints 0/1
    labels = ['CE', 'CI', 'BE', 'BI']
    present = [l for l in labels if l in df.columns]
    return df, present


def compare(pred_df, gold_df, outdir: str):
    safe_mkdir(outdir)
    # align rows by persona_id + step_number + file if present
    key_cols = [c for c in ('persona_id', 'file', 'step_number') if c in pred_df.columns and c in gold_df.columns]
    if not key_cols:
        # fallback: compare by index
        merged = pred_df.reset_index().merge(gold_df.reset_index(), left_index=True, right_index=True, suffixes=('_pred','_gold'))
    else:
        merged = pred_df.merge(gold_df, on=key_cols, suffixes=('_pred', '_gold'))

    labels = ['CE', 'CI', 'BE', 'BI']
    metrics = {}
    rows_out = []
    for l in labels:
        p_col = (l + '_pred') if (l + '_pred') in merged.columns else l
        g_col = (l + '_gold') if (l + '_gold') in merged.columns else l
        if p_col not in merged.columns or g_col not in merged.columns:
            continue
        y_pred = merged[p_col].fillna(0).astype(int)
        y_true = merged[g_col].fillna(0).astype(int)
        if precision_recall_fscore_support is None:
            # basic counts
            tp = int(((y_pred==1) & (y_true==1)).sum())
            fp = int(((y_pred==1) & (y_true==0)).sum())
            fn = int(((y_pred==0) & (y_true==1)).sum())
            prec = tp / (tp+fp) if (tp+fp)>0 else 0.0
            rec = tp / (tp+fn) if (tp+fn)>0 else 0.0
            f1 = 2*prec*rec/(prec+rec) if (prec+rec)>0 else 0.0
        else:
            prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary', zero_division=0)
        metrics[l] = {'precision': float(prec), 'recall': float(rec), 'f1': float(f1), 'support': int(y_true.sum())}

    # row-by-row diff and score correlation
    if 'score_pred' in merged.columns and 'score_gold' in merged.columns:
        # Pearson correlation
        try:
            corr = float(np.corrcoef(merged['score_pred'].fillna(0).astype(float), merged['score_gold'].fillna(0).astype(float))[0,1])
        except Exception:
            corr = None
    else:
        corr = None

    # write report
    report = {'metrics': metrics, 'score_correlation': corr, 'rows_compared': int(len(merged))}
    with open(os.path.join(outdir, 'report.json'), 'w') as f:
        json.dump(report, f, indent=2)

    # write merged sample CSV with key cols and prediction/ground truth
    sample_cols = key_cols + []
    for l in labels:
        p_col = (l + '_pred') if (l + '_pred') in merged.columns else l
        g_col = (l + '_gold') if (l + '_gold') in merged.columns else l
        if p_col in merged.columns:
            sample_cols.append(p_col)
        if g_col in merged.columns:
            sample_cols.append(g_col)
    if 'score_pred' in merged.columns:
        sample_cols.append('score_pred')
    if 'score_gold' in merged.columns:
        sample_cols.append('score_gold')

    sample_cols = [c for c in sample_cols if c in merged.columns]
    merged.to_csv(os.path.join(outdir, 'merged_comparison.csv'), columns=sample_cols, index=False)

    print('Wrote report to', outdir)
    print(json.dumps(report, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pred', required=True, help='Predictions CSV (output of trajectory_to_dataframe.py)')
    p.add_argument('--gold', required=True, help='Golden CSV/JSON with ground truth labels')
    p.add_argument('--outdir', default=os.path.join(os.path.dirname(__file__), '..', 'scored_test', 'compare_results'), help='Output directory for reports')
    args = p.parse_args()

    pred_df = load_df(args.pred)
    gold_df = load_df(args.gold)
    compare(pred_df, gold_df, args.outdir)


if __name__ == '__main__':
    main()
