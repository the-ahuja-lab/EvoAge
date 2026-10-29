# BioChatter on the EvoAge knowledge graph

BioChatter answering natural-language questions against the **existing EvoAge
Neo4j graph**, using BioChatter's own framework (schema-driven Cypher
generation) rather than any EvoAge pipeline code.

Everything here is **read-only** — no EvoAge service, database, or config file
is modified.

## Why there is no BioCypher build step

BioChatter ships **no knowledge graph and no data**. It is the query-generation
half of the BioCypher ecosystem: you give it a schema description, it writes
Cypher against whatever database you point it at.

Normally that schema description is the `schema_info.yaml` BioCypher writes while
*building* a graph. The EvoAge graph already exists and was not built with
BioCypher, so `generate_schema_info.py` introspects the live database and emits
the same structure. The entire BioCypher build stage is skipped.

## Files

| File | Purpose |
|---|---|
| `generate_schema_info.py` | Introspects the live Neo4j and writes `schema_info.yaml` |
| `schema_info.yaml` | Generated schema description BioChatter reads (16 entities, 89 relationships) |
| `evoage_biochatter.py` | Asks questions: NL → Cypher → Neo4j → NL answer |
| `.env` | Local overrides (LLM provider/model). Secrets stay in the EvoAge backend `.env` |

## Setup

Uses the existing `biochatter` conda env (biochatter 0.14.2):

```bash
conda activate biochatter
cd /storage/Arushi/090526_EvoAge/kg_formation/hypothesis_testing/EVOAGE_VS_OTHERS/Biochatter
```

Neo4j credentials and the LLM key are read from
`/storage/Arushi/EvoAge-backend_3/Backend/.env` — nothing is duplicated here.
Override the path with `EVOAGE_ENV=...` if needed.

## Usage

```bash
# regenerate the schema (only needed if the graph schema changes; ~13 s)
python generate_schema_info.py

# ask one question
python evoage_biochatter.py "Which genes are associated with Alzheimer disease?"

# interactive
python evoage_biochatter.py
```

Each question prints the generated Cypher, the raw rows, and a prose answer.

## Verified examples

| Question | Generated Cypher | Result |
|---|---|---|
| Which genes are associated with Alzheimer disease? | `MATCH (d:Disease)-[:Disease_Gene]->(g:Gene) WHERE d.name_lower CONTAINS 'alzheimer' RETURN g.id, g.name LIMIT 25` | ADAM10, MEF2C, STX6, … |
| Which biological processes is the gene SIRT1 involved in? | `MATCH (g:Gene)-[:Gene_BiologicalProcess]->(bp:BiologicalProcess) WHERE g.id_lower CONTAINS 'sirt1' …` | rDNA heterochromatin formation, transcription regulation, … |
| What chemicals are associated with the gene APOE? | `MATCH (g:Gene)-[:Gene_ChemicalEntity]->(c:ChemicalEntity) WHERE g.id_lower = 'apoe' …` | lovastatin, retinol, … |
| How many diseases are in the knowledge graph? | `MATCH (d:Disease) RETURN count(d)` | 44,263 |

## Configuration

`.env` in this folder holds all LLM settings and **overrides** anything in the
EvoAge backend `.env`, so this benchmark is unaffected by which EvoAge tree is
currently checked out. Neo4j credentials are still inherited from the EvoAge
backend `.env` (one source of truth for the graph); uncomment the `NEO4J_*`
lines to pin them locally instead.

```env
LLM_PROVIDER=deepseek        # deepseek | google_genai | openai | anthropic
LLM_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://opencode.ai/zen/go/v1
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_API_KEY=            # REQUIRED -- must be set here
```

> As of 2026-08-02 the `EvoAge-backend_3` tree was swapped (the DeepSeek variant
> moved to `EvoAge-backend_3_depseek_discard`, and the tree from
> `EvoAge-backend_3_save` took its place). The current tree runs `USE = medgemma`
> and carries **no `DEEPSEEK_*` settings**, so `DEEPSEEK_API_KEY` has no fallback
> and must be set in this folder's `.env`. Neo4j URI and username are unchanged,
> so the graph side needs nothing. `.env` and `results/` are gitignored.

DeepSeek is the default because, as of 2026-08-02, **all 17 Gemini keys in the
EvoAge pool are dead or quota-exhausted** (15 × HTTP 429 `RESOURCE_EXHAUSTED`,
1 × 401, 1 × 400) and the OpenAI key is exhausted. Switching back to Gemini is a
one-line change once quota returns; the key-rotation logic in `answer()` already
advances past any per-key failure.

## Workarounds baked in

Four things had to be handled for BioChatter 0.14.2 to work against this graph.

1. **`DatabaseAgent.connect()` is broken upstream.** It calls
   `neo4j_utils.Driver(user=..., password=...)`, but that class takes
   `db_user=` / `db_passwd=`. The wrong names are absorbed by its `**kwargs`, so
   authentication silently fails and the driver drops into offline mode with no
   error at the call site. `EvoAgeDatabaseAgent.connect()` overrides this. Worth
   reporting upstream.

2. **DeepSeek reasoning tokens.** `deepseek-v4-flash` spends output tokens on
   internal reasoning before answering, so a small `max_tokens` returns empty
   `content`. `DeepSeekConversation` passes
   `extra_body={"thinking": {"type": "disabled"}}` and a 4096-token budget —
   the same workaround the EvoAge backend uses.

3. **Markdown fences.** The model wraps Cypher in ` ```cypher ` blocks, which
   BioChatter hands to the driver verbatim as a syntax error. `_clean_cypher()`
   strips them before execution.

4. **Graph conventions the schema cannot express.** BioChatter's entity-selection
   prompt shows the LLM only bare label names, so it mapped gene symbols like
   APOE and SIRT1 onto `ChemicalEntity` nodes and returned nothing. Exact
   equality on `name` also misses almost everything, since disease names vary
   ("Alzheimer Disease" vs "Alzheimer's disease"). `QUERY_CONVENTIONS` tells the
   model what each label means, that symbols live in `id` / `id_lower` while
   `name` is the descriptive name, to match with `CONTAINS` on `name_lower`, and
   to always add a `LIMIT` (the graph has 1.2B relationships).

## Graph facts

Introspected from the live database:

- Neo4j **5.27.0** community at `neo4j://192.168.3.153:3333`
- **16 node labels**, **89 relationship types**, 108 source→target patterns
- **45,555,597 nodes**, **1,237,567,694 relationships**
- Labels: Gene, Protein, ChemicalEntity, Disease, Phenotype, BiologicalProcess,
  MolecularFunction, CellularComponent, AnatomicalEntity, Tissue, Pathway,
  Mutation, Mirna, PlantSpecies, Species, PMID

Note the installed `neo4j` Python driver is 4.4.13 against a 5.27 server. It
works, but is a version mismatch worth resolving eventually.

## Limitation

BioChatter answers by **retrieving from the graph** — it has no link prediction.
Questions that need scoring of triples not present in the KG (EvoAge's
RotatE/RESCAL path) are out of scope for this setup by design.
