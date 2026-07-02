# 3. Per-Source Preprocessing

> 📂 **Source Code & Notebooks:** [pipeline/02_data_processing](https://github.com/the-ahuja-lab/EvoAge/tree/main/pipeline/02_data_processing)


This section documents how each of the 48+ raw data sources is converted into the standard EvoAge triple schema before relation-type classification and KG merging. It is based on the actual notebooks in `kg_formation/data_processing/`.

---

## **3.1 Two Preprocessing Paradigms**

Every source notebook follows one of two patterns, depending on what the raw data looks like:

| Paradigm | Raw data shape | Example sources | Core task |
|---|---|---|---|
| **A. Relation-typed CSV** | Entity1/Entity2 columns + a relation/type label already present | PharmKG, DRKG, PrimeKG, STITCH, STRING, Hetionet, CKG | Split by relation type → resolve each Head/Tail to a canonical ID using reference dictionaries |
| **B. Raw RDF/OWL triples** | Plain `(subject_uri, object_uri)` pairs, no relation or type column at all | PheKnowLator, MonarchKG | Parse ontology URI prefixes → infer entity type → infer relation from the (Head_type, Tail_type) pair → resolve IDs |

Both paradigms converge on the same output schema (`DESIRED_COLS` — see [§3.5](#35-standard-output-schema)) so that every source plugs into the same downstream merging step ([KG Construction](kg-construction.md)).

---

## **3.2 Paradigm A — Relation-Typed CSV Sources**

### **Worked example: PharmKG**

**Notebook**: `kg_formation/data_processing/pharmkg.ipynb`
**Raw input**: `raw_PharmKG-180k.csv` — has `Entity1_name`, `Entity1_type`, `Entity2_name`, `Entity2_type`, `relationship_type` columns already.

### **Step 1 — Load reference dictionaries once**

All ID-resolution dictionaries are built **once at the top of the notebook**, not rebuilt inside each relation block. The standard set of dictionaries every relation-typed source needs:

```python
# Chemical resolution
Pubchem_Smile_CID_Dict       # SMILES -> PubChem CID
DB2PC_dict, Chebi2PC_dict    # DrugBank / ChEBI -> PubChem CID
Pubchem_Syn_fil_dict_lower   # chemical synonym (lowercased) -> PubChem CID

# Disease resolution (DO -> MeSH cascade)
DOID_disname_DOID_dict       # DO label -> DOID            (preferred)
Meshname2DOID_dict           # MeSH label -> MeSH xref     (fallback 1)
MESH_dict                    # MeSH ID -> name             (fallback 2)
Mesh_supp_dict                # MeSH supplementary ID -> name (fallback 3)

# Gene resolution
NCBI_fullname_2_SYMBOL_dict  # full gene description -> canonical Symbol
synonym_map                  # alias/synonym -> canonical Symbol (built ONCE)
NCBI_ALL_GENEname_dict       # canonical Symbol -> description
```

### **Step 2 — Standardize entity types and build the Relation label**

```python
KG_file['Entity1_type'] = KG_file['Entity1_type'].str.lower()
KG_file['Entity2_type'] = KG_file['Entity2_type'].str.lower()
KG_file['RELATION'] = KG_file['Entity1_type'] + '_' + KG_file['Entity2_type']

def format_relation(relation):
    """gene_disease -> Gene_Disease"""
    return '_'.join([p.capitalize() for p in relation.split('_')])

KG_file['RELATION'] = KG_file['RELATION'].apply(format_relation)
```

This gives a `Relation` column like `Gene_Disease`, `Chemical_Gene`, etc. — used to split the source into per-relation-type slices.

### **Step 3 — Split into per-relation DataFrames**

```python
relation_dfs = {}
for relation in KG_file['Relation'].unique():
    relation_dfs[relation] = KG_file[KG_file['Relation'] == relation].copy()
```

### **Step 4 — Resolve Head/Tail per entity type**

Three reusable resolver functions handle every relation-type block. Each follows the same pattern: **map → validate → swap original into an audit column → drop unresolved rows**.

```python
def resolve_gene_head(df):
    """
    Full gene description -> canonical Symbol -> validated against NCBI.
    Audit trail: original value preserved in Head_Ori.
    """
    df = df.copy()
    df['Head_Ori'] = df['Head'].map(NCBI_fullname_2_SYMBOL_dict).fillna(df['Head'])
    df[['Head', 'Head_Ori']] = df[['Head_Ori', 'Head']]
    df['Head'] = df['Head'].str.upper()
    df['Head_Alias_mapped'] = df['Head'].apply(lambda x: synonym_map.get(x, x))
    df['Head_Detail_name']  = df['Head_Alias_mapped'].map(NCBI_ALL_GENEname_dict)
    df['Head_ID_IS'] = 'NCBI_ID'
    return df
    # resolve_gene_tail is the mirror of this for the Tail column


def resolve_disease(df, col):
    """
    4-source cascade, in priority order:
      1. DO label -> DOID                  (preferred)
      2. MeSH label -> MeSH xref           (fallback)
      3. MeSH ID -> name
      4. MeSH supplementary ID -> name
    Rows with no match in any of the 4 are dropped.
    """
    df = df.copy()
    id_col, orig_col = f'{col}_ID_tmp', f'{col}_Orignal'
    df[id_col] = (df[col].map(DOID_disname_DOID_dict)
                  .fillna(df[col].map(Meshname2DOID_dict))
                  .fillna(df[col].map(MESH_dict))
                  .fillna(df[col].map(Mesh_supp_dict)))
    df = df[df[id_col].notna()]
    df[orig_col] = df[col]
    df[col] = df[id_col]
    df.drop(columns=[id_col], inplace=True)
    df[f'{col}_ID_IS'] = 'DOID_ID'
    return df


def resolve_chemical(df, col):
    """Case-insensitive name -> PubChem CID via synonym lookup. Unmatched rows dropped."""
    df = df.copy()
    id_col, orig_col = f'{col}_ID_tmp', f'{col}_Orignal'
    df[id_col] = df[col].map(Pubchem_Syn_fil_dict_lower)
    df[id_col] = df[id_col].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', np.nan)
    df = df[df[id_col].notna()]
    df[orig_col] = df[col]
    df[col] = df[id_col]
    df.drop(columns=[id_col], inplace=True)
    df[f'{col}_ID_IS'] = 'Pubchem'
    return df
```

### **Step 5 — Process each relation block, validate, save**

Each of the 9 PharmKG relation types is processed with the **same 4-line pattern**: pull the slice → resolve Head → resolve Tail → drop unresolved → save.

```python
df_Gene_Disease = relation_dfs.get('Gene_Disease', pd.DataFrame()).copy()
df_Gene_Disease = resolve_gene_head(df_Gene_Disease)
df_Gene_Disease = df_Gene_Disease[~df_Gene_Disease['Head_Detail_name'].isna()]
df_Gene_Disease = resolve_disease(df_Gene_Disease, 'Tail')
df_Gene_Disease['KG_Source'] = 'PharmKG'
df_Gene_Disease['Head_ID_IS'] = 'NCBI_ID'
df_Gene_Disease = select_cols(df_Gene_Disease)
save(df_Gene_Disease, 'PharmKG_Gene_Disease.csv')
```

| Relation type | Head resolution | Tail resolution |
|---|---|---|
| Gene_Gene | NCBI Symbol | NCBI Symbol |
| Gene_Disease | NCBI Symbol | DOID (DO→MeSH cascade) |
| Gene_Chemical | NCBI Symbol | PubChem CID |
| Chemical_Gene | PubChem CID | NCBI Symbol |
| Chemical_Chemical | PubChem CID | PubChem CID |
| Chemical_Disease | PubChem CID | DOID (DO→MeSH cascade) |
| Disease_Gene | DOID | NCBI Symbol |
| Disease_Disease | DOID | DOID |
| Disease_Chemical | DOID | PubChem CID |

### **Sources following this same paradigm**

DRKG, PrimeKG, Hetionet, CKG, CROssBAR, iBKH, TARKG, STITCH, STRING, miRTarBase, BindingDB/SMS/Biosnap/ChEMBL/DrugBank (combined notebook), BioGrakn — all have pre-labeled relation or entity-type columns and use the same map → validate → swap → drop pattern, just with source-specific column names and dictionaries.

---

## **3.3 Paradigm B — Raw RDF/OWL Triple Sources**

### **Worked example: PheKnowLator**

**Notebook**: `kg_formation/data_processing/phenknowlator.ipynb`
**Raw input**: `PheKnowLator_v1_Full_BioKG_NoDisjointness_Closed_ELK_Triples_Labels.txt` — just two columns, `subject` and `object`, both full ontology URIs. **There is no relation column and no entity-type column at all.**

This is fundamentally different from Paradigm A: everything (entity type, relation type) has to be **derived from the URI structure itself**.

### **Step 1 — Parse the URI into a clean ID + ontology prefix**

```python
def parse_uri(uri):
    uri = str(uri)
    if "obolibrary.org/obo/" in uri:
        raw = uri.split("/obo/")[-1]            # e.g. DOID_5041, GO_0002537
        prefix = raw.split("_")[0]
        return raw.replace("_", ":"), prefix     # -> "DOID:5041", "DOID"
    elif "uniprot.org/geneid/" in uri:
        return "NCBI:" + uri.split("/geneid/")[-1], "Gene"
    elif "reactome.org" in uri or "identifiers.org/reactome" in uri:
        raw = uri.split("/")[-1]
        return raw, "R-HSA"
    else:
        raw = uri.split("/")[-1].split("#")[-1]
        if raw.startswith("R-HSA"):
            return raw, "R-HSA"
        prefix = raw.split("_")[0].split(":")[0]
        return raw, prefix
```

### **Step 2 — Map ontology prefix → entity type**

```python
prefix_to_type = {
    "DOID": "Disease",       "HP": "Phenotype",      "GO": "GO_Term",
    "CHEBI": "Chemical",     "Gene": "Gene",          "UBERON": "Anatomy",
    "CL": "CellType",        "PR": "Protein",         "PRO": "Protein",
    "R-HSA": "Pathway",      "PATO": "Phenotype_Quality",
    "NCBITaxon": "Species",  "SO": "SequenceFeature", "FMA": "Anatomy",
    "HsapDv": "DevStage",    "NBO": "Behavior",       "CARO": "Anatomy",
}
```

Applied to both subject and object URIs:

```python
df["subject_id"], df["subject_prefix"] = zip(*df["subject"].map(parse_uri))
df["object_id"],  df["object_prefix"]  = zip(*df["object"].map(parse_uri))
df["subject_type"] = df["subject_prefix"].map(lambda p: prefix_to_type.get(p, "Other"))
df["object_type"]  = df["object_prefix"].map(lambda p: prefix_to_type.get(p, "Other"))
```

### **Step 3 — Infer the relation from the (Head_type, Tail_type) pair**

Since there's no relation label in the raw file, the relation is **inferred purely from which two entity types are connected**:

```python
type_pair_to_relation = {
    ("Disease",  "GO_Term"):    "disease_associated_with_go",
    ("Disease",  "Pathway"):    "disease_associated_with_pathway",
    ("Disease",  "Phenotype"):  "disease_has_phenotype",
    ("Chemical", "Disease"):    "chemical_associated_with_disease",
    ("Chemical", "Gene"):       "chemical_interacts_with_gene",
    ("Chemical", "Pathway"):    "chemical_associated_with_pathway",
    ("GO_Term",  "GO_Term"):    "go_subclass_of",
    ("GO_Term",  "Gene"):       "go_associated_with_gene",
    ("GO_Term",  "Pathway"):    "go_associated_with_pathway",
    ("Gene",     "Gene"):       "gene_interacts_with_gene",
    ("Gene",     "Pathway"):    "gene_participates_in_pathway",
    ("Gene",     "Disease"):    "gene_associated_with_disease",
    ("Phenotype","Gene"):       "phenotype_associated_with_gene",
    ("Phenotype","Disease"):    "phenotype_associated_with_disease",
    ("Protein",  "Protein"):    "protein_interacts_with_protein",
    ("Anatomy",  "Gene"):       "anatomy_expresses_gene",
    ("Anatomy",  "Anatomy"):    "anatomy_subclass_of",
    ("CellType", "Anatomy"):    "celltype_part_of_anatomy",
    ("Species",  "Gene"):       "species_has_gene",
}
df["relation"] = df.apply(
    lambda r: type_pair_to_relation.get((r["subject_type"], r["object_type"]), "related_to"),
    axis=1
)
```

In practice, the **Relation column actually used downstream is simplified further** to just `Head_type + '_' + Tail_type` (e.g. `Gene_Gene`, `Disease_Phenotype`) — the semantic relation strings above are computed but the type-pair string is what drives the per-relation file split.

### **Step 4 — Filter to entity types worth keeping, split, and write semi-processed files**

```python
keep_relations = {
    'Anatomy_Anatomy', 'CellType_CellType', 'CellType_GO_Term',
    'Chemical_Chemical', 'Chemical_Disease', 'Chemical_GO_Term',
    'Chemical_Gene', 'Disease_Disease', 'Disease_GO_Term',
    'Disease_Phenotype', 'GO_Term_GO_Term', 'GO_Term_Gene',
    'Gene_Gene', 'Phenotype_Gene', 'Phenotype_Phenotype',
    'Protein_Chemical', 'Protein_GO_Term', 'Protein_Protein',
}
filtered = edges[edges["Relation"].isin(keep_relations)]
for rel, grp in filtered.groupby("Relation"):
    grp.to_csv(f"{out_dir}/{rel}.csv", index=False)
```

This produces one **semi-processed** CSV per relation type — these still have raw ontology IDs (DOID:5041, GO:0002537, NCBI:7157) in the Head/Tail columns, not yet resolved to names.

### **Step 5 — Per-relation-type ID resolution (second pass)**

Each semi-processed file is then read back in and resolved against the appropriate ontology dictionary — this mirrors Paradigm A's resolver pattern but uses **direct dictionary lookups** (no fuzzy/synonym matching needed, since ontology IDs are already canonical):

```python
# Gene_Gene: NCBI ID -> Symbol -> validated description
Gene_Gene['Head'] = Gene_Gene['Head'].str.replace('NCBI:', '', regex=False)
Gene_Gene['Head_ID'] = (Gene_Gene['Head'].astype(str).astype(int)
                         .map(NCBI_ALL_GENEIDname_dict))
Gene_Gene = Gene_Gene.rename(columns={"Head": "Head_ID", "Head_ID": "Head"})
Gene_Gene['Head_detail_name'] = Gene_Gene['Head'].map(NCBI_Synbol_GENEname_dict)
Gene_Gene = Gene_Gene[~Gene_Gene['Head_detail_name'].isna()]   # drop unresolved
# ... same for Tail ...
save(Gene_Gene, 'Gene_Gene.csv')

# GO_Term_GO_Term: GO ID -> name, AND re-derive Head_type/Tail_type from
# the GO namespace itself (biological_process / molecular_function / cellular_component)
GO_Term_GO_Term['Head_type'] = GO_Term_GO_Term['Head'].map(GO_namespace_dict)
GO_Term_GO_Term['Tail_type'] = GO_Term_GO_Term['Tail'].map(GO_namespace_dict)

# Chemical_Chemical: CHEBI -> PubChem CID, then enrich with IUPAC name + SMILES
Chemical_Chemical['Head_ID'] = Chemical_Chemical['Head'].map(Chebi2PC_dict)
Chemical_Chemical['Head_IUPAC']  = Chemical_Chemical['Head'].map(Pubchem_IUPAC_CID_Dict)
Chemical_Chemical['Head_Smiles'] = Chemical_Chemical['Head'].map(Pubchem_CID_Smile_Dict)
```

Notice the **GO terms split further by namespace** — `GO_Term_GO_Term` becomes three separate files (`BiologicalProcess_BiologicalProcess.csv`, `CellularComponent_CellularComponent.csv`, `MolecularFunction_MolecularFunction.csv`). The same split is applied to `Disease_GO_Term` → `Disease_BiologicalProcess`, `Disease_CellularComponent`, `Disease_MolecularFunction`.

### **Sources following this same paradigm**

MonarchKG, PheKnowLator — any source distributed as raw RDF/OWL/triple dumps rather than a relational CSV with named columns.

---

## **3.4 Canonical ID System per Node Type**

The single hardest problem across 48+ heterogeneous sources is that **the same entity type arrives under a different identifier system in almost every source**.

EvoAge fixes this by **deciding one canonical ID system per node type up front**, and converting every source's native identifier into that single system during preprocessing:

| Node Type | Canonical ID System |
|---|---|
| **Gene** | NCBI (Gene Symbol / Gene ID) |
| **Protein** | UniProt |
| **Disease** | DOID / MONDO |
| **Chemical** | PubChem / DrugBank |
| **Phenotype** | HPO |
| **Anatomy** | Uberon → GO |
| **Tissue** | BTO |
| **Pathway** | KEGG / Reactome |
| **Biological Process** | GO |
| **Cellular Component** | GO |
| **Molecular Function** | GO |
| **Species** | Scientific name |
| **Plant** | Scientific name |
| **PMID** | PMID |

### **Why this matters for graph connectivity**

Take `TP53`:
- **GenAge**: gene symbol `TP53`
- **PharmKG**: full description `tumor protein p53`
- **DRKG**: Ensembl ID `ENSG00000141510`
- **PheKnowLator**: URI-encoded ID `NCBI:7157`

Unless all four collapse to the same canonical identifier (NCBI Gene ID `7157` / Symbol `TP53`), the KG would contain **four separate disconnected nodes** for the same biological gene.

---

## **3.5 Standard Output Schema**

Regardless of paradigm, every processed file is restricted to the same column whitelist before saving — this is what lets 48 heterogeneous sources merge cleanly later:

```python
DESIRED_COLS = [
    "Head", "Relation", "Tail", "Head_type", "Relation_type", "Tail_type",
    "Source", "KG_Source", "Head_ID", "Head_Detail_name", "Head_ENS",
    "Tail_name", "Tail_DOID_Name", "Tail_ENS", "Tail_Detail_name",
    "Tail_Alias_mapped", "Head_ID_IS", "Tail_ID_IS",
    "Head_Orignal", "Tail_Orignal", "PubMed_ID", "Sentence_tokenized",
]

def select_cols(df):
    return df[[c for c in DESIRED_COLS if c in df.columns]]

def save(df, filename):
    path = os.path.join(OUT_PATH, filename)
    df.to_csv(path, index=False)
    print(f"Saved {len(df):,} rows -> {path}")
```

Key fields every source must populate:

| Field | Purpose |
|---|---|
| `Head`, `Tail` | Canonical resolved IDs (NCBI Symbol, PubChem CID, DOID, GO ID, etc.) |
| `Head_type`, `Tail_type` | Standardized entity type strings (Gene, Chemical, Disease, Protein, ...) |
| `Head_ID_IS`, `Tail_ID_IS` | Which ID system the resolved value belongs to (NCBI_ID, Pubchem, DOID_ID, HPO_ID, ...) |
| `Head_Orignal`, `Tail_Orignal` | Original (pre-resolution) value, kept as an audit trail |
| `KG_Source` | Which of the 48 sources this row came from |

---

## **3.6 Per-Source Notebook Inventory**

For reference, the full set of preprocessing notebooks in `kg_formation/data_processing/`:

**General biomedical / relation-typed CSV (Paradigm A):**
`pharmkg.ipynb`, `DRKG_EvoKG_Data_Processing.ipynb`, `PrimeKG.ipynb`, `hetionet.ipynb`, `ckg.ipynb`, `crossbar.ipynb`, `ibkh.ipynb`, `tarkg.ipynb`, `biograkn.ipynb`, `mirTARbase.ipynb`, `dtinet.ipynb`, `biningdb_sms_biosnap_chembl_drugbank.ipynb`, `STITCH_STRING_Human_KG_FIXED.ipynb`, `STRING_KG_Processing_FIXED.ipynb`, `1_harmonizome.ipynb`, `2_harmonizone.ipynb`

**Raw RDF/OWL triples (Paradigm B):**
`phenknowlator.ipynb`, `monarchkg.ipynb`, `monarchkg_new.ipynb`, `monarchkg_part2.ipynb`

**Aging-specific:**
`genage-Copy1.ipynb`, `drugage.ipynb`, `cellage.ipynb`, `gendr.ipynb`, `agextend.ipynb`, `aging_atlas.ipynb`, `ageanno.ipynb`, `ageannomo.ipynb`, `Agingbank.ipynb`, `digital_aging_atlas.ipynb`, `hald.ipynb`, `MetaboAge_4_KG.ipynb`

**Phytochemical / misc:**
`immpat_ttd_phytohub_othersources.ipynb`

**Species-specific** (see `species_specific_data_source/`):

```
species_specific_data_source/
├── Celegans/    fic.ipynb, stitch.ipynb, string.ipynb, wormbase.ipynb, worminteractomedataabse.ipynb
├── Drosophila/  flybase.ipynb, stitch.ipynb, string.ipynb
├── Mouse/       mgido.ipynb, stitch.ipynb, string_mousenet.ipynb
├── Yeast/       esldb.ipynb, sgd.ipynb, stitch_ch_ch.ipynb, stitch_ch_ge.ipynb, string_yeastnet_biogrid.ipynb
└── Zebrafish/   stitch.ipynb, string.ipynb, zfin.ipynb
```

Each species folder follows Paradigm A (STITCH/STRING-style relation-typed CSVs) with species-specific ID resolution feeding into the [ortholog mapping pipeline](ortholog-mapping.md).

---

## **Next Steps**

1. ✅ **Per-source preprocessing done?** → Move to [Relation Processing](relation-processing.md)
2. **Need ortholog/species mapping for these sources?** → See [Ortholog Mapping](ortholog-mapping.md)
