#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Per-relation score cutoffs (GT vs Random), deterministic — no Monte Carlo.
Three methods per relation: Youden's J, ROC knee, KDE density intersection.
Uses ALL scores.

Adapted for the two-folder layout:
  GT     -> relation_samples_ALLGT_output/{relation}_GT_SCORE.pkl
  Random -> relation_samples_ALLRANDOM_output/{relation}_RAND_SCORE.pkl
matched by relation name (case-insensitive).

Memory-safe ROC: the original code built an (n_scores x n_thresh) boolean
matrix via broadcasting, which for a 237M-row relation would allocate ~47 GB
and OOM. Here TPR/FPR at every threshold are computed with sort + searchsorted
(O(n log n) once, then O(n_thresh)), so it scales to hundreds of millions.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

# ========= CONFIG =========
GT_DIR     = Path("/path/to/cutoff/output/relation_samples_ALLGT_output")
RANDOM_DIR = Path("/path/to/cutoff/output/relation_samples_ALLRANDOM_output")
OUTPUT_IMG = GT_DIR / "youden_cutoffs_distribution.png"
OUTPUT_CSV = GT_DIR / "youden_cutoffs_per_relation.csv"
FIGSIZE = (10, 6)
N_THRESH = 200
SEED = 42
# =========================
rng = np.random.default_rng(SEED)


def find_pairs(gt_dir: Path, rnd_dir: Path):
    """Match {relation}_GT_SCORE.pkl to {relation}_RAND_SCORE.pkl (case-insensitive)."""
    gt = {}
    for p in gt_dir.glob("*_GT_SCORE.pkl"):
        base = p.name[:-len("_GT_SCORE.pkl")]
        gt[base.lower()] = (base, p)
    rnd = {}
    for p in rnd_dir.glob("*_RAND_SCORE.pkl"):
        base = p.name[:-len("_RAND_SCORE.pkl")]
        rnd[base.lower()] = p
    pairs = {}
    for key, (base, gp) in gt.items():
        if key in rnd:
            pairs[base] = {"GT": gp, "RANDOM": rnd[key]}
    return pairs


def get_scores(df: pd.DataFrame) -> np.ndarray:
    if "score" in df.columns:
        s = pd.to_numeric(df["score"], errors="coerce")
    else:
        s = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    return s.dropna().to_numpy(dtype=np.float64)


def roc_over_grid(gt_sorted: np.ndarray, rnd_sorted: np.ndarray, thresholds: np.ndarray):
    """TPR/FPR/J at each threshold t, where a triple is 'positive' if score >= t.
    Uses searchsorted on pre-sorted arrays — no big broadcast matrix.
    TPR(t) = fraction of GT   with score >= t
    FPR(t) = fraction of RAND with score >= t
    """
    n_gt, n_rnd = gt_sorted.size, rnd_sorted.size
    # count with score >= t  ==  n - (index of first element >= t)
    ge_gt  = n_gt  - np.searchsorted(gt_sorted,  thresholds, side="left")
    ge_rnd = n_rnd - np.searchsorted(rnd_sorted, thresholds, side="left")
    tpr = ge_gt  / n_gt
    fpr = ge_rnd / n_rnd
    return tpr, fpr, tpr - fpr


def youden_cutoff(gt_sorted, rnd_sorted, n_thresh=N_THRESH):
    lo = min(gt_sorted[0], rnd_sorted[0])
    hi = max(gt_sorted[-1], rnd_sorted[-1])
    thresholds = np.linspace(lo, hi, n_thresh)
    tpr, fpr, j = roc_over_grid(gt_sorted, rnd_sorted, thresholds)
    i = int(np.argmax(j))
    return thresholds[i], tpr[i], fpr[i], j[i], tpr, fpr, thresholds


def roc_knee(tpr, fpr, thresholds):
    dist = np.sqrt((1 - tpr) ** 2 + fpr ** 2)
    i = int(np.argmin(dist))
    return thresholds[i], tpr[i], fpr[i]


