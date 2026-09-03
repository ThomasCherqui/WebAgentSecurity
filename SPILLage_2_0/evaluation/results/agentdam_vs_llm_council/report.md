# LLM Council vs AgentDAM

Gold source: `/home/zhonghao/Documents/Thomas/home/spillage_release/data/input/gold/gold.csv`

AgentDAM contains 1014 predictions. The common intersection of `(task, persona, step)` contains 1014 rows (467 Amazon, 547 eBay).

AgentDAM rows are aligned by ordinal position within each persona trajectory; its internal `source_step` is retained in `matched_rows.csv` for auditing.

## Results

| scope | rank | system | compared | coverage | accuracy | precision | recall | F1 | TP | TN | FP | FN |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CE_only | 1 | llm_council | 1014 | 100.0% | 87.7% | 82.4% | 98.2% | 89.6% | 537 | 352 | 115 | 10 |
| CE_only | 2 | agentdam | 1014 | 100.0% | 63.8% | 93.7% | 35.3% | 51.3% | 193 | 454 | 13 | 354 |
| oversharing_any_label | 1 | llm_council | 1014 | 100.0% | 91.5% | 88.0% | 100.0% | 93.6% | 630 | 298 | 86 | 0 |
| oversharing_any_label | 2 | agentdam | 1014 | 100.0% | 57.6% | 98.5% | 32.2% | 48.6% | 203 | 381 | 3 | 427 |

## Definitions

- `CE_only`: AgentDAM score and LLM Council CE are compared with gold CE.
- `oversharing_any_label`: positive if any of CE, BE, CI, or BI is positive.
- Rankings use F1, then recall, precision, and accuracy.
