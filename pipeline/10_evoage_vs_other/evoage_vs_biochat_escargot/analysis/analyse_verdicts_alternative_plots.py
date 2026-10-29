"""Single-plot version: verdicts by level, drawn as a lollipop (dot) plot.

One figure, publication ready. A dot marks the number of hypotheses each system
placed at each level of the verdict ladder, with a thin stem carrying the eye
back to the axis -- the same information as grouped bars at a fraction of the ink.

Self-contained: reads the three MedGemma-judged result files directly and joins
them on DOI (verified unique and identical across all three files; Title is
carried for readability but not used for matching).

Output (./verdict_analysis/):
    figure_verdict_lollipop.svg / .png

To plot a different single view instead, swap the call in main() -- the other
forms live in verdict_analysis_complete.py.

Usage:
    python analyse_verdicts_alternative_plots.py
"""

import ast
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
# Result CSVs live one level up, beside the two baseline directories.
ROOT = os.path.dirname(HERE)
OUTDIR = os.path.join(HERE, "verdict_analysis")

BIOCHATTER_CSV = os.path.join(
    ROOT, "Biochatter", "hypothesis_ques_answer",
    "biochatter_hypothesis_results_medgemma.csv")
ESCARGOT_CSV = os.path.join(
    ROOT, "escargot", "hypothesis_ques_answer",
    "escargot_hypothesis_results_medgemma.csv")
EVOAGE_CSV = os.path.join(ROOT, "evoage_results",
                          "hypothesis_pipeline_results_final_with_percentile_buckets_full.csv")

LADDER = ["no_support", "weak_support", "partial_support", "support", "strong_support"]
LABEL = ["No\nsupport", "Weak\nsupport", "Partial\nsupport", "Support", "Strong\nsupport"]
RANK = {v: i for i, v in enumerate(LADDER)}
SYSTEMS = ["EvoAge", "Escargot", "BioChatter"]

# Validated categorical palette (adjacent OKLab dE 33.6 / 27.6 normal vision,
# worst case 10.4 under deuteranopia, all clearing 2:1 contrast on the surface).
COLOR = {"EvoAge": "#2a78d6", "Escargot": "#eb6834", "BioChatter": "#1baf7a"}
INK, INK_SOFT, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2de", "#fcfcfb"


def parse_evoage_verdict(value):
    """EvoAge stores its judge output as a stringified dict in one column."""
    try:
        return (ast.literal_eval(value) or {}).get("verdict")
    except (ValueError, SyntaxError, TypeError):
        return None


def load() -> pd.DataFrame:
    """One row per hypothesis, joined on DOI, with a verdict column per system."""
    def key(series):
        return series.astype(str).str.strip().str.lower().str.rstrip("/")

    def clean(series):
        cleaned = series.astype(str).str.strip().str.lower()
        return cleaned.where(cleaned.isin(LADDER))

    evo = pd.read_csv(EVOAGE_CSV)
    esc = pd.read_csv(ESCARGOT_CSV)
    bio = pd.read_csv(BIOCHATTER_CSV)

    evo = evo.assign(EvoAge=evo["EvoAge_hypothesis_response"].apply(parse_evoage_verdict),
                     _key=key(evo["DOI"]))
    esc = esc.assign(Escargot=esc["Medgemma_verdict"], _key=key(esc["DOI"]))
    bio = bio.assign(BioChatter=bio["Medgemma_verdict"], _key=key(bio["DOI"]))

    merged = (evo[["_key", "Title", "DOI", "Right Hypothesis", "EvoAge"]]
              .merge(esc[["_key", "Escargot"]], on="_key", how="inner", validate="1:1")
              .merge(bio[["_key", "BioChatter"]], on="_key", how="inner", validate="1:1"))

    for system in SYSTEMS:
        merged[system] = clean(merged[system])
    return merged.drop(columns="_key")


def plot_lollipop(frame):
    """Verdicts by level: a dot marks the count, a stem carries it to the axis."""
    fig, ax = plt.subplots(figsize=(7.6, 5.0), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    counts = {s: frame[s].value_counts().reindex(LADDER).fillna(0).astype(int)
              for s in SYSTEMS}
    y_base = np.arange(len(LADDER))[::-1]
    offsets = {"EvoAge": 0.23, "Escargot": 0.0, "BioChatter": -0.23}

    for system in SYSTEMS:
        y = y_base + offsets[system]
        values = counts[system].values
        ax.hlines(y, 0, values, color=COLOR[system], linewidth=1.8, alpha=0.55)
        ax.plot(values, y, "o", markersize=8, color=COLOR[system],
                markeredgecolor=SURFACE, markeredgewidth=1.4,
                label=system, linestyle="none", zorder=3)
        for yi, value in zip(y, values):
            if value > 0:
                ax.text(value + 2.4, yi, str(value), va="center",
                        fontsize=8.5, color=INK_SOFT)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=9, length=3)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, linewidth=0.7)

    ax.set_yticks(y_base)
    ax.set_yticklabels([l.replace("\n", " ") for l in LABEL],
                       fontsize=10, color=INK)
    ax.set_ylim(-0.6, len(LADDER) - 0.4)
    ax.set_xlim(0, max(108, len(frame) * 1.08))
    ax.set_xlabel("Hypotheses (n)", fontsize=10, color=INK_SOFT)
    ax.set_title(f"Verdicts by level across {len(frame)} biological hypotheses",
                 loc="left", fontsize=12, color=INK, pad=12, fontweight="bold")
    ax.legend(frameon=False, fontsize=10, loc="lower right", labelcolor=INK_SOFT)

    fig.tight_layout()
    return fig


def main() -> None:
    os.makedirs(OUTDIR, exist_ok=True)
    frame = load()
    print(f"joined {len(frame)} hypotheses on DOI")
    for system in SYSTEMS:
        n = frame[system].isin(LADDER[1:]).sum()
        print(f"  {system:<11} any support: {n}/{len(frame)} ({100*n/len(frame):.0f}%)")

    fig = plot_lollipop(frame)
    svg = os.path.join(OUTDIR, "figure_verdict_lollipop.svg")
    png = os.path.join(OUTDIR, "figure_verdict_lollipop.png")
    fig.savefig(svg, format="svg", facecolor=SURFACE, bbox_inches="tight")
    fig.savefig(png, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print(f"\nwrote {svg}\nwrote {png}")


if __name__ == "__main__":
    main()
