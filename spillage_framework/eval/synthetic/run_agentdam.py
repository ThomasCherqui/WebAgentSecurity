#!/usr/bin/env python3
"""Run the binary AgentDAM judge on the synthetic SPILLage dataset."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent.parent
AGENTDAM_DIR = ROOT / "ai-agent-privacy" / "agentdam"
sys.path.insert(0, str(AGENTDAM_DIR))

from privacy_eval import PrivacyEvaluator  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=SCRIPT_DIR / "spillage_eval_set.jsonl")
    parser.add_argument("--output", type=Path, default=SCRIPT_DIR / "results/agentdam/predictions.jsonl")
    parser.add_argument("--config", type=Path, default=AGENTDAM_DIR / "configs/p_cot_privacy_judge_ollama.json")
    parser.add_argument("--model", default=None)
    parser.add_argument("--ollama-host", default=None)
    parser.add_argument("--input-mode", choices=("action", "full-step"), default="action")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def step_text(record: dict, mode: str) -> str:
    step = record["input"]
    if mode == "action":
        return str(step.get("action") or "").strip()
    return "\n".join(
        f"{field}: {step[field]}"
        for field in ("action", "evaluation", "memory_update", "next_goal")
        if step.get(field)
    )


def sensitive_data(record: dict) -> list[str]:
    value = record.get("irrelevant_attributes", "")
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split("|") if item.strip()]


def main() -> None:
    args = parse_args()
    evaluator = PrivacyEvaluator(args.config, model=args.model, ollama_host=args.ollama_host)
    model = evaluator.llm_params["model"]
    records = read_jsonl(args.dataset)
    existing = read_jsonl(args.output) if args.output.exists() else []
    completed = {(row["id"], row["model"], row["input_mode"]) for row in existing}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    processed = 0
    with args.output.open("a", encoding="utf-8") as stream:
        for record in records:
            key = (str(record["id"]), model, args.input_mode)
            if key in completed:
                continue
            if args.limit and processed >= args.limit:
                break
            action = step_text(record, args.input_mode)
            score, response = evaluator.test(action, sensitive_data(record))
            expected = record.get("expected", {})
            row = {
                "id": record["id"], "persona": record.get("persona"),
                "case_id": record.get("case_id"), "difficulty": record.get("difficulty"),
                "model": model, "input_mode": args.input_mode,
                "agentdam_score": int(score > 0),
                "expected_any": int(expected.get("is_oversharing", any(expected.get(x, 0) for x in ("CE", "BE", "CI", "BI")))),
                "agentdam_output": response, "action_str": action,
            }
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            processed += 1
            print(f"[{processed}] {record['id']} -> {row['agentdam_score']}", flush=True)
    print(f"Done: {processed} new rows; output: {args.output}")


if __name__ == "__main__":
    main()
