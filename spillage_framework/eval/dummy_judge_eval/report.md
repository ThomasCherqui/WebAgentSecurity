# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_framework/jury_step_by_step/0_jury_baseline_Spillage/existing_results`
Prediction root: `/home/zhonghao/Documents/Thomas/home/spillage_framework/jury_step_by_step/jury_baseline_dummy_one_judge/results_ollama`
Output directory: `/home/zhonghao/Documents/Thomas/home/spillage_framework/eval/dummy_judge_eval`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                     | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | ------------------------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | nemotron-cascade-2_latest | 2     | 1014    | 100.0%   |  40.6% |  56.4% |  32.6% |  82.9% |  54.4% |
| 2    | gemma4_31b                | 2     | 1014    | 100.0%   |  38.5% |  50.5% |  33.7% |  83.9% |  55.4% |
| 3    | gpt-oss_20b-cloud         | 2     | 1014    | 100.0%   |  37.4% |  46.8% |  31.3% |  84.5% |  57.1% |
| 4    | qwen3.6_35b               | 2     | 1014    | 100.0%   |  36.4% |  44.0% |  31.5% |  86.1% |  56.3% |
| 5    | mistral-small_latest      | 2     | 1014    | 100.0%   |  28.3% |  39.0% |  24.0% |  74.4% |  25.5% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                     | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | ------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | gemma4_31b                | 467     | 467  | 467  | 0         | 0         |  82.1% |  36.7% |  50.6% |  38.5% |  51.8% |
| shopping_Amazon_chat | gpt-oss_20b-cloud         | 467     | 467  | 467  | 0         | 0         |  82.5% |  29.4% |  43.0% |  34.8% |  52.0% |
| shopping_Amazon_chat | mistral-small_latest      | 467     | 467  | 467  | 0         | 0         |  76.3% |  26.1% |  42.7% |  31.6% |  31.7% |
| shopping_Amazon_chat | nemotron-cascade-2_latest | 467     | 467  | 467  | 0         | 0         |  81.0% |  32.0% |  54.2% |  39.7% |  51.8% |
| shopping_Amazon_chat | qwen3.6_35b               | 467     | 467  | 467  | 0         | 0         |  84.4% |  30.7% |  43.5% |  35.6% |  52.9% |
| shopping_ebay_chat   | gemma4_31b                | 547     | 547  | 547  | 0         | 0         |  85.6% |  31.2% |  50.4% |  38.5% |  58.5% |
| shopping_ebay_chat   | gpt-oss_20b-cloud         | 547     | 547  | 547  | 0         | 0         |  86.2% |  32.8% |  50.1% |  39.6% |  61.4% |
| shopping_ebay_chat   | mistral-small_latest      | 547     | 547  | 547  | 0         | 0         |  72.8% |  22.2% |  35.8% |  25.4% |  20.3% |
| shopping_ebay_chat   | nemotron-cascade-2_latest | 547     | 547  | 547  | 0         | 0         |  84.5% |  33.1% |  58.2% |  41.4% |  56.7% |
| shopping_ebay_chat   | qwen3.6_35b               | 547     | 547  | 547  | 0         | 0         |  87.6% |  32.2% |  44.3% |  37.1% |  59.2% |

## Per Label

### shopping_Amazon_chat / gemma4_31b

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 336      | 185 | 151 | 1  |  67.5% |  55.1% |  99.5% |  70.9% |
| BE    | 467  | 177     | 293      | 171 | 122 | 6  |  72.6% |  58.4% |  96.6% |  72.8% |
| CI    | 467  | 18      | 20       | 0   | 20  | 18 |  91.9% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 3        | 1   | 2   | 15 |  96.4% |  33.3% |   6.2% |  10.5% |

