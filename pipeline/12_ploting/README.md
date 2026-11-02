# Figure generation

[`all_figures.ipynb`](all_figures.ipynb) is the panel-by-panel plotting
notebook for the EvoAge manuscript. It contains Main Figures 1, 2, 4, and 5 and
Supplementary Figures 1–7. Figure 3 is a schematic and is not generated here.

The notebook is committed with its outputs stored, allowing the current figures
to be inspected without rerunning the cells.

## Scope

The notebook primarily reads prepared CSV, NumPy, JSON, and Excel outputs from
upstream pipeline stages and converts them into publication figures. Expensive
operations—such as knowledge-graph construction, model training, full entity
ranking, randomization runs, Bayesian fitting, and bootstrap evaluation—are not
rerun in the plotting cells. Some panels perform lightweight data preparation or
descriptive calculations needed to draw the figure.

Major input areas include:

| Source | Figure content |
|---|---|
| `final_kg_building_3/STATS/` and species-wise KG summaries | Figure 1 composition and graph-statistics panels |
| `training_3/Training_Stats/` and training evaluation tables | Figure 2 training and evaluation panels |
| `multiagent_hypo/` and benchmark verdict summaries | Figure 4 hypothesis and model-comparison panels |
| `all_figures/yeast-exp/` | Figure 5 yeast thermal-screen panels |
| `IISC/Synaptic_BACE_Nanodomain/` | Supplementary BACE1 validation and FOV panels |
| `trained_evalutation_holy/` | Supplementary type-compatible ranking, null-model, and candidate-sensitivity panels |

## Reproducing a panel

1. Open `all_figures.ipynb` in JupyterLab or another compatible notebook
   environment.
2. Locate the Markdown heading for the required figure and panel.
3. Confirm that the input paths in that cell exist in your environment.
4. Run the panel cell. If it depends on a setup cell immediately above it, run
   that setup cell first.

The notebook uses common scientific Python packages, including `numpy`,
`pandas`, `matplotlib`, `scipy`, and panel-specific libraries where noted in the
cells.

## Path portability

Many inputs use absolute `/storage/Arushi/...` or `/storage3/arushis/...` paths
from the original analysis environment. To reproduce the figures elsewhere,
update the path variables near the top of the relevant cells to point to the
corresponding pipeline outputs. The stored notebook outputs remain viewable even
when those source paths are unavailable.
