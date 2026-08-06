import os
import json
import kuzu
import pandas as pd
from tqdm import tqdm

# ==========================================
# 1. HELPER FUNCTIONS (From existing scripts)
# ==========================================
def humanize_identifier(value):
    value = "" if value is None else str(value).strip()
    if not value: return "related to"
    normalized = value.replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    replacements = {
        "No Effect": "has no effect on", "NoEffect": "has no effect on",
        "Inhibits": "inhibits", "Promotes": "promotes",
        "Positively Associated With Aging": "is positively associated with aging",
        "Positively Associated With": "is positively associated with",
        "Negatively Associated With Aging": "is negatively associated with aging",
        "Negatively Associated With": "is negatively associated with",
        "Not Associated With": "is not associated with",
    }
    for old, new in replacements.items(): normalized = normalized.replace(old, new)
    lowered = normalized.lower()
    if " no effect " in f" {lowered} ": return "has no effect on"
    if " inhibits " in f" {lowered} ": return "inhibits"
    if " promotes " in f" {lowered} ": return "promotes"
    if " positively associated with aging " in f" {lowered} ": return "is positively associated with aging"
    if " positively associated with " in f" {lowered} ": return "is positively associated with"
    if " negatively associated with aging " in f" {lowered} ": return "is negatively associated with aging"
    if " negatively associated with " in f" {lowered} ": return "is negatively associated with"
    if " not associated with " in f" {lowered} ": return "is not associated with"
    if " " not in normalized: return f"is associated with {normalized.lower()}"
    return normalized.lower()

def normalize_relation_label(raw_relation):
    relation = "" if raw_relation is None else str(raw_relation).strip()
    if not relation: return "related to"
    exact_map = {
        "ChemicalEntity_NoEffect_BiologicalProcess": "has no effect on", "ChemicalEntity_Gene": "is associated with",
        "ChemicalEntity_Promotes_BiologicalProcess": "promotes", "ChemicalEntity_Inhibits_BiologicalProcess": "inhibits",
        "ChemicalEntity_PositivelyAssociatedWith_BiologicalProcess": "is positively associated with",
        "ChemicalEntity_NegativelyAssociatedWith_BiologicalProcess": "is negatively associated with",
        "ChemicalEntity_NegativelyAssociatedWithAging_BiologicalProcess": "is negatively associated with aging",
        "ChemicalEntity_NotAssociatedWith_BiologicalProcess": "is not associated with",
        "ChemicalEntity_ChemicalEntity": "is associated with", "ChemicalEntity_Disease": "is associated with",
        "ChemicalEntity_Tissue": "is associated with", "ChemicalEntity_Mutation": "is associated with",
        "ChemicalEntity_BiologicalProcess": "is associated with", "Gene_Disease": "is associated with",
        "Gene_BiologicalProcess": "is associated with", "Gene_Tissue": "is associated with",
        "Gene_Gene": "interacts with", "Gene_ChemicalEntity": "is associated with",
        "Gene_Mutation": "is associated with", "Gene_Promotes_BiologicalProcess": "promotes",
        "Gene_Inhibits_BiologicalProcess": "inhibits", "Gene_PositivelyAssociatedWith_BiologicalProcess": "is positively associated with",
        "Gene_NegativelyAssociatedWith_BiologicalProcess": "is negatively associated with",
        "Gene_NotAssociatedWith_BiologicalProcess": "is not associated with",
        "Disease_Disease": "is associated with", "Disease_Gene": "is associated with",
        "Disease_Mutation": "is associated with", "Protein_Tissue": "is associated with",
        "Mutation_Disease": "is associated with", "Mutation_Gene": "is associated with",
        "Mutation_Mutation": "is associated with", "Mutation_ChemicalEntity": "is associated with",
        "BiologicalProcess_BiologicalProcess": "is associated with",
    }
    if relation in exact_map: return exact_map[relation]
    return humanize_identifier(relation)

def normalize_relation_type(raw_relation_type, raw_relation):
    relation_type = "" if raw_relation_type is None else str(raw_relation_type).strip()
    if relation_type.lower() in ("", "nan", "none", "null"): relation_type = ""
    if relation_type: return humanize_identifier(relation_type)
    return humanize_identifier(raw_relation)

def _make_node_description(row):
    species = (row.get('species') or '').strip()
    species_str = ''
    if species and species.lower() not in ('', 'homo sapiens', 'homo sapiens '):
        species_str = f", species: {species}"
    desc_name = (row.get('detail_name') or '').strip() or row['id']
    return json.dumps({"description": f"{desc_name} (Entity Type: {row['type']}{species_str})"})

def make_edge_data(head, rel, tail, rtype, head_species=None, tail_species=None):
    relation_label = normalize_relation_label(rel)
    relation_type_label = normalize_relation_type(rtype, rel)
    hs = (head_species or '').strip()
    ts = (tail_species or '').strip()
    species_info = ''
    if (hs and hs.lower() != 'homo sapiens') and (ts and ts.lower() != 'homo sapiens'):
        species_info = f" (Species: {hs or 'unknown'} -> {ts or 'unknown'})"
    return json.dumps({
        "relation": relation_label,
        "relation_type": relation_type_label,
        "original_relation": rel,
        "original_relation_type": rtype,
        "description": f"{head} {relation_label} {tail}. (Interaction type: {relation_type_label}){species_info}"
    })


