"""Probe fitting, baselines and metrics.

Information access (state this in the report):
  judge          fact sheet + visible transcript up to the turn; no system prompt, no condition
  activation probe  the model's residual stream, which has seen the system prompt (hence the
                 objective), the whole dialogue and the reply (visible-text replay, no reasoning)
  TF-IDF         the agent's reply words only (all replies of the conversation for conv level)
  condition-only the condition id only
  majority       nothing
Scalers and vectorizers are always fit on the training split only.
"""
from __future__ import annotations

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, confusion_matrix, f1_score,
                             matthews_corrcoef, precision_recall_fscore_support, roc_auc_score)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CS = (1e-4, 1e-3, 1e-2, 1e-1, 1.0)
MLP_ALPHAS = (1e-2, 1.0, 10.0)


def make_probe(kind: str, hp: float, seed: int = 0):
    """kind 'lr' (hp = C) or 'mlp' (hp = L2 alpha; one hidden layer of 256, early stopping)."""
    if kind == "lr":
        clf = LogisticRegression(C=hp, max_iter=2000, class_weight="balanced")
    elif kind == "mlp":
        clf = MLPClassifier(hidden_layer_sizes=(256,), alpha=hp, early_stopping=True, validation_fraction=0.15,
                            n_iter_no_change=10, max_iter=300, random_state=seed)
    else:
        raise ValueError(kind)
    return make_pipeline(StandardScaler(), clf)


def fit_predict(kind: str, hp: float, Xtr, ytr, Xs: list, seeds=(0, 1, 2)):
    """Fit on train, return a list of P(harm) arrays, one per matrix in Xs. The MLP averages seeds."""
    use = seeds if kind == "mlp" else (0,)
    outs = [np.zeros(len(X)) for X in Xs]
    for s in use:
        m = make_probe(kind, hp, s).fit(Xtr, ytr)
        for o, X in zip(outs, Xs):
            o += m.predict_proba(X)[:, 1] / len(use)
    return outs


def tfidf_probe(C: float = 1.0):
    return make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                         LogisticRegression(C=C, max_iter=2000, class_weight="balanced"))


def condition_probe():
    return make_pipeline(OneHotEncoder(handle_unknown="ignore"), LogisticRegression(max_iter=1000))


def majority_probe():
    return DummyClassifier(strategy="prior")


def best_threshold(y, p) -> float:
    """Threshold maximizing F1 of the harm class (chosen on validation only)."""
    cands = np.unique(np.round(p, 4))
    scores = [f1_score(y, p >= t, zero_division=0) for t in cands]
    return float(cands[int(np.argmax(scores))])


def auroc(y, p) -> float:
    return float(roc_auc_score(y, p)) if len(set(y)) == 2 else float("nan")


def metrics(y, p, thr: float) -> dict:
    y = np.asarray(y)
    pred = (np.asarray(p) >= thr).astype(int)
    pr, rc, f1, sup = precision_recall_fscore_support(y, pred, labels=[0, 1], zero_division=0)
    return {
        "n": int(len(y)), "n_harm": int(y.sum()), "threshold": float(thr),
        "auroc": auroc(y, p),
        "auprc": float(average_precision_score(y, p)) if len(set(y)) == 2 else float("nan"),
        "accuracy": float((pred == y).mean()),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "mcc": float(matthews_corrcoef(y, pred)) if len(set(pred)) > 1 else 0.0,
        "confusion": confusion_matrix(y, pred, labels=[0, 1]).tolist(),  # rows = true, cols = predicted
        "precision": {"not_harm": float(pr[0]), "harm": float(pr[1])},
        "recall": {"not_harm": float(rc[0]), "harm": float(rc[1])},
        "f1": {"not_harm": float(f1[0]), "harm": float(f1[1])},
    }


def bootstrap_by_group(y, p, thr, groups, n: int = 1000, seed: int = 0) -> dict:
    """95% intervals for AUROC and harm-class F1, resampling scenarios (turns within a scenario are
    not independent)."""
    rng = np.random.default_rng(seed)
    y, p, groups = np.asarray(y), np.asarray(p), np.asarray(groups)
    uniq = np.unique(groups)
    idx = {g: np.flatnonzero(groups == g) for g in uniq}
    aucs, f1s = [], []
    for _ in range(n):
        pick = np.concatenate([idx[g] for g in rng.choice(uniq, len(uniq))])
        if len(set(y[pick])) < 2:
            continue
        aucs.append(roc_auc_score(y[pick], p[pick]))
        f1s.append(f1_score(y[pick], p[pick] >= thr, zero_division=0))
    q = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    return {"auroc_ci": q(aucs), "f1_harm_ci": q(f1s), "n_boot": len(aucs)}
