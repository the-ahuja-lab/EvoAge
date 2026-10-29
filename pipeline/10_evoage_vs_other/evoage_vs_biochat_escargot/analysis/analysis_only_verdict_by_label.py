import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analyse_verdicts_three_systems import (
    LADDER, SYSTEMS, COLOR, INK, INK_SOFT, GRID, SURFACE, OUTDIR, load,
)

FLAT_LABEL = ["No support", "Weak", "Partial", "Support", "Strong"]


def style_axis(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=8, length=3)
    ax.set_axisbelow(True)


def panel_dotplot(ax, frame):
    """Counts per verdict level as dots on stems, one row per level."""
    counts = {s: frame[s].value_counts().reindex(LADDER).fillna(0).astype(int)
              for s in SYSTEMS}
    y_base = np.arange(len(LADDER))[::-1]
    offsets = {"EvoAge": 0.22, "Escargot": 0.0, "BioChatter": -0.22}

    for system in SYSTEMS:
        y = y_base + offsets[system]
        values = counts[system].values
        ax.hlines(y, 0, values, color=COLOR[system], linewidth=1.6, alpha=0.55)
        ax.plot(values, y, "o", markersize=7, color=COLOR[system],
                markeredgecolor=SURFACE, markeredgewidth=1.2,
                label=system, linestyle="none")
        for yi, v in zip(y, values):
            if v > 0:
                ax.text(v + 2.2, yi, str(v), va="center", fontsize=7.2, color=INK_SOFT)

    style_axis(ax)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_yticks(y_base)
    ax.set_yticklabels(FLAT_LABEL, fontsize=8.5, color=INK)
    ax.set_ylim(-0.6, len(LADDER) - 0.4)
    ax.set_xlim(0, 108)
    ax.set_xlabel("Hypotheses (n)", fontsize=8.5, color=INK_SOFT)
    ax.set_title("a   Verdicts by level", loc="left", fontsize=10,
                 color=INK, pad=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK_SOFT)


def main() -> None:
    os.makedirs(OUTDIR, exist_ok=True)
    frame = load()

    fig = plt.figure(figsize=(5.6, 4.3), facecolor=SURFACE)
    ax = fig.add_subplot(1, 1, 1)
    panel_dotplot(ax, frame)
    fig.subplots_adjust(left=0.18, right=0.97, top=0.90, bottom=0.13)

    svg = os.path.join(OUTDIR, "figure_verdict_by_level.svg")
    png = os.path.join(OUTDIR, "figure_verdict_by_level.png")
    fig.savefig(svg, format="svg", facecolor=SURFACE, bbox_inches="tight")
    fig.savefig(png, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {svg}\nwrote {png}")


if __name__ == "__main__":
    main()