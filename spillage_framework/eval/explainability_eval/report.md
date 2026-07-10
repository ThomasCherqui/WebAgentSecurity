# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_framework/jury_step_by_step/0_jury_baseline_Spillage/existing_results`
Prediction root: `spillage_framework/jury_step_by_step/jury_explainability_and_prompts/results_ollama`
Output directory: `spillage_framework/eval/explainability_eval`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                                                         | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | ------------------------------------------------------------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | comparative_counterexamples_fewshot/gpt-oss_20b-cloud         | 1     | 467     | 100.0%   |  36.9% |  41.8% |  34.7% |  83.9% |  51.2% |
| 2    | comparative_counterexamples_fewshot/gemma4_31b-cloud          | 1     | 467     | 100.0%   |  36.2% |  48.2% |  29.0% |  82.6% |  50.7% |
| 3    | balanced_fewshot/gpt-oss_20b-cloud                            | 1     | 467     | 100.0%   |  35.8% |  45.9% |  29.4% |  83.4% |  53.5% |
| 4    | balanced_fewshot/gemma4_31b-cloud                             | 1     | 467     | 100.0%   |  35.7% |  49.4% |  28.0% |  82.5% |  53.7% |
| 5    | strict_evidence_fewshot/gemma4_31b                            | 1     | 467     | 100.0%   |  35.6% |  42.8% |  31.2% |  84.5% |  52.0% |
| 6    | balanced_fewshot/nemotron-3-nano_30b-cloud                    | 1     | 467     | 100.0%   |  35.3% |  39.6% |  32.0% |  85.1% |  56.3% |
| 7    | strict_evidence_fewshot/gpt-oss_20b-cloud                     | 1     | 467     | 100.0%   |  34.0% |  39.6% |  31.0% |  83.7% |  52.2% |
| 8    | strict_evidence_fewshot/nemotron-3-nano_30b-cloud             | 1     | 467     | 100.0%   |  27.7% |  24.8% |  31.6% |  81.8% |  45.0% |
| 9    | comparative_counterexamples_fewshot/nemotron-3-nano_30b-cloud | 1     | 467     | 100.0%   |  27.7% |  24.6% |  32.2% |  80.4% |  41.3% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                                                         | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | ------------------------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | balanced_fewshot/gemma4_31b-cloud                             | 467     | 467  | 467  | 0         | 0         |  82.5% |  28.0% |  49.4% |  35.7% |  53.7% |
| shopping_Amazon_chat | balanced_fewshot/gpt-oss_20b-cloud                            | 467     | 467  | 467  | 0         | 0         |  83.4% |  29.4% |  45.9% |  35.8% |  53.5% |
| shopping_Amazon_chat | balanced_fewshot/nemotron-3-nano_30b-cloud                    | 467     | 467  | 467  | 0         | 0         |  85.1% |  32.0% |  39.6% |  35.3% |  56.3% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/gemma4_31b-cloud          | 467     | 467  | 467  | 0         | 0         |  82.6% |  29.0% |  48.2% |  36.2% |  50.7% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/gpt-oss_20b-cloud         | 467     | 467  | 467  | 0         | 0         |  83.9% |  34.7% |  41.8% |  36.9% |  51.2% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/nemotron-3-nano_30b-cloud | 467     | 467  | 467  | 0         | 0         |  80.4% |  32.2% |  24.6% |  27.7% |  41.3% |
| shopping_Amazon_chat | strict_evidence_fewshot/gemma4_31b                            | 467     | 467  | 467  | 0         | 0         |  84.5% |  31.2% |  42.8% |  35.6% |  52.0% |
| shopping_Amazon_chat | strict_evidence_fewshot/gpt-oss_20b-cloud                     | 467     | 467  | 467  | 0         | 0         |  83.7% |  31.0% |  39.6% |  34.0% |  52.2% |
| shopping_Amazon_chat | strict_evidence_fewshot/nemotron-3-nano_30b-cloud             | 467     | 467  | 467  | 0         | 0         |  81.8% |  31.6% |  24.8% |  27.7% |  45.0% |

## Per Label

