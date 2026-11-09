"""Post-hoc check: probes on the "pre" token only (the last prompt token, before any reply text).

    python scripts/eval_pre.py

The "pre" vector is computed before the model has produced a single reply token, so a probe on it can
only use the system prompt and the dialogue so far. If it still predicts the judge's label for the
upcoming reply, the activations carry information beyond the produced tokens.

For each level the layer and C are chosen on validation AUROC among position == "pre" (from
results/val_sweep.csv, the same selection rule as the main probes), the threshold maximizes validation F1,
and the probe is fit on train only. Evaluates test and test_ood. Added after the one-shot test
evaluation, so report it as post-hoc. Writes results/pre_metrics.json, fig/table_pre_heldout.png and
fig/table_pre_within_condition.png.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402

from src.probe_data import (ACT_DIR, all_labeled_turn_ids, build_rows, features, load_labels,  # noqa: E402
                            load_reply_texts, load_splits)
from src.probes import auroc, best_threshold, bootstrap_by_group, fit_predict, metrics  # noqa: E402
import plot_tables as pt  # noqa: E402

LEVELS = {"turn": ("turn", "final"), "conv_final": ("conv", "final"), "conv_mean": ("conv", "mean")}
CONDS = ("neutral", "conversion", "harmful")


def best_pre():
    best = {}
    for r in csv.DictReader(open(ROOT / "results" / "val_sweep.csv")):
        if r["kind"] != "lr" or r["position"] != "pre":
            continue
        v = float(r["val_auroc"])
        if r["level"] not in best or v > best[r["level"]][0]:
            best[r["level"]] = (v, int(r["layer"]), float(r["hp"]))
    return best


def main():
    acts = np.load(ACT_DIR / "acts.npy", mmap_mode="r")
    row_of = {t: i for i, t in enumerate(all_labeled_turn_ids())}
    done = {l.split()[0] for l in (ACT_DIR / "done.txt").read_text().splitlines() if l.strip()}
    row_of = {t: i for t, i in row_of.items() if t.split("#")[0] in done}
    labels = load_labels(include_test=True)
    splits, texts = load_splits(), load_reply_texts()
    rows = {lv: build_rows(lv, labels, row_of, splits, texts) for lv in ("turn", "conv")}

    results = {}
    for level, (val_auc, layer, C) in best_pre().items():
        lv, agg = LEVELS[level]
        r = rows[lv]
        tr, va = r.mask("train"), r.mask("val")
        Xtr = features(acts, r, tr, layer, "pre", agg)
        Xva = features(acts, r, va, layer, "pre", agg)
        Xs = {s: features(acts, r, r.mask(s), layer, "pre", agg) for s in pt.SPLITS}
        pva, *pte = fit_predict("lr", C, Xtr, r.y[tr], [Xva] + [Xs[s] for s in pt.SPLITS])
        thr = best_threshold(r.y[va], pva)
        entry = {"layer": layer, "C": C, "val_auroc": auroc(r.y[va], pva), "val_thr": thr}
        for s, p in zip(pt.SPLITS, pte):
            m = r.mask(s)
            y, g, c = r.y[m], r.scenario[m], r.condition[m]
            res = metrics(y, p, thr)
            res.update(bootstrap_by_group(y, p, thr, g))
            res["auroc_by_condition"] = {k: auroc(y[c == k], p[c == k]) for k in CONDS if (c == k).any()}
            entry[s] = res
        results[level] = entry
        print(level, f"L{layer} C={C} val AUROC {entry['val_auroc']:.3f} thr {thr:.4f}",
              {s: round(entry[s]["auroc"], 3) for s in pt.SPLITS})
    (ROOT / "results" / "pre_metrics.json").write_text(json.dumps(results, indent=2))

    def mean_probe(key):
        return lambda: pt.main_get(key)

    def pre_probe(level):
        return lambda: results[level]

    turn_rows = [
        (f"Linear probe (L{results['turn']['layer']})", pre_probe("turn"), False),
        ("Condition-only", mean_probe("baseline condition-only / turn"), False),
        ("Majority class", mean_probe("baseline majority / turn"), False),
    ]
    conv_rows = [
        (f"Linear probe, final-turn vector (L{results['conv_final']['layer']})", pre_probe("conv_final"), False),
        (f"Linear probe, mean vector (L{results['conv_mean']['layer']})", pre_probe("conv_mean"), False),
        ("Condition-only", mean_probe("baseline condition-only / conv"), False),
        ("Majority class", mean_probe("baseline majority / conv"), False),
    ]

    # main table: AUROC [CI], F1, MCC per split (only methods that are fair to compare with a pre-token probe)
    width, col_x, col_w = 12.4, [4.85, 6.95, 7.85, 8.75, 10.85, 11.75], [2.1, 0.9, 0.9, 2.1, 0.9, 0.9]
    col_x = [4.9, 7.0, 7.9, 8.8, 10.9, 11.8]
    blocks = []
    for name, rws in (("Turn-Level", turn_rows), ("Conversation-Level", conv_rows)):
        cells, vals = [], [[] for _ in range(6)]
        for lab, fn, _ in rws:
            d, c = fn(), []
            for si, sp in enumerate(pt.SPLITS):
                m = d[sp]
                c += [pt.fmt_auc(m), f"{m['f1']['harm']:.3f}", f"{m['mcc']:.2f}"]
                vals[si * 3 + 0].append(m["auroc"])
                vals[si * 3 + 1].append(m["f1"]["harm"])
                vals[si * 3 + 2].append(m["mcc"])
            cells.append((lab, c))
        blocks.append((name, cells, [pt.best_idx(v) for v in vals]))
    pt.draw(None, col_x, col_w, "Held-out Results: Pre Token",
            [("Test", 0, 2), ("Test-OOD", 3, 5)], ["AUROC [95% CI]", "F1", "MCC"] * 2, blocks, [],
            ROOT / "fig/table_pre_heldout.png", 13.2, None)

    # within-condition table
    w_x, w_w = [5.2, 6.35, 7.5, 8.75, 9.9, 11.05], [1.15] * 6
    blocks = []
    for name, rws in (("Turn-Level", turn_rows), ("Conversation-Level", [r for r in conv_rows if "Majority" not in r[0]])):
        cells, cols = [], [[] for _ in range(6)]
        for lab, fn, _ in rws:
            d, c = fn(), []
            for si, sp in enumerate(pt.SPLITS):
                by = d[sp]["auroc_by_condition"]
                for ki, k in enumerate(CONDS):
                    v = by.get(k)
                    c.append(f"{v:.3f}" if pt.ok(v) else "n/a")
                    cols[si * 3 + ki].append(v if pt.ok(v) else None)
            cells.append((lab, c))
        best = []
        for col in cols:
            masked = [None if ("Condition-only" in cells[i][0] or "Majority" in cells[i][0]) else v
                      for i, v in enumerate(col)]
            best.append(pt.best_idx(masked))
        blocks.append((name, cells, best))
    pt.draw(None, w_x, w_w, "Within-Condition AUROC: Pre Token",
            [("Test", 0, 2), ("Test-OOD", 3, 5)], ["Neutral", "Conversion", "Harmful"] * 2, blocks, [],
            ROOT / "fig/table_pre_within_condition.png", 12.4, None)
    print("wrote results/pre_metrics.json, fig/table_pre_heldout.png, fig/table_pre_within_condition.png")


if __name__ == "__main__":
    main()
