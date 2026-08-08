# Running BioChatter on the EvoAge knowledge graph — steps and required changes

How BioChatter was made to answer questions from the existing EvoAge Neo4j
graph, and exactly what had to be provided to get there.

**The BioChatter framework itself was not modified.** It is used as installed
from PyPI (`biochatter==0.14.2`). Every adaptation lives in *our own* files in
this folder, using ordinary Python subclassing and configuration — the supported
extension points. Query generation, entity/relationship/property selection and
retrieval are all BioChatter's own logic.

### Verifying that claim

All 45 installed `biochatter/*` files were hash-checked against the package's
own `RECORD` manifest: **0 modified, 0 missing.**

```bash
cd /home/arushis/miniconda3/envs/biochatter/lib/python3.11/site-packages
python - <<'PY'
import base64, csv, hashlib, os
bad = checked = 0
for row in csv.reader(open("biochatter-0.14.2.dist-info/RECORD")):
    if len(row) < 3 or not row[1].startswith("sha256=") or not row[0].startswith("biochatter/"):
        continue
    got = base64.urlsafe_b64encode(
        hashlib.sha256(open(row[0], "rb").read()).digest()).rstrip(b"=").decode()
    checked += 1
    bad += got != row[1].split("=", 1)[1]
print(f"checked {checked} files | modified: {bad}")
PY
```

---

## Background: why any work was needed

BioChatter ships **no knowledge graph and no data**. It is the query-generation
half of the BioCypher ecosystem: given a *schema description*, it writes Cypher
against whatever database you point it at.

Normally that description is the `schema_info.yaml` BioCypher writes while
*building* a graph. The EvoAge graph already exists and was not built with
BioCypher, so the whole BioCypher build stage had to be replaced with a single
introspection step. Nothing else about the framework changes.

---

## Steps

### Step 1 — Install BioChatter

```bash
conda create -n biochatter python=3.11 -y
conda activate biochatter
pip install biochatter          # 0.14.2
```

No BioCypher install is required — the graph already exists.

### Step 2 — Describe the existing graph

`generate_schema_info.py` connects to the live Neo4j and writes
`schema_info.yaml` in the format BioChatter expects.

```bash
python generate_schema_info.py     # ~13 s
```

It emits, per entity and per relationship: `is_relationship`,
`present_in_knowledge_graph`, `properties`, and `source`/`target`, plus
`is_schema_info: true` at the top level.

Two details that matter:

- **`label_as_edge`** is set to the exact Neo4j relationship type. BioChatter
  PascalCases its dictionary keys; without this the generated Cypher would not
  match the real type names.
- **Counts come from `apoc.meta.stats()`**, which reads Neo4j's internal count
  store. A `MATCH (n) RETURN count(n)` on this graph would scan 45M nodes and
  1.2B relationships; the count store returns in milliseconds.

Result: 16 entities, 89 relationships.

### Step 3 — Configure

`.env` in this folder (overrides the EvoAge backend `.env`, so it is unaffected
by which EvoAge tree is checked out):

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://opencode.ai/zen/go/v1
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_API_KEY=<key>
NEO4J_URI=neo4j://192.168.3.153:3333
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=neo4j
```

### Step 4 — Ask questions

```bash
python evoage_biochatter.py "Which genes are associated with Alzheimer disease?"
python evoage_biochatter.py                    # interactive
python run_benchmark.py                        # the 37-question comparison set
```

---

## Changes required (all external to BioChatter)

Four adaptations were needed. Each is implemented by subclassing or by passing
configuration — no framework file is touched.

### 1. Neo4j connection — working around an upstream bug

**Problem.** `DatabaseAgent.connect()` calls
`neo4j_utils.Driver(user=..., password=...)`, but that class takes
`db_user=` / `db_passwd=`. The mismatched names are absorbed by its `**kwargs`,
so authentication silently fails and the driver drops into offline mode — with
no error raised at the call site. Every query then returns nothing.

**Fix.** `EvoAgeDatabaseAgent.connect()` overrides the method and passes the
correct argument names. This is a genuine bug in biochatter 0.14.2 and is worth
reporting upstream.

### 2. LLM backend — DeepSeek via an OpenAI-compatible proxy

**Problem.** `deepseek-v4-flash` spends output tokens on internal reasoning
before answering, so a small `max_tokens` budget returns empty `content`
(observed: 59 reasoning tokens consumed a 20-token budget).

**Fix.** `DeepSeekConversation` subclasses BioChatter's own `GptConversation`
(which already supports a custom `base_url`) and passes
`extra_body={"thinking": {"type": "disabled"}}` with a 4096-token budget. It also
points the correction model at the same model, since `GptConversation` defaults
that to a GPT model the proxy does not serve.

### 3. Markdown fences around generated Cypher

**Problem.** The model returns Cypher inside a ```` ```cypher ```` block.
BioChatter passes LLM output to the driver verbatim, so this is a syntax error.