### shopping_Amazon_chat / balanced_fewshot/gemma4_31b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 340      | 185 | 155 | 1  |  66.6% |  54.4% |  99.5% |  70.3% |
| BE    | 467  | 177     | 303      | 174 | 129 | 3  |  71.7% |  57.4% |  98.3% |  72.5% |
| CI    | 467  | 18      | 3        | 0   | 3   | 18 |  95.5% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 2        | 0   | 2   | 16 |  96.1% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / balanced_fewshot/gpt-oss_20b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 300      | 168 | 132 | 18 |  67.9% |  56.0% |  90.3% |  69.1% |
| BE    | 467  | 177     | 268      | 165 | 103 | 12 |  75.4% |  61.6% |  93.2% |  74.2% |
| CI    | 467  | 18      | 10       | 0   | 10  | 18 |  94.0% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 1        | 0   | 1   | 16 |  96.4% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / balanced_fewshot/nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 254      | 155 | 99 | 31 |  72.2% |  61.0% |  83.3% |  70.5% |
| BE    | 467  | 177     | 198      | 133 | 65 | 44 |  76.7% |  67.2% |  75.1% |  70.9% |
| CI    | 467  | 18      | 2        | 0   | 2  | 18 |  95.7% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 4        | 0   | 4  | 16 |  95.7% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/gemma4_31b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 321      | 181 | 140 | 5  |  69.0% |  56.4% |  97.3% |  71.4% |
| BE    | 467  | 177     | 283      | 169 | 114 | 8  |  73.9% |  59.7% |  95.5% |  73.5% |
| CI    | 467  | 18      | 13       | 0   | 13  | 18 |  93.4% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 11       | 0   | 11  | 16 |  94.2% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/gpt-oss_20b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 248      | 145 | 103 | 41 |  69.2% |  58.5% |  78.0% |  66.8% |
| BE    | 467  | 177     | 232      | 148 | 84  | 29 |  75.8% |  63.8% |  83.6% |  72.4% |
| CI    | 467  | 18      | 6        | 1   | 5   | 17 |  95.3% |  16.7% |   5.6% |   8.3% |
| BI    | 467  | 16      | 5        | 0   | 5   | 16 |  95.5% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | -- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 147      | 84 | 63 | 102 |  64.7% |  57.1% |  45.2% |  50.5% |
| BE    | 467  | 177     | 122      | 83 | 39 | 94  |  71.5% |  68.0% |  46.9% |  55.5% |
| CI    | 467  | 18      | 9        | 0  | 9  | 18  |  94.2% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 27       | 1  | 26 | 15  |  91.2% |   3.7% |   6.2% |   4.7% |

### shopping_Amazon_chat / strict_evidence_fewshot/gemma4_31b

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 327      | 180 | 147 | 6  |  67.2% |  55.0% |  96.8% |  70.2% |
| BE    | 467  | 177     | 189      | 132 | 57  | 45 |  78.2% |  69.8% |  74.6% |  72.1% |
| CI    | 467  | 18      | 0        | 0   | 0   | 18 |  96.1% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 0        | 0   | 0   | 16 |  96.6% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / strict_evidence_fewshot/gpt-oss_20b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 317      | 176 | 141 | 10 |  67.7% |  55.5% |  94.6% |  70.0% |
| BE    | 467  | 177     | 165      | 113 | 52  | 64 |  75.2% |  68.5% |  63.8% |  66.1% |
| CI    | 467  | 18      | 3        | 0   | 3   | 18 |  95.5% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 0        | 0   | 0   | 16 |  96.6% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / strict_evidence_fewshot/nemotron-3-nano_30b-cloud

| label | rows | support | pred_pos | tp | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | -- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 163      | 94 | 69 | 92 |  65.5% |  57.7% |  50.5% |  53.9% |
| BE    | 467  | 177     | 125      | 86 | 39 | 91 |  72.2% |  68.8% |  48.6% |  57.0% |
| CI    | 467  | 18      | 14       | 0  | 14 | 18 |  93.1% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 1        | 0  | 1  | 16 |  96.4% |   0.0% |   0.0% |   0.0% |
