# Analysis 4: Type-Compatible Evaluation

> 📂 **Source code:** [`pipeline/08_evaluation_analysis/type_specific_evaluation`](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/08_evaluation_analysis/type_specific_evaluation)

## Purpose

This analysis evaluates the EvoAge RESCAL model against biologically valid candidate entities. For each relation, head and tail predictions are restricted to entities with compatible types, and all other known true triples from the training, validation, and test sets are filtered from the candidate pool.

The workflow combines exact full-pool ranking, type-preserving randomized controls, and candidate-count sensitivity analyses. This separates model performance from effects caused by invalid entity types or the number of sampled negatives.

## Workflow

The scripts are organized in execution order:

1. **`R1A_exact_type_ranking.py`** — Performs exact filtered ranking over the complete type-compatible head and tail candidate pools. It reports overall and per-relation MRR, mean rank, and Hits@K metrics.
2. **`R1B_shuffled_full_ranking.py`** — Builds type-preserving null triples and evaluates them with the same exact ranking engine used for the real test set.
3. **`R1C_candidate_sensitivity_evoage.py`** — Repeats EvoAge evaluation across increasing numbers of sampled type-compatible candidates to measure the sensitivity of ranking metrics to candidate-set size.
4. **`R1D_candidate_sensitivity_synthetic.py`** — Runs the corresponding candidate-sensitivity and randomized-control analysis on a synthetic typed knowledge graph.
5. **`R2_make_evaluation_panels.py`** — Combines the resulting summary tables into the publication evaluation panels.

## Inputs and outputs

The ranking scripts require the EvoAge train, validation, and test splits; the typed entity and relation dictionaries; and the trained RESCAL model. Paths, GPU selection, seeds, sampling sizes, and output locations are supplied through command-line arguments.

The workflow writes rank arrays, candidate-pool metadata, overall and per-relation CSV summaries, JSON results, and run metadata. Large intermediate rank arrays and model artifacts are not stored in Git; the scripts can resume from existing intermediate outputs.

## Interpretation

The exact evaluation measures each target against every valid entity for that relation side rather than against unrestricted or biologically incompatible entities. The shuffled and synthetic controls provide matched null comparisons, while the candidate-sensitivity sweeps show how performance changes as the evaluation pool grows.
