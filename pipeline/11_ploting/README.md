# Figure generation

`all_figures-raidhani.ipynb` — the notebook that produces the figures for the
paper, from the statistics tables written by the earlier pipeline stages.

| | |
|---|---|
| **Main figures** | 1, 2, 4, 5 (panel by panel) |
| **Supplementary** | 1–7 |
| **Kernel** | `KG_pykeen` |

Figure 3 is a schematic and is not generated here.

The notebook is committed **with its outputs stored**, so every panel can be
viewed as published without rerunning anything.

## Inputs

Each panel reads a statistics table produced upstream rather than recomputing
from the knowledge graph — for example:

| Source | Feeds |
|---|---|
| `final_kg_building_3/STATS/` | Figure 1 composition and data-source panels |
| `training_3/Training_Stats/` | Figure 2 training loss and split summaries |
| `multiagent_hypo/` | Figure 4 hypothesis verdict panels |
| `all_figures/yeast-exp/` | Figure 5 yeast thermal-screen panels |

Paths are absolute and point at the machine this analysis ran on; adjust them at
the top of the relevant cell to rerun against your own copy of the pipeline
outputs.
