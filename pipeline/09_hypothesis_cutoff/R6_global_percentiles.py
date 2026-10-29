#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Global percentile stats across ALL GT triple scores pooled from every
*_GT_SCORE.pkl in the GT output folder. Scores are negative (closer to 0 =
better), so p100/max is the BEST score and p0/min is the WORST.

Memory: pools every score into one array. Total is ~1.2B floats (~10 GB) for
this KG — fits comfortably in 200 GB RAM. Each pkl's score column is extracted
as float32 (halves memory vs float64) and only that column is kept.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ============================= CONFIG =============================
GT_DIR  = Path("/path/to/cutoff/output/relation_samples_ALLGT_output")
OUT_CSV = GT_DIR / "GLOBAL_GT_score_percentiles.csv"

SCORE_COL = "score"
PCTS = [0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100]
# =================================================================


def load_scores(pkl: Path) -> np.ndarray:
    df = pd.read_pickle(pkl)
    col = SCORE_COL if SCORE_COL in df.columns else df.columns[-1]
    s = pd.to_numeric(df[col], errors="coerce").to_numpy()
    s = s[np.isfinite(s)]
    return s.astype(np.float32, copy=False)   # float32 to halve memory


def main():
    pkls = sorted(GT_DIR.glob("*_GT_SCORE.pkl"))
    if not pkls:
        raise SystemExit(f"No *_GT_SCORE.pkl found in {GT_DIR}")
    print(f"Found {len(pkls)} GT files. Pooling all scores...")

    parts = []
    total = 0
    for p in tqdm(pkls, desc="loading", unit="file"):
        s = load_scores(p)
        if s.size:
            parts.append(s)
            total += s.size
        tqdm.write(f"  {p.name}: {s.size:,} scores (running total {total:,})")

    print(f"\nConcatenating {total:,} scores across {len(parts)} relations...")
    allscores = np.concatenate(parts)
    del parts

    print("Computing global stats (percentiles use exact full data)...")
    pcs = np.percentile(allscores, PCTS)
    stats = {
        "n": int(allscores.size),
        "mean": float(allscores.mean()),
        "std": float(allscores.std()),
        "min": float(allscores.min()),
        "max": float(allscores.max()),
        "range": float(allscores.max() - allscores.min()),
    }
    # p25/p75 for IQR
    p25, p75 = np.percentile(allscores, [25, 75])
    stats["iqr"] = float(p75 - p25)
    for pct, val in zip(PCTS, pcs):
        stats[f"p{pct}"] = float(val)

    df_out = pd.DataFrame([stats])
    df_out.to_csv(OUT_CSV, index=False)

    print("\n===== GLOBAL GT SCORE STATS (all relations pooled) =====")
    print(f"n     = {stats['n']:,}")
    print(f"mean  = {stats['mean']:.6f}   std = {stats['std']:.6f}")
    print(f"min   = {stats['min']:.6f} (worst)   max = {stats['max']:.6f} (best)")
    print("percentiles (low pct = worse/more-negative, high pct = better/near-zero):")
    for pct in PCTS:
        print(f"  p{pct:<3} = {stats[f'p{pct}']:.6f}")
    print(f"\n✅ Saved -> {OUT_CSV}")


if __name__ == "__main__":
    main()
