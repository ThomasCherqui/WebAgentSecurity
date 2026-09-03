# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_release/data/input/gold/gold.csv`
Prediction root: `data/output/prompt_judges`
Output directory: `evaluation/results/prompt_judges`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                                        | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | -------------------------------------------- | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | comparative_counterexamples_fewshot/gemma    | 2     | 1014    | 100.0%   |  70.9% |  84.0% |  62.6% |  93.5% |  77.6% |
| 2    | balanced_fewshot/gemma                       | 2     | 1014    | 100.0%   |  48.2% |  52.4% |  48.8% |  91.5% |  74.4% |
| 3    | comparative_counterexamples_fewshot/gpt-oss  | 2     | 1014    | 100.0%   |  47.4% |  49.2% |  47.8% |  89.5% |  65.0% |
| 4    | balanced_fewshot/gpt-oss                     | 2     | 1014    | 100.0%   |  47.2% |  49.5% |  53.7% |  91.1% |  71.0% |
| 5    | strict_evidence_fewshot/gemma                | 2     | 1014    | 100.0%   |  45.9% |  44.0% |  56.8% |  90.8% |  67.5% |
| 6    | strict_evidence_fewshot/gpt-oss              | 2     | 1014    | 100.0%   |  42.7% |  41.5% |  46.4% |  89.3% |  62.7% |
| 7    | balanced_fewshot/nemotron                    | 2     | 1014    | 100.0%   |  38.4% |  36.0% |  41.6% |  87.7% |  59.6% |
| 8    | comparative_counterexamples_fewshot/nemotron | 2     | 1014    | 100.0%   |  34.9% |  32.0% |  46.9% |  82.0% |  40.7% |
| 9    | strict_evidence_fewshot/nemotron             | 2     | 1014    | 100.0%   |  30.2% |  23.3% |  43.1% |  82.3% |  42.1% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                                        | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | -------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | balanced_fewshot/gemma                       | 467     | 467  | 467  | 0         | 0         |  91.6% |  60.6% |  55.9% |  54.0% |  73.9% |
| shopping_Amazon_chat | balanced_fewshot/gpt-oss                     | 467     | 467  | 467  | 0         | 0         |  90.4% |  66.1% |  48.0% |  48.4% |  68.3% |
| shopping_Amazon_chat | balanced_fewshot/nemotron                    | 467     | 467  | 467  | 0         | 0         |  88.0% |  42.6% |  37.0% |  39.4% |  60.0% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/gemma    | 467     | 467  | 467  | 0         | 0         |  92.9% |  60.6% |  79.1% |  68.1% |  76.0% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/gpt-oss  | 467     | 467  | 467  | 0         | 0         |  88.4% |  46.2% |  42.5% |  44.2% |  61.0% |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/nemotron | 467     | 467  | 467  | 0         | 0         |  80.7% |  49.5% |  35.6% |  37.3% |  38.1% |
| shopping_Amazon_chat | strict_evidence_fewshot/gemma                | 467     | 467  | 467  | 0         | 0         |  90.2% |  43.1% |  41.9% |  41.6% |  66.6% |
| shopping_Amazon_chat | strict_evidence_fewshot/gpt-oss              | 467     | 467  | 467  | 0         | 0         |  88.2% |  42.9% |  38.6% |  39.5% |  59.1% |
| shopping_Amazon_chat | strict_evidence_fewshot/nemotron             | 467     | 467  | 467  | 0         | 0         |  81.8% |  43.4% |  24.0% |  30.7% |  39.6% |
| shopping_ebay_chat   | balanced_fewshot/gemma                       | 547     | 547  | 547  | 0         | 0         |  91.4% |  38.7% |  49.3% |  43.3% |  74.8% |
| shopping_ebay_chat   | balanced_fewshot/gpt-oss                     | 547     | 547  | 547  | 0         | 0         |  91.6% |  43.1% |  50.7% |  46.3% |  73.3% |
| shopping_ebay_chat   | balanced_fewshot/nemotron                    | 547     | 547  | 547  | 0         | 0         |  87.4% |  40.8% |  35.1% |  37.5% |  59.2% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/gemma    | 547     | 547  | 547  | 0         | 0         |  94.1% |  64.3% |  88.1% |  73.3% |  79.0% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/gpt-oss  | 547     | 547  | 547  | 0         | 0         |  90.5% |  49.1% |  55.0% |  50.0% |  68.4% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/nemotron | 547     | 547  | 547  | 0         | 0         |  83.0% |  44.6% |  28.9% |  33.0% |  43.0% |
| shopping_ebay_chat   | strict_evidence_fewshot/gemma                | 547     | 547  | 547  | 0         | 0         |  91.2% |  68.6% |  45.8% |  49.5% |  68.2% |
| shopping_ebay_chat   | strict_evidence_fewshot/gpt-oss              | 547     | 547  | 547  | 0         | 0         |  90.2% |  49.4% |  43.9% |  45.4% |  65.8% |
| shopping_ebay_chat   | strict_evidence_fewshot/nemotron             | 547     | 547  | 547  | 0         | 0         |  82.7% |  42.8% |  22.8% |  29.7% |  44.2% |

