"""Complete, self-contained analysis: three result files in, publication figure out.

Reads the three MedGemma-judged result files, joins them hypothesis by
hypothesis, and renders the comparison figure. Nothing is imported from the
other analysis scripts -- this file does the whole job on its own.

INPUTS
    BioChatter : Biochatter/hypothesis_ques_answer/biochatter_hypothesis_results_medgemma.csv
    Escargot   : escargot/hypothesis_ques_answer/escargot_hypothesis_results_medgemma.csv
    EvoAge     : .../hypothesis_pipeline_results_final_with_percentile_buckets_full.csv

OUTPUTS  (./verdict_analysis/)
    figure_verdict_alternative.svg / .png   the figure panel
    verdict_paired.csv                      Title, DOI, Right Hypothesis + the three verdicts
    verdict_summary.csv                     counts and percentages per system

JOINING
    Rows are joined on DOI, not on Title and not on row order. DOI was verified
    unique (101/101) and identical across all three files, so it is a safe key;
    Title is carried through for readability but is not used for matching, and
    positional alignment is avoided because it would silently mispair rows if any
    file were ever re-sorted or re-run on a subset.

VERDICT LADDER
    no_support < weak_support < partial_support < support < strong_support
    Values outside this ladder (EvoAge emits "unknown" for a few runs, and a
    judge call can fail) become NaN. They are counted in the denominator and
    reported separately rather than folded into no_support.

Usage:
    python verdict_analysis_complete.py
"""

import ast
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LADDER = ["no_support", "weak_support", "partial_support", "support", "strong_support"]
SUPPORTED = LADDER[1:]
RANK = {v: i for i, v in enumerate(LADDER)}

SHORT_LABEL = ["No\nsupport", "Weak", "Partial", "Support", "Strong"]
FLAT_LABEL = ["No support", "Weak", "Partial", "Support", "Strong"]

SYSTEMS = ["EvoAge", "Escargot", "BioChatter"]
KEY = "DOI"
CARRY = ["Title", "DOI", "Right Hypothesis"]

# Categorical palette, validated: adjacent OKLab dE 33.6 and 27.6 under normal
# vision, worst case 10.4 under deuteranopia, all clearing 2:1 on the surface.
COLOR = {"EvoAge": "#2a78d6", "Escargot": "#eb6834", "BioChatter": "#1baf7a"}
# Sequential single-hue ramp for the agreement matrices (magnitude, not identity).
SEQ = LinearSegmentedColormap.from_list(
    "evoage_blue", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

INK = "#0b0b0b"
INK_SOFT = "#52514e"
GRID = "#e3e2de"
SURFACE = "#fcfcfb"


# ---------------------------------------------------------------------------
# Load and join
# ---------------------------------------------------------------------------

def parse_evoage_verdict(value):
    """EvoAge stores its judge output as a stringified dict in one column."""
    try:
        return (ast.literal_eval(value) or {}).get("verdict")
    except (ValueError, SyntaxError, TypeError):
        return None


def normalise_key(series: pd.Series) -> pd.Series:
    """DOIs vary in trailing slash and case between files."""
    return series.astype(str).str.strip().str.lower().str.rstrip("/")


def clean_verdict(series: pd.Series) -> pd.Series:
    """Lowercase and blank anything outside the ladder, so it is never counted
    as a real verdict."""
    cleaned = series.astype(str).str.strip().str.lower()
    return cleaned.where(cleaned.isin(LADDER))


def load() -> pd.DataFrame:
    bio = pd.read_csv(BIOCHATTER_CSV)
    esc = pd.read_csv(ESCARGOT_CSV)
    evo = pd.read_csv(EVOAGE_CSV)

    evo = evo.assign(
        EvoAge=evo["EvoAge_hypothesis_response"].apply(parse_evoage_verdict),
        _key=normalise_key(evo[KEY]),
    )
    esc = esc.assign(Escargot=esc["Medgemma_verdict"], _key=normalise_key(esc[KEY]))
    bio = bio.assign(BioChatter=bio["Medgemma_verdict"], _key=normalise_key(bio[KEY]))

    # Fail loudly rather than silently dropping or mispairing rows.
    for name, frame in (("EvoAge", evo), ("Escargot", esc), ("BioChatter", bio)):
        duplicated = frame["_key"].duplicated().sum()
        if duplicated:
            raise SystemExit(f"{name}: {duplicated} duplicate {KEY} values -- cannot join safely")

    merged = (evo[["_key"] + CARRY + ["EvoAge"]]
              .merge(esc[["_key", "Escargot"]], on="_key", how="inner", validate="1:1")
              .merge(bio[["_key", "BioChatter"]], on="_key", how="inner", validate="1:1"))

    if len(merged) != len(evo):
        missing = len(evo) - len(merged)
        print(f"warning: {missing} hypotheses did not match on {KEY} and were dropped")

    for system in SYSTEMS:
        merged[system] = clean_verdict(merged[system])

    return merged.drop(columns="_key")


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------

def style_axis(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=8, length=3)
    ax.set_axisbelow(True)


def panel_dotplot(ax, frame):
    """a - counts per verdict level, as dots on stems."""
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
        for yi, value in zip(y, values):
            if value > 0:
                ax.text(value + 2.2, yi, str(value), va="center",
                        fontsize=7.2, color=INK_SOFT)

    style_axis(ax)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_yticks(y_base)
    ax.set_yticklabels(FLAT_LABEL, fontsize=8.5, color=INK)
    ax.set_ylim(-0.6, len(LADDER) - 0.4)
    ax.set_xlim(0, max(108, len(frame) * 1.07))
    ax.set_xlabel("Hypotheses (n)", fontsize=8.5, color=INK_SOFT)
    ax.set_title("a   Verdicts by level", loc="left", fontsize=10,
                 color=INK, pad=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="lower right", labelcolor=INK_SOFT)


def panel_cumulative(ax, frame):
    """b - share of hypotheses reaching at least each level."""
    x = np.arange(len(LADDER))
    total = len(frame)

    for system in SYSTEMS:
        ranks = frame[system].map(RANK).dropna()
        share = [100 * (ranks >= i).sum() / total for i in x]
        ax.plot(x, share, "-o", color=COLOR[system], linewidth=2,
                markersize=6.5, markeredgecolor=SURFACE, markeredgewidth=1.2,
                label=system)
        ax.annotate(f"{share[1]:.0f}%", xy=(1, share[1]), xytext=(6, 6),
                    textcoords="offset points", fontsize=7.5, color=COLOR[system])

    style_axis(ax)
    ax.yaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(SHORT_LABEL, fontsize=8, color=INK_SOFT)
    ax.set_ylim(-4, 108)
    ax.set_ylabel("Hypotheses reaching at least\nthis level (%)",
                  fontsize=8.5, color=INK_SOFT)
    ax.set_title("b   Cumulative attainment across the ladder", loc="left",
                 fontsize=10, color=INK, pad=10, fontweight="bold")
    ax.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=INK_SOFT)