# ==========================================
# 2. MAIN SCRIPT
# ==========================================
KUZU_DB_PATH = "cache/graph_test_kuzu"
file_new = "Aging_1_to_many_forfinetune_updated_test2.csv"

# Load the test CSV
print(f"Loading test CSV: {file_new}...")
df_new = pd.read_csv(file_new, low_memory=False)

# Preprocessing to format IDs
print("Preprocessing data...")
for detail_col, base_col in (('head_detail_name', 'head'), ('tail_detail_name', 'tail')):
    if detail_col in df_new.columns and base_col in df_new.columns:
        missing_mask = df_new[detail_col].isna() | (df_new[detail_col].astype(str).str.strip() == '')
        df_new.loc[missing_mask, detail_col] = df_new.loc[missing_mask, base_col]

entity_types = ["BiologicalProcess", "Disease", "Protein", "Tissue", "Gene"]
for entity_type in entity_types:
    mask_head = df_new['head_type'] == entity_type
    df_new.loc[mask_head, 'head'] = df_new.loc[mask_head, 'head'].astype(str) + " (" + df_new.loc[mask_head, 'head_detail_name'].astype(str) + ")"
    mask_tail = df_new['tail_type'] == entity_type
    df_new.loc[mask_tail, 'tail'] = df_new.loc[mask_tail, 'tail'].astype(str) + " (" + df_new.loc[mask_tail, 'tail_detail_name'].astype(str) + ")"

mask_head_mutation = df_new['head_type'] == "Mutation"
df_new.loc[mask_head_mutation, 'head_detail_name'] = df_new.loc[mask_head_mutation, 'head']
mask_tail_mutation = df_new['tail_type'] == "Mutation"
df_new.loc[mask_tail_mutation, 'tail_detail_name'] = df_new.loc[mask_tail_mutation, 'tail']

df_new['head'] = df_new['head'].astype(str).str.strip()
df_new['tail'] = df_new['tail'].astype(str).str.strip()

print(f"Connecting to Test KuzuDB at {KUZU_DB_PATH}...")
os.makedirs(os.path.dirname(KUZU_DB_PATH), exist_ok=True)
db = kuzu.Database(KUZU_DB_PATH, buffer_pool_size=10 * 1024**3)
conn = kuzu.Connection(db)

# Create schema if not exists
try:
    conn.execute("CREATE NODE TABLE Entity(id STRING, data STRING, PRIMARY KEY(id))")
    print("Created Entity node table.")
except Exception as e:
    print(f"Note: {e}")

try:
    conn.execute("CREATE REL TABLE Relation(FROM Entity TO Entity, data STRING)")
    print("Created Relation edge table.")
except Exception as e:
    print(f"Note: {e}")

# Nodes
heads = df_new[['head', 'head_type', 'head_species', 'head_detail_name']].rename(columns={'head': 'id', 'head_type': 'type', 'head_species': 'species', 'head_detail_name': 'detail_name'})
tails = df_new[['tail', 'tail_type', 'tail_species', 'tail_detail_name']].rename(columns={'tail': 'id', 'tail_type': 'type', 'tail_species': 'species', 'tail_detail_name': 'detail_name'})
nodes_df = pd.concat([heads, tails]).drop_duplicates(subset=['id'])
nodes_df = nodes_df[nodes_df['id'].astype(bool)]

print(f"Found {len(nodes_df)} unique nodes in test set.")
nodes_df['data'] = nodes_df.apply(_make_node_description, axis=1)

for _, row in tqdm(nodes_df.iterrows(), total=len(nodes_df), desc="Adding Nodes"):
    try:
        conn.execute("CREATE (a:Entity {id: $id, data: $data})", {"id": row['id'], "data": row['data']})
    except Exception as e:
        # Ignore already exists errors if rerunning
        pass

# Edges
new_edges = []
for _, r in df_new.iterrows():
    head = str(r['head']).strip()
    tail = str(r['tail']).strip()
    rel = str(r['relation']).strip()
    data_json = make_edge_data(r.get('head_detail_name'), r['relation'], r.get('tail_detail_name'), r.get('relation_type'), r.get('head_species'), r.get('tail_species'))
    new_edges.append({"head": head, "tail": tail, "data": data_json})

print(f"Found {len(new_edges)} edges to add.")
for edge in tqdm(new_edges, desc="Adding Edges"):
    try:
        conn.execute("MATCH (a:Entity {id: $head}), (b:Entity {id: $tail}) CREATE (a)-[r:Relation {data: $data}]->(b)", 
                     {"head": edge['head'], "tail": edge['tail'], "data": edge['data']})
    except Exception as e:
        pass

print("\nTest database generation complete!")
print(f"Database saved to: {KUZU_DB_PATH}")
