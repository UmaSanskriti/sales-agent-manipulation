"""Diagram of the three token positions read per agent turn -> fig/fig_token_positions.png"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "fig" / "fig_token_positions.png"
GREY, BLUE, ORANGE, GREEN = "#e5e7eb", "#2563eb", "#ea580c", "#16a34a"

fig, ax = plt.subplots(figsize=(11, 3.6), dpi=200)
ax.set_xlim(0, 11); ax.set_ylim(0, 3.6); ax.axis("off")

def box(x, w, text, fc, ec="#6b7280", fs=10, bold=False):
    ax.add_patch(FancyBboxPatch((x, 1.5), w, 0.8, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=fc, ec=ec, lw=1.5))
    ax.text(x + w / 2, 1.9, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")

box(0.2, 3.4, "system prompt + dialogue so far", GREY)
box(3.8, 1.5, "<|start|>assistant", "#dbeafe", BLUE, 8, True)
reply_x = [5.5, 6.55, 7.6, 8.65]
for x, t in zip(reply_x, ["Hi,", "this", "plan", "…  end."]):
    box(x, 0.95, t, "#dcfce7", GREEN, 10)
box(9.7, 1.1, "<|end|>", GREY, fs=9)

# pre
ax.annotate("", xy=(4.55, 1.45), xytext=(4.55, 0.75), arrowprops=dict(arrowstyle="->", color=BLUE, lw=2))
ax.text(4.55, 0.5, "pre", ha="center", fontsize=14, color=BLUE, fontweight="bold")
ax.text(4.55, 0.1, "before any reply text", ha="center", fontsize=9, color="#374151")
# last
ax.annotate("", xy=(9.125, 1.45), xytext=(9.125, 0.75), arrowprops=dict(arrowstyle="->", color=ORANGE, lw=2))
ax.text(9.125, 0.5, "last", ha="center", fontsize=14, color=ORANGE, fontweight="bold")
ax.text(9.125, 0.1, "final reply token", ha="center", fontsize=9, color="#374151")
# mean bracket
ax.plot([5.5, 5.5, 9.6, 9.6], [2.45, 2.65, 2.65, 2.45], color=GREEN, lw=2)
ax.text(7.55, 2.85, "mean", ha="center", fontsize=14, color=GREEN, fontweight="bold")
ax.text(7.55, 3.2, "average over all reply tokens", ha="center", fontsize=9, color="#374151")
ax.text(0.2, 3.2, "One judged agent turn", fontsize=11, fontweight="bold")

fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(OUT)
