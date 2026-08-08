# Comparative Analysis

EvoAge was benchmarked against two different classes of system, in two separate
comparisons.

**Part A** compares EvoAge with biomedical language models answering from their
own parametric knowledge — MedGemma, BioMistral, and an AgingKG-finetuned
BioMistral.

**Part B** compares EvoAge with knowledge-graph question-answering frameworks —
BioChatter and Escargot — all three querying the same EvoAge knowledge graph.

---

## Part A — EvoAge vs MedGemma vs BioMistral vs BioMistral-Finetuned

### A1. What is being compared

This comparison asks whether a biomedical language model, answering from what it
already knows, can discriminate a literature-supported hypothesis from its
logical inverse — and how that compares with EvoAge, which answers from
retrieved graph evidence.

Three models were evaluated:

| Model | Role |
|---|---|
| **MedGemma-27B** | Biomedical language model, as published |
| **BioMistral-7B** | Biomedical language model, as published |
| **BioMistral-7B (AgingKG-finetuned)** | The same base model after AgingKG-guided domain adaptation |

### A2. How they were run

Each model was served locally through SGLang as an OpenAI-compatible endpoint,
and driven by the same evaluation script. Every model was given the **same
prompts**, in the same two-step sequence, and **temperature was fixed at 0** so
that responses are deterministic and differences between models cannot be
attributed to sampling.

Each hypothesis was evaluated in two steps:

1. **Verdict.** The model is asked to place the hypothesis on the same
   five-level ladder used throughout this work —
   `no_support → weak_support → partial_support → support → strong_support` —
   and to reply with the verdict alone. The prompt instructs it to judge using
   established biomedical knowledge, and to choose the lower level when
   uncertain.
2. **Explanation.** The verdict is appended to the conversation and the model is
   asked to justify it in two or three sentences, grounded in known mechanisms,
   pathways or evidence.

Both the verdict and the explanation were **recorded for every hypothesis**, so
each verdict can be audited rather than taken on trust.

### A3. What each model was asked

Every model saw the identical set of hypotheses: for each of the 101 curated
publications, both the literature-supported **right hypothesis** and its
logically inverted counterpart. Evaluating both members of the pair is what
makes the test meaningful — a model that affirms everything scores well on the
supported statements and fails on the inverses.

Unlike Part B, no knowledge graph evidence is supplied here. These models answer
from parametric knowledge alone, which is the capability under test.

### A4. Reproducing it

Code lives in the repository under
`pipeline/09_evoage_vs_other/evoage_vs_medgemma_biomistral/`:

| Path | What it does |
|---|---|
| `All_Hypothesis_fixed_with_ent.csv` | The 101 right/inverse hypothesis pairs |
| `medgemma/` | Server launch and evaluation run for MedGemma |
| `BioMistral/` | Server launch and evaluation run for base BioMistral |
| `BioMistralFinetuned/` | Server launch and evaluation run for the AgingKG-finetuned model |
| `run_all.sh` | Runs all three in sequence |

```bash
./run_all.sh
```

Each model directory carries an identical `run_hypothesis.py`, so the prompts,
the two-step sequence and `temperature=0` are the same for every model; only the
served model path differs. Each run writes `All_Hypothesis_evaluated.csv` into
its own directory, adding verdict and explanation columns for both the right and
the inverse hypothesis.

---

## Part B — EvoAge vs BioChatter vs Escargot

How EvoAge was benchmarked against two published KG-question-answering frameworks on the same knowledge graph, the same language model, and the same 101 hypotheses — so that the reasoning architecture was the only variable.

---

### B1. What the comparison is for

EvoAge is not the only system that answers biological questions over a knowledge graph. The relevant question is therefore not "does EvoAge produce evidence?" but **"given the same graph and the same language model, does EvoAge convert that shared knowledge into better-graded biological evidence than existing frameworks?"**

Answering that requires holding everything except the reasoning framework constant. That constraint drove every design decision below.

---

### B2. Choice of baselines

