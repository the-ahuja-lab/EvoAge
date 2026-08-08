# EvoAge: Cross-Species Aging Knowledge Integration through a Knowledge-Grounded AI Platform

Aging biology is scattered across species-specific resources and general biomedical databases, which makes conserved mechanisms hard to see and harder to test. **EvoAge** brings that knowledge together: 51 source layers harmonized into a cross-species knowledge graph of ~1.23 billion unique relationships and 45.6 million entities across human, mouse, zebrafish, fly, worm, and yeast, connected through one-to-one and one-to-many orthology. On top of the graph sit a RESCAL embedding model for calibrated link and edge-type prediction, and a conversational multi-agent reasoning layer that grades biological hypotheses against curated graph evidence rather than model intuition.

## What you will find here

This documentation walks through the pipeline end to end, in the order it was actually run:

- **Building the graph** — collecting and version-pinning every source, harmonizing identifiers and relation labels, merging relation-wise, and mapping non-human genes to human orthologs.
- **Assembling the KGs** — constructing the Aging, Biomedical, and combined EvoAge graphs and loading them into Neo4j.
- **Embedding and evaluation** — training and benchmarking the embedding models, plus the species-proportional, shuffled-control, and aging-specific evaluations.
- **Setup and reference** — system prerequisites, installation, schema details, and the language model adaptation work.

## Why this documentation exists

The EvoAge graph is large enough that reproducing it from the paper alone would be impractical. These pages record the exact inputs, scripts, parameters, and intermediate files behind every step, so that each result can be traced to its source, rerun, or adapted for a different set of species or databases.

## Pipeline

| Step | Page |
| ---- | ---- |
| — | [System Prerequisites](system-prerequisites.md) |
| — | [Installation](installation.md) |
| 01 | [Data Collection](data-collection.md) |
| 02 | [Preprocessing](preprocessing.md) |
| 03 | [Relation Processing](relation-processing.md) |
| 04 | [Ortholog Mapping](ortholog-mapping.md) |
| 05 | [KG Construction](kg-construction.md) |
| 06 | [KG Tensors and Splitting](kg-tensors-and-splitting.md) |
| 07 | [Training & Evaluation](training.md) |
| 08 | [Other Analysis](other-analysis.md) |
| 08.1 | [Species Evaluation](other-analysis-1-species.md) |
| 08.2 | [Shuffled KG Baseline](other-analysis-2-shuffled.md) |
| 08.3 | [Aging-Specific Test Set](other-analysis-3-aging.md) |
| 09 | [Comparative Analysis](comparative-analysis.md) |
| 10 | [LLM Finetuning](LLM_finetuning.md) |
| 11 | [Figure Generation](figure-generation.md) |
| — | [Neo4j Knowledge Graph](neo4j-kg.md) |

**Web server:** [evoage.ahujalab.iiitd.edu.in](https://evoage.ahujalab.iiitd.edu.in/) · **Code:** [github.com/the-ahuja-lab/EvoAge](https://github.com/the-ahuja-lab/EvoAge)
