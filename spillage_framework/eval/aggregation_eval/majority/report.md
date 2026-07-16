# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_framework/jury_step_by_step/0_jury_baseline_Spillage/existing_results`
Prediction root: `spillage_framework/jury_step_by_step/jury_aggregation/results_ollama/majority`
Output directory: `spillage_framework/eval/aggregation_eval/majority`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                                                                                              | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | -------------------------------------------------------------------------------------------------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | balanced_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                    | 1     | 467     | 100.0%   |  36.5% |  48.1% |  29.4% |  84.2% |  55.5% |
| 2    | balanced_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                          | 1     | 547     | 100.0%   |  36.4% |  48.1% |  29.3% |  86.1% |  60.1% |
| 3    | comparative_counterexamples_fewshot/gemma4_31b__gpt-oss_20b__nemotron-cascade-2_latest             | 1     | 547     | 100.0%   |  36.0% |  41.9% |  31.6% |  87.1% |  57.6% |
| 4    | comparative_counterexamples_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud | 1     | 467     | 100.0%   |  35.6% |  42.0% |  30.9% |  84.6% |  53.3% |
| 5    | strict_evidence_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                   | 2     | 1014    | 100.0%   |  35.2% |  40.4% |  32.3% |  86.1% |  56.2% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                                                                                              | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | -------------------------------------------------------------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | balanced_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                    | 467     | 467  | 467  | 0         | 0         |  84.2% |  29.4% |  48.1% |  36.5% |  55.5% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud | 467     | 467  | 467  | 0         | 0         |  84.6% |  30.9% |  42.0% |  35.6% |  53.3% |
| shopping_Amazon_chat | strict_evidence_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                   | 467     | 467  | 467  | 0         | 0         |  84.5% |  31.9% |  40.2% |  34.8% |  53.5% |
| shopping_ebay_chat   | balanced_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                          | 547     | 547  | 547  | 0         | 0         |  86.1% |  29.3% |  48.1% |  36.4% |  60.1% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/gemma4_31b__gpt-oss_20b__nemotron-cascade-2_latest             | 547     | 547  | 547  | 0         | 0         |  87.1% |  31.6% |  41.9% |  36.0% |  57.6% |
| shopping_ebay_chat   | strict_evidence_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud                   | 547     | 547  | 547  | 0         | 0         |  87.4% |  32.6% |  40.5% |  35.6% |  58.5% |

## Per Label

### shopping_Amazon_chat / balanced_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 321      | 181 | 140 | 5  |  69.0% |  56.4% |  97.3% |  71.4% |
| BE    | 467  | 177     | 274      | 168 | 106 | 9  |  75.4% |  61.3% |  94.9% |  74.5% |
| CI    | 467  | 18      | 1        | 0   | 1   | 18 |  95.9% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 1        | 0   | 1   | 16 |  96.4% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/gemma4_31b-cloud__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 258      | 152 | 106 | 34 |  70.0% |  58.9% |  81.7% |  68.5% |
| BE    | 467  | 177     | 237      | 153 | 84  | 24 |  76.9% |  64.6% |  86.4% |  73.9% |
| CI    | 467  | 18      | 3        | 0   | 3   | 18 |  95.5% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 2        | 0   | 2   | 16 |  96.1% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / strict_evidence_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 313      | 176 | 137 | 10 |  68.5% |  56.2% |  94.6% |  70.5% |
| BE    | 467  | 177     | 164      | 117 | 47  | 60 |  77.1% |  71.3% |  66.1% |  68.6% |
| CI    | 467  | 18      | 1        | 0   | 1   | 18 |  95.9% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 0        | 0   | 0   | 16 |  96.6% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / balanced_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 363      | 223 | 140 | 2  |  74.0% |  61.4% |  99.1% |  75.9% |
| BE    | 547  | 178     | 297      | 166 | 131 | 12 |  73.9% |  55.9% |  93.3% |  69.9% |
| CI    | 547  | 13      | 0        | 0   | 0   | 13 |  97.6% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 6       | 0        | 0   | 0   | 6  |  98.9% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/gemma4_31b__gpt-oss_20b__nemotron-cascade-2_latest

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 314      | 198 | 116 | 27 |  73.9% |  63.1% |  88.0% |  73.5% |
| BE    | 547  | 178     | 224      | 142 | 82  | 36 |  78.4% |  63.4% |  79.8% |  70.6% |
| CI    | 547  | 13      | 3        | 0   | 3   | 13 |  97.1% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 6       | 0        | 0   | 0   | 6  |  98.9% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / strict_evidence_fewshot/gemma4_31b__gpt-oss_20b-cloud__nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 351      | 218 | 133 | 7  |  74.4% |  62.1% |  96.9% |  75.7% |
| BE    | 547  | 178     | 170      | 116 | 54  | 62 |  78.8% |  68.2% |  65.2% |  66.7% |
| CI    | 547  | 13      | 1        | 0   | 1   | 13 |  97.4% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 6       | 0        | 0   | 0   | 6  |  98.9% |   0.0% |   0.0% |   0.0% |
