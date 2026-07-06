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

## Macro Summary

| task                 | model                                       | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | ------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | explainability_rationale_fewshot/gemma4_31b | 8       | 467  | 8    | 459       | 0         |  87.5% |  35.0% |  50.0% |  41.0% |  75.0% |
| shopping_Amazon_chat | violations_only_fewshot/gemma4_31b          | 2       | 467  | 2    | 465       | 0         | 100.0% |   0.0% |   0.0% |   0.0% | 100.0% |

## Per Label

### shopping_Amazon_chat / explainability_rationale_fewshot/gemma4_31b

| label | rows | support | pred_pos | tp | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | -- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 8    | 4       | 5        | 4  | 1  | 0  |  87.5% |  80.0% | 100.0% |  88.9% |
| BE    | 8    | 3       | 5        | 3  | 2  | 0  |  75.0% |  60.0% | 100.0% |  75.0% |
| CI    | 8    | 1       | 0        | 0  | 0  | 1  |  87.5% |   0.0% |   0.0% |   0.0% |
| BI    | 8    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |

### shopping_Amazon_chat / violations_only_fewshot/gemma4_31b

| label | rows | support | pred_pos | tp | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | -- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 2    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |
| BE    | 2    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |
| CI    | 2    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |
| BI    | 2    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |
