import pandas as pd
import json
import os
import shutil
import kuzu


def humanize_identifier(value):
    value = "" if value is None else str(value).strip()
    if not value:
        return "related to"

    normalized = value.replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())

    replacements = {
        "No Effect": "has no effect on",
        "NoEffect": "has no effect on",
        "Inhibits": "inhibits",
        "Promotes": "promotes",
        "Positively Associated With Aging": "is positively associated with aging",
        "Positively Associated With": "is positively associated with",
        "Negatively Associated With Aging": "is negatively associated with aging",
        "Negatively Associated With": "is negatively associated with",
        "Not Associated With": "is not associated with",
    }

    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    lowered = normalized.lower()
    if " no effect " in f" {lowered} ":
        return "has no effect on"
    if " inhibits " in f" {lowered} ":
        return "inhibits"
    if " promotes " in f" {lowered} ":
        return "promotes"
    if " positively associated with aging " in f" {lowered} ":
        return "is positively associated with aging"
    if " positively associated with " in f" {lowered} ":
        return "is positively associated with"
    if " negatively associated with aging " in f" {lowered} ":
        return "is negatively associated with aging"
    if " negatively associated with " in f" {lowered} ":
        return "is negatively associated with"
    if " not associated with " in f" {lowered} ":
        return "is not associated with"

    if " " not in normalized:
        return f"is associated with {normalized.lower()}"

    return normalized.lower()


def normalize_relation_label(raw_relation):
    relation = "" if raw_relation is None else str(raw_relation).strip()
    if not relation:
        return "related to"

    exact_map = {
        "ChemicalEntity_NoEffect_BiologicalProcess": "has no effect on",
        "ChemicalEntity_Gene": "is associated with",
        "ChemicalEntity_Promotes_BiologicalProcess": "promotes",
        "ChemicalEntity_Inhibits_BiologicalProcess": "inhibits",
        "ChemicalEntity_PositivelyAssociatedWith_BiologicalProcess": "is positively associated with",
        "ChemicalEntity_NegativelyAssociatedWith_BiologicalProcess": "is negatively associated with",
        "ChemicalEntity_NegativelyAssociatedWithAging_BiologicalProcess": "is negatively associated with aging",
        "ChemicalEntity_NotAssociatedWith_BiologicalProcess": "is not associated with",
        "ChemicalEntity_ChemicalEntity": "is associated with",
        "ChemicalEntity_Disease": "is associated with",
        "ChemicalEntity_Tissue": "is associated with",
        "ChemicalEntity_Mutation": "is associated with",
        "ChemicalEntity_BiologicalProcess": "is associated with",
        "Gene_Disease": "is associated with",
        "Gene_BiologicalProcess": "is associated with",
        "Gene_Tissue": "is associated with",
        "Gene_Gene": "interacts with",
        "Gene_ChemicalEntity": "is associated with",
        "Gene_Mutation": "is associated with",
        "Gene_Promotes_BiologicalProcess": "promotes",
        "Gene_Inhibits_BiologicalProcess": "inhibits",
        "Gene_PositivelyAssociatedWith_BiologicalProcess": "is positively associated with",
        "Gene_NegativelyAssociatedWith_BiologicalProcess": "is negatively associated with",
        "Gene_NotAssociatedWith_BiologicalProcess": "is not associated with",
        "Disease_Disease": "is associated with",
        "Disease_Gene": "is associated with",
        "Disease_Mutation": "is associated with",
        "Protein_Tissue": "is associated with",
        "Mutation_Disease": "is associated with",
        "Mutation_Gene": "is associated with",
        "Mutation_Mutation": "is associated with",
        "Mutation_ChemicalEntity": "is associated with",
        "BiologicalProcess_BiologicalProcess": "is associated with",
    }

    if relation in exact_map:
        return exact_map[relation]

    return humanize_identifier(relation)