| System | Why it qualifies |
|---|---|
| **BioChatter** (v0.14.2, PyPI) | Generates Cypher against an existing graph, so it can be pointed at the EvoAge graph itself. |
| **Escargot** | Same — generates queries against a target database it introspects. |

Both were selected because they query a graph that already exists. That is the property the comparison depends on: a framework that retrieves from its own vector store, or builds its own graph from supplied documents, cannot be run on a shared graph without changing the variable under test.

**Held constant across all three systems**

- The same Neo4j instance of the EvoAge KG — 45.56 M nodes, 1.2376 B relationships, 16 node types, 89 relationship types
- The same 101 DOI-anchored hypotheses
- The same judge model, rubric and verdict ladder

All baseline runs were read-only. No baseline modified the graph or any EvoAge service.

---

### B3. Adapting the baselines — and why this is conservative

**No framework logic was modified.** Both baselines were used as published; every adaptation was made externally through configuration and standard Python subclassing, which are the extension points each framework provides. For BioChatter this was verified by checksum — all 45 installed package files matched the hashes in the distribution manifest, confirming no framework file had been altered.

The adaptations fall into three categories:

1. **Describing the EvoAge graph in the form each framework expects.** BioChatter expects a BioCypher-style schema; since the EvoAge graph was not built with BioCypher and was not going to be rebuilt, we introspected the live database and emitted an equivalent description (labels, properties, source/target types, sizes from the Neo4j count store), preserving exact relationship type names. Escargot derives node properties from *indexed* properties only, which omitted the lowercased matching properties entity resolution depends on; without them it fell back on the property conventions of the graph it was originally developed against and generated queries referencing non-existent properties. Both baselines were therefore given equivalent explicit information about the graph, including two EvoAge conventions the schema alone does not convey — gene and protein symbols live in the identifier property rather than the name property, and names must be matched case-insensitively.

2. **Removing non-executable text from generated queries.** Both frameworks returned statements wrapped in Markdown fences or preceded by explanatory prose, which they forward to the driver unaltered. Equivalent cleaning was applied to both, so neither was penalised for a formatting behaviour of the shared language model.

3. **Connecting each framework to the shared database and model endpoints.** BioChatter's connector passes credentials under argument names the driver does not accept, so authentication fails silently into an offline state; this was corrected in a subclass. Escargot's model interface does not accept a custom endpoint address, so it was subclassed to reach the shared endpoint.

**These adaptations raise baseline performance rather than lower it.** Every one of them exists to let a baseline produce a working query where it otherwise could not. The comparison is therefore conservative with respect to the conclusion drawn from it.

**Independent check that the baselines were functioning.** To establish that Escargot's difficulty was a configuration issue and not a broken installation, it was run unmodified against a small instance of the graph it was originally developed for (AlzKB), loaded into a separate isolated database. Its query planning and generation operated correctly there, confirming the framework was working and the adaptation needed was limited to the schema description.

---

### B4. Grading

Each system returned its own evidence and answer. Prose cannot be scored, so all outputs were placed on one ordinal ladder by a judge model:

```
no_support → weak_support → partial_support → support → strong_support
```

**Judge model:** MedGemma-27B (`medgemma-27b-text-it`), served locally at a single shared endpoint, `temperature=0.0`, JSON-constrained output. **All three systems' verdicts come from this same model** — EvoAge's adjudication layer routes its judge call to the same local MedGemma deployment that grades the two baselines. No system was scored by a model the others did not face.

**Rubric for the baselines:** a single system-neutral prompt, published verbatim in the pipeline code. Its design points:

- The verdict is decided by **returned evidence only**. The judge may use background knowledge to *interpret* evidence, never to *substitute* for missing evidence — stated explicitly: "if removing your outside knowledge would lower the verdict, the verdict is too high."
- **Blinded to system identity.** The prompt states the judge is not told which system produced the output, and it never is.
- **Essential-link test.** A link whose absence collapses the central claim, with zero or opposing evidence, caps the verdict regardless of anything else.
- **Specificity test.** If the same evidence would appear for an arbitrary entity of the same type, it carries almost no weight for *this* entity.
- **Fluency earns nothing.** "A fluent, confident answer that is not backed by returned evidence is worth NOTHING."
- **Zero-evidence rule enforced in code, not left to the model.** When a query returns no rows there is by definition no evidence, and `no_support` is assigned deterministically. This is enforced programmatically because a model shown an empty result set will often reason from its own training knowledge and award support anyway.

