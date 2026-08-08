# Figure Generation

The final stage of the pipeline turns the statistics tables written by the
earlier steps into the figures used in the paper.

All panels are produced by a single notebook,
`pipeline/11_ploting/all_figures-raidhani.ipynb`, which covers **main figures 1,
2, 4 and 5** panel by panel, together with **supplementary figures 1–7**. Figure
3 is a schematic and is not generated here.

Each panel reads a statistics table produced upstream — graph composition and
data-source counts from KG construction, loss curves and split summaries from
training, verdict distributions from the hypothesis pipeline, and the yeast
thermal-screen results — rather than recomputing anything from the knowledge
graph itself. Keeping plotting separate from computation means a figure can be
restyled without rerunning any part of the pipeline.

The notebook is committed with its outputs stored, so every panel can be
inspected exactly as published without executing a cell.