def density_intersection(gt_scores, rnd_scores, n_points=1000):
    """Score where GT and Random densities cross (scanning from high scores).
    Uses ALL points via histogram density (no subsampling, no KDE) so it scales
    to hundreds of millions of rows. GT and Random are binned on a common grid;
    the crossing is where GT density first exceeds Random from the high-score end.
    """
    lo = min(gt_scores.min(), rnd_scores.min())
    hi = max(gt_scores.max(), rnd_scores.max())
    if lo == hi:
        return np.nan
    edges = np.linspace(lo, hi, n_points + 1)
    # density=True normalizes each to area 1 (all points counted, C-level pass)
    dens_gt, _  = np.histogram(gt_scores,  bins=edges, density=True)
    dens_rnd, _ = np.histogram(rnd_scores, bins=edges, density=True)
    centers = 0.5 * (edges[:-1] + edges[1:])
    diff = dens_gt - dens_rnd
    sc = np.where(np.diff(np.sign(diff)) != 0)[0]
    if sc.size == 0:
        return np.nan
    # Choose the meaningful crossing: the one between the Random mode (low scores,
    # Random density dominates) and the GT mode (high scores, GT dominates).
    # Histogram noise in the near-zero tails can create spurious sign flips, so
    # don't just take the last crossing — take the one nearest the midpoint of
    # the two distributions' medians, which is where the real separation lies.
    mid = 0.5 * (np.median(gt_scores) + np.median(rnd_scores))
    best = sc[np.argmin(np.abs(centers[sc] - mid))]
    d0, d1 = diff[best], diff[best + 1]
    x0, x1 = centers[best], centers[best + 1]
    return x0 + (-d0 / (d1 - d0)) * (x1 - x0) if d1 != d0 else x0


def main():
    pairs = find_pairs(GT_DIR, RANDOM_DIR)
    if not pairs:
        raise SystemExit(f"No GT/RAND pairs found in {GT_DIR} / {RANDOM_DIR}")

    records, youden_cutoffs = [], []
    print(f"Found {len(pairs)} relations. Calculating cutoffs...")

    pbar = tqdm(sorted(pairs.keys()), desc="relations", unit="rel")
    for rel in pbar:
        # show which relation we're on right now (updates the bar's suffix)
        pbar.set_postfix_str(f"{rel[:35]} | loading")

        gt_scores  = get_scores(pd.read_pickle(pairs[rel]["GT"]))
        rnd_scores = get_scores(pd.read_pickle(pairs[rel]["RANDOM"]))
        n_gt, n_rnd = gt_scores.size, rnd_scores.size
        if n_gt == 0 or n_rnd == 0:
            tqdm.write(f"  ⚠️ {rel}: skipping (n_gt={n_gt}, n_random={n_rnd})")
            continue

        # sorting + scanning is the slow part for the huge (PMID) relations;
        # surface it so the bar doesn't look frozen on a 200M+ row relation
        pbar.set_postfix_str(f"{rel[:35]} | sorting {max(n_gt, n_rnd):,}")
        gt_sorted  = np.sort(gt_scores)
        rnd_sorted = np.sort(rnd_scores)

        pbar.set_postfix_str(f"{rel[:35]} | youden/knee")
        cj, tpr_j, fpr_j, j_val, tpr_c, fpr_c, thr = youden_cutoff(gt_sorted, rnd_sorted)
        ck, tpr_k, fpr_k = roc_knee(tpr_c, fpr_c, thr)

        pbar.set_postfix_str(f"{rel[:35]} | density")
        cd = density_intersection(gt_scores, rnd_scores)

        youden_cutoffs.append(cj)
        records.append({
            "relation": rel, "n_gt": n_gt, "n_random": n_rnd,
            "cutoff_density_intersection": cd,
            "cutoff_youdenJ": cj, "youdenJ_TPR": tpr_j, "youdenJ_FPR": fpr_j, "youdenJ_J": j_val,
            "cutoff_roc_knee": ck, "roc_knee_TPR": tpr_k, "roc_knee_FPR": fpr_k,
        })
        tqdm.write(f"  - {rel}: Youden = {cj:.4f} (TPR={tpr_j:.3f}, FPR={fpr_j:.3f}, J={j_val:.3f}) | "
                   f"knee = {ck:.4f} | density = {cd:.4f}")

    df_out = pd.DataFrame(records)
    df_out.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Wrote per-relation cutoffs to {OUTPUT_CSV}")

    if len(youden_cutoffs) > 1:
        fig, ax = plt.subplots(figsize=FIGSIZE)
        ax.hist(youden_cutoffs, bins=15, density=True, alpha=0.6, label="Histogram of Cutoffs")
        try:
            kde = gaussian_kde(youden_cutoffs)
            xr = np.linspace(min(youden_cutoffs), max(youden_cutoffs), 200)
            ax.plot(xr, kde(xr), color="firebrick", lw=2, label="Density Estimate (KDE)")
        except Exception:
            pass
        m = float(np.mean(youden_cutoffs))
        ax.axvline(m, color="darkblue", ls="--", lw=2, label=f"Mean Cutoff: {m:.4f}")
        ax.set_xlabel("Youden's J Cutoff Value"); ax.set_ylabel("Density")
        ax.set_title("Distribution of Optimal Cutoffs Across All Relations")
        ax.grid(True, ls="--", lw=0.5); ax.legend()
        plt.tight_layout(); plt.savefig(OUTPUT_IMG, dpi=300); plt.close(fig)
        print(f"✅ Wrote distribution plot to {OUTPUT_IMG}")


if __name__ == "__main__":
    main()
