# Jury Evaluation

## Matching

Reference rows are loaded from the configured reference-annotation source.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- legacy reference task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Reference source: `data/input/gold/gold.csv`
Prediction root: `data/output/aggregation/llm_council`
Output directory: `evaluation/results/aggregation/llm_council`

## Model Ranking

Primary ranking is weighted macro F1 across matched rows. Accuracy is shown, but not used as the main decision metric because most labels are negative.

| rank | model                                            | tasks | matched | coverage | f1     | recall | prec   | acc    | exact  |
| ---- | ------------------------------------------------ | ----- | ------- | -------- | ------ | ------ | ------ | ------ | ------ |
| 1    | comparative_counterexamples_fewshot/qwen_council | 2     | 1014    | 100.0%   |  82.3% |  90.7% |  77.3% |  94.9% |  81.6% |

Decision hint: prefer the top macro-F1 model if you want the best overall CE/BE/CI/BI balance; prefer higher recall if missing leaks is more costly than false positives; prefer higher precision if manual review budget is tight.

## Macro Summary

| task                 | model                                            | matched | reference | pred | reference_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | ------------------------------------------------ | ------- | --------- | ---- | -------------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | comparative_counterexamples_fewshot/qwen_council | 467     | 467       | 467  | 0              | 0         |  94.4% |  77.9% |  82.3% |  79.3% |  80.7% |
| shopping_ebay_chat   | comparative_counterexamples_fewshot/qwen_council | 547     | 547       | 547  | 0              | 0         |  95.3% |  76.9% |  97.8% |  84.8% |  82.3% |

## Per Label

### shopping_Amazon_chat / comparative_counterexamples_fewshot/qwen_council

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 467  | 256     | 310      | 253 | 57 | 3  |  87.2% |  81.6% |  98.8% |  89.4% |
| BE    | 467  | 262     | 278      | 253 | 25 | 9  |  92.7% |  91.0% |  96.6% |  93.7% |
| CI    | 467  | 7       | 9        | 5   | 4  | 2  |  98.7% |  55.6% |  71.4% |  62.5% |
| BI    | 467  | 8       | 6        | 5   | 1  | 3  |  99.1% |  83.3% |  62.5% |  71.4% |

### shopping_ebay_chat / comparative_counterexamples_fewshot/qwen_council

| label | rows | support | pred_pos | tp  | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | --- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 547  | 291     | 342      | 284 | 58 | 7  |  88.1% |  83.0% |  97.6% |  89.7% |
| BE    | 547  | 270     | 268      | 253 | 15 | 17 |  94.1% |  94.4% |  93.7% |  94.1% |
| CI    | 547  | 5       | 10       | 5   | 5  | 0  |  99.1% |  50.0% | 100.0% |  66.7% |
| BI    | 547  | 4       | 5        | 4   | 1  | 0  |  99.8% |  80.0% | 100.0% |  88.9% |
