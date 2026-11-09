# Validation sweep (train-fit, val-scored)

Baselines (val AUROC): majority/turn 0.500, condition_only/turn 0.690, tfidf/turn 0.816, majority/conv 0.500, condition_only/conv 0.751, tfidf/conv 0.842

## lr / turn
Best: position mean, layer 17, C 0.001 -> val AUROC 0.869 (neutral 0.803, conversion 0.868, harmful 0.837)

| position | best layer | best val AUROC | worst layer | worst val AUROC |
|---|---|---|---|---|
| pre | 17 | 0.807 | 0 | 0.500 |
| last | 18 | 0.795 | 0 | 0.456 |
| mean | 17 | 0.869 | 0 | 0.794 |

## lr / conv_final
Best: position mean, layer 21, C 0.0001 -> val AUROC 0.882 (neutral 0.754, conversion 0.948, harmful 0.839)

| position | best layer | best val AUROC | worst layer | worst val AUROC |
|---|---|---|---|---|
| pre | 18 | 0.843 | 0 | 0.500 |
| last | 34 | 0.875 | 0 | 0.538 |
| mean | 21 | 0.882 | 1 | 0.794 |

## lr / conv_mean
Best: position mean, layer 35, C 1.0 -> val AUROC 0.912 (neutral 0.896, conversion 0.933, harmful 0.677)

| position | best layer | best val AUROC | worst layer | worst val AUROC |
|---|---|---|---|---|
| pre | 18 | 0.893 | 0 | 0.500 |
| last | 15 | 0.863 | 0 | 0.413 |
| mean | 35 | 0.912 | 0 | 0.842 |
