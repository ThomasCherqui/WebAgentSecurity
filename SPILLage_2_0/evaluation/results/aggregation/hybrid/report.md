# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_release/data/input/gold/gold.csv`
Prediction root: `data/output/aggregation/hybrid`
Output directory: `evaluation/results/aggregation/hybrid`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                                                               | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | ------------------------------------------------------------------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | comparative_counterexamples_fewshot/ensemble_gemma_gpt-oss_nemotron | 2     | 1014    | 100.0%   |  54.2% |  51.5% |  60.5% |  91.3% |  69.6% |
| 2    | balanced_fewshot/ensemble_gemma_gpt-oss_nemotron                    | 2     | 1014    | 100.0%   |  46.4% |  48.9% |  52.4% |  92.3% |  75.2% |
| 3    | strict_evidence_fewshot/ensemble_gemma_gpt-oss_nemotron             | 2     | 1014    | 100.0%   |  40.1% |  39.0% |  43.6% |  89.8% |  64.4% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                                                               | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | ------------------------------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | balanced_fewshot/ensemble_gemma_gpt-oss_nemotron                    | 467     | 467  | 467  | 0         | 0         |  92.1% |  66.4% |  50.4% |  49.6% |  73.7% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/ensemble_gemma_gpt-oss_nemotron | 467     | 467  | 467  | 0         | 0         |  90.5% |  68.0% |  51.3% |  56.1% |  67.2% |
| shopping_Amazon_chat | strict_evidence_fewshot/ensemble_gemma_gpt-oss_nemotron             | 467     | 467  | 467  | 0         | 0         |  89.1% |  43.7% |  39.1% |  40.2% |  62.7% |
| shopping_ebay_chat   | balanced_fewshot/ensemble_gemma_gpt-oss_nemotron                    | 547     | 547  | 547  | 0         | 0         |  92.6% |  40.5% |  47.5% |  43.7% |  76.6% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/ensemble_gemma_gpt-oss_nemotron | 547     | 547  | 547  | 0         | 0         |  92.1% |  54.1% |  51.6% |  52.6% |  71.7% |
| shopping_ebay_chat   | strict_evidence_fewshot/ensemble_gemma_gpt-oss_nemotron             | 547     | 547  | 547  | 0         | 0         |  90.4% |  43.5% |  39.0% |  40.1% |  65.8% |

## Per Label

### shopping_Amazon_chat / balanced_fewshot/ensemble_gemma_gpt-oss_nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 321      | 248 | 73 | 8  |  82.7% |  77.3% |  96.9% |  86.0% |
| BE    | 467  | 262     | 274      | 242 | 32 | 20 |  88.9% |  88.3% |  92.4% |  90.3% |
| CI    | 467  | 7       | 1        | 0   | 1  | 7  |  98.3% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 1        | 1   | 0  | 7  |  98.5% | 100.0% |  12.5% |  22.2% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/ensemble_gemma_gpt-oss_nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 258      | 209 | 49 | 47 |  79.4% |  81.0% |  81.6% |  81.3% |
| BE    | 467  | 262     | 237      | 216 | 21 | 46 |  85.7% |  91.1% |  82.4% |  86.6% |
| CI    | 467  | 7       | 4        | 2   | 2  | 5  |  98.5% |  50.0% |  28.6% |  36.4% |
| BI    | 467  | 8       | 2        | 1   | 1  | 7  |  98.3% |  50.0% |  12.5% |  20.0% |

### shopping_Amazon_chat / strict_evidence_fewshot/ensemble_gemma_gpt-oss_nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 313      | 246 | 67 | 10  |  83.5% |  78.6% |  96.1% |  86.5% |
| BE    | 467  | 262     | 164      | 158 | 6  | 104 |  76.4% |  96.3% |  60.3% |  74.2% |
| CI    | 467  | 7       | 1        | 0   | 1  | 7   |  98.3% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 0        | 0   | 0  | 8   |  98.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / balanced_fewshot/ensemble_gemma_gpt-oss_nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 363      | 288 | 75 | 3  |  85.7% |  79.3% |  99.0% |  88.1% |
| BE    | 547  | 270     | 297      | 246 | 51 | 24 |  86.3% |  82.8% |  91.1% |  86.8% |
| CI    | 547  | 5       | 1        | 0   | 1  | 5  |  98.9% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 0        | 0   | 0  | 4  |  99.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/ensemble_gemma_gpt-oss_nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 314      | 255 | 59 | 36 |  82.6% |  81.2% |  87.6% |  84.3% |
| BE    | 547  | 270     | 224      | 213 | 11 | 57 |  87.6% |  95.1% |  78.9% |  86.2% |
| CI    | 547  | 5       | 5        | 2   | 3  | 3  |  98.9% |  40.0% |  40.0% |  40.0% |
| BI    | 547  | 4       | 0        | 0   | 0  | 4  |  99.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / strict_evidence_fewshot/ensemble_gemma_gpt-oss_nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 351      | 281 | 70 | 10  |  85.4% |  80.1% |  96.6% |  87.5% |
| BE    | 547  | 270     | 170      | 160 | 10 | 110 |  78.1% |  94.1% |  59.3% |  72.7% |
| CI    | 547  | 5       | 2        | 0   | 2  | 5   |  98.7% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 0        | 0   | 0  | 4   |  99.3% |   0.0% |   0.0% |   0.0% |