The two baseline judge scripts are checked against each other at startup and refuse to run if their rubric copies have diverged, so "both baselines were graded by an identical prompt" is a property of the code rather than a claim to be taken on trust.

**Where EvoAge's verdict comes from, stated precisely.** EvoAge's verdict is produced by its own adjudication layer — the Judge module that synthesizes the four specialist agents' per-link findings — which is a component of the system under test rather than an external scorer. The baselines have no such component: they return prose, and prose carries no verdict, so an external judge call is required to place them on the ladder at all. The judge model and the five-level ladder are identical in both cases; the prompts are not. EvoAge's Judge reasons over four agents' structured `link_findings` and tiers evidence as curated versus predicted, whereas the baseline rubric was deliberately reworded to name no system and to drop that tiering, which presupposes a predictive component retrieval-only systems do not have.

This asymmetry is a property of what is being compared — an end-to-end reasoning architecture against retrieval frameworks — not a scoring choice made after the fact. It is reported here rather than smoothed over, and the neutral rubric can be applied to EvoAge's outputs as a sensitivity analysis using the same judge scripts.

---

### B5. Joining and counting

- Results were joined across systems **on DOI**, not on title and not on row order. DOI was verified unique within each file and identical across all three (101/101), and the merge is validated 1:1, so no pairing can be introduced by re-sorting.
- Verdicts falling **outside the ladder** — a system returning `unknown`, or a judge call failing — were **retained in the denominator and reported separately**, never folded into `no_support`.
- Primary outcome: the proportion of hypotheses receiving **any** level of support (weak support or above).

---

### B6. Reproducing it

Code lives in the repository under `pipeline/09_evoage_vs_other/evoage_vs_biochat_escargot/`:

| Path | What it does |
|---|---|
| `Biochatter/evoage_biochatter.py` | Adapter: connector subclass and the added prompt context |
| `Biochatter/generate_schema_info.py` | Introspects the live graph into a BioCypher-style schema |
| `Biochatter/hypothesis_ques_answer/medgemma_analyse_biochatter_response.py` | Judge; **defines the verbatim rubric** |
| `escargot/escargot/` | The published Escargot framework, vendored **unmodified** (commit `936a005`) |
| `escargot/evoage/` | The adaptation: model-endpoint subclass and explicit schema supply |
| `escargot/alzkb_sanity/` | Unmodified-framework sanity check on the graph Escargot ships against |
| `escargot/hypothesis_ques_answer/medgemma_analyse_escargot_response.py` | Judge; same rubric, guarded against divergence |
| `analysis/verdict_analysis_complete.py` | DOI join, verdict counts, figure panel |
| `evoage_results/` | EvoAge's own verdicts on the same 101 hypotheses |

```bash
cp .env.example Biochatter/.env    # Neo4j + model-endpoint credentials

# 1. run each baseline over the 101 hypotheses
python Biochatter/hypothesis_ques_answer/run_hypothesis_benchmark.py
python escargot/hypothesis_ques_answer/run_hypothesis_benchmark.py

# 2. grade the outputs with the blinded MedGemma judge
python Biochatter/hypothesis_ques_answer/medgemma_analyse_biochatter_response.py
python escargot/hypothesis_ques_answer/medgemma_analyse_escargot_response.py

# 3. join on DOI and produce counts and figures
python analysis/verdict_analysis_complete.py
```

The vendored Escargot copy is included deliberately: it can be diffed against
the upstream repository at the recorded commit to confirm that no framework
logic was altered.

Judge robustness can be checked by pointing the same scripts at a second, independent model with `--model` and `--verdict-col`, which writes a parallel verdict column for inter-judge agreement.
