# Post-hoc baseline: condition + TF-IDF

Added after the one-shot test evaluation; C fixed at 1.0, threshold from validation F1. Intervals: 95% bootstrap over scenarios.

## turn level (val AUROC 0.824, threshold 0.3866)

| split | n (harm) | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | neutral | conversion | harmful |
|---|---|---|---|---|---|---|---|---|---|
| test | 354 (212) | 0.829 [0.80, 0.86] | 0.876 | 0.802 | 0.453 | 0.712 | 0.793 | 0.813 | 0.781 |
| test_ood | 424 (253) | 0.857 [0.82, 0.89] | 0.890 | 0.832 | 0.547 | 0.760 | 0.872 | 0.767 | 0.769 |

## conv level (val AUROC 0.846, threshold 0.4513)

| split | n (harm) | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | neutral | conversion | harmful |
|---|---|---|---|---|---|---|---|---|---|
| test | 96 (86) | 0.884 [0.81, 0.98] | 0.986 | 0.930 | 0.330 | 0.665 | 0.661 | 0.917 | n/a |
| test_ood | 120 (101) | 0.913 [0.87, 0.95] | 0.984 | 0.898 | 0.452 | 0.751 | 0.788 | 0.926 | n/a |
