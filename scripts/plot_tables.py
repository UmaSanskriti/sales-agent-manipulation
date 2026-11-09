"""Render the held-out results tables as images for the write-up.

    python scripts/plot_tables.py

Reads results/test_metrics.json, results/cond_tfidf_metrics.json and results/meandiff_metrics.json
(no recomputation) and writes
    fig/table_main_heldout.png        AUROC [95% CI] and MCC on test and test_ood
    fig/table_within_condition.png    AUROC within each prompt condition on test and test_ood
Dagger rows (post-hoc) were added after the one-shot test evaluation.
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INK, INK2, RULE, BAND = "#0b0b0b", "#52514e", "#b9b8b2", "#f3f2ef"
plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.5})

MAIN = json.loads((ROOT / "results/test_metrics.json").read_text())
CT = json.loads((ROOT / "results/cond_tfidf_metrics.json").read_text())
MD = json.loads((ROOT / "results/meandiff_metrics.json").read_text())


def main_get(key):
    return MAIN[key]


def ct_get(level):
    return CT[level]


def md_get(key):
    return MD[key]


# (label, accessor returning {split: metrics dict}, post_hoc, is_probe)
TURN_ROWS = [
    ("Linear probe (LR, L17, mean)", lambda: main_get("probe lr / turn (L17, mean)"), False),
    ("Mean-difference probe (L17, mean)†", lambda: md_get("meandiff std / turn (frozen LR layer: L17, mean)"), True),
    ("TF-IDF (reply words)", lambda: main_get("baseline tfidf / turn"), False),
    ("Condition + TF-IDF†", lambda: ct_get("turn"), True),
    ("Condition-only", lambda: main_get("baseline condition-only / turn"), False),
    ("Majority class", lambda: main_get("baseline majority / turn"), False),
]
CONV_ROWS = [
    ("Linear probe, final-turn vector (L21, mean)", lambda: main_get("probe lr / conv_final (L21, mean)"), False),
    ("Linear probe, mean vector (L35, mean)", lambda: main_get("probe lr / conv_mean (L35, mean)"), False),
    ("Linear probe, max over turn scores (L17, mean)", lambda: main_get("probe lr / turn->conv max (L17, mean)"), False),
    ("Mean-difference, final-turn vector (L21)†", lambda: md_get("meandiff std / conv_final (frozen LR layer: L21, mean)"), True),
    ("Mean-difference, mean vector (L35)†", lambda: md_get("meandiff std / conv_mean (frozen LR layer: L35, mean)"), True),
    ("TF-IDF (all replies)", lambda: main_get("baseline tfidf / conv"), False),
    ("Condition + TF-IDF†", lambda: ct_get("conv"), True),
    ("Condition-only", lambda: main_get("baseline condition-only / conv"), False),
    ("Majority class", lambda: main_get("baseline majority / conv"), False),
]
SPLITS = ("test", "test_ood")
SPLIT_NAMES = {"test": "Test (seen product lines)", "test_ood": "Test-OOD (held-out product line)"}


def fmt_auc(m):
    return f"{m['auroc']:.3f}  [{m['auroc_ci'][0]:.2f}, {m['auroc_ci'][1]:.2f}]"


def ok(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def draw(rows_spec, col_x, col_w, title, header_groups, header_cols, blocks, notes, path, width, bold_fn):
    """blocks: list of (block title, rows, n_note). Each cell is a pre-formatted string."""
    row_h, head_h = 0.30, 0.34
    n_rows = sum(len(b[1]) + 1 for b in blocks)
    height = 0.55 + 2 * head_h + n_rows * row_h + 0.25 + 0.2 * len(notes) + 0.15
    fig = plt.figure(figsize=(width, height), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")
    y = 0.32
    ax.text(0.15, y, title, fontsize=11, fontweight="bold", color=INK, va="center")
    y += 0.35
    ax.hlines(y, 0.1, width - 0.1, color=INK, lw=1.2)
    y += head_h / 2
    for label, c0, c1 in header_groups:
        ax.text((col_x[c0] + col_x[c1] + col_w[c1]) / 2, y, label, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color=INK)
        ax.hlines(y + head_h / 2 - 0.02, col_x[c0] + 0.05, col_x[c1] + col_w[c1] - 0.05, color=RULE, lw=0.8)
    y += head_h
    ax.text(0.15, y, "Method", ha="left", va="center", fontsize=9, color=INK2)
    for i, h in enumerate(header_cols):
        ax.text(col_x[i] + col_w[i] / 2, y, h, ha="center", va="center", fontsize=9, color=INK2)
    y += head_h / 2 + 0.03
    ax.hlines(y, 0.1, width - 0.1, color=INK, lw=0.8)
    y += 0.02
    for bt, rows, cells_best in blocks:
        ax.add_patch(plt.Rectangle((0.1, y), width - 0.2, row_h, color=BAND, lw=0))
        ax.text(0.15, y + row_h / 2, bt, ha="left", va="center", fontsize=9, fontweight="bold", color=INK)
        y += row_h
        for r, (label, cells) in enumerate(rows):
            ax.text(0.25, y + row_h / 2, label, ha="left", va="center", fontsize=9.5, color=INK)
            for i, c in enumerate(cells):
                bold = cells_best[i] == r
                ax.text(col_x[i] + col_w[i] / 2, y + row_h / 2, c, ha="center", va="center", fontsize=9.5,
                        color=INK, fontweight="bold" if bold else "normal")
            y += row_h
    ax.hlines(y + 0.04, 0.1, width - 0.1, color=INK, lw=1.2)
    y += 0.2
    for n in notes:
        ax.text(0.15, y, n, fontsize=8, color=INK2, va="center")
        y += 0.2
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def best_idx(vals):
    """Index of the largest finite value, or None."""
    ids = [i for i, v in enumerate(vals) if ok(v)]
    return max(ids, key=lambda i: vals[i]) if ids else None


def main_table():
    width = 12.4
    # columns: test AUROC [CI] | F1 | MCC | test-OOD AUROC [CI] | F1 | MCC
    col_x = [4.15, 6.25, 7.15, 8.05, 10.15, 11.05]
    col_w = [2.1, 0.9, 0.9, 2.1, 0.9, 0.9]
    blocks = []
    for name, rows in (("Turn-Level", TURN_ROWS), ("Conversation-Level", CONV_ROWS)):
        rows = [r for r in rows if "Mean-difference" not in r[0] and "max over" not in r[0]]
        data = [(lab.replace("\u2020", ""), fn()) for lab, fn, _ in rows]
        cells, vals = [], [[] for _ in range(6)]
        for lab, d in data:
            c = []
            for si, sp in enumerate(SPLITS):
                m = d[sp]
                c += [fmt_auc(m), f"{m['f1']['harm']:.3f}", f"{m['mcc']:.2f}"]
                vals[si * 3 + 0].append(m["auroc"])
                vals[si * 3 + 1].append(m["f1"]["harm"])
                vals[si * 3 + 2].append(m["mcc"])
            cells.append((lab, c))
        blocks.append((name, cells, [best_idx(v) for v in vals]))
    draw(None, col_x, col_w, "Held-out Results",
         [("Test", 0, 2), ("Test-OOD", 3, 5)],
         ["AUROC [95% CI]", "F1", "MCC"] * 2, blocks, [],
         ROOT / "fig/table_main_heldout.png", width, None)


def within_table():
    width = 11.4
    col_x = [4.85, 6.0, 7.15, 8.3, 9.45, 10.6]
    col_x = [4.2, 5.35, 6.5, 7.75, 8.9, 10.05]
    col_w = [1.15] * 6
    keys = ("neutral", "conversion", "harmful")
    blocks = []
    for name, rows, skip in (("Turn-Level", TURN_ROWS, ()),
                             ("Conversation-Level", CONV_ROWS, ())):
        rows = [r for r in rows if "Mean-difference" not in r[0] and "max over" not in r[0]
                and not (name.startswith("Conv") and "Majority" in r[0])]
        cells, cols = [], [[] for _ in range(6)]
        for lab, fn, _ in rows:
            lab = lab.replace("\u2020", "")
            d = fn()
            c = []
            for si, s in enumerate(SPLITS):
                by = d[s]["auroc_by_condition"]
                for ki, k in enumerate(keys):
                    v = by.get(k)
                    c.append(f"{v:.3f}" if ok(v) else "n/a")
                    cols[si * 3 + ki].append(v if ok(v) else None)
            cells.append((lab, c))
        best = []
        for ci, col in enumerate(cols):
            # exclude the trivial constant-score baselines from "best"
            masked = [None if ("Condition-only" in cells[i][0] or "Majority" in cells[i][0]) else v
                      for i, v in enumerate(col)]
            best.append(best_idx(masked))
        blocks.append((name, cells, best))
    draw(None, col_x, col_w, "Within-Condition AUROC",
         [("Test", 0, 2), ("Test-OOD", 3, 5)],
         ["Neutral", "Conversion", "Harmful"] * 2, blocks, [],
         ROOT / "fig/table_within_condition.png", width, None)


if __name__ == "__main__":
    main_table()
    within_table()
    print("wrote fig/table_main_heldout.png, fig/table_within_condition.png")