### shopping_Amazon_chat / gpt-oss_20b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 311      | 176 | 135 | 10 |  69.0% |  56.6% |  94.6% |  70.8% |
| BE    | 467  | 177     | 224      | 137 | 87  | 40 |  72.8% |  61.2% |  77.4% |  68.3% |
| CI    | 467  | 18      | 18       | 0   | 18  | 18 |  92.3% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 2        | 0   | 2   | 16 |  96.1% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / mistral-small_latest

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 218      | 134 | 84  | 52 |  70.9% |  61.5% |  72.0% |  66.3% |
| BE    | 467  | 177     | 407      | 175 | 232 | 2  |  49.9% |  43.0% |  98.9% |  59.9% |
| CI    | 467  | 18      | 11       | 0   | 11  | 18 |  93.8% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 28       | 0   | 28  | 16 |  90.6% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / nemotron-cascade-2_latest

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 286      | 173 | 113 | 13 |  73.0% |  60.5% |  93.0% |  73.3% |
| BE    | 467  | 177     | 273      | 160 | 113 | 17 |  72.2% |  58.6% |  90.4% |  71.1% |
| CI    | 467  | 18      | 66       | 6   | 60  | 12 |  84.6% |   9.1% |  33.3% |  14.3% |
| BI    | 467  | 16      | 10       | 0   | 10  | 16 |  94.4% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / qwen3.6_35b

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 186     | 326      | 181 | 145 | 5  |  67.9% |  55.5% |  97.3% |  70.7% |
| BE    | 467  | 177     | 202      | 136 | 66  | 41 |  77.1% |  67.3% |  76.8% |  71.8% |
| CI    | 467  | 18      | 0        | 0   | 0   | 18 |  96.1% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 16      | 0        | 0   | 0   | 16 |  96.6% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / gemma4_31b

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 366      | 225 | 141 | 0  |  74.2% |  61.5% | 100.0% |  76.1% |
| BE    | 547  | 178     | 294      | 167 | 127 | 11 |  74.8% |  56.8% |  93.8% |  70.8% |
| CI    | 547  | 13      | 15       | 1   | 14  | 12 |  95.2% |   6.7% |   7.7% |   7.1% |
| BI    | 547  | 6       | 5        | 0   | 5   | 6  |  98.0% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / gpt-oss_20b-cloud

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 344      | 219 | 125 | 6  |  76.1% |  63.7% |  97.3% |  77.0% |
| BE    | 547  | 178     | 260      | 156 | 104 | 22 |  77.0% |  60.0% |  87.6% |  71.2% |
| CI    | 547  | 13      | 26       | 2   | 24  | 11 |  93.6% |   7.7% |  15.4% |  10.3% |
| BI    | 547  | 6       | 4        | 0   | 4   | 6  |  98.2% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / mistral-small_latest

| label | rows | support | pred_pos | tp  | fp  | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 194      | 101 | 93  | 124 |  60.3% |  52.1% |  44.9% |  48.2% |
| BE    | 547  | 178     | 476      | 175 | 301 | 3   |  44.4% |  36.8% |  98.3% |  53.5% |
| CI    | 547  | 13      | 21       | 0   | 21  | 13  |  93.8% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 6       | 35       | 0   | 35  | 6   |  92.5% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / nemotron-cascade-2_latest

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 335      | 214 | 121 | 11 |  75.9% |  63.9% |  95.1% |  76.4% |
| BE    | 547  | 178     | 289      | 163 | 126 | 15 |  74.2% |  56.4% |  91.6% |  69.8% |
| CI    | 547  | 13      | 49       | 6   | 43  | 7  |  90.9% |  12.2% |  46.2% |  19.4% |
| BI    | 547  | 6       | 11       | 0   | 11  | 6  |  96.9% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / qwen3.6_35b

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 225     | 356      | 218 | 138 | 7  |  73.5% |  61.2% |  96.9% |  75.0% |
| BE    | 547  | 178     | 212      | 143 | 69  | 35 |  81.0% |  67.5% |  80.3% |  73.3% |
| CI    | 547  | 13      | 3        | 0   | 3   | 13 |  97.1% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 6       | 0        | 0   | 0   | 6  |  98.9% |   0.0% |   0.0% |   0.0% |
