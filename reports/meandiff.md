# Post-hoc sanity check: mean-difference probe

Direction = centroid(harm) - centroid(not harm) on train; threshold from val F1; nothing tuned on test. 'raw' = unstandardized activations, 'std' = train-standardized. Intervals: 95% bootstrap over scenarios.

## test

| method | val AUROC | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | neutral | conversion | harmful |
|---|---|---|---|---|---|---|---|---|---|
| meandiff raw / turn (frozen LR layer: L17, mean) | 0.777 | 0.766 [0.69, 0.85] | 0.809 | 0.804 | 0.447 | 0.703 | 0.728 | 0.769 | 0.686 |
| meandiff raw / turn (own val-best layer: L22, mean) | 0.807 | 0.799 [0.74, 0.86] | 0.839 | 0.822 | 0.509 | 0.738 | 0.723 | 0.781 | 0.706 |
| meandiff std / turn (frozen LR layer: L17, mean) | 0.810 | 0.807 [0.74, 0.87] | 0.848 | 0.812 | 0.505 | 0.746 | 0.749 | 0.797 | 0.719 |
| meandiff std / turn (own val-best layer: L19, mean) | 0.815 | 0.810 [0.75, 0.87] | 0.848 | 0.802 | 0.481 | 0.736 | 0.745 | 0.798 | 0.705 |
| meandiff raw / conv_final (frozen LR layer: L21, mean) | 0.856 | 0.880 [0.78, 0.99] | 0.985 | 0.911 | 0.264 | 0.648 | 0.693 | 0.933 | n/a |
| meandiff raw / conv_final (own val-best layer: L36, last) | 0.863 | 0.901 [0.77, 1.00] | 0.986 | 0.950 | 0.331 | 0.594 | 0.818 | 0.983 | n/a |
| meandiff std / conv_final (frozen LR layer: L21, mean) | 0.859 | 0.879 [0.80, 0.98] | 0.985 | 0.936 | 0.358 | 0.671 | 0.708 | 0.933 | n/a |
| meandiff std / conv_final (own val-best layer: L18, mean) | 0.876 | 0.894 [0.82, 0.98] | 0.987 | 0.942 | 0.442 | 0.721 | 0.750 | 0.917 | n/a |
| meandiff raw / conv_mean (frozen LR layer: L35, mean) | 0.793 | 0.840 [0.72, 0.97] | 0.977 | 0.955 | 0.441 | 0.644 | 0.688 | 0.867 | n/a |
| meandiff raw / conv_mean (own val-best layer: L18, pre) | 0.869 | 0.894 [0.82, 0.97] | 0.986 | 0.942 | 0.442 | 0.721 | 0.849 | 0.717 | n/a |
| meandiff std / conv_mean (frozen LR layer: L35, mean) | 0.798 | 0.826 [0.69, 0.97] | 0.975 | 0.961 | 0.527 | 0.650 | 0.656 | 0.883 | n/a |
| meandiff std / conv_mean (own val-best layer: L18, pre) | 0.877 | 0.909 [0.84, 0.98] | 0.988 | 0.940 | 0.535 | 0.809 | 0.865 | 0.733 | n/a |

## test_ood

| method | val AUROC | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | neutral | conversion | harmful |
|---|---|---|---|---|---|---|---|---|---|
| meandiff raw / turn (frozen LR layer: L17, mean) | 0.777 | 0.781 [0.74, 0.82] | 0.836 | 0.797 | 0.419 | 0.685 | 0.773 | 0.752 | 0.717 |
| meandiff raw / turn (own val-best layer: L22, mean) | 0.807 | 0.829 [0.79, 0.87] | 0.867 | 0.833 | 0.543 | 0.754 | 0.790 | 0.784 | 0.742 |
| meandiff std / turn (frozen LR layer: L17, mean) | 0.810 | 0.838 [0.79, 0.88] | 0.875 | 0.818 | 0.529 | 0.759 | 0.819 | 0.801 | 0.757 |
| meandiff std / turn (own val-best layer: L19, mean) | 0.815 | 0.847 [0.80, 0.89] | 0.881 | 0.823 | 0.544 | 0.768 | 0.826 | 0.803 | 0.755 |
| meandiff raw / conv_final (frozen LR layer: L21, mean) | 0.856 | 0.870 [0.78, 0.92] | 0.970 | 0.909 | 0.485 | 0.761 | 0.736 | 0.914 | n/a |
| meandiff raw / conv_final (own val-best layer: L36, last) | 0.863 | 0.807 [0.74, 0.89] | 0.958 | 0.925 | 0.379 | 0.622 | 0.640 | 0.771 | n/a |
| meandiff std / conv_final (frozen LR layer: L21, mean) | 0.859 | 0.870 [0.78, 0.93] | 0.970 | 0.916 | 0.457 | 0.724 | 0.753 | 0.903 | n/a |
| meandiff std / conv_final (own val-best layer: L18, mean) | 0.876 | 0.885 [0.80, 0.93] | 0.975 | 0.915 | 0.480 | 0.745 | 0.764 | 0.931 | n/a |
| meandiff raw / conv_mean (frozen LR layer: L35, mean) | 0.793 | 0.811 [0.70, 0.88] | 0.960 | 0.925 | 0.397 | 0.643 | 0.662 | 0.731 | n/a |
| meandiff raw / conv_mean (own val-best layer: L18, pre) | 0.869 | 0.870 [0.79, 0.92] | 0.974 | 0.907 | 0.367 | 0.671 | 0.813 | 0.869 | n/a |
| meandiff std / conv_mean (frozen LR layer: L35, mean) | 0.798 | 0.842 [0.76, 0.90] | 0.969 | 0.925 | 0.379 | 0.622 | 0.701 | 0.783 | n/a |
| meandiff std / conv_mean (own val-best layer: L18, pre) | 0.877 | 0.877 [0.80, 0.93] | 0.976 | 0.902 | 0.348 | 0.666 | 0.810 | 0.886 | n/a |
