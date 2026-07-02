# EvoAge Neo4j Knowledge Graph Construction
## 1. Overview 

This document describes how the EvoAge Neo4j graph was built, loaded, and maintained: schema design, indexing strategy, bulk-loading workflow, post-load enrichment, deduplication, and performance troubleshooting.



EvoAge is a multi-species aging knowledge graph integrating **48+ biomedical source databases** (DRKG, PrimeKG, Hetionet, Monarch, CKG, STRING, miRTarBase, DrugAge, GenAge, CellAge, AgingBank, AgeXtend, Aging Atlas, and others) across six species: **Human, Mouse, Zebrafish, Drosophila, *C. elegans*, and Yeast**.

At current scale, the graph contains:
- **~45M nodes**
- **~1.2B+ relationships**
- **16 node labels**
- **~85 relationship types**

The graph is served by Neo4j (with the APOC plugin) running as a systemd service, queried via `cypher-shell` / the Bolt protocol.

---

## 2. Graph Schema

### 2.1 Node labels (16)

| Label | Description |
|---|---|
| `Gene` | Gene entities across all six species |
| `Protein` | Protein entities |
| `Disease` | Disease Ontology terms |
| `Phenotype` | Phenotype terms (e.g., HPO/MPO) |
| `Pathway` | Biological pathways |
| `BiologicalProcess` | GO biological process terms |
| `MolecularFunction` | GO molecular function terms |
| `CellularComponent` | GO cellular component terms |
| `ChemicalEntity` | Chemicals/compounds (PubChem CID-based) |
| `PlantSpecies` | Plant source species for chemicals |
| `Mirna` | microRNA entities |
| `Mutation` | Genetic mutations/variants |
| `AnatomicalEntity` | Anatomical structures |
| `Tissue` | Tissue types |
| `Species` | Species nodes (for cross-species edges) |
| `PMID` | Literature/publication references |

### 2.2 Relationship types (~85)

Relationships fall into two broad categories:
- **Causal**: e.g. `Inhibits`, `Promotes`
- **Associative**: e.g. `PositivelyAssociatedWithAging`, `NegativelyAssociatedWithAging`

Plus standard biomedical edge types such as `Gene_Gene` (ortholog), `Protein_Disease`, `Mutation_Gene`, `ChemicalEntity_Gene`, `Mirna_Gene`, `Gene_Pathway`, `Gene_Phenotype`, species-association edges, etc. Every relationship type follows a `HeadType_TailType` (or descriptive) naming convention for traceability back to source.

### 2.3 Common node properties

| Property | Notes |
|---|---|
| `id` | Primary identifier (unique per label, indexed) |
| `model_id` | Internal numeric ID assigned post-load (see §7.1) |
| `name` | Human-readable name |
| *(type-specific)* | e.g. `alternative_name`, `iupac_name`, `smiles` on `ChemicalEntity` |

Each label has a **unique RANGE index on `id`**, created before bulk loading and used throughout for `MERGE` performance and coverage checks (see §4 — Indexing Strategy).

---

## 3. Infrastructure Setup

