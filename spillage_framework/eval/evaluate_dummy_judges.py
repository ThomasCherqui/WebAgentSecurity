#!/usr/bin/env python3
"""Evaluate jury predictions against the SPILLage golden results.

The golden labels are built from:
  jury_step_by_step/0_jury_baseline_Spillage/existing_results

The predictions are read from:
  jury_step_by_step/jury_baseline_dummy_one_judge/results_ollama

Matching is exact on:
  task + normalized persona name + normalized step number

Outputs:
  - golden/golden_<task>.csv
  - golden/golden_all.csv
  - comparisons/<task>/<model>/matched_rows.csv
  - comparisons/<task>/<model>/unmatched_gold.csv
  - comparisons/<task>/<model>/unmatched_predictions.csv
  - metrics_by_label.csv
  - metrics_macro.csv
  - metrics_by_model.csv
  - report.md
  - report.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


LABELS = ("CE", "BE", "CI", "BI")
GOLD_TASK_PREFIX = "browseruse_"


@dataclass(frozen=True)
class RowKey:
    task: str
    persona: str
    step: int


def normalize_task(name: str) -> str:
    """Normalize task names across golden and prediction folders."""
    name = str(name).strip()
    if name.startswith(GOLD_TASK_PREFIX):
        name = name[len(GOLD_TASK_PREFIX) :]
    return name


def normalize_persona(name: Any) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip())


def normalize_step(step: Any) -> int:
    match = re.search(r"\d+", str(step or ""))
    if not match:
        raise ValueError(f"Could not parse step number from {step!r}")
    return int(match.group(0))


def to_binary(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if value is None:
        return 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return 1
    if text in {"0", "false", "no", "n", ""}:
        return 0
    try:
        return 1 if int(float(text)) != 0 else 0
    except ValueError:
        return 0


def safe_model_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "model"


def read_json(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_json_files(path: Path) -> Iterable[Path]:
    return sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".json")


def make_key(row: Mapping[str, Any]) -> RowKey:
    return RowKey(
        task=normalize_task(str(row["task"])),
        persona=normalize_persona(row["persona"]),
        step=normalize_step(row["step"]),
    )


def extract_verdict(step_payload: Mapping[str, Any]) -> Dict[str, int]:
    verdict = step_payload.get("jury_verdict") or {}
    return {label: to_binary(verdict.get(label, 0)) for label in LABELS}


def build_golden_rows(gold_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for task_dir in sorted(p for p in gold_root.iterdir() if p.is_dir()):
        task = normalize_task(task_dir.name)
        for path in iter_json_files(task_dir):
            if path.name == "jury_results_fixed.json":
                continue
            persona = normalize_persona(path.stem)
            data = read_json(path)
            step_names = sorted(
                (name for name in data if str(name).lower().startswith("step")),
                key=normalize_step,
            )
            for step_name in step_names:
                step_payload = data.get(step_name) or {}
                if not isinstance(step_payload, Mapping):
                    continue
                row: Dict[str, Any] = {
                    "task": task,
                    "gold_task_dir": task_dir.name,
                    "persona": persona,
                    "step": normalize_step(step_name),
                    "gold_file": path.name,
                }
                row.update(extract_verdict(step_payload))
                rows.append(row)
    return rows


def read_prediction_rows(pred_root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for pred_path in sorted(pred_root.rglob("predictions.csv")):
        rel_parts = pred_path.relative_to(pred_root).parts
        if len(rel_parts) < 2:
            continue
        path_task = normalize_task(rel_parts[0])
        path_model = "/".join(rel_parts[1:-1]) or pred_path.parent.name
        with pred_path.open(newline="", encoding="utf-8") as f:
            for raw in csv.DictReader(f):
                task = normalize_task(raw.get("domain") or path_task)
                reported_model = (
                    raw.get("model")
                    or raw.get("candidate_models")
                    or raw.get("chairman_model")
                    or ""
                )
                row: Dict[str, Any] = {
                    "task": task,
                    "model": path_model,
                    "reported_model": reported_model,
                    "prompt_slug": raw.get("prompt_slug", ""),
                    "persona": normalize_persona(raw.get("persona", "")),
                    "step": normalize_step(raw.get("step", "")),
                    "prediction_file": str(pred_path),
                    "response": raw.get("response", ""),
                    "combined_text": raw.get("combined_text") or raw.get("trajectory_step", ""),
                }
                for label in LABELS:
                    row[label] = to_binary(raw.get(label, 0))
                rows.append(row)
    return rows


def ensure_unique(rows: Sequence[Mapping[str, Any]], source: str) -> Dict[RowKey, Mapping[str, Any]]:
    indexed: Dict[RowKey, Mapping[str, Any]] = {}
    duplicates: List[RowKey] = []
    for row in rows:
        key = make_key(row)
        if key in indexed:
            duplicates.append(key)
        indexed[key] = row
    if duplicates:
        sample = ", ".join(f"{k.task}/{k.persona}/step {k.step}" for k in duplicates[:5])
        raise ValueError(f"Duplicate {source} rows for matching key(s): {sample}")
    return indexed


def confusion_counts(y_true: Sequence[int], y_pred: Sequence[int]) -> Dict[str, int]:
    tp = sum(1 for g, p in zip(y_true, y_pred) if g == 1 and p == 1)
    tn = sum(1 for g, p in zip(y_true, y_pred) if g == 0 and p == 0)
    fp = sum(1 for g, p in zip(y_true, y_pred) if g == 0 and p == 1)
    fn = sum(1 for g, p in zip(y_true, y_pred) if g == 1 and p == 0)
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def metrics_from_counts(counts: Mapping[str, int]) -> Dict[str, float]:
    tp = counts["tp"]
    tn = counts["tn"]
    fp = counts["fp"]
    fn = counts["fn"]
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    return {
        "accuracy": safe_div(tp + tn, tp + tn + fp + fn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": float(tp + fn),
        "predicted_positive": float(tp + fp),
        "tp": float(tp),
        "tn": float(tn),
        "fp": float(fp),
        "fn": float(fn),
    }


def evaluate_pair(
    task: str,
    model: str,
    gold_rows: Sequence[Mapping[str, Any]],
    pred_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    gold_by_key = ensure_unique(gold_rows, f"gold {task}")
    pred_by_key = ensure_unique(pred_rows, f"predictions {task}/{model}")
    common_keys = sorted(set(gold_by_key) & set(pred_by_key), key=lambda k: (k.persona, k.step))

    matched: List[Dict[str, Any]] = []
    for key in common_keys:
        gold = gold_by_key[key]
        pred = pred_by_key[key]
        row: Dict[str, Any] = {
            "task": task,
            "model": model,
            "reported_model": pred.get("reported_model", ""),
            "prompt_slug": pred.get("prompt_slug", ""),
            "persona": key.persona,
            "step": key.step,
        }
        exact = True
        for label in LABELS:
            gold_value = int(gold[label])
            pred_value = int(pred[label])
            row[f"{label}_gold"] = gold_value
            row[f"{label}_pred"] = pred_value
            row[f"{label}_match"] = int(gold_value == pred_value)
            exact = exact and gold_value == pred_value
        row["exact_labelset_match"] = int(exact)
        matched.append(row)

    by_label: List[Dict[str, Any]] = []
    for label in LABELS:
        y_true = [int(row[f"{label}_gold"]) for row in matched]
        y_pred = [int(row[f"{label}_pred"]) for row in matched]
        values = metrics_from_counts(confusion_counts(y_true, y_pred))
        by_label.append({"task": task, "model": model, "label": label, "rows_compared": len(matched), **values})

    macro = {
        metric: safe_div(sum(float(row[metric]) for row in by_label), len(by_label))
        for metric in ("accuracy", "precision", "recall", "f1")
    }
    macro_row: Dict[str, Any] = {
        "task": task,
        "model": model,
        "rows_compared": len(matched),
        "gold_rows": len(gold_rows),
        "prediction_rows": len(pred_rows),
        "unmatched_gold_rows": len(set(gold_by_key) - set(pred_by_key)),
        "unmatched_prediction_rows": len(set(pred_by_key) - set(gold_by_key)),
        "exact_labelset_accuracy": safe_div(sum(row["exact_labelset_match"] for row in matched), len(matched)),
        **{f"macro_{k}": v for k, v in macro.items()},
    }

    unmatched_gold = [dict(gold_by_key[key]) for key in sorted(set(gold_by_key) - set(pred_by_key), key=lambda k: (k.persona, k.step))]
    unmatched_pred = [dict(pred_by_key[key]) for key in sorted(set(pred_by_key) - set(gold_by_key), key=lambda k: (k.persona, k.step))]
    return matched, by_label, [macro_row], unmatched_gold, unmatched_pred


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: List[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: Any) -> str:
    return f"{float(value) * 100:5.1f}%"


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    text_rows = [[str(cell) for cell in row] for row in rows]
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in text_rows)) if text_rows else len(headers[i])
        for i in range(len(headers))
    ]
    header = "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |"
    sep = "| " + " | ".join("-" * widths[i] for i in range(len(headers))) + " |"
    body = ["| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |" for row in text_rows]
    return "\n".join([header, sep, *body])


def aggregate_model_metrics(macro_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in macro_rows:
        grouped[str(row["model"])].append(row)

    aggregate_rows: List[Dict[str, Any]] = []
    for model, rows in grouped.items():
        total_matched = sum(int(row["rows_compared"]) for row in rows)
        total_gold = sum(int(row["gold_rows"]) for row in rows)
        total_pred = sum(int(row["prediction_rows"]) for row in rows)
        total_gold_only = sum(int(row["unmatched_gold_rows"]) for row in rows)
        total_pred_only = sum(int(row["unmatched_prediction_rows"]) for row in rows)

        def weighted(metric: str) -> float:
            return safe_div(
                sum(float(row[metric]) * int(row["rows_compared"]) for row in rows),
                total_matched,
            )

        aggregate_rows.append(
            {
                "rank": 0,
                "model": model,
                "tasks": len(rows),
                "rows_compared": total_matched,
                "gold_rows": total_gold,
                "prediction_rows": total_pred,
                "coverage": safe_div(total_matched, total_gold),
                "unmatched_gold_rows": total_gold_only,
                "unmatched_prediction_rows": total_pred_only,
                "weighted_macro_accuracy": weighted("macro_accuracy"),
                "weighted_macro_precision": weighted("macro_precision"),
                "weighted_macro_recall": weighted("macro_recall"),
                "weighted_macro_f1": weighted("macro_f1"),
                "weighted_exact_labelset_accuracy": weighted("exact_labelset_accuracy"),
            }
        )

    aggregate_rows.sort(
        key=lambda row: (
            float(row["weighted_macro_f1"]),
            float(row["weighted_macro_recall"]),
            float(row["weighted_macro_precision"]),
            float(row["weighted_exact_labelset_accuracy"]),
            float(row["coverage"]),
        ),
        reverse=True,
    )
    for index, row in enumerate(aggregate_rows, start=1):
        row["rank"] = index
    return aggregate_rows


def build_report(
    macro_rows: Sequence[Mapping[str, Any]],
    label_rows: Sequence[Mapping[str, Any]],
    model_rows: Sequence[Mapping[str, Any]],
    output_dir: Path,
    gold_root: Path,
    pred_root: Path,
) -> str:
    lines = [
        "# Jury Evaluation",
        "",
        "## Matching",
        "",
        "Golden rows are built from `jury_verdict` in the existing-results JSON files.",
        "Prediction rows are read from each `predictions.csv`.",
        "Rows are matched exactly on `(task, persona, step)` after these normalizations:",
        "",
        "- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;",
        "- persona names are trimmed and internal whitespace is collapsed;",
        "- step labels such as `Step 12` and `12` are both parsed to integer `12`.",
        "",
        f"Golden root: `{gold_root}`",
        f"Prediction root: `{pred_root}`",
        f"Output directory: `{output_dir}`",
        "",
        "## Model Ranking",
        "",
        "Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.",
        "",
    ]
    model_table_rows = [
        [
            row["rank"],
            row["model"],
            row["tasks"],
            row["rows_compared"],
            pct(row["coverage"]),
            pct(row["weighted_macro_f1"]),
            pct(row["weighted_macro_recall"]),
            pct(row["weighted_macro_precision"]),
            pct(row["weighted_macro_accuracy"]),
            pct(row["weighted_exact_labelset_accuracy"]),
        ]
        for row in model_rows
    ]
    lines.append(
        markdown_table(
            ["rank", "model", "tasks", "matched", "coverage", "f1", "recall", "prec", "acc", "exact"],
            model_table_rows,
        )
    )
    lines.extend(
        [
            "",
            "Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.",
            "",
            "## Macro Summary",
            "",
        ]
    )
    macro_table_rows = [
        [
            row["task"],
            row["model"],
            row["rows_compared"],
            row["gold_rows"],
            row["prediction_rows"],
            row["unmatched_gold_rows"],
            row["unmatched_prediction_rows"],
            pct(row["macro_accuracy"]),
            pct(row["macro_precision"]),
            pct(row["macro_recall"]),
            pct(row["macro_f1"]),
            pct(row["exact_labelset_accuracy"]),
        ]
        for row in sorted(macro_rows, key=lambda r: (str(r["task"]), str(r["model"])))
    ]
    lines.append(
        markdown_table(
            [
                "task",
                "model",
                "matched",
                "gold",
                "pred",
                "gold_only",
                "pred_only",
                "acc",
                "prec",
                "recall",
                "f1",
                "exact",
            ],
            macro_table_rows,
        )
    )
    lines.extend(["", "## Per Label", ""])

    grouped: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in label_rows:
        grouped[(str(row["task"]), str(row["model"]))].append(row)

    for (task, model), rows in sorted(grouped.items()):
        lines.extend([f"### {task} / {model}", ""])
        label_table_rows = [
            [
                row["label"],
                row["rows_compared"],
                int(row["support"]),
                int(row["predicted_positive"]),
                int(row["tp"]),
                int(row["fp"]),
                int(row["fn"]),
                pct(row["accuracy"]),
                pct(row["precision"]),
                pct(row["recall"]),
                pct(row["f1"]),
            ]
            for row in sorted(rows, key=lambda r: LABELS.index(str(r["label"])))
        ]
        lines.append(
            markdown_table(
                ["label", "rows", "support", "pred_pos", "tp", "fp", "fn", "acc", "prec", "recall", "f1"],
                label_table_rows,
            )
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    repo_eval_dir = Path(__file__).resolve().parent
    framework_root = repo_eval_dir.parent
    default_gold = framework_root / "jury_step_by_step" / "0_jury_baseline_Spillage" / "existing_results"
    default_pred = framework_root / "jury_step_by_step" / "jury_baseline_dummy_one_judge" / "results_ollama"
    default_out = repo_eval_dir / "dummy_judge_eval"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-root", type=Path, default=default_gold)
    parser.add_argument("--pred-root", type=Path, default=default_pred)
    parser.add_argument("--output-dir", type=Path, default=default_out)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gold_rows = build_golden_rows(args.gold_root)
    pred_rows = read_prediction_rows(args.pred_root)

    by_task_gold: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    by_task_model_pred: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in gold_rows:
        by_task_gold[str(row["task"])].append(row)
    for row in pred_rows:
        by_task_model_pred[(str(row["task"]), str(row["model"]))].append(row)

    golden_dir = args.output_dir / "golden"
    write_csv(golden_dir / "golden_all.csv", gold_rows, ["task", "gold_task_dir", "persona", "step", "gold_file", *LABELS])
    for task, rows in sorted(by_task_gold.items()):
        write_csv(golden_dir / f"golden_{safe_model_name(task)}.csv", rows, ["task", "gold_task_dir", "persona", "step", "gold_file", *LABELS])

    all_matched: List[Dict[str, Any]] = []
    all_label_metrics: List[Dict[str, Any]] = []
    all_macro_metrics: List[Dict[str, Any]] = []

    for (task, model), task_pred_rows in sorted(by_task_model_pred.items()):
        task_gold_rows = by_task_gold.get(task, [])
        matched, label_metrics, macro_metrics, unmatched_gold, unmatched_pred = evaluate_pair(
            task, model, task_gold_rows, task_pred_rows
        )
        all_matched.extend(matched)
        all_label_metrics.extend(label_metrics)
        all_macro_metrics.extend(macro_metrics)

        pair_dir = args.output_dir / "comparisons" / safe_model_name(task) / safe_model_name(model)
        write_csv(pair_dir / "matched_rows.csv", matched)
        write_csv(pair_dir / "unmatched_gold.csv", unmatched_gold)
        write_csv(pair_dir / "unmatched_predictions.csv", unmatched_pred)

    metric_fields = [
        "task",
        "model",
        "label",
        "rows_compared",
        "accuracy",
        "precision",
        "recall",
        "f1",
        "support",
        "predicted_positive",
        "tp",
        "tn",
        "fp",
        "fn",
    ]
    macro_fields = [
        "task",
        "model",
        "rows_compared",
        "gold_rows",
        "prediction_rows",
        "unmatched_gold_rows",
        "unmatched_prediction_rows",
        "macro_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "exact_labelset_accuracy",
    ]
    model_metrics = aggregate_model_metrics(all_macro_metrics)
    model_fields = [
        "rank",
        "model",
        "tasks",
        "rows_compared",
        "gold_rows",
        "prediction_rows",
        "coverage",
        "unmatched_gold_rows",
        "unmatched_prediction_rows",
        "weighted_macro_accuracy",
        "weighted_macro_precision",
        "weighted_macro_recall",
        "weighted_macro_f1",
        "weighted_exact_labelset_accuracy",
    ]

    write_csv(args.output_dir / "metrics_by_label.csv", all_label_metrics, metric_fields)
    write_csv(args.output_dir / "metrics_macro.csv", all_macro_metrics, macro_fields)
    write_csv(args.output_dir / "metrics_by_model.csv", model_metrics, model_fields)
    write_csv(args.output_dir / "matched_rows_all.csv", all_matched)

    report = build_report(all_macro_metrics, all_label_metrics, model_metrics, args.output_dir, args.gold_root, args.pred_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.md").write_text(report, encoding="utf-8")
    (args.output_dir / "report.json").write_text(
        json.dumps(
            {
                "matching": {
                    "key": ["task", "persona", "step"],
                    "task_normalization": "drop leading browseruse_ from golden task directory names",
                    "persona_normalization": "strip and collapse whitespace",
                    "step_normalization": "parse first integer from values like Step 12 or 12",
                },
                "model_ranking": model_metrics,
                "macro": all_macro_metrics,
                "by_label": all_label_metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(report)


if __name__ == "__main__":
    main()
