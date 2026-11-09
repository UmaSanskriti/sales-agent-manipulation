"""Post-hoc baseline: condition id + TF-IDF reply text (TRD M9 "Condition + TF-IDF").

    python scripts/eval_cond_tfidf.py

CPU only; needs no activations or GPU. Same rows, splits, train-only fitting, val-F1 threshold and
scenario bootstrap as scripts/eval_test.py. Nothing is tuned on test: C is fixed at the same default
as the plain TF-IDF baseline (1.0), and the threshold comes from validation.

This was added after the one-shot test evaluation, so report it as a post-hoc addition. It does not
touch results/test_metrics.json or reports/probe_results.md; it writes
results/cond_tfidf_metrics.json and reports/cond_tfidf.md.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import OneHotEncoder  # noqa: E402

from src.probe_data import (ACT_DIR, all_labeled_turn_ids, build_rows, load_labels,  # noqa: E402
                            load_reply_texts, load_splits)
from src.probes import auroc, best_threshold, bootstrap_by_group, metrics  # noqa: E402

EVAL_SPLITS = ("test", "test_ood")
CONDS = ("neutral", "conversion", "harmful")


def cond_tfidf_probe(C: float = 1.0):
    """Reply TF-IDF (same settings as src.probes.tfidf_probe) plus a one-hot condition column."""
    feats = ColumnTransformer([
        ("text", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), "text"),
        ("cond", OneHotEncoder(handle_unknown="ignore"), ["cond"]),
    ])
    return make_pipeline(feats, LogisticRegression(C=C, max_iter=2000, class_weight="balanced"))


def frame(r, mask):
    import pandas as pd
    return pd.DataFrame({"text": np.array(r.text, dtype=object)[mask], "cond": r.condition[mask]})


def main():
    # same example set as the other methods: turns that have activations
    row_of = {t: i for i, t in enumerate(all_labeled_turn_ids())}
    done = {l.split()[0] for l in (ACT_DIR / "done.txt").read_text().splitlines() if l.strip()}
    row_of = {t: i for t, i in row_of.items() if t.split("#")[0] in done}
    labels = load_labels(include_test=True)
    splits, texts = load_splits(), load_reply_texts()
    rows = {lv: build_rows(lv, labels, row_of, splits, texts) for lv in ("turn", "conv")}

    results, L = {}, ["# Post-hoc baseline: condition + TF-IDF", "",
                      "Added after the one-shot test evaluation; C fixed at 1.0, threshold from validation F1. "
                      "Intervals: 95% bootstrap over scenarios.", ""]
    for lv in ("turn", "conv"):
        r = rows[lv]
        tr, va = r.mask("train"), r.mask("val")
        m = cond_tfidf_probe().fit(frame(r, tr), r.y[tr])
        pva = m.predict_proba(frame(r, va))[:, 1]
        thr = best_threshold(r.y[va], pva)
        results[lv] = {"val_auroc": auroc(r.y[va], pva), "val_thr": thr}
        for s in EVAL_SPLITS:
            ms = r.mask(s)
            y, g, c = r.y[ms], r.scenario[ms], r.condition[ms]
            p = m.predict_proba(frame(r, ms))[:, 1]
            res = metrics(y, p, thr)
            res.update(bootstrap_by_group(y, p, thr, g))
            res["auroc_by_condition"] = {k: auroc(y[c == k], p[c == k]) for k in CONDS if (c == k).any()}
            results[lv][s] = res
        L += [f"## {lv} level (val AUROC {results[lv]['val_auroc']:.3f}, threshold {thr:.4f})", "",
              "| split | n (harm) | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | neutral | conversion | harmful |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for s in EVAL_SPLITS:
            x = results[lv][s]
            b = x["auroc_by_condition"]
            L.append(f"| {s} | {x['n']} ({x['n_harm']}) | {x['auroc']:.3f} [{x['auroc_ci'][0]:.2f}, "
                     f"{x['auroc_ci'][1]:.2f}] | {x['auprc']:.3f} | {x['f1']['harm']:.3f} | {x['mcc']:.3f} | "
                     f"{x['balanced_accuracy']:.3f} | " +
                     " | ".join(f"{b[k]:.3f}" if k in b and b[k] == b[k] else "n/a" for k in CONDS) + " |")
        L.append("")
    (ROOT / "results" / "cond_tfidf_metrics.json").write_text(json.dumps(results, indent=2))
    (ROOT / "reports" / "cond_tfidf.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
