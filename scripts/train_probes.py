"""Sweep probes on TRAIN, select on VAL, freeze the choice. Never reads test labels or test activations.

    python scripts/train_probes.py                    # all layers
    python scripts/train_probes.py --layer-step 3     # quick pass

Probe kinds: lr, mlp. Levels: turn (one row per agent turn), conv_final (final turn's vector),
conv_mean (mean of the conversation's turn vectors). Target: judge harm_tier > 0.

Writes results/val_sweep.csv, reports/val_sweep.md, fig/auroc_by_layer_*.png and
configs/probe_frozen.yaml (best config per kind x level, val-F1 threshold, baseline val scores).
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

from src.acts import POSITIONS  # noqa: E402
from src.probe_data import (ACT_DIR, all_labeled_turn_ids, build_rows, check_counts, features,  # noqa: E402
                            load_labels, load_reply_texts, load_splits)
from src.probes import (CS, MLP_ALPHAS, auroc, best_threshold, condition_probe, fit_predict,  # noqa: E402
                        majority_probe, tfidf_probe)

LEVELS = {"turn": ("turn", "final"), "conv_final": ("conv", "final"), "conv_mean": ("conv", "mean")}


def one_fit(acts, rows, level, kind, hp, pos, layer):
    lv, agg = LEVELS[level]
    tr, va = rows[lv].mask("train"), rows[lv].mask("val")
    Xtr = features(acts, rows[lv], tr, layer, pos, agg)
    Xva = features(acts, rows[lv], va, layer, pos, agg)
    ptr, pva = fit_predict(kind, hp, Xtr, rows[lv].y[tr], [Xtr, Xva])
    yva, cva = rows[lv].y[va], rows[lv].condition[va]
    rec = {"level": level, "kind": kind, "hp": hp, "position": pos, "layer": layer,
           "train_auroc": auroc(rows[lv].y[tr], ptr), "val_auroc": auroc(yva, pva)}
    for c in ("neutral", "conversion", "harmful"):
        m = cva == c
        rec[f"val_auroc_{c}"] = auroc(yva[m], pva[m]) if m.any() else float("nan")
    rec["val_thr"] = best_threshold(yva, pva)
    return rec


def baseline_scores(rows):
    out = {}
    for lv in ("turn", "conv"):
        r = rows[lv]
        tr, va = r.mask("train"), r.mask("val")
        ytr, yva = r.y[tr], r.y[va]
        txt = np.array(r.text, dtype=object)
        cond = r.condition.reshape(-1, 1)
        for name, mk, Xtr, Xva in (
            ("majority", majority_probe, np.zeros((tr.sum(), 1)), np.zeros((va.sum(), 1))),
            ("condition_only", condition_probe, cond[tr], cond[va]),
            ("tfidf", tfidf_probe, txt[tr], txt[va]),
        ):
            m = mk().fit(Xtr, ytr)
            p = m.predict_proba(Xva)[:, 1]
            out[f"{name}/{lv}"] = {"val_auroc": auroc(yva, p), "val_thr": best_threshold(yva, p)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer-step", type=int, default=1)
    ap.add_argument("--jobs", type=int, default=-1)
    ap.add_argument("--levels", nargs="+", default=list(LEVELS))
    ap.add_argument("--kinds", nargs="+", default=["lr", "mlp"])
    a = ap.parse_args()

    acts = np.load(ACT_DIR / "acts.npy", mmap_mode="r")
    row_of = {t: i for i, t in enumerate(all_labeled_turn_ids())}
    done = {l.split()[0] for l in (ACT_DIR / "done.txt").read_text().splitlines() if l.strip()}
    row_of = {t: i for t, i in row_of.items() if t.split("#")[0] in done}
    labels = load_labels(include_test=False)  # train + val only
    splits = load_splits()
    texts = load_reply_texts()
    rows = {lv: build_rows(lv, labels, row_of, splits, texts) for lv in ("turn", "conv")}
    for lv, r in rows.items():
        bad = [p for p in check_counts(r) if not p.startswith("test")]
        print(lv, {s: (int(r.y[r.mask(s)].sum()), int(r.mask(s).sum())) for s in ("train", "val")})
        if bad:
            sys.exit(f"STOP (TRD M6): too few examples: {bad}")

    n_layers = acts.shape[1]
    layers = list(range(0, n_layers, a.layer_step))
    if (n_layers - 1) not in layers:
        layers.append(n_layers - 1)
    jobs = [(level, kind, hp, pos, layer)
            for level in a.levels for kind in a.kinds for hp in (CS if kind == "lr" else MLP_ALPHAS)
            for pos in POSITIONS for layer in layers]
    print(f"{len(jobs)} fits")
    res = Parallel(n_jobs=a.jobs, verbose=5)(delayed(one_fit)(acts, rows, *j) for j in jobs)

    (ROOT / "results").mkdir(exist_ok=True)
    with open(ROOT / "results" / "val_sweep.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0]))
        w.writeheader()
        w.writerows(res)

    base = baseline_scores(rows)
    frozen = {"target": "harm_tier > 0", "selection": "val AUROC", "threshold": "val F1 of harm class",
              "baselines": base, "probes": {}}
    lines = ["# Validation sweep (train-fit, val-scored)", "",
             "Baselines (val AUROC): " + ", ".join(f"{k} {v['val_auroc']:.3f}" for k, v in base.items()), ""]
    for level in a.levels:
        for kind in a.kinds:
            sub = [r for r in res if r["level"] == level and r["kind"] == kind]
            best = max(sub, key=lambda r: r["val_auroc"])
            frozen["probes"][f"{kind}/{level}"] = {k: best[k] for k in
                                                    ("position", "layer", "hp", "val_auroc", "val_thr")}
            lines += [f"## {kind} / {level}",
                      f"Best: position {best['position']}, layer {best['layer']}, "
                      f"{'C' if kind == 'lr' else 'alpha'} {best['hp']} -> val AUROC {best['val_auroc']:.3f} "
                      f"(neutral {best['val_auroc_neutral']:.3f}, conversion {best['val_auroc_conversion']:.3f}, "
                      f"harmful {best['val_auroc_harmful']:.3f})", "",
                      "| position | best layer | best val AUROC | worst layer | worst val AUROC |", "|---|---|---|---|---|"]
            for pos in POSITIONS:
                per_layer = {}
                for r in sub:
                    if r["position"] == pos:
                        per_layer[r["layer"]] = max(per_layer.get(r["layer"], 0), r["val_auroc"])
                bl, wl = max(per_layer, key=per_layer.get), min(per_layer, key=per_layer.get)
                lines.append(f"| {pos} | {bl} | {per_layer[bl]:.3f} | {wl} | {per_layer[wl]:.3f} |")
            lines.append("")
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "val_sweep.md").write_text("\n".join(lines))
    (ROOT / "configs" / "probe_frozen.yaml").write_text(yaml.safe_dump(frozen, sort_keys=False))
    plot(res, a.levels, a.kinds)
    print("\n".join(lines))


def plot(res, levels, kinds):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    (ROOT / "fig").mkdir(exist_ok=True)
    for level in levels:
        fig, axes = plt.subplots(1, len(kinds), figsize=(5.5 * len(kinds), 4), squeeze=False)
        for ax, kind in zip(axes[0], kinds):
            for pos in POSITIONS:
                best = {}
                for r in res:
                    if (r["level"], r["kind"], r["position"]) == (level, kind, pos):
                        best[r["layer"]] = max(best.get(r["layer"], 0), r["val_auroc"])
                xs = sorted(best)
                ax.plot(xs, [best[x] for x in xs], marker="o", ms=3, label=pos)
            ax.axhline(0.5, color="gray", lw=0.8, ls="--")
            ax.set(title=f"{kind} / {level}", xlabel="layer (0 = embeddings)", ylabel="val AUROC")
            ax.legend()
        fig.tight_layout()
        fig.savefig(ROOT / "fig" / f"auroc_by_layer_{level}.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
