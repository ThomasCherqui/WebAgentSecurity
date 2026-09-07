# Evaluation

All evaluations use the corrected step-level reference annotations in `../data/input/gold/gold.csv`.

Trajectory rows are matched on normalised `(task, persona, step)` identifiers. Reports include coverage so missing or duplicated predictions can be detected before comparing quality.

## Scripts

To rebuild every evaluation from saved predictions without calling any model:

```bash
./evaluation/run_all.sh
```

`evaluate.py` computes CE, BE, CI, and BI metrics for any prediction tree containing `predictions.csv` files:

```bash
python3 evaluation/evaluate.py \
  --pred-root data/output/dummy_judges \
  --output-dir evaluation/results/dummy_judges
```

Change `--pred-root` to evaluate prompt judges, majority, hybrid, or the LLM council.

The script reports accuracy, precision, recall, F1, exact label-set accuracy, and per-label results. Macro-F1 is generally more informative than raw accuracy because CI and BI positives are rare.

`compare_agentdam.py` compares AgentDAM and the LLM council on their common trajectory steps:

```bash
python3 evaluation/compare_agentdam.py
```

The AgentDAM comparison reports both `CE_only` and `oversharing_any_label`. It is separate because AgentDAM is binary and cannot be treated as a four-label classifier.

## Results

- `results/dummy_judges/`: individual baseline evaluation.
- `results/prompt_judges/`: prompt/model experiments.
- `results/aggregation/`: majority, hybrid, and council evaluation.
- `results/agentdam_vs_llm_council/`: binary AgentDAM comparison.
- `results/synthetic/`: synthetic multi-label metrics and separate AgentDAM comparison.
- `all_step_performance.csv`: reference and predicted labels for every trajectory and synthetic step, excluding AgentDAM.

The filename `gold.csv` and detailed-output fields such as `CE_gold` are retained as stable technical identifiers. They refer to the reference annotations and do not imply that those annotations are objective or exhaustive.

`report.md` provides a readable summary; CSV and JSON files contain the corresponding detailed results. For the synthetic benchmark, `multilabel_metrics_summary.csv` provides the ranking and `multilabel_metrics_details.json` contains per-label confusion counts.
