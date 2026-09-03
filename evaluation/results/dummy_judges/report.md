# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_release/data/input/gold/gold.csv`
Prediction root: `data/output/dummy_judges`
Output directory: `evaluation/results/dummy_judges`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model    | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | -------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | gemma    | 2     | 1014    | 100.0%   |  46.5% |  53.4% |  42.2% |  91.2% |  72.9% |
| 2    | gpt-oss  | 2     | 1014    | 100.0%   |  46.4% |  51.2% |  48.0% |  89.1% |  68.0% |
| 3    | nemotron | 2     | 1014    | 100.0%   |  44.8% |  55.3% |  42.1% |  88.4% |  67.6% |
| 4    | qwen     | 2     | 1014    | 100.0%   |  42.1% |  42.5% |  42.9% |  91.0% |  69.4% |
| 5    | mistral  | 2     | 1014    | 100.0%   |  34.7% |  38.9% |  33.7% |  79.9% |  37.8% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model    | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | -------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | gemma    | 467     | 467  | 467  | 0         | 0         |  90.4% |  40.1% |  48.6% |  43.9% |  71.1% |
| shopping_Amazon_chat | gpt-oss  | 467     | 467  | 467  | 0         | 0         |  88.0% |  54.4% |  48.3% |  47.7% |  65.5% |
| shopping_Amazon_chat | mistral  | 467     | 467  | 467  | 0         | 0         |  82.7% |  36.3% |  42.1% |  38.1% |  45.4% |
| shopping_Amazon_chat | nemotron | 467     | 467  | 467  | 0         | 0         |  87.3% |  42.5% |  55.3% |  44.9% |  64.9% |
| shopping_Amazon_chat | qwen     | 467     | 467  | 467  | 0         | 0         |  90.0% |  42.4% |  42.3% |  41.7% |  67.0% |
| shopping_ebay_chat   | gemma    | 547     | 547  | 547  | 0         | 0         |  92.0% |  44.0% |  57.6% |  48.8% |  74.4% |
| shopping_ebay_chat   | gpt-oss  | 547     | 547  | 547  | 0         | 0         |  90.0% |  42.7% |  53.6% |  45.2% |  70.2% |
| shopping_ebay_chat   | mistral  | 547     | 547  | 547  | 0         | 0         |  77.4% |  31.5% |  36.2% |  31.8% |  31.3% |
| shopping_ebay_chat   | nemotron | 547     | 547  | 547  | 0         | 0         |  89.3% |  41.8% |  55.2% |  44.7% |  69.8% |
| shopping_ebay_chat   | qwen     | 547     | 547  | 547  | 0         | 0         |  91.9% |  43.3% |  42.7% |  42.5% |  71.5% |

## Per Label

### shopping_Amazon_chat / gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 336      | 256 | 80 | 0  |  82.9% |  76.2% | 100.0% |  86.5% |
| BE    | 467  | 262     | 293      | 247 | 46 | 15 |  86.9% |  84.3% |  94.3% |  89.0% |
| CI    | 467  | 7       | 20       | 0   | 20 | 7  |  94.2% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 3        | 0   | 3  | 8  |  97.6% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 311      | 241 | 70 | 15 |  81.8% |  77.5% |  94.1% |  85.0% |
| BE    | 467  | 262     | 224      | 189 | 35 | 73 |  76.9% |  84.4% |  72.1% |  77.8% |
| CI    | 467  | 7       | 18       | 1   | 17 | 6  |  95.1% |   5.6% |  14.3% |   8.0% |
| BI    | 467  | 8       | 2        | 1   | 1  | 7  |  98.3% |  50.0% |  12.5% |  20.0% |

### shopping_Amazon_chat / mistral

| label | rows | support | pred_pos | tp  | fp  | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 218      | 177 | 41  | 79 |  74.3% |  81.2% |  69.1% |  74.7% |
| BE    | 467  | 262     | 407      | 260 | 147 | 2  |  68.1% |  63.9% |  99.2% |  77.7% |
| CI    | 467  | 7       | 11       | 0   | 11  | 7  |  96.1% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 28       | 0   | 28  | 8  |  92.3% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 286      | 234 | 52 | 22 |  84.2% |  81.8% |  91.4% |  86.3% |
| BE    | 467  | 262     | 273      | 228 | 45 | 34 |  83.1% |  83.5% |  87.0% |  85.2% |
| CI    | 467  | 7       | 66       | 3   | 63 | 4  |  85.7% |   4.5% |  42.9% |   8.2% |
| BI    | 467  | 8       | 10       | 0   | 10 | 8  |  96.1% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / qwen

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 326      | 249 | 77 | 7  |  82.0% |  76.4% |  97.3% |  85.6% |
| BE    | 467  | 262     | 202      | 188 | 14 | 74 |  81.2% |  93.1% |  71.8% |  81.0% |
| CI    | 467  | 7       | 0        | 0   | 0  | 7  |  98.5% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 0        | 0   | 0  | 8  |  98.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 366      | 289 | 77 | 2  |  85.6% |  79.0% |  99.3% |  88.0% |
| BE    | 547  | 270     | 294      | 246 | 48 | 24 |  86.8% |  83.7% |  91.1% |  87.2% |
| CI    | 547  | 5       | 15       | 2   | 13 | 3  |  97.1% |  13.3% |  40.0% |  20.0% |
| BI    | 547  | 4       | 5        | 0   | 5  | 4  |  98.4% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 344      | 276 | 68 | 15 |  84.8% |  80.2% |  94.8% |  86.9% |
| BE    | 547  | 270     | 260      | 215 | 45 | 55 |  81.7% |  82.7% |  79.6% |  81.1% |
| CI    | 547  | 5       | 26       | 2   | 24 | 3  |  95.1% |   7.7% |  40.0% |  12.9% |
| BI    | 547  | 4       | 4        | 0   | 4  | 4  |  98.5% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / mistral

| label | rows | support | pred_pos | tp  | fp  | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | --- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 194      | 137 | 57  | 154 |  61.4% |  70.6% |  47.1% |  56.5% |
| BE    | 547  | 270     | 476      | 264 | 212 | 6   |  60.1% |  55.5% |  97.8% |  70.8% |
| CI    | 547  | 5       | 21       | 0   | 21  | 5   |  95.2% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 35       | 0   | 35  | 4   |  92.9% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 335      | 269 | 66 | 22 |  83.9% |  80.3% |  92.4% |  85.9% |
| BE    | 547  | 270     | 289      | 239 | 50 | 31 |  85.2% |  82.7% |  88.5% |  85.5% |
| CI    | 547  | 5       | 49       | 2   | 47 | 3  |  90.9% |   4.1% |  40.0% |   7.4% |
| BI    | 547  | 4       | 11       | 0   | 11 | 4  |  97.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / qwen

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 356      | 284 | 72 | 7  |  85.6% |  79.8% |  97.6% |  87.8% |
| BE    | 547  | 270     | 212      | 198 | 14 | 72 |  84.3% |  93.4% |  73.3% |  82.2% |
| CI    | 547  | 5       | 3        | 0   | 3  | 5  |  98.5% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 0        | 0   | 0  | 4  |  99.3% |   0.0% |   0.0% |   0.0% |
