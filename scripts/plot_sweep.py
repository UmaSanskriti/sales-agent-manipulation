"""Write-up figures from the validation sweep (results/val_sweep.csv + configs/probe_frozen.yaml).

    python scripts/plot_sweep.py

fig/fig1_turn_layer_sweep.png        turn-level probe, val AUROC by layer, one line per token position
fig/fig2_conv_layer_sweep.png        conversation-level probes (final-turn vector, mean vector), same layout
fig/fig_layer_sweep_combined.png     all three panels in one figure
Each point is the best C for that (position, layer) on validation. Dashed lines: val AUROC of the
TF-IDF and condition-only baselines. The vertical tick marks the layer frozen for the test evaluation.
Validation data only: no test labels are read.
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SERIES = {"mean": ("#2a78d6", "o"), "pre": ("#eb6834", "s"), "last": ("#1baf7a", "^")}  # fixed slot order
ORDER = ("mean", "pre", "last")
TITLES = {"turn": "Turn level", "conv_final": "Conversation level: final-turn vector",
          "conv_mean": "Conversation level: mean vector"}

plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID})


def load():
    best = defaultdict(float)
    for r in csv.DictReader(open(ROOT / "results" / "val_sweep.csv")):
        if r["kind"] != "lr":
            continue
        k = (r["level"], r["position"], int(r["layer"]))
        best[k] = max(best[k], float(r["val_auroc"]))
    return best


def panel(ax, best, level, frozen, ylim):
    cfg = frozen["probes"][f"lr/{level}"]
    base_lv = "turn" if level == "turn" else "conv"
    ends = {}
    for pos in ORDER:
        col, mk = SERIES[pos]
        xs = sorted(l for (lv, p, l) in best if lv == level and p == pos)
        ys = [best[(level, pos, l)] for l in xs]
        ax.plot(xs, ys, color=col, lw=1.8, marker=mk, ms=4, mfc=col, mec="#fcfcfb", mew=0.6, zorder=3)
        ends[pos] = (xs[-1], ys[-1])
    styles = {"tfidf": (0, (5, 3)), "condition_only": (0, (1, 2)), "majority": (0, (5, 2, 1, 2))}
    for name, key in (("TF-IDF baseline", "tfidf"), ("Condition-only baseline", "condition_only"),
                      ("Majority-class baseline", "majority")):
        y = frozen["baselines"][f"{key}/{base_lv}"]["val_auroc"]
        ax.axhline(y, color=INK2, lw=1.1, ls=styles[key], zorder=1)
        ax.plot([], [], color=INK2, lw=1.1, ls=styles[key], label=f"{name} ({y:.3f})")
    y_best = best[(level, cfg["position"], cfg["layer"])]
    ax.vlines(cfg["layer"], 0.52, y_best, color=INK2, lw=0.8, alpha=0.5, zorder=0)
    # callout sits in the empty band below the curves (conv panels) or just above the peak (turn panel)
    if level == "turn":
        xt, yt, ha, va = cfg["layer"] + 1.5, ylim[1] - 0.02, "left", "top"
    else:
        xt, yt, ha, va = cfg["layer"] - 1.5, 0.60, "right", "center"
    ax.annotate(f"selected: L{cfg['layer']}, {cfg['position']}\nval AUROC {y_best:.3f}",
                (cfg["layer"], y_best), xytext=(xt, yt), fontsize=8.5, color=INK, ha=ha, va=va,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
    # direct labels at the right end (aqua is low-contrast, so labels are required); nudged apart
    ys = sorted((ends[p][1], p) for p in ORDER)
    pos_y, prev = {}, -9
    for y, pos in ys:
        prev = max(y, prev + 0.028)
        pos_y[pos] = prev
    for pos in ORDER:
        ax.text(ends[pos][0] + 0.6, pos_y[pos], pos, color=SERIES[pos][0] if pos != "last" else "#12805a",
                fontsize=9, va="center", fontweight="bold")
    ax.legend(loc="lower right" if level == "turn" else "lower left", bbox_to_anchor=(1.0, 0.0) if level == "turn" else (0.1, 0.0), frameon=False, fontsize=8, labelcolor=INK2, handlelength=3.2)
    ax.set_ylim(*ylim)
    ax.set_xlim(-0.5, 39.5)
    ax.set_title(TITLES[level], loc="left", fontsize=11, color=INK)
    ax.set_xlabel("Layer (0 = embedding output)")
    ax.yaxis.grid(True, color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def combined(best, frozen, out):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4), dpi=200, sharey=True)
    for ax, lv in zip(axes, ("turn", "conv_final", "conv_mean")):
        panel(ax, best, lv, frozen, (0.32, 0.96))
    axes[0].set_ylabel("Validation AUROC")
    fig.tight_layout()
    fig.savefig(out / "fig_layer_sweep_combined.png", facecolor="#fcfcfb")


def main():
    best = load()
    frozen = yaml.safe_load((ROOT / "configs" / "probe_frozen.yaml").read_text())
    out = ROOT / "fig"

    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=200)
    panel(ax, best, "turn", frozen, (0.44, 0.94))
    ax.set_ylabel("Validation AUROC")
    fig.tight_layout()
    fig.savefig(out / "fig1_turn_layer_sweep.png", facecolor="#fcfcfb")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=200, sharey=True)
    for ax, lv in zip(axes, ("conv_final", "conv_mean")):
        panel(ax, best, lv, frozen, (0.40, 0.96))
    axes[0].set_ylabel("Validation AUROC")
    fig.tight_layout()
    fig.savefig(out / "fig2_conv_layer_sweep.png", facecolor="#fcfcfb")
    combined(best, frozen, out)
    print("wrote", out / "fig1_turn_layer_sweep.png", out / "fig2_conv_layer_sweep.png")


if __name__ == "__main__":
    main()
