#!/usr/bin/env python3
"""Create the two-page publication evaluation panel.

Uses only:
  Run from any directory:
  python R2_make_evaluation_panels.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

EVO_SWEEP = RESULTS / "evoage_candidate_sensitivity.csv"
SIM_SWEEP = RESULTS / "synthetic_candidate_sensitivity.csv"
FULL_OVERALL = RESULTS / "evoage_full_ranking.csv"
FULL_NULL = RESULTS / "evoage_full_ranking_null.csv"

COL = {
    "eval": "#0072B2",       # Okabe-Ito blue
    "control": "#D55E00",    # vermillion
    "chance": "#333333",
    "tail": "#009E73",       # bluish green
    "head": "#CC79A7",       # reddish purple
    "both": "#0072B2",
}


def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    return path


def style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.linewidth": 0.8,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8.5,
        "figure.dpi": 150,
        "savefig.dpi": 400,
        "savefig.bbox": "tight",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        # Keep SVG labels editable as text in Adobe Illustrator.
        "svg.fonttype": "none",
    })


def panel_label(ax, label: str) -> None:
    ax.text(-0.14, 1.08, label, transform=ax.transAxes, fontsize=13,
            fontweight="bold", va="top", ha="left")


def clean_axis(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#D8D8D8", linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)


def setup_k_axis(ax, ks) -> None:
    ax.set_xscale("log", base=2)
    ax.set_xticks(ks)
    ax.set_xticklabels([f"{int(k):,}" for k in ks], rotation=30,
                       ha="right", rotation_mode="anchor", fontsize=8)
    ax.xaxis.set_minor_locator(LogLocator(base=2, subs=[]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Sampled type-compatible negatives per query (K)")
    clean_axis(ax)


def line(ax, x, y, label, color, marker, linestyle="-"):
    ax.plot(x, y, label=label, color=color, marker=marker, linestyle=linestyle,
            linewidth=2.0, markersize=5.2, markeredgecolor="white",
            markeredgewidth=0.55, zorder=3)


def log_bars(ax, x, values, width, *, offset=0.0, label=None, color=None,
             floor=None):
    """Draw log-scale bars without geometry extending towards log(0).

    A conventional bar starts at zero, which is infinitely far below a
    logarithmic axis. Matplotlib clips that hidden geometry correctly, but
    releasing the SVG clipping masks in Illustrator exposes very long bars.
    Starting at a finite floor keeps the exported vector artwork editable.
    """
    values = np.asarray(values, dtype=float)
    if floor is None:
        floor = values[values > 0].min() / 2.5
    ax.bar(np.asarray(x) + offset, values - floor, width, bottom=floor,
           label=label, color=color)
    return floor


def figure_candidate_sensitivity(evo: pd.DataFrame, sim: pd.DataFrame):
    """Figure 1: metric dependence on candidate-set size in real and synthetic KGs."""
    fig, axes = plt.subplots(2, 4, figsize=(15.8, 7.3), constrained_layout=True)

    evo_eval = evo[evo["mode"] == "eval"].sort_values("K")
    evo_ctrl = evo[evo["mode"] == "control"].sort_values("K")
    evo_ks = evo_eval["K"].to_numpy()
    sim = sim.sort_values("K")
    sim_ks = sim["K"].to_numpy()

    specifications = []
    metric_specs = [
        ("MRR", "micro_MRR", "micro_MRR"),
        ("Hits@1", "micro_H@1", "micro_H1"),
        ("Hits@3", "micro_H@3", "micro_H3"),
        ("Hits@10", "micro_H@10", "micro_H10"),
    ]
    for col, (label, evo_metric, sim_metric) in enumerate(metric_specs):
        evo_random = (evo_eval["micro_random_MRR"] if label == "MRR" else
                      np.minimum(int(label.split("@")[1]), evo_ks + 1) / (evo_ks + 1))
        sim_random = (sim["rand_MRR"] if label == "MRR" else
                      np.minimum(int(label.split("@")[1]), sim_ks + 1) / (sim_ks + 1))
        specifications.extend([
            (axes[0, col], evo_ks, evo_eval[evo_metric], evo_ctrl[evo_metric],
             evo_random, "EvoAge", label, "ABCD"[col]),
            (axes[1, col], sim_ks, sim[f"eval_{sim_metric}"], sim[f"control_{sim_metric}"],
             sim_random, "Synthetic typed DCSBM", label, "EFGH"[col]),
        ])

    for ax, x, y_eval, y_ctrl, y_rand, dataset, metric, letter in specifications:
        line(ax, x, y_eval, "Observed test triples", COL["eval"], "o")
        line(ax, x, y_ctrl, "Type-preserving shuffle", COL["control"], "s", "--")
        line(ax, x, y_rand, "Uniform-rank expectation", COL["chance"], "^", ":")
        setup_k_axis(ax, x)
        ax.set_ylabel(metric)
        ax.set_ylim(bottom=0)
        ax.set_title(f"{dataset}: {metric}")
        panel_label(ax, letter)

    # One shared legend avoids four repeated legends.
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3,
               frameon=False, bbox_to_anchor=(0.5, -0.035))
    fig.suptitle("Entity-prediction metrics depend strongly on candidate-set size",
                 fontsize=14, fontweight="bold")
    fig.text(0.5, -0.065,
             "Micro metrics combine head and tail queries. Synthetic graph: typed degree-corrected "
             "stochastic block model; control: within-relation degree-preserving shuffle.",
             ha="center", va="top", fontsize=8.2)
    return fig


def figure_full_ranking(full: pd.DataFrame, null: pd.DataFrame):
    """Figure 2: definitive exact full-pool results and exact shuffled null."""
    fig, axes = plt.subplots(1, 5, figsize=(17.2, 4.15), constrained_layout=True)

    order = ["micro_tail", "micro_head", "micro_both"]
    labels = ["Tail", "Head", "Both"]
    f = full.set_index("view").loc[order]
    x = np.arange(3)
    width = 0.36

    # Log scale is necessary because head chance metrics are very small.
    full_metrics = [
        ("MRR", "random_MRR", "MRR"),
        ("H@1", "random_H@1", "Hits@1"),
        ("H@3", "random_H@3", "Hits@3"),
        ("H@10", "random_H@10", "Hits@10"),
    ]
    for i, (metric, random_metric, label) in enumerate(full_metrics):
        ax = axes[i]
        values = np.concatenate((f[metric].to_numpy(dtype=float),
                                 f[random_metric].to_numpy(dtype=float)))
        floor = values[values > 0].min() / 2.5
        log_bars(ax, x, f[metric], width, offset=-width / 2,
                 label="RESCAL", color=COL["eval"], floor=floor)
        log_bars(ax, x, f[random_metric], width, offset=width / 2,
                 label="Uniform-rank expectation", color="#A9A9A9", floor=floor)
        ax.set_yscale("log")
        ax.set_ylim(bottom=floor)
        ax.set_xticks(x, labels)
        ax.set_ylabel(f"{label} (log scale)")
        ax.set_title(f"Exact filtered full-pool {label}")
        clean_axis(ax); panel_label(ax, "ABCD"[i])
        if i == 0:
            ax.legend(frameon=False, loc="upper right")

    # Exact full-ranking observed vs relation/type-preserving null.
    ax = axes[4]
    n = null.set_index("method")
    metrics = ["micro_MRR", "micro_H@1", "micro_H@3", "micro_H@10", "micro_H@100"]
    metric_labels = ["MRR", "Hits@1", "Hits@3", "Hits@10", "Hits@100"]
    xx = np.arange(len(metrics))
    observed = n.loc["eval", metrics].to_numpy(dtype=float)
    shuffled = n.loc["shuffle", metrics].to_numpy(dtype=float)
    floor = np.concatenate((observed, shuffled)).min() / 2.5
    log_bars(ax, xx, observed, width, offset=-width / 2,
             label="Observed test triples", color=COL["eval"], floor=floor)
    log_bars(ax, xx, shuffled, width, offset=width / 2,
             label="Type-preserving shuffle", color=COL["control"], floor=floor)
    ax.set_yscale("log")
    ax.set_ylim(bottom=floor)
    ax.set_xticks(xx, metric_labels, rotation=22, ha="right")
    ax.set_ylabel("Metric value (log scale)")
    ax.set_title("Exact full-pool null comparison")
    clean_axis(ax); panel_label(ax, "E")
    ax.legend(frameon=False, loc="upper left")

    fig.suptitle("Definitive evaluation over all filtered, type-compatible candidates",
                 fontsize=14, fontweight="bold")
    fig.text(0.5, -0.04,
             "Known positives in train, validation and test are filtered. Both denotes the micro-average "
             "over all head- and tail-prediction queries.",
             ha="center", va="top", fontsize=8.4)
    return fig


def export_values(evo, sim, full, null, output: Path) -> None:
    rows = []
    for _, r in evo.iterrows():
        for metric in ("micro_MRR", "micro_H@1", "micro_H@3", "micro_H@10",
                       "micro_random_MRR"):
            if metric in r:
                rows.append({"figure": 1, "dataset": "EvoAge", "protocol": r["mode"],
                             "K": r["K"], "metric": metric, "value": r[metric]})
        for cutoff in (1, 3, 10):
            rows.append({"figure": 1, "dataset": "EvoAge", "protocol": "random",
                         "K": r["K"], "metric": f"micro_H@{cutoff}",
                         "value": min(cutoff, r["K"] + 1) / (r["K"] + 1)})
    for _, r in sim.iterrows():
        for protocol, prefix in (("eval", "eval"), ("control", "control"), ("random", "rand")):
            for suffix in ("micro_MRR", "micro_H1", "micro_H3", "micro_H10"):
                col = f"{prefix}_{suffix}" if prefix != "rand" else f"rand_{suffix.split('_')[-1]}"
                if col in r:
                    rows.append({"figure": 1, "dataset": "Synthetic DCSBM", "protocol": protocol,
                                 "K": r["K"], "metric": suffix, "value": r[col]})
        if "rand_H3" not in r:
            rows.append({"figure": 1, "dataset": "Synthetic DCSBM", "protocol": "random",
                         "K": r["K"], "metric": "micro_H3",
                         "value": min(3, r["K"] + 1) / (r["K"] + 1)})
    for _, r in full.iterrows():
        if r["view"] in {"micro_tail", "micro_head", "micro_both"}:
            for metric in ("MRR", "random_MRR", "H@1", "random_H@1",
                           "H@3", "random_H@3", "H@10", "random_H@10"):
                rows.append({"figure": 2, "dataset": "EvoAge full ranking", "protocol": r["view"],
                             "K": "full", "metric": metric, "value": r[metric]})
    for _, r in null.iterrows():
        for metric in ("micro_MRR", "micro_H@1", "micro_H@3", "micro_H@10", "micro_H@100"):
            rows.append({"figure": 2, "dataset": "EvoAge full-ranking null",
                         "protocol": r["method"], "K": "full", "metric": metric,
                         "value": r[metric]})
    pd.DataFrame(rows).to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=HERE)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    style()

    evo = pd.read_csv(require(EVO_SWEEP))
    sim = pd.read_csv(require(SIM_SWEEP))
    full = pd.read_csv(require(FULL_OVERALL))
    null = pd.read_csv(require(FULL_NULL))

    # Manuscript comparison uses the same K grid in both datasets.
    evo = evo[evo["K"].between(16, 1024)].copy()
    sim = sim[sim["K"].between(16, 1024)].copy()

    fig1 = figure_candidate_sensitivity(evo, sim)
    fig2 = figure_full_ranking(full, null)

    combined = args.out_dir / "eval_panel_final.pdf"
    with PdfPages(combined, metadata={
        "Title": "Reviewer 3: candidate sensitivity and full type-compatible ranking",
        "Author": "EvoAge authors",
        "Subject": "Filtered entity-prediction evaluation",
    }) as pdf:
        pdf.savefig(fig1, bbox_inches="tight")
        pdf.savefig(fig2, bbox_inches="tight")

    for fig, stem in ((fig1, "figure1_candidate_sensitivity"),
                      (fig2, "figure2_full_ranking")):
        fig.savefig(args.out_dir / f"{stem}.pdf", bbox_inches="tight")
        fig.savefig(args.out_dir / f"{stem}.png", bbox_inches="tight", dpi=400)
        fig.savefig(args.out_dir / f"{stem}.svg", bbox_inches="tight")
        plt.close(fig)

    export_values(evo, sim, full, null, args.out_dir / "plotted_values.csv")
    print(f"Wrote {combined}")


if __name__ == "__main__":
    main()
