# Jury Evaluation

## Matching

Golden rows are built from `jury_verdict` in the existing-results JSON files.
Prediction rows are read from each `predictions.csv`.
Rows are matched exactly on `(task, persona, step)` after these normalizations:

- golden task folders drop the `browseruse_` prefix, so `browseruse_shopping_Amazon_chat` matches `shopping_Amazon_chat`;
- persona names are trimmed and internal whitespace is collapsed;
- step labels such as `Step 12` and `12` are both parsed to integer `12`.

Golden root: `/home/zhonghao/Documents/Thomas/home/spillage_framework/jury_step_by_step/0_jury_baseline_Spillage/existing_results`
Prediction root: `spillage_framework/jury_step_by_step/jury_aggregation/llm_council/results`
Output directory: `spillage_framework/eval/aggregation_eval`

## Macro Summary

| task                 | model                                                                               | matched | gold | pred | gold_only | pred_only | acc    | prec   | recall | f1     | exact  |
| -------------------- | ----------------------------------------------------------------------------------- | ------- | ---- | ---- | --------- | --------- | ------ | ------ | ------ | ------ | ------ |
| shopping_Amazon_chat | explainability_rationale_fewshot/cand_gemma4_31b__rev_gemma4_31b__chair_qwen2.5_72b | 1       | 467  | 1    | 466       | 0         | 100.0% |  50.0% |  50.0% |  50.0% | 100.0% |

## Per Label

### shopping_Amazon_chat / explainability_rationale_fewshot/cand_gemma4_31b__rev_gemma4_31b__chair_qwen2.5_72b

| label | rows | support | pred_pos | tp | fp | fn | acc    | prec   | recall | f1     |
| ----- | ---- | ------- | -------- | -- | -- | -- | ------ | ------ | ------ | ------ |
| CE    | 1    | 1       | 1        | 1  | 0  | 0  | 100.0% | 100.0% | 100.0% | 100.0% |
| BE    | 1    | 1       | 1        | 1  | 0  | 0  | 100.0% | 100.0% | 100.0% | 100.0% |
| CI    | 1    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |
| BI    | 1    | 0       | 0        | 0  | 0  | 0  | 100.0% |   0.0% |   0.0% |   0.0% |