## Per Label

### shopping_Amazon_chat / balanced_fewshot/gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 340      | 256 | 84 | 0  |  82.0% |  75.3% | 100.0% |  85.9% |
| BE    | 467  | 262     | 303      | 254 | 49 | 8  |  87.8% |  83.8% |  96.9% |  89.9% |
| CI    | 467  | 7       | 3        | 1   | 2  | 6  |  98.3% |  33.3% |  14.3% |  20.0% |
| BI    | 467  | 8       | 2        | 1   | 1  | 7  |  98.3% |  50.0% |  12.5% |  20.0% |

### shopping_Amazon_chat / balanced_fewshot/gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 300      | 232 | 68 | 24 |  80.3% |  77.3% |  90.6% |  83.5% |
| BE    | 467  | 262     | 268      | 233 | 35 | 29 |  86.3% |  86.9% |  88.9% |  87.9% |
| CI    | 467  | 7       | 10       | 0   | 10 | 7  |  96.4% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 1        | 1   | 0  | 7  |  98.5% | 100.0% |  12.5% |  22.2% |

### shopping_Amazon_chat / balanced_fewshot/nemotron

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 254      | 206 | 48 | 50 |  79.0% |  81.1% |  80.5% |  80.8% |
| BE    | 467  | 262     | 198      | 177 | 21 | 85 |  77.3% |  89.4% |  67.6% |  77.0% |
| CI    | 467  | 7       | 2        | 0   | 2  | 7  |  98.1% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 4        | 0   | 4  | 8  |  97.4% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 321      | 256 | 65 | 0  |  86.1% |  79.8% | 100.0% |  88.7% |
| BE    | 467  | 262     | 283      | 249 | 34 | 13 |  89.9% |  88.0% |  95.0% |  91.4% |
| CI    | 467  | 7       | 13       | 5   | 8  | 2  |  97.9% |  38.5% |  71.4% |  50.0% |
| BI    | 467  | 8       | 11       | 4   | 7  | 4  |  97.6% |  36.4% |  50.0% |  42.1% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 248      | 194 | 54 | 62 |  75.2% |  78.2% |  75.8% |  77.0% |
| BE    | 467  | 262     | 232      | 209 | 23 | 53 |  83.7% |  90.1% |  79.8% |  84.6% |
| CI    | 467  | 7       | 6        | 1   | 5  | 6  |  97.6% |  16.7% |  14.3% |  15.4% |
| BI    | 467  | 8       | 5        | 0   | 5  | 8  |  97.2% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / comparative_counterexamples_fewshot/nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 147      | 122 | 25 | 134 |  66.0% |  83.0% |  47.7% |  60.5% |
| BE    | 467  | 262     | 122      | 113 | 9  | 149 |  66.2% |  92.6% |  43.1% |  58.9% |
| CI    | 467  | 7       | 9        | 1   | 8  | 6   |  97.0% |  11.1% |  14.3% |  12.5% |
| BI    | 467  | 8       | 27       | 3   | 24 | 5   |  93.8% |  11.1% |  37.5% |  17.1% |

