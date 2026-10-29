# Relation- and type-preserving shuffled control

This module reproduces the corrected 30-seed randomization analysis used as a
supplementary robustness control. Large shuffled triples, caches, embeddings and
per-query rank arrays are excluded from Git; `example_results/` contains only the
compact aggregate tables from the completed K = 16 analysis.

## Scripts

- `R1_make_type_preserving_shuffles.py` creates full-size shuffled test sets. Heads
  and tails are permuted separately within each relation and their original entity-type
  strata. Triples present in train, validation or test are redrawn, and the script
  stops if any known triple or type violation remains.
- `R2_score_type_preserving_shuffles.py` evaluates the original test set and all
  shuffled sets with filtered head and tail prediction, using the bundled
  `sampled_ranking_engine.py` implementation.
- `R3_plot_randomization_control.py` computes one-sided empirical permutation p-values
  and generates the radar and cumulative Hits@k figures.

## Example workflow

```bash
python R1_make_type_preserving_shuffles.py \
  --data DATA_DIR --source cache --work PART_A_CACHE \
  --out work/type_shuffles --n_seeds 30 --no_npz

python R2_score_type_preserving_shuffles.py \
  --data_path DATA_DIR --model_path MODEL_DIR \
  --work PART_A_CACHE --d1_dir work/type_shuffles \
  --out_dir work/type_shuffles/scoring \
  --K 16 --n_seeds 30 --gpus 0,1

python R3_plot_randomization_control.py \
  --results_dir work/type_shuffles/scoring/results_K16
```

`--no_npz` avoids redundant compressed copies; the scorer reads the generated head and
tail arrays directly. All scripts are resumable through their existing completion files.

## Completed analysis

The completed run contained 30 randomized sets of 118,287,941 triples across 86
relations. Validation found zero known-positive triples and zero type violations.
The original test set exceeded every randomized replicate for MRR, Hits@1, Hits@3 and
Hits@10, giving the minimum attainable one-sided empirical p-value of 1/31 = 0.0323.

This analysis used 16 distinct, filtered, type-compatible negatives per query and is a
supplementary robustness test; the repository's exact full-ranking analysis remains the
primary evaluation.
