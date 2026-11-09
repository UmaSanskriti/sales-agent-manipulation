"""One-shot evaluation on test and test_ood with the frozen configs. The ONLY script that reads test labels.

    python scripts/eval_test.py            # refuses to run twice unless --force

Refits each frozen probe on TRAIN only (scaler too), applies the val-chosen threshold, and scores
probes and baselines on test (in-distribution) and test_ood (held-out product line).
Writes reports/probe_results.md and results/test_metrics.json.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from src.probe_data import (ACT_DIR, all_labeled_turn_ids, build_rows, features, load_labels,  # noqa: E402
                            load_reply_texts, load_splits)
from src.probes import (auroc, bootstrap_by_group, condition_probe, fit_predict, majority_probe, metrics,  # noqa: E402
                        tfidf_probe)

LEVELS = {"turn": ("turn", "final"), "conv_final": ("conv", "final"), "conv_mean": ("conv", "mean")}
EVAL_SPLITS = ("test", "test_ood")


def fmt_cm(cm):
    return f"[[{cm[0][0]}, {cm[0][1]}], [{cm[1][0]}, {cm[1][1]}]]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    out_json = ROOT / "results" / "test_metrics.json"
    if out_json.exists() and not a.force:
        sys.exit(f"{out_json} exists: the test set is read once. Pass --force to overwrite.")
    frozen = yaml.safe_load((ROOT / "configs" / "probe_frozen.yaml").read_text())

    acts = np.load(ACT_DIR / "acts.npy", mmap_mode="r")
    row_of = {t: i for i, t in enumerate(all_labeled_turn_ids())}
    done = {l.strip() for l in (ACT_DIR / "done.txt").read_text().splitlines() if l.strip()}
    row_of = {t: i for t, i in row_of.items() if t.split("#")[0] in done}
    labels = load_labels(include_test=True)
    splits = load_splits()
    texts = load_reply_texts()
    rows = {lv: build_rows(lv, labels, row_of, splits, texts) for lv in ("turn", "conv")}

    results = {}

    def record(name, lv, split_ps, thr):
        r = rows[lv]
        results[name] = {}
        for s, p in split_ps.items():
            m = r.mask(s)
            y, g, c = r.y[m], r.scenario[m], r.condition[m]
            res = metrics(y, p, thr)
            res.update(bootstrap_by_group(y, p, thr, g))
            res["auroc_by_condition"] = {k: auroc(y[c == k], p[c == k])
                                         for k in ("neutral", "conversion", "harmful") if (c == k).any()}
            results[name][s] = res

    # activation probes
    for key, cfg in frozen["probes"].items():
        kind, level = key.split("/")
        lv, agg = LEVELS[level]
        r = rows[lv]
        tr = r.mask("train")
        Xtr = features(acts, r, tr, cfg["layer"], cfg["position"], agg)
        Xs = [features(acts, r, r.mask(s), cfg["layer"], cfg["position"], agg) for s in EVAL_SPLITS]
        ps = fit_predict(kind, cfg["hp"], Xtr, r.y[tr], Xs)
        record(f"probe {kind} / {level} (L{cfg['layer']}, {cfg['position']})", lv,
               dict(zip(EVAL_SPLITS, ps)), cfg["val_thr"])

    # baselines (thresholds from validation, as for the probes)
    for lv in ("turn", "conv"):
        r = rows[lv]
        tr, va = r.mask("train"), r.mask("val")
        txt = np.array(r.text, dtype=object)
        cond = r.condition.reshape(-1, 1)
        for name, mk, X in (("majority", majority_probe, np.zeros((len(r.y), 1))),
                            ("condition-only", condition_probe, cond), ("tfidf", tfidf_probe, txt)):
            m = mk().fit(X[tr], r.y[tr])
            thr = frozen["baselines"][f"{name.replace('-', '_')}/{lv}"]["val_thr"]
            record(f"baseline {name} / {lv}", lv, {s: m.predict_proba(X[r.mask(s)])[:, 1] for s in EVAL_SPLITS}, thr)

    # message-level probes aggregated to conversations (max P(harm) over turns)
    for key, cfg in frozen["probes"].items():
        kind, level = key.split("/")
        if level != "turn":
            continue
        t, c = rows["turn"], rows["conv"]
        tr = t.mask("train")
        Xtr = features(acts, t, tr, cfg["layer"], cfg["position"])
        Xall = features(acts, t, np.ones(len(t.y), bool), cfg["layer"], cfg["position"])
        (p_all,) = fit_predict(kind, cfg["hp"], Xtr, t.y[tr], [Xall])
        by_conv = {}
        for tid, p in zip(t.ids, p_all):
            by_conv[tid.split("#")[0]] = max(by_conv.get(tid.split("#")[0], 0.0), p)
        conv_scores = np.array([by_conv[cid] for cid in c.ids])
        record(f"probe {kind} / turn->conv max (L{cfg['layer']}, {cfg['position']})", "conv",
               {s: conv_scores[c.mask(s)] for s in EVAL_SPLITS}, cfg["val_thr"])

    (ROOT / "results").mkdir(exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2))

    L = ["# Held-out results (frozen probes; harm = judge harm_tier > 0)", "",
         "Information access: judge = fact sheet + visible transcript (no system prompt, no condition); "
         "probe = residual stream with system prompt + dialogue + reply, visible-text replay (no reasoning); "
         "TF-IDF = reply words only; condition-only = condition id; majority = nothing.", "",
         "Confusion matrices are [[TN, FP], [FN, TP]] (rows = judge label, cols = prediction). "
         "Intervals are 95% bootstrap over scenarios.", ""]
    for s in EVAL_SPLITS:
        L += [f"## {s}", "", "| method | n (harm) | AUROC [95% CI] | AUPRC | F1 harm | MCC | bal. acc | "
              "P/R harm | P/R not harm | confusion |", "|---|---|---|---|---|---|---|---|---|---|"]
        for name, res in results.items():
            m = res[s]
            L.append(f"| {name} | {m['n']} ({m['n_harm']}) | {m['auroc']:.3f} [{m['auroc_ci'][0]:.2f}, "
                     f"{m['auroc_ci'][1]:.2f}] | {m['auprc']:.3f} | {m['f1']['harm']:.3f} | {m['mcc']:.3f} | "
                     f"{m['balanced_accuracy']:.3f} | {m['precision']['harm']:.2f}/{m['recall']['harm']:.2f} | "
                     f"{m['precision']['not_harm']:.2f}/{m['recall']['not_harm']:.2f} | {fmt_cm(m['confusion'])} |")
        L += ["", "Within-condition AUROC (does the probe read behavior, not just the prompt?):", "",
              "| method | neutral | conversion | harmful |", "|---|---|---|---|"]
        for name, res in results.items():
            b = res[s]["auroc_by_condition"]
            L.append(f"| {name} | " + " | ".join(f"{b[k]:.3f}" if k in b else "n/a"
                                                 for k in ("neutral", "conversion", "harmful")) + " |")
        L.append("")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "probe_results.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
