"""Post-hoc sanity check: mean-difference probe (TRD M9), no training.

    python scripts/eval_meandiff.py

Direction w = mean(harm) - mean(not harm) over TRAIN activations; score = (x - midpoint) . w / |w|.
Two variants: raw activations, and train-standardized activations (the preprocessing the LR probe uses).
Two layer choices per level: the layer/position frozen for the LR probe (configs/probe_frozen.yaml), and
the layer/position this method itself would pick by val AUROC (full sweep). Threshold = val-F1 maximizer.
Nothing is tuned on test. CPU only.

Added after the one-shot test evaluation, so report it as post-hoc. Writes results/meandiff_metrics.json
and reports/meandiff.md; leaves the main results untouched.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from src.acts import POSITIONS  # noqa: E402
from src.probe_data import (ACT_DIR, all_labeled_turn_ids, build_rows, features, load_labels,  # noqa: E402
                            load_reply_texts, load_splits)
from src.probes import auroc, best_threshold, bootstrap_by_group, metrics  # noqa: E402

LEVELS = {"turn": ("turn", "final"), "conv_final": ("conv", "final"), "conv_mean": ("conv", "mean")}
EVAL_SPLITS = ("test", "test_ood")
CONDS = ("neutral", "conversion", "harmful")


def fit_dir(Xtr, ytr, standardize: bool):
    mu, sd = (Xtr.mean(0), Xtr.std(0) + 1e-6) if standardize else (0.0, 1.0)
    Z = (Xtr - mu) / sd
    c1, c0 = Z[ytr == 1].mean(0), Z[ytr == 0].mean(0)
    w = c1 - c0
    w = w / (np.linalg.norm(w) + 1e-12)
    mid = (c1 + c0) / 2
    return lambda X: ((X - mu) / sd - mid) @ w


def main():
    frozen = yaml.safe_load((ROOT / "configs" / "probe_frozen.yaml").read_text())
    acts = np.load(ACT_DIR / "acts.npy", mmap_mode="r")
    n_layers = acts.shape[1]
    row_of = {t: i for i, t in enumerate(all_labeled_turn_ids())}
    done = {l.split()[0] for l in (ACT_DIR / "done.txt").read_text().splitlines() if l.strip()}
    row_of = {t: i for t, i in row_of.items() if t.split("#")[0] in done}
    labels = load_labels(include_test=True)
    splits, texts = load_splits(), load_reply_texts()
    rows = {lv: build_rows(lv, labels, row_of, splits, texts) for lv in ("turn", "conv")}

    results = {}
    for level, (lv, agg) in LEVELS.items():
        r = rows[lv]
        tr, va = r.mask("train"), r.mask("val")
        cfg = frozen["probes"][f"lr/{level}"]
        for std in (False, True):
            # val sweep over layer x position for this method
            sweep = {}
            for pos in POSITIONS:
                for layer in range(n_layers):
                    Xtr = features(acts, r, tr, layer, pos, agg)
                    Xva = features(acts, r, va, layer, pos, agg)
                    sweep[(layer, pos)] = auroc(r.y[va], fit_dir(Xtr, r.y[tr], std)(Xva))
            best = max(sweep, key=lambda k: (sweep[k] if sweep[k] == sweep[k] else -1))
            choices = {"frozen LR layer": (cfg["layer"], cfg["position"]), "own val-best layer": best}
            for cname, (layer, pos) in choices.items():
                name = f"meandiff {'std' if std else 'raw'} / {level} ({cname}: L{layer}, {pos})"
                score = fit_dir(features(acts, r, tr, layer, pos, agg), r.y[tr], std)
                pva = score(features(acts, r, va, layer, pos, agg))
                thr = best_threshold(r.y[va], pva)
                results[name] = {"val_auroc": auroc(r.y[va], pva), "val_thr": thr}
                for s in EVAL_SPLITS:
                    m = r.mask(s)
                    y, g, c = r.y[m], r.scenario[m], r.condition[m]
                    p = score(features(acts, r, m, layer, pos, agg))
                    res = metrics(y, p, thr)
                    res.update(bootstrap_by_group(y, p, thr, g))
                    res["auroc_by_condition"] = {k: auroc(y[c == k], p[c == k]) for k in CONDS if (c == k).any()}
                    results[name][s] = res

    (ROOT / "results" / "meandiff_metrics.json").write_text(json.dumps(results, indent=2))
    L = ["# Post-hoc sanity check: mean-difference probe", "",
         "Direction = centroid(harm) - centroid(not harm) on train; threshold from val F1; nothing tuned on test. "
         "'raw' = unstandardized activations, 'std' = train-standardized. Intervals: 95% bootstrap over scenarios.", ""]
    for s in EVAL_SPLITS:
        L += [f"## {s}", "", "| method | val AUROC | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | neutral | conversion | harmful |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for name, res in results.items():
            x, b = res[s], res[s]["auroc_by_condition"]
            L.append(f"| {name} | {res['val_auroc']:.3f} | {x['auroc']:.3f} [{x['auroc_ci'][0]:.2f}, {x['auroc_ci'][1]:.2f}] | "
                     f"{x['auprc']:.3f} | {x['f1']['harm']:.3f} | {x['mcc']:.3f} | {x['balanced_accuracy']:.3f} | " +
                     " | ".join(f"{b[k]:.3f}" if k in b and b[k] == b[k] else "n/a" for k in CONDS) + " |")
        L.append("")
    (ROOT / "reports" / "meandiff.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
