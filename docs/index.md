<<<<<<< HEAD
# EvoAge: Unifying Evolutionary Biology and AI Agent to Decipher Aging


---

## 1. The Aging Paradox
Aging is the ultimate biological complexity, governed by an intricate interplay of molecular pathways unfolding over decades. While short-lived model organisms—from yeast and roundworms to mice—have revealed highly conserved longevity pathways (like mTOR, insulin signaling, and mitochondrial function), this critical knowledge remains trapped in species-specific databases. 

This database fragmentation presents a major bottleneck: **How do we translate a longevity discovery in a yeast cell into a testable therapeutic target for human pathology?**

---

## 2. The EvoAge Breakthrough
**EvoAge** bridges this gap by unifying evolutionary orthology, systems biology, and Agentic AI. It integrates **48 public databases** into a massive, harmonized multi-species Knowledge Graph:

* **1.2 Billion Triples**: Spanning 16 biological entity types and 89 relation types.
* **6 Key Species**: Human (*Homo sapiens*), Mouse (*Mus musculus*), Fruit Fly (*Drosophila melanogaster*), Roundworm (*Caenorhabditis elegans*), Yeast (*Saccharomyces cerevisiae*), and Zebrafish (*Danio rerio*).
* **80,000+ Gene Orthology Mappings**: Translating genes from model organisms into a unified, human-centric vector space.

---

## 3. A "Mosaic of Experts" Powered by AI Agent
To make this massive dataset accessible, EvoAge deploys a hybrid **AI Agentic platform** . By combining the structured factual substrate of a **Neo4j graph database** with optimized **Knowledge Graph Embeddings (KGE)**, EvoAge acts as a reasoning engine:

1. **Fact Curation & Retrieval**: Natural-language querying of Neo4j to find verified biological associations.
2. **Link Prediction**: Using KGE models (RESCAL and RotatE) to predict missing yet highly plausible interactions.
3. **Hypothesis Testing**: Scoring user-provided biological hypotheses and validating them against statistical cutoffs (using Youden's J thresholding).

---

## 4. From Silicon to Synapse: Validating a Novel Alzheimer’s Mechanism
EvoAge isn't just a database—it's a discovery engine. In benchmarking, it significantly outperformed general-purpose LLMs in rejecting implausible biological hypotheses. 

More importantly, **EvoAge predicted a previously unknown Alzheimer's disease (AD) mechanism**: a nanoscale redistribution of the $\beta$-secretase enzyme **BACE1** from postsynaptic density anchors toward perisynaptic endocytic compartments. 

This prediction was experimentally validated using:
* 🧠 **Human Patient-Derived iPSC Neurons**
* 🐭 **Transgenic AD Mouse Models**
* 💀 **Postmortem Human Brain Tissue**

By showing that synaptic BACE1 remodeling is an evolutionarily conserved hallmark, EvoAge demonstrated its power to transition hypotheses from computational inference straight to the lab bench.

---

## 5. Explore the Pipeline Documentation
* [Step 01: Data Collection](data-collection.md)
* [Step 02: Preprocessing](preprocessing.md)
* [Step 03: Relation Processing](relation-processing.md)
* [Step 04: Ortholog Mapping](ortholog-mapping.md)
* [Step 05: KG Construction](kg-construction.md)
* [Step 06: Tensors & Splitting](kg-tensors-and-splitting.md)
* [Step 07: Training & Evaluation](training.md)
* [Other Analysis: Species Evaluation](other-analysis-1-species.md)
* [Other Analysis: Shuffled KG Baseline](other-analysis-2-shuffled.md)
* [Other Analysis: Aging-Specific Test Set](other-analysis-3-aging.md)
* [Neo4j Knowledge Graph Construction](neo4j-kg.md)
=======
# EvoAge: Cross-Species Aging Knowledge Integration through a Knowledge-Grounded AI Platform

Aging biology is scattered across species-specific resources and general biomedical databases, which makes conserved mechanisms hard to see and harder to test. **EvoAge** brings that knowledge together: 51 source layers harmonized into a cross-species knowledge graph of ~1.23 billion unique relationships and 45.6 million entities across human, mouse, zebrafish, fly, worm, and yeast, connected through one-to-one and one-to-many orthology. On top of the graph sit a RESCAL embedding model for calibrated link and edge-type prediction, and a conversational multi-agent reasoning layer that grades biological hypotheses against curated graph evidence rather than model intuition.

## What you will find here

This documentation walks through the pipeline end to end, in the order it was actually run:

- **Building the graph** — collecting and version-pinning every source, harmonizing identifiers and relation labels, merging relation-wise, and mapping non-human genes to human orthologs.
- **Assembling the KGs** — constructing the Aging, Biomedical, and combined EvoAge graphs and loading them into Neo4j.
- **Embedding and evaluation** — training and benchmarking the embedding models, plus the species-proportional, shuffled-control, and aging-specific evaluations.
- **Setup and reference** — system prerequisites, schema details, and the supporting analyses behind the manuscript figures.

## Why this documentation exists

The EvoAge graph is large enough that reproducing it from the paper alone would be impractical. These pages record the exact inputs, scripts, parameters, and intermediate files behind every step, so that each result can be traced to its source, rerun, or adapted for a different set of species or databases.

## Pipeline

Here is the exact original table with **only** the file paths/names changed to match your updated list:

Here is the exact original table with **only** the file paths updated:

| Step | Page |
| ---- | ---- |
| — | [System Prerequisites](system-prerequisites.md) |
| 01 | [Data Collection](data-collection.md) |
| 02 | [Preprocessing](preprocessing.md) |
| 03 | [Relation Processing](relation-processing.md) |
| 04 | [Ortholog Mapping](ortholog-mapping.md) |
| 05 | [KG Construction](kg-construction.md) |
| 06 | [KG Tensors and Splitting](kg-tensors-and-splitting.md) |
| 07 | [Training](training.md) |
| 08 | [Other Analysis](other-analysis.md) |
| 08.1 | [Other Analysis - 1 Species](other-analysis-1-species.md) |
| 08.2 | [Other Analysis - 2 Shuffled](other-analysis-2-shuffled.md) |
| 08.3 | [Other Analysis - 3 Aging](other-analysis-3-aging.md) |
| 09 | [LLM Finetuning](LLM_finetuning.md) |
| — | [Neo4j KG](neo4j-kg.md) |

**Web server:** [evoage.ahujalab.iiitd.edu.in](https://evoage.ahujalab.iiitd.edu.in/) · **Code:** [github.com/the-ahuja-lab/EvoAge](https://github.com/the-ahuja-lab/EvoAge)
>>>>>>> d0f0097 (Doc Changes)
