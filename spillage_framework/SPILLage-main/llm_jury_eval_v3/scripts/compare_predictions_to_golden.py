#!/usr/bin/env python3
"""Compare predictions CSV to golden dataset CSV/JSON.

Outputs:
 - JSON report with per-label precision/recall/F1
 - CSV with row-by-row comparison and flags indicating matches
 - prints brief summary

Usage:
  python compare_predictions_to_golden.py --pred predictions.csv --gold golden.csv --outdir ./scored_test/compare_results
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict

import math
import csv

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
    # y_true and y_pred are array-like of 0/1
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
    # Normalize key columns to avoid dtype mismatches (e.g., 'Step 1' vs 1)
    if key_cols:
        # normalize step_number to integer-like where possible
        if 'step_number' in key_cols:
            for df in (pred_df, gold_df):
                try:
                    # extract digits if values like 'Step 1' exist, else coerce to numeric
                    if 'step_number' in df.columns:
                        # convert to string, extract first integer group
                        df['step_number'] = df['step_number'].astype(str).str.extract(r"(\d+)")[0]
                        df['step_number'] = pd.to_numeric(df['step_number'], errors='coerce').astype('Int64')
                except Exception:
                    # leave as-is if anything goes wrong
                    pass
        # for any remaining key columns, stringify to ensure mergeability
        for c in key_cols:
            if c in pred_df.columns:
                pred_df[c] = pred_df[c].astype(str)
            if c in gold_df.columns:
                gold_df[c] = gold_df[c].astype(str)
        # attempt progressive merges: full key set, then drop 'file', then drop 'step_number', then only persona_id
        def try_merge(cols):
            try:
                m = pred_df.merge(gold_df, on=cols, suffixes=('_pred', '_gold'))
                return m
            except Exception:
                return pd.DataFrame()

        merged = try_merge(key_cols)
        tried = [list(key_cols)]
        if merged.empty:
            if 'file' in key_cols:
                cols = [c for c in key_cols if c != 'file']
                merged = try_merge(cols)
                tried.append(cols)
        if merged.empty:
            if 'step_number' in key_cols:
                cols = [c for c in key_cols if c != 'step_number']
                merged = try_merge(cols)
                tried.append(cols)
        if merged.empty:
            if 'persona_id' in key_cols:
                cols = ['persona_id']
                merged = try_merge(cols)
                tried.append(cols)
        if merged.empty:
            # final fallback: merge by index
            merged = pred_df.reset_index().merge(gold_df.reset_index(), left_index=True, right_index=True, suffixes=('_pred','_gold'))
            tried.append(['index'])
        print('Tried merge key sets (in order):', tried)
    else:
        # fallback: compare by index
        merged = pred_df.reset_index().merge(gold_df.reset_index(), left_index=True, right_index=True, suffixes=('_pred','_gold'))

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