def panel_matrix(ax, frame, baseline, show_ylabel=True):
    """c - EvoAge against one baseline, hypothesis by hypothesis."""
    pair = frame[["EvoAge", baseline]].dropna()
    n = len(LADDER)
    matrix = np.zeros((n, n), dtype=int)
    for evo, base in zip(pair["EvoAge"], pair[baseline]):
        matrix[RANK[evo], RANK[base]] += 1

    display = matrix[::-1]        # row 0 at the bottom: higher reads upward
    ax.imshow(display, cmap=SEQ, vmin=0, vmax=max(1, matrix.max()), aspect="equal")

    for i in range(n):
        for j in range(n):
            value = display[i, j]
            if value:
                strong = value > matrix.max() * 0.55
                ax.text(j, i, str(value), ha="center", va="center", fontsize=8,
                        color="#ffffff" if strong else INK)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(FLAT_LABEL, fontsize=7.5, color=INK_SOFT, rotation=40, ha="right")
    ax.set_yticklabels(FLAT_LABEL[::-1], fontsize=7.5, color=INK_SOFT)
    ax.set_xlabel(f"{baseline} verdict", fontsize=8.5, color=INK_SOFT)
    if show_ylabel:
        ax.set_ylabel("EvoAge verdict", fontsize=8.5, color=INK_SOFT)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=1.5)

    above = int(sum(matrix[i, j] for i in range(n) for j in range(n) if i > j))
    ax.set_title(f"EvoAge higher in {above}/{len(pair)}", loc="left",
                 fontsize=8.5, color=INK_SOFT, pad=6)


def build_figure(frame):
    fig = plt.figure(figsize=(11.5, 8.6), facecolor=SURFACE)
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.05],
                            hspace=0.45, wspace=0.3,
                            left=0.09, right=0.97, top=0.93, bottom=0.10)

    panel_dotplot(fig.add_subplot(grid[0, 0]), frame)
    panel_cumulative(fig.add_subplot(grid[0, 1]), frame)

    ax_c1 = fig.add_subplot(grid[1, 0])
    ax_c2 = fig.add_subplot(grid[1, 1])
    panel_matrix(ax_c1, frame, "Escargot", show_ylabel=True)
    panel_matrix(ax_c2, frame, "BioChatter", show_ylabel=False)
    ax_c1.text(-0.28, 1.16, "c   Per-hypothesis agreement (EvoAge vs each baseline)",
               transform=ax_c1.transAxes, fontsize=10, color=INK,
               fontweight="bold", ha="left")
    return fig


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def write_tables(frame):
    rows = []
    for system in SYSTEMS:
        counts = frame[system].value_counts().reindex(LADDER).fillna(0).astype(int)
        row = {"system": system, "n_hypotheses": len(frame)}
        row.update({v: int(counts[v]) for v in LADDER})
        row["any_support_n"] = int(frame[system].isin(SUPPORTED).sum())
        row["any_support_pct"] = round(100 * row["any_support_n"] / len(frame), 1)
        row["unusable_or_unknown"] = int(frame[system].isna().sum())
        rows.append(row)

    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(OUTDIR, "verdict_summary.csv"), index=False)
    frame[CARRY + SYSTEMS].to_csv(
        os.path.join(OUTDIR, "verdict_paired.csv"), index=False)
    return summary


def main() -> None:
    os.makedirs(OUTDIR, exist_ok=True)

    frame = load()
    print(f"joined {len(frame)} hypotheses on {KEY}\n")

    summary = write_tables(frame)
    print(summary.to_string(index=False))
    print()

    fig = build_figure(frame)
    svg = os.path.join(OUTDIR, "figure_verdict_alternative.svg")
    png = os.path.join(OUTDIR, "figure_verdict_alternative.png")
    fig.savefig(svg, format="svg", facecolor=SURFACE, bbox_inches="tight")
    fig.savefig(png, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)

    for path in (svg, png,
                 os.path.join(OUTDIR, "verdict_summary.csv"),
                 os.path.join(OUTDIR, "verdict_paired.csv")):
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