def normalize_relation_type(raw_relation_type, raw_relation):
    relation_type = "" if raw_relation_type is None else str(raw_relation_type).strip()
    if relation_type.lower() in ("", "nan", "none", "null"):
        relation_type = ""
    if relation_type:
        return humanize_identifier(relation_type)
    # If no explicit relation_type, return a human-readable form of the raw relation
    return humanize_identifier(raw_relation)

working_dir = "cache"
db_path = os.path.join(working_dir, "graph_kuzu")

if os.path.exists(db_path):
    print("Clearing old Kuzu DB...")
    if os.path.isdir(db_path):
        shutil.rmtree(db_path)
    else:
        os.remove(db_path)
    
if os.path.exists(db_path + ".wal"):
    os.remove(db_path + ".wal")

os.makedirs(working_dir, exist_ok=True)
print("Loading parquet...")
cols = ['head', 'head_detail_name', 'head_type', 'relation', 'relation_type', 'tail', 'tail_detail_name', 'tail_type']
df = pd.read_csv("Aging_1_to_many_forfinetune_updated_training.csv",low_memory=False)
df.head().to_csv("Aging_1_to_many_forfinetune_updated_training_head.csv",index=False)




#################################################
# Prefix head with: head (head_detail_name)
entity_types = [
    "BiologicalProcess",
    "Disease",
    "Protein",
    "Tissue",
    "Gene"
]

for entity_type in entity_types:
    # -------------------------
    # HEAD
    # -------------------------
    mask_head = df['head_type'] == entity_type
    df.loc[mask_head, 'head'] = (
        df.loc[mask_head, 'head'].astype(str)
        + " ("
        + df.loc[mask_head, 'head_detail_name'].astype(str)
        + ")"
    )
    # -------------------------
    # TAIL
    # -------------------------
    mask_tail = df['tail_type'] == entity_type
    df.loc[mask_tail, 'tail'] = (
        df.loc[mask_tail, 'tail'].astype(str)
        + " ("
        + df.loc[mask_tail, 'tail_detail_name'].astype(str)
        + ")"
    )
    print(f"{entity_type}:")
    print("  Head updated:", mask_head.sum())
    print("  Tail updated:", mask_tail.sum())



###############################


###############################
# Replace head with head_detail_name for Mutation rows
mask_head_mutation = df['head_type'] == "Mutation"

df.loc[mask_head_mutation, 'head_detail_name'] = df.loc[
    mask_head_mutation,
    'head'
]


# Replace tail with tail_detail_name for Mutation rows
mask_tail_mutation = df['tail_type'] == "Mutation"
df.loc[mask_tail_mutation, 'tail_detail_name'] = df.loc[
    mask_tail_mutation,
    'tail'
]

################################





# Fill missing detail name columns from base columns when available
for detail_col, base_col in (('head_detail_name', 'head'), ('tail_detail_name', 'tail')):
    if detail_col in df.columns and base_col in df.columns:
        missing_mask = df[detail_col].isna() | (df[detail_col].astype(str).str.strip() == '')
        n_missing = int(missing_mask.sum())
        if n_missing:
            df.loc[missing_mask, detail_col] = df.loc[missing_mask, base_col]
            print(f"Filled {n_missing} rows of {detail_col} from {base_col}")


print("Preparing node data (Vectorized for speed)...")
heads = df[['head', 'head_type', 'head_species', 'head_detail_name']].rename(
    columns={'head': 'id', 'head_type': 'type', 'head_species': 'species', 'head_detail_name': 'detail_name'}
)
tails = df[['tail', 'tail_type', 'tail_species', 'tail_detail_name']].rename(
    columns={'tail': 'id', 'tail_type': 'type', 'tail_species': 'species', 'tail_detail_name': 'detail_name'}
)


# Combine, drop duplicates to get unique nodes instantly
nodes_df = pd.concat([heads, tails]).drop_duplicates(subset=['id'])

