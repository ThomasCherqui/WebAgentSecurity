#!/usr/bin/env python3
"""Compare complete AgentDAM and LLM Council predictions against gold."""
from __future__ import annotations

import csv
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
ROOT = EVAL_DIR.parent
GOLD_PATH = ROOT / "data/input/gold/gold.csv"
AGENTDAM_PATH = ROOT / "data/output/agentDAM/predictions.csv"
COUNCIL_ROOT = ROOT / "data/output/aggregation/llm_council"
COUNCIL_RELATIVE = (
    "comparative_counterexamples_fewshot/"
    "comparative_counterexamples_fewshot_qwen25_council/predictions.csv"
)
COUNCIL_PATHS = [
    COUNCIL_ROOT / domain / COUNCIL_RELATIVE
    for domain in ("shopping_Amazon_chat", "shopping_ebay_chat")
]
OUTPUT_DIR = EVAL_DIR / "results" / "agentdam_vs_llm_council"
LABELS = ("CE", "BE", "CI", "BI")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def key(task: str, persona: str, step: str) -> tuple[str, str, int]:
    return task.strip(), " ".join(persona.casefold().split()), int(step)


def binary(value: str) -> int:
    return int(float(value or 0) > 0)


def calculate(gold: list[int], predicted: list[int]) -> dict[str, float | int]:
    tp = sum(g == p == 1 for g, p in zip(gold, predicted))
    tn = sum(g == p == 0 for g, p in zip(gold, predicted))
    fp = sum(g == 0 and p == 1 for g, p in zip(gold, predicted))
    fn = sum(g == 1 and p == 0 for g, p in zip(gold, predicted))
    total = len(gold)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    gold_rows = read_csv(GOLD_PATH)
    agent_rows = read_csv(AGENTDAM_PATH)
    council_rows = [row for path in COUNCIL_PATHS for row in read_csv(path)]
    gold = {key(r["task"], r["persona"], r["step"]): r for r in gold_rows}
    # AgentDAM source_step preserves irregular internal browser-use numbers.
    # Gold and Council use ordinal positions within each persona trajectory.
    agent: dict[tuple[str, str, int], dict[str, str]] = {}
    agent_ordinals: dict[tuple[str, str], int] = {}
    for row in agent_rows:
        group = (row["task"].strip(), " ".join(row["persona"].casefold().split()))
        agent_ordinals[group] = agent_ordinals.get(group, 0) + 1
        agent[key(row["task"], row["persona"], str(agent_ordinals[group]))] = row
    council = {key(r["domain"], r["persona"], r["step"]): r for r in council_rows}
    common = sorted(set(gold) & set(agent) & set(council))

    matched = []
    for row_key in common:
        task, persona, step = row_key
        g, a, c = gold[row_key], agent[row_key], council[row_key]
        matched.append({
            "task": task, "persona": persona, "step": step,
            "agentdam_source_step": a["source_step"],
            **{f"gold_{label}": binary(g[label]) for label in LABELS},
            "agentdam_score": binary(a["agentdam_score"]),
            **{f"council_{label}": binary(c[label]) for label in LABELS},
            "gold_any": int(any(binary(g[label]) for label in LABELS)),
            "council_any": int(any(binary(c[label]) for label in LABELS)),
        })

    scopes = {
        "CE_only": ("gold_CE", {"agentdam": "agentdam_score", "llm_council": "council_CE"}),
        "oversharing_any_label": (
            "gold_any", {"agentdam": "agentdam_score", "llm_council": "council_any"}
        ),
    }
    metric_rows = []
    domain_rows = []
    for scope, (gold_field, systems) in scopes.items():
        ranked = []
        for system, prediction_field in systems.items():
            values = calculate(
                [r[gold_field] for r in matched],
                [r[prediction_field] for r in matched],
            )
            ranked.append((system, values))
            for domain in sorted({r["task"] for r in matched}):
                subset = [r for r in matched if r["task"] == domain]
                domain_rows.append({
                    "scope": scope, "system": system, "domain": domain,
                    "compared": len(subset),
                    **calculate([r[gold_field] for r in subset], [r[prediction_field] for r in subset]),
                })
        ranked.sort(key=lambda item: (
            item[1]["f1"], item[1]["recall"], item[1]["precision"], item[1]["accuracy"]
        ), reverse=True)
        for rank, (system, values) in enumerate(ranked, 1):
            available = len(agent) if system == "agentdam" else len(council)
            metric_rows.append({
                "scope": scope, "rank": rank, "system": system,
                "gold_rows": len(gold), "system_available_rows": available,
                "system_coverage": available / len(gold), "compared": len(matched),
                "common_coverage": len(matched) / len(gold), **values,
            })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "matched_rows.csv", matched, list(matched[0]))
    write_csv(OUTPUT_DIR / "metrics.csv", metric_rows, list(metric_rows[0]))
    write_csv(OUTPUT_DIR / "metrics_by_domain.csv", domain_rows, list(domain_rows[0]))

    lines = [
        "# LLM Council vs AgentDAM", "",
        f"Gold source: `{GOLD_PATH}`", "",
        f"AgentDAM contains {len(agent)} predictions. The common intersection of "
        f"`(task, persona, step)` contains {len(matched)} rows "
        f"({sum(r['task'] == 'shopping_Amazon_chat' for r in matched)} Amazon, "
        f"{sum(r['task'] == 'shopping_ebay_chat' for r in matched)} eBay).", "",
        "AgentDAM rows are aligned by ordinal position within each persona trajectory; "
        "its internal `source_step` is retained in `matched_rows.csv` for auditing.", "",
        "## Results", "",
        "| scope | rank | system | compared | coverage | accuracy | precision | recall | F1 | TP | TN | FP | FN |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in metric_rows:
        lines.append(
            f"| {r['scope']} | {r['rank']} | {r['system']} | {r['compared']} | "
            f"{100*r['common_coverage']:.1f}% | {100*r['accuracy']:.1f}% | "
            f"{100*r['precision']:.1f}% | {100*r['recall']:.1f}% | {100*r['f1']:.1f}% | "
            f"{r['tp']} | {r['tn']} | {r['fp']} | {r['fn']} |"
        )
    lines += ["", "## Definitions", "",
              "- `CE_only`: AgentDAM score and LLM Council CE are compared with gold CE.",
              "- `oversharing_any_label`: positive if any of CE, BE, CI, or BI is positive.",
              "- Rankings use F1, then recall, precision, and accuracy."]
    (OUTPUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Compared {len(matched)}/{len(gold)} gold rows; wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
