# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_framework/jury_step_by_step/0_jury_baseline_Spillage/existing_results`
Prediction root: `spillage_framework/jury_step_by_step/jury_aggregation/results_ollama/llm_council`
Output directory: `spillage_framework/eval/aggregation_eval/llm_council`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                                                                                  | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | -------------------------------------------------------------------------------------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | comparative_counterexamples_fewshot/comparative_counterexamples_fewshot_qwen25_council | 2     | 1014    | 100.0%   |  36.3% |  46.4% |  29.8% |  84.6% |  55.0% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                                                                                  | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | -------------------------------------------------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/comparative_counterexamples_fewshot_qwen25_council | 467     | 467  | 467  | 0         | 0         |  83.1% |  29.1% |  47.1% |  36.0% |  52.5% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/comparative_counterexamples_fewshot_qwen25_council | 547     | 547  | 547  | 0         | 0         |  86.0% |  30.3% |  45.8% |  36.5% |  57.2% |

## Per Label

### shopping_Amazon_chat / comparative_counterexamples_fewshot/comparative_counterexamples_fewshot_qwen25_council

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 310      | 176 | 134 | 10 |  69.2% |  56.8% |  94.6% |  71.0% |
| BE    | 467  | 177     | 278      | 166 | 112 | 11 |  73.7% |  59.7% |  93.8% |  73.0% |
| CI    | 467  | 18      | 9        | 0   | 9   | 18 |  94.2% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 6        | 0   | 6   | 16 |  95.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/comparative_counterexamples_fewshot_qwen25_council

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 342      | 209 | 133 | 16 |  72.8% |  61.1% |  92.9% |  73.7% |
| BE    | 547  | 178     | 268      | 161 | 107 | 17 |  77.3% |  60.1% |  90.4% |  72.2% |
| CI    | 547  | 13      | 10       | 0   | 10  | 13 |  95.8% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 6       | 5        | 0   | 5   | 6  |  98.0% |   0.0% |   0.0% |   0.0% |