- **Neo4j** installed as a native systemd service, with the **APOC** plugin enabled.
- Access via `cypher-shell -a bolt://<host>:<port> -u <user> -p <password>`.
- `server.directories.import` set to `/` so that `LOAD CSV FROM 'file:///...'` can reference **absolute paths** anywhere on disk (rather than only Neo4j's default `import/` folder). This was necessary because source CSVs live under a shared project directory, not the default import path.

### 3.1 Memory configuration

For a graph at this scale, default Neo4j memory settings (heap ~512MB, page cache ~10GB) are far too small and cause `MemoryPoolOutOfMemoryError`. On a machine with several hundred GB of RAM, `neo4j.conf` was tuned roughly as follows (values are illustrative — set relative to your machine's total RAM):

```conf
server.memory.heap.initial_size=31g
server.memory.heap.max_size=31g
server.memory.pagecache.size=150g
dbms.memory.transaction.total.max=15g
```

Verify applied settings with:
```cypher
CALL dbms.listConfig() YIELD name, value
WHERE name CONTAINS 'memory'
RETURN name, value;
```

After editing `neo4j.conf`, restart the service and confirm no old `cypher-shell` jobs are still attached to the previous instance before relaunching heavy loads.

---

## 4. Indexing Strategy

Indexes were not an afterthought — they turned out to be the single biggest lever for load performance, and got created (and re-diagnosed) iteratively as loading problems surfaced.

### 4.1 Why indexing matters here

Every `MERGE (n:Label {id: ...})` call needs to check whether a node with that `id` already exists. Without an index on `id`, Neo4j does this by scanning **every existing node of that label** (`NodeByLabelScan`) — cheap when a label has a handful of nodes, catastrophic once it has millions. This was the root cause behind one load (`PROTEIN_DISEASE.csv`, 31.2M rows) taking 7–8 hours: `Protein` and `Disease` nodes were shared across many relation files, so by the time this file loaded, both labels already held hundreds of thousands of nodes with no index to seek against.

### 4.2 Creating a unique constraint (which also creates an index) per label

A **unique constraint on `id`** was created for every one of the 16 node labels, before bulk loading began for that label. A unique constraint both enforces the `id` uniqueness invariant the whole KG relies on *and* implicitly creates the backing index used by `MERGE`:

```cypher
CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (n:Gene) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT protein_id IF NOT EXISTS FOR (n:Protein) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (n:Disease) REQUIRE n.id IS UNIQUE;
-- ... repeated for all 16 labels: Pathway, Phenotype, BiologicalProcess,
-- MolecularFunction, CellularComponent, ChemicalEntity, PlantSpecies,
-- Mirna, Mutation, AnatomicalEntity, Tissue, Species, PMID
```

`IF NOT EXISTS` makes this safe to re-run — it won't error if the constraint already exists, and if `id` isn't actually guaranteed unique for a given label, a plain range index is used instead:
```cypher
CREATE INDEX gene_id_idx IF NOT EXISTS FOR (n:Gene) ON (n.id);
```

### 4.3 Index creation on an already-loaded label

Constraints/indexes were ideally created **before** the first load touched a label, but in practice a few labels (`Protein`, `Disease`) were only indexed after the slow-load symptom appeared, i.e. against data that already existed. Neo4j handles this fine — index population runs as a background job over existing nodes:

```cypher
SHOW INDEXES YIELD name, state, populationPercent
WHERE name IN ['protein_id', 'disease_id'];
```

Loads were paused until `state = 'ONLINE'` and `populationPercent = 100` before resuming, since an index still populating doesn't yet give the `MERGE` speedup.

### 4.4 Verifying an index is actually being used

Rather than assume an index is helping, a small sample was profiled directly:

```cypher
LOAD CSV WITH HEADERS FROM 'file:///path/to/sample_100_rows.csv' AS row
WITH row LIMIT 100
PROFILE
MERGE (h:Protein {id: row.head})
RETURN count(*);
```

The `PROFILE` output was checked for `NodeUniqueIndexSeek` (indexed — fast) rather than `NodeByLabelScan` (unindexed — slow). This confirmed the fix before committing to a multi-hour full-file reload.

### 4.5 Result

Once all 16 labels had `ONLINE` unique constraints on `id`, `MERGE`-based loads that had been taking hours dropped to minutes for comparable file sizes, since every node lookup became an index seek instead of a label scan.

---

## 5. Data Preparation (pre-Neo4j)

Before anything touches Neo4j, source databases are processed independently:

1. Each source database is parsed into a **unified triple schema**:
   `Head | Head_name | Tail | Tail_name | Relation | Head_type | Tail_type | kg_source`
2. Relation-wise CSVs are merged across sources (e.g. multiple `Gene_Gene` sources combined into one `Gene_Gene.csv`).
3. Each relation-wise CSV is deduplicated on `(Head, Relation, Tail)`.
4. Files with mixed `Head_type`/`Tail_type` columns (e.g. cross-species association files) are kept separate from single-type files, since they require dynamic label resolution at load time (§6.2).

This stage produces the clean, relation-wise CSVs that are the direct input to the Neo4j loading step below.

---

## 6. Bulk Loading Pipeline

### 6.1 Standard load (fixed node types)

For files where head/tail node types are fixed and known in advance (e.g. `Protein_Disease.csv`), loading uses `LOAD CSV` + `apoc.periodic.iterate` for batching, rather than a raw `LOAD CSV ... MERGE` (which does not batch and will exhaust the transaction memory limit on large files):

```cypher
CALL apoc.periodic.iterate(
  "LOAD CSV WITH HEADERS FROM 'file:///path/to/Protein_Disease.csv' AS row RETURN row",
  "MERGE (h:Protein {id: row.head})
   ON CREATE SET h.name = row.head_name
   MERGE (t:Disease {id: row.tail})
   ON CREATE SET t.name = row.tail_name
   MERGE (h)-[r:Protein_Disease]->(t)
   ON CREATE SET r.kg_source = row.kg_source",
  {batchSize: 500, parallel: false, logProgress: true}
);
```

### 6.2 Dynamic label resolution (mixed-type files)

For species-association files and similar cases where `head_type`/`tail_type` vary row-to-row, hardcoded labels are replaced with `apoc.merge.node`, which accepts the label as a parameter:

```cypher
CALL apoc.periodic.iterate(
  "LOAD CSV WITH HEADERS FROM 'file:///path/to/species_associated.csv' AS row RETURN row",
  "CALL apoc.merge.node([row.head_type], {id: row.head}, {name: row.head_name}, {}) YIELD node AS h
   CALL apoc.merge.node([row.tail_type], {id: row.tail}, {name: row.tail_name}, {}) YIELD node AS t
   MERGE (h)-[r:ASSOCIATED_WITH]->(t)
   ON CREATE SET r.kg_source = row.kg_source",
  {batchSize: 300, parallel: false, logProgress: true}
);
```

The empty `onMatchProps` (`{}`) argument is important — it prevents `apoc.merge.node` from overwriting existing node properties on repeated matches.

### 6.3 Execution workflow

Every new load, without exception, follows this sequence:

1. **Dry run on 2 rows** — append `LIMIT 2` to the `LOAD CSV` step and `RETURN` the result to sanity-check parsing and typing in Neo4j Browser before committing to a full run.
2. **Full run in the background** — long-running loads (multi-hour, multi-million-row files) are launched with `nohup` so they survive terminal/laptop disconnects:
   ```bash
   nohup cypher-shell -a bolt://<host>:<port> -u <user> -p <password> \
     -f load_relation.cypher > relation_load.log 2>&1 &
   ```
3. **Monitor progress**:
   ```bash
   tail -f relation_load.log
   ```
   ```cypher
   CALL dbms.listQueries();
   ```
4. **Verify the job is still alive** with `ps aux | grep cypher-shell` if the log goes quiet — a live PID with growing runtime is expected, not a hang, for files with tens of millions of rows at `batchSize:200–500`.

### 6.4 Loader shell script — `load_csv.sh`

A reusable wrapper takes a CSV filename (relative to a fixed base directory), a log filename, and a `.cypher` file containing just the `MERGE` clause. It assembles the full `apoc.periodic.iterate` call and fires it off via `nohup` so the job survives disconnects:

```bash
#!/bin/bash
PASSWORD="<password>"
USERNAME="<username>"
CSV_BASE="<path>/evokg_new/rem_human_files/"   # fixed base dir for this batch of files
CSV_PATH=$1
LOG_FILE=$2
MERGE_FILE=$3   # a .cypher file containing just the MERGE clause, not a raw string

if [[ -z "$CSV_PATH" || -z "$LOG_FILE" || -z "$MERGE_FILE" ]]; then
  echo "Usage: ./load_csv.sh <CSV_PATH> <LOG_FILE> <MERGE_FILE>"
  exit 1
fi

# Load the MERGE query safely from file (avoids quoting/escaping issues
# that come from inlining large Cypher blocks as shell strings)
MERGE_QUERY=$(<"$MERGE_FILE")

# Resolve full CSV path relative to the base directory
CSV_PATH="$CSV_BASE$CSV_PATH"

# Run the job in the background, output redirected to the log file
nohup cypher-shell \
  -a bolt://<host>:<port> \
  -u "$USERNAME" \
  -p "$PASSWORD" <<EOF > "$LOG_FILE" 2>&1 &
CALL apoc.periodic.iterate(
 'LOAD CSV WITH HEADERS FROM "file:///$CSV_PATH" AS row RETURN row',
  "$MERGE_QUERY RETURN count(*)",
  {batchSize:200, parallel:false, logProgress:true}
)
EOF
```

**Usage:**
```bash
./load_csv.sh Protein_Disease.csv protein_disease_load.log protein_disease_merge.cypher
```

Design notes:
- The `MERGE` clause lives in its own `.cypher` file (`$MERGE_FILE`) rather than being typed inline as a shell string — this avoids quote-escaping headaches for anything beyond a trivial one-line `MERGE`.
- `CSV_BASE` is fixed per batch of files (e.g. one base dir per species or per data drop), so callers only pass the filename, not the full path — this cut down on path-typo errors across dozens of relation files.
- The heredoc (`<<EOF ... EOF`) feeds the assembled Cypher directly to `cypher-shell` on stdin, avoiding an extra intermediate `.cypher` file per run.
- Credentials and the base path are hardcoded at the top of the script rather than passed as arguments, since they're constant across an entire loading session — only `CSV_PATH`, `LOG_FILE`, and `MERGE_FILE` vary per call.

---

## 7. Post-Load Enrichment

### 7.1 Assigning `model_id`

After the raw graph is loaded, every node across all 16 labels receives an internal `model_id` (used downstream for embedding/model training pipelines). This is done with a reusable `add_model_id.sh` script driving `apoc.periodic.iterate` at `batchSize:500`:

```cypher
CALL apoc.periodic.iterate(
  "MATCH (n:Gene) WHERE n.model_id IS NULL RETURN n",
  "SET n.model_id = <assigned_id>",
  {batchSize: 500, parallel: false, logProgress: true}
);
```

**Coverage verification** after assignment uses a per-label `UNION ALL` query (leveraging the unique `id` index on each label) to catch any nodes missed:

```cypher
MATCH (n:Gene) WHERE n.model_id IS NULL RETURN 'Gene' AS label, count(n) AS missing
UNION ALL
MATCH (n:Protein) WHERE n.model_id IS NULL RETURN 'Protein' AS label, count(n) AS missing
// ... repeated for all 16 labels
```

This surfaced edge cases such as `ChemicalEntity`/`PlantSpecies` nodes whose `id` was a full chemical name string rather than a numeric CID — these were assigned `model_id`s manually.

### 7.2 Adding supplementary properties

Additional properties sourced from later-arriving data (e.g. `alternative_name`, `iupac_name`, `smiles` for `ChemicalEntity`) are added using the same `apoc.periodic.iterate` batched-update pattern, driven from a CSV keyed on `id`.

---