**Fix.** `_clean_cypher()` strips the fences before the statement reaches the
driver.

### 4. Graph conventions the schema cannot express

**Problem.** Two failure modes appeared in testing:

- BioChatter's entity-selection prompt shows the LLM only bare label names. Asked
  about gene symbols such as APOE or SIRT1, it selected `ChemicalEntity` and
  returned nothing.
- Exact equality on `name` misses almost everything, because names vary in case
  and punctuation — the graph holds both `Alzheimer Disease` and
  `Alzheimer's disease`.

**Fix.** A `QUERY_CONVENTIONS` block is appended to each question before query
generation, stating: what each label means (Gene vs Protein vs ChemicalEntity);
that symbols live in `id`/`id_lower` while `name` is the descriptive name; to
match case-insensitively with `CONTAINS` on `name_lower`; and to always add a
`LIMIT`, since the graph has 1.2B relationships.

This is prompt context supplied to BioChatter, not a change to how it builds
prompts.

---

## Effect of the fixes

Same question, before and after:

| | Generated Cypher | Rows |
|---|---|---|
| Before | `MATCH (g:Gene)-[:Gene_Disease]->(d:Disease) WHERE d.name = 'Alzheimer disease' RETURN g.name` | 0 |
| After | `MATCH (d:Disease)-[:Disease_Gene]->(g:Gene) WHERE d.name_lower CONTAINS 'alzheimer' RETURN g.id, g.name LIMIT 25` | 25 (ADAM10, MEF2C, STX6, …) |

Further verified results:

| Question | Result |
|---|---|
| Which biological processes is SIRT1 involved in? | rDNA heterochromatin formation, transcription regulation, … |
| What chemicals are associated with APOE? | lovastatin, retinol, … |
| Which diseases is TP53 associated with? | colorectal cancer, lung small cell carcinoma, T-cell ALL, … |
| How many diseases are in the knowledge graph? | 44,263 — matches EvoAge's `/kg_statistics` exactly |

---

## Graph facts (introspected from the live database)

- Neo4j **5.27.0** community, `neo4j://192.168.3.153:3333`
- **16 node labels**, **89 relationship types**, 108 source→target patterns
- **45,555,597 nodes**, **1,237,567,694 relationships**
- Labels: Gene, Protein, ChemicalEntity, Disease, Phenotype, BiologicalProcess,
  MolecularFunction, CellularComponent, AnatomicalEntity, Tissue, Pathway,
  Mutation, Mirna, PlantSpecies, Species, PMID

Note: the installed `neo4j` Python driver is 4.4.13 against a 5.27 server. It
works, but the version mismatch is worth resolving eventually.

---

## Scope limitation

BioChatter answers by **retrieving from the graph**. It has no embedding model
and no scoring, so questions requiring evaluation of triples *absent* from the
graph — EvoAge's RotatE/RESCAL hypothesis-testing path — are outside its design.
This is architectural, not a configuration gap: no amount of prompt tuning gives
a retrieval system a verdict on an edge that does not exist.