# Clean node ids: strip and remove empty ids which would violate Kuzu PK NOT NULL
nodes_df['id'] = nodes_df['id'].astype(str).str.strip()
before_nodes = len(nodes_df)
nodes_df = nodes_df[nodes_df['id'].astype(bool)]
dropped_nodes = before_nodes - len(nodes_df)
if dropped_nodes:
    print(f"Dropped {dropped_nodes} nodes with empty id")

# Build the JSON payload string
def _make_node_description(row):
    # include species only when it is present and not Homo sapiens
    species = (row.get('species') or '').strip()
    species_str = ''
    if species and species.lower() not in ('', 'homo sapiens', 'homo sapiens '):
        species_str = f", species: {species}"
    desc_name = (row.get('detail_name') or '').strip() or row['id']
    return json.dumps({"description": f"{desc_name} (Entity Type: {row['type']}{species_str})"})

nodes_df['data'] = nodes_df.apply(_make_node_description, axis=1)
nodes_df = nodes_df[['id', 'data']]

print("Preparing edge data...")
edges_df = pd.DataFrame({
    'from': df['head'],
    'to': df['tail']
})

def make_edge_data(head, rel, tail, rtype, head_species=None, tail_species=None):
    relation_label = normalize_relation_label(rel)
    relation_type_label = normalize_relation_type(rtype, rel)
    # include species info in edge description if either endpoint is non-human
    hs = (head_species or '').strip()
    ts = (tail_species or '').strip()
    species_info = ''
    if (hs and hs.lower() != 'homo sapiens') or (ts and ts.lower() != 'homo sapiens'):
        species_info = f" (Species: {hs or 'unknown'} -> {ts or 'unknown'})"
    return json.dumps({
        "relation": relation_label,
        "relation_type": relation_type_label,
        "original_relation": rel,
        "original_relation_type": rtype,
        "description": f"{head} {relation_label} {tail}. (Interaction type: {relation_type_label}){species_info}"
    })

edges_df['data'] = df.apply(lambda r: make_edge_data(r['head_detail_name'], r['relation'], r['tail_detail_name'], r['relation_type'], r.get('head_species'), r.get('tail_species')), axis=1)

# Clean edges: strip endpoint ids and drop rows with missing endpoints
edges_df['from'] = edges_df['from'].astype(str).str.strip()
edges_df['to'] = edges_df['to'].astype(str).str.strip()
before_edges = len(edges_df)
edges_df = edges_df[edges_df['from'].astype(bool) & edges_df['to'].astype(bool)]
dropped_edges = before_edges - len(edges_df)
if dropped_edges:
    print(f"Dropped {dropped_edges} edges with missing endpoints")

nodes_parquet = "nodes_tmp.parquet"
edges_parquet = "edges_tmp.parquet"

print("Writing compressed Parquet files for blazing fast Kuzu ingestion...")
# Parquet handles strings and newlines natively, so we don't need to sanitize quotes!
nodes_df.to_parquet(nodes_parquet, index=False, engine='pyarrow')
edges_df.to_parquet(edges_parquet, index=False, engine='pyarrow')

print("Loading into KuzuDB (with strict memory limits)...")
# Limit Kuzu DB to use only 10GB of RAM to prevent the Slurm OOM Killer from terminating it!
db = kuzu.Database(db_path, buffer_pool_size=10 * 1024**3)
conn = kuzu.Connection(db)

try:
    conn.execute("CREATE NODE TABLE Entity(id STRING, data STRING, PRIMARY KEY(id))")
except Exception as e:
    pass
try:
    conn.execute("CREATE REL TABLE Relation(FROM Entity TO Entity, data STRING)")
except Exception as e:
    pass

print("Executing high-speed Parquet COPY into Graph Engine...")
conn.execute(f'COPY Entity FROM "{nodes_parquet}"')
conn.execute(f'COPY Relation FROM "{edges_parquet}"')

print(f"Successfully loaded nodes and edges from Parquet into GraphGen Kuzu storage!")
os.remove(nodes_parquet)
os.remove(edges_parquet)
