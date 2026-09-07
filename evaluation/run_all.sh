#!/usr/bin/env bash
set -euo pipefail

python3 evaluation/evaluate.py --pred-root data/output/dummy_judges --output-dir evaluation/results/dummy_judges
python3 evaluation/evaluate.py --pred-root data/output/prompt_judges --output-dir evaluation/results/prompt_judges
python3 evaluation/evaluate.py --pred-root data/output/aggregation/majority --output-dir evaluation/results/aggregation/majority
python3 evaluation/evaluate.py --pred-root data/output/aggregation/hybrid --output-dir evaluation/results/aggregation/hybrid
python3 evaluation/evaluate.py --pred-root data/output/aggregation/llm_council --output-dir evaluation/results/aggregation/llm_council
python3 evaluation/compare_agentdam.py

python3 steps/synthetic/run.py \
  --stage evaluate \
  --dataset data/input/synthetic/spillage_eval_set.jsonl \
  --output-dir data/output/synthetic \
  --prompt-template steps/prompt_judges/prompts/comparative_counterexamples_fewshot.md

mkdir -p evaluation/results/synthetic
cp data/output/synthetic/comparative_counterexamples_fewshot/metrics/multilabel_metrics_summary.csv evaluation/results/synthetic/
cp data/output/synthetic/comparative_counterexamples_fewshot/metrics/multilabel_metrics_details.json evaluation/results/synthetic/
cp data/output/synthetic/comparative_counterexamples_fewshot/metrics/agentdam_vs_llm_council.csv evaluation/results/synthetic/
cp data/output/synthetic/comparative_counterexamples_fewshot/metrics/agentdam_vs_llm_council.json evaluation/results/synthetic/
