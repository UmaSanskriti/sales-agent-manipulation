# Held-out results (frozen probes; harm = judge harm_tier > 0)

Information access: judge = fact sheet + visible transcript (no system prompt, no condition); probe = residual stream with system prompt + dialogue + reply, visible-text replay (no reasoning); TF-IDF = reply words only; condition-only = condition id; majority = nothing.

Confusion matrices are [[TN, FP], [FN, TP]] (rows = judge label, cols = prediction). Intervals are 95% bootstrap over scenarios.

## test

| method | n (harm) | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | P/R harm | P/R not harm | confusion |
|---|---|---|---|---|---|---|---|---|---|
| probe lr / turn (L17, mean) | 354 (212) | 0.866 [0.84, 0.90] | 0.910 | 0.793 | 0.540 | 0.775 | 0.85/0.74 | 0.68/0.81 | [[115, 27], [55, 157]] |
| probe lr / conv_final (L21, mean) | 96 (86) | 0.870 [0.79, 0.99] | 0.983 | 0.955 | 0.475 | 0.688 | 0.93/0.98 | 0.67/0.40 | [[4, 6], [2, 84]] |
| probe lr / conv_mean (L35, mean) | 96 (86) | 0.881 [0.83, 0.96] | 0.985 | 0.938 | 0.227 | 0.583 | 0.91/0.97 | 0.40/0.20 | [[2, 8], [3, 83]] |
| baseline majority / turn | 354 (212) | 0.500 [0.50, 0.50] | 0.599 | 0.749 | 0.000 | 0.500 | 0.60/1.00 | 0.00/0.00 | [[0, 142], [0, 212]] |
| baseline condition-only / turn | 354 (212) | 0.695 [0.66, 0.74] | 0.730 | 0.749 | 0.000 | 0.500 | 0.60/1.00 | 0.00/0.00 | [[0, 142], [0, 212]] |
| baseline tfidf / turn | 354 (212) | 0.836 [0.79, 0.87] | 0.889 | 0.801 | 0.446 | 0.707 | 0.74/0.87 | 0.74/0.54 | [[77, 65], [27, 185]] |
| baseline majority / conv | 96 (86) | 0.500 [0.50, 0.50] | 0.896 | 0.945 | 0.000 | 0.500 | 0.90/1.00 | 0.00/0.00 | [[0, 10], [0, 86]] |
| baseline condition-only / conv | 96 (86) | 0.798 [0.73, 0.87] | 0.960 | 0.945 | 0.000 | 0.500 | 0.90/1.00 | 0.00/0.00 | [[0, 10], [0, 86]] |
| baseline tfidf / conv | 96 (86) | 0.822 [0.69, 0.96] | 0.974 | 0.904 | 0.305 | 0.686 | 0.94/0.87 | 0.31/0.50 | [[5, 5], [11, 75]] |
| probe lr / turn->conv max (L17, mean) | 96 (86) | 0.850 [0.72, 0.97] | 0.979 | 0.908 | 0.430 | 0.780 | 0.96/0.86 | 0.37/0.70 | [[7, 3], [12, 74]] |

Within-condition AUROC (does the probe read behavior, not just the prompt?):

| method | neutral | conversion | harmful |
|---|---|---|---|
| probe lr / turn (L17, mean) | 0.826 | 0.856 | 0.813 |
| probe lr / conv_final (L21, mean) | 0.745 | 0.833 | nan |
| probe lr / conv_mean (L35, mean) | 0.818 | 0.833 | nan |
| baseline majority / turn | 0.500 | 0.500 | 0.500 |
| baseline condition-only / turn | 0.500 | 0.500 | 0.500 |
| baseline tfidf / turn | 0.780 | 0.817 | 0.774 |
| baseline majority / conv | 0.500 | 0.500 | nan |
| baseline condition-only / conv | 0.500 | 0.500 | nan |
| baseline tfidf / conv | 0.656 | 0.950 | nan |
| probe lr / turn->conv max (L17, mean) | 0.776 | 0.733 | nan |

## test_ood

| method | n (harm) | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | P/R harm | P/R not harm | confusion |
|---|---|---|---|---|---|---|---|---|---|
| probe lr / turn (L17, mean) | 424 (253) | 0.892 [0.86, 0.92] | 0.928 | 0.799 | 0.565 | 0.788 | 0.87/0.74 | 0.68/0.84 | [[143, 28], [66, 187]] |
| probe lr / conv_final (L21, mean) | 120 (101) | 0.899 [0.82, 0.94] | 0.979 | 0.933 | 0.495 | 0.696 | 0.90/0.97 | 0.73/0.42 | [[8, 11], [3, 98]] |
| probe lr / conv_mean (L35, mean) | 120 (101) | 0.925 [0.88, 0.96] | 0.985 | 0.933 | 0.510 | 0.717 | 0.91/0.96 | 0.69/0.47 | [[9, 10], [4, 97]] |
| baseline majority / turn | 424 (253) | 0.500 [0.50, 0.50] | 0.597 | 0.747 | 0.000 | 0.500 | 0.60/1.00 | 0.00/0.00 | [[0, 171], [0, 253]] |
| baseline condition-only / turn | 424 (253) | 0.722 [0.68, 0.76] | 0.752 | 0.747 | 0.000 | 0.500 | 0.60/1.00 | 0.00/0.00 | [[0, 171], [0, 253]] |
| baseline tfidf / turn | 424 (253) | 0.854 [0.81, 0.89] | 0.895 | 0.832 | 0.543 | 0.755 | 0.77/0.90 | 0.81/0.61 | [[104, 67], [25, 228]] |
| baseline majority / conv | 120 (101) | 0.500 [0.50, 0.50] | 0.842 | 0.914 | 0.000 | 0.500 | 0.84/1.00 | 0.00/0.00 | [[0, 19], [0, 101]] |
| baseline condition-only / conv | 120 (101) | 0.792 [0.75, 0.85] | 0.938 | 0.914 | 0.000 | 0.500 | 0.84/1.00 | 0.00/0.00 | [[0, 19], [0, 101]] |
| baseline tfidf / conv | 120 (101) | 0.894 [0.83, 0.94] | 0.980 | 0.860 | 0.425 | 0.764 | 0.94/0.79 | 0.40/0.74 | [[14, 5], [21, 80]] |
| probe lr / turn->conv max (L17, mean) | 120 (101) | 0.962 [0.92, 0.99] | 0.993 | 0.939 | 0.659 | 0.855 | 0.96/0.92 | 0.65/0.79 | [[15, 4], [8, 93]] |

Within-condition AUROC (does the probe read behavior, not just the prompt?):

| method | neutral | conversion | harmful |
|---|---|---|---|
| probe lr / turn (L17, mean) | 0.880 | 0.846 | 0.863 |
| probe lr / conv_final (L21, mean) | 0.742 | 0.943 | nan |
| probe lr / conv_mean (L35, mean) | 0.898 | 0.903 | nan |
| baseline majority / turn | 0.500 | 0.500 | 0.500 |
| baseline condition-only / turn | 0.500 | 0.500 | 0.500 |
| baseline tfidf / turn | 0.865 | 0.772 | 0.794 |
| baseline majority / conv | 0.500 | 0.500 | nan |
| baseline condition-only / conv | 0.500 | 0.500 | nan |
| baseline tfidf / conv | 0.780 | 0.914 | nan |
| probe lr / turn->conv max (L17, mean) | 0.915 | 0.971 | nan |
