# EvoAge: Unifying Evolutionary Biology and AI Agent to Decipher Aging


---

## 1. The Aging Paradox
Aging is the ultimate biological complexity, governed by an intricate interplay of molecular pathways unfolding over decades. While short-lived model organisms—from yeast and roundworms to mice—have revealed highly conserved longevity pathways (like mTOR, insulin signaling, and mitochondrial function), this critical knowledge remains trapped in species-specific databases. 

This database fragmentation presents a major bottleneck: **How do we translate a longevity discovery in a yeast cell into a testable therapeutic target for human pathology?**

---

## 2. The EvoAge Breakthrough
**EvoAge** bridges this gap by unifying evolutionary orthology, systems biology, and Agentic AI. It integrates **48 public databases** into a massive, harmonized multi-species Knowledge Graph:

* **1.04 Billion Triples**: Spanning 16 biological entity types and 89 relation types.
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
