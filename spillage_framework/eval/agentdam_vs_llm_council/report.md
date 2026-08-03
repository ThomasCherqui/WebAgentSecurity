# LLM Council vs AgentDAM

Gold source: `spillage_framework/eval/gold_corrected.csv`

Both systems are scored on the same intersection of `(task, persona, step)`. AgentDAM contains 475 predictions, of which 464 match the gold and LLM Council keys (456 Amazon, 8 eBay). The head-to-head comparison therefore uses those 464 rows.

## Results

| scope | rank | system | compared | coverage | accuracy | precision | recall | F1 | TP | TN | FP | FN |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CE_only | 1 | llm_council | 464 | 45.8% | 74.6% | 80.9% | 69.3% | 74.7% | 174 | 172 | 41 | 77 |
| CE_only | 2 | agentdam | 464 | 45.8% | 61.2% | 79.8% | 37.8% | 51.4% | 95 | 189 | 24 | 156 |
| oversharing_any_label | 1 | llm_council | 464 | 45.8% | 85.1% | 89.8% | 87.1% | 88.4% | 263 | 132 | 30 | 39 |
| oversharing_any_label | 2 | agentdam | 464 | 45.8% | 53.7% | 86.6% | 34.1% | 48.9% | 103 | 146 | 16 | 199 |

## Definitions

- `CE_only`: AgentDAM score and LLM Council CE are compared with gold CE.
- `oversharing_any_label`: positive if any of CE, BE, CI, or BI is positive.
- Rankings use F1, then recall, precision, and accuracy.