### shopping_Amazon_chat / strict_evidence_fewshot/gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 327      | 254 | 73 | 2  |  83.9% |  77.7% |  99.2% |  87.1% |
| BE    | 467  | 262     | 189      | 179 | 10 | 83 |  80.1% |  94.7% |  68.3% |  79.4% |
| CI    | 467  | 7       | 0        | 0   | 0  | 7  |  98.5% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 0        | 0   | 0  | 8  |  98.3% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / strict_evidence_fewshot/gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 317      | 242 | 75 | 14  |  80.9% |  76.3% |  94.5% |  84.5% |
| BE    | 467  | 262     | 165      | 157 | 8  | 105 |  75.8% |  95.2% |  59.9% |  73.5% |
| CI    | 467  | 7       | 3        | 0   | 3  | 7   |  97.9% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 0        | 0   | 0  | 8   |  98.3% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / strict_evidence_fewshot/nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 163      | 133 | 30 | 123 |  67.2% |  81.6% |  52.0% |  63.5% |
| BE    | 467  | 262     | 125      | 115 | 10 | 147 |  66.4% |  92.0% |  43.9% |  59.4% |
| CI    | 467  | 7       | 14       | 0   | 14 | 7   |  95.5% |   0.0% |   0.0% |   0.0% |
| BI    | 467  | 8       | 1        | 0   | 1  | 8   |  98.1% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / balanced_fewshot/gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 366      | 285 | 81 | 6  |  84.1% |  77.9% |  97.9% |  86.8% |
| BE    | 547  | 270     | 349      | 268 | 81 | 2  |  84.8% |  76.8% |  99.3% |  86.6% |
| CI    | 547  | 5       | 6        | 0   | 6  | 5  |  98.0% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 3        | 0   | 3  | 4  |  98.7% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / balanced_fewshot/gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 343      | 276 | 67 | 15 |  85.0% |  80.5% |  94.8% |  87.1% |
| BE    | 547  | 270     | 287      | 238 | 49 | 32 |  85.2% |  82.9% |  88.1% |  85.5% |
| CI    | 547  | 5       | 11       | 1   | 10 | 4  |  97.4% |   9.1% |  20.0% |  12.5% |
| BI    | 547  | 4       | 2        | 0   | 2  | 4  |  98.9% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / balanced_fewshot/nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 285      | 225 | 60 | 66  |  77.0% |  78.9% |  77.3% |  78.1% |
| BE    | 547  | 270     | 202      | 170 | 32 | 100 |  75.9% |  84.2% |  63.0% |  72.0% |
| CI    | 547  | 5       | 5        | 0   | 5  | 5   |  98.2% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 3        | 0   | 3  | 4   |  98.7% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 340      | 277 | 63 | 14 |  85.9% |  81.5% |  95.2% |  87.8% |
| BE    | 547  | 270     | 298      | 263 | 35 | 7  |  92.3% |  88.3% |  97.4% |  92.6% |
| CI    | 547  | 5       | 8        | 3   | 5  | 2  |  98.7% |  37.5% |  60.0% |  46.2% |
| BI    | 547  | 4       | 8        | 4   | 4  | 0  |  99.3% |  50.0% | 100.0% |  66.7% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 308      | 249 | 59 | 42 |  81.5% |  80.8% |  85.6% |  83.1% |
| BE    | 547  | 270     | 222      | 201 | 21 | 69 |  83.5% |  90.5% |  74.4% |  81.7% |
| CI    | 547  | 5       | 12       | 3   | 9  | 2  |  98.0% |  25.0% |  60.0% |  35.3% |
| BI    | 547  | 4       | 2        | 0   | 2  | 4  |  98.9% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 188      | 149 | 39 | 142 |  66.9% |  79.3% |  51.2% |  62.2% |
| BE    | 547  | 270     | 129      | 120 | 9  | 150 |  70.9% |  93.0% |  44.4% |  60.2% |
| CI    | 547  | 5       | 16       | 1   | 15 | 4   |  96.5% |   6.2% |  20.0% |   9.5% |
| BI    | 547  | 4       | 9        | 0   | 9  | 4   |  97.6% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / strict_evidence_fewshot/gemma

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 361      | 286 | 75 | 5  |  85.4% |  79.2% |  98.3% |  87.7% |
| BE    | 547  | 270     | 184      | 175 | 9  | 95 |  81.0% |  95.1% |  64.8% |  77.1% |
| CI    | 547  | 5       | 1        | 1   | 0  | 4  |  99.3% | 100.0% |  20.0% |  33.3% |
| BI    | 547  | 4       | 0        | 0   | 0  | 4  |  99.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / strict_evidence_fewshot/gpt-oss

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 354      | 282 | 72 | 9   |  85.2% |  79.7% |  96.9% |  87.4% |
| BE    | 547  | 270     | 171      | 159 | 12 | 111 |  77.5% |  93.0% |  58.9% |  72.1% |
| CI    | 547  | 5       | 4        | 1   | 3  | 4   |  98.7% |  25.0% |  20.0% |  22.2% |
| BI    | 547  | 4       | 0        | 0   | 0  | 4   |  99.3% |   0.0% |   0.0% |   0.0% |

### shopping_ebay_chat / strict_evidence_fewshot/nemotron

| label | rows | support | pred_pos | tp  | fp | fn  | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | --- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 169      | 138 | 31 | 153 |  66.4% |  81.7% |  47.4% |  60.0% |
| BE    | 547  | 270     | 132      | 118 | 14 | 152 |  69.7% |  89.4% |  43.7% |  58.7% |
| CI    | 547  | 5       | 19       | 0   | 19 | 5   |  95.6% |   0.0% |   0.0% |   0.0% |
| BI    | 547  | 4       | 1        | 0   | 1  | 4   |  99.1% |   0.0% |   0.0% |   0.0% |
