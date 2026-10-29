# Hypothesis Cutoff

This stage calculates score cutoffs for interpreting EvoAge link-prediction results. We compare model scores for known knowledge-graph triples against scores for randomly generated triples, then use the two score distributions to select relation-specific thresholds.

## Workflow

The scripts in `pipeline/09_hypothesis_cutoff/` are run in order:

1. **Collect ground-truth triples (`R1`)** — Extract all known triples for each relation from the EvoAge training KG tensor and write them in the format required for DGL-KE scoring.
2. **Generate random triples (`R2`)** — Create a matched random set for each relation using valid head and tail entity types, while excluding triples already present in the KG.
3. **Score ground-truth triples (`R3`)** — Use the trained EvoAge RESCAL model to calculate a score for every known triple.
4. **Score random triples (`R4`)** — Score the generated random triples using the same model and inference settings.
5. **Calculate relation cutoffs (`R5`)** — Compare the ground-truth and random score distributions for each relation. The script reports Youden's J, ROC-knee, and density-intersection thresholds.
6. **Calculate global percentiles (`R6`)** — Pool the ground-truth scores across relations and calculate summary statistics and percentiles for global score interpretation.


## Main outputs

- `relation_cutoff_summary.csv` — Relation-level cutoff values and associated performance statistics.
- `GLOBAL_GT_score_percentiles.csv` — Global summary statistics and score percentiles calculated across all ground-truth triples.

## Use in EvoAge hypothesis testing

The EvoAge hypothesis-testing module uses the relation-specific Youden's J cutoff to classify each scored hypothesis triple as **ACCEPT** or **REJECT**. It also compares the score with the global ground-truth percentiles to show how strong the predicted relationship is relative to known triples across the complete EvoAge graph.

Before running the workflow, update the configuration paths near the top of each script for the KG tensor, mappings, trained model, input directories, and output directories. The scoring stages require the trained DGL-KE RESCAL model; GPU execution is recommended for the large score sets.
