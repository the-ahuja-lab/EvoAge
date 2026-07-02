"""
═══════════════════════════════════════════════════════════════════════════════
 SPECIES TRIPLES — 1-to-1 ortholog KG
═══════════════════════════════════════════════════════════════════════════════
 Sources:
   • Human   : all relation folders under generalised/ (except OTHER_SPECIES)
   • Other   : *_ortho_1_to_1.csv files under OTHER_SPECIES/
 Output:
   making_species_assocaitedwithconnection/1_to_1_ortholog/
     → Homo_sapiens.parquet, Mus_musculus.parquet, etc. (one file per species)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm
from collections import defaultdict

warnings.filterwarnings('ignore')

# ── Paths ─────────────────────────────────────────────────────────────────────
GENERALISED  = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised'
SPECIES_ROOT = os.path.join(GENERALISED, 'OTHER_SPECIES')
OUT_DIR      = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/making_species_assocaitedwithconnection/1_to_1_ortholog'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Species list ──────────────────────────────────────────────────────────────
SPECIES_LIST = [
    'Homo sapiens',
    'Saccharomyces cerevisiae',
    'Caenorhabditis elegans',
    'Drosophila melanogaster',
    'Danio rerio',
    'Mus musculus',
]

# ── Collect Human files ───────────────────────────────────────────────────────
human_files = (
    glob.glob(os.path.join(GENERALISED, '**/*.csv'),     recursive=True) +
    glob.glob(os.path.join(GENERALISED, '**/*.parquet'), recursive=True)
)
human_files = [
    f for f in human_files
    if 'OTHER_SPECIES'       not in f
    and '.ipynb_checkpoints' not in f
    and not os.path.basename(f).startswith('_')
    and not os.path.basename(f).endswith('.bak')
]

# ── Collect OTHER_SPECIES 1-to-1 files ───────────────────────────────────────
ortho_files = glob.glob(os.path.join(SPECIES_ROOT, '**/*_ortho_1_to_1.csv'), recursive=True)
ortho_files = [f for f in ortho_files if '.ipynb_checkpoints' not in f]

all_files = sorted(human_files + ortho_files)
print(f"Human files  : {len(human_files)}")
print(f"Ortho 1-to-1 : {len(ortho_files)}")
print(f"Total        : {len(all_files)}\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_file(path):
    if path.lower().endswith('.parquet'):
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)

def generate_species_triples(df):
    """
    From each file produce two sets of triples:
      head_species → Species_AssociatedWith → head
      tail_species → Species_AssociatedWith → tail
    """
    results = []

    if 'head_species' in df.columns and 'head' in df.columns and 'head_type' in df.columns:
        t1 = pd.DataFrame({
            'head'      : df['head_species'],
            'relation'  : 'Species_AssociatedWith',
            'tail'      : df['head'],
            'head_type' : 'Species',
            'tail_type' : df['head_type'],
        }).dropna(subset=['head', 'tail'])
        results.append(t1)

    if 'tail_species' in df.columns and 'tail' in df.columns and 'tail_type' in df.columns:
        t2 = pd.DataFrame({
            'head'      : df['tail_species'],
            'relation'  : 'Species_AssociatedWith',
            'tail'      : df['tail'],
            'head_type' : 'Species',
            'tail_type' : df['tail_type'],
        }).dropna(subset=['head', 'tail'])
        results.append(t2)

    if not results:
        return pd.DataFrame()

    combined = pd.concat(results, ignore_index=True)
    combined = combined.drop_duplicates(subset=['head', 'relation', 'tail'])
    return combined

# ── Main loop ─────────────────────────────────────────────────────────────────
node_type_buckets = defaultdict(list)

for path in tqdm(all_files, desc="Processing", unit="file",
                 bar_format="{l_bar}{bar:30}{r_bar}"):
    try:
        df = load_file(path)
        df.columns = df.columns.str.lower()

        if not any(c in df.columns for c in ['head_species', 'tail_species']):
            tqdm.write(f"  ⏭️  no species cols: {os.path.basename(path)}")
            continue

        triples = generate_species_triples(df)
        if triples.empty:
            continue

        for tail_type, grp in triples.groupby('tail_type'):
            node_type_buckets[str(tail_type)].append(grp)

        tqdm.write(f"  ✅  {os.path.relpath(path, GENERALISED)}  "
                   f"({len(triples):,} triples)")

    except Exception as e:
        tqdm.write(f"  ❌  {os.path.basename(path)}: {e}")

# ── Merge all buckets into one dataframe ──────────────────────────────────────
print(f"\n{'═'*60}")
print("  Merging all triples ...")

all_triples = []
for dfs in node_type_buckets.values():
    all_triples.extend(dfs)

combined = pd.concat(all_triples, ignore_index=True)
combined = combined.drop_duplicates(subset=['head', 'relation', 'tail'])
print(f"  Total unique triples: {len(combined):,}")

# ── Split by species and save one parquet per species ─────────────────────────
print(f"\n{'═'*60}")
print("  Saving per-species parquet files ...")
print(f"{'═'*60}")

summary = []
for species in SPECIES_LIST:
    df_species = combined[combined['head'] == species].copy()

    # Fix mixed-type columns for parquet compatibility
    for col in df_species.columns:
        df_species[col] = df_species[col].astype(str)

    filename = species.replace(' ', '_') + '.parquet'
    out_path = os.path.join(OUT_DIR, filename)
    df_species.to_parquet(out_path, index=False)

    summary.append({'species': species, 'rows': len(df_species), 'file': filename})
    print(f"  ✅  {filename:50s}  {len(df_species):>10,} rows")

# ── Save summary ──────────────────────────────────────────────────────────────
summary_df = pd.DataFrame(summary)
summary_df.to_csv(os.path.join(OUT_DIR, '1_to_1_SUMMARY.csv'), index=False)

print(f"\n{'═'*60}")
print(f"  Species saved  : {len(summary_df)}")
print(f"  Total triples  : {summary_df['rows'].sum():,}")
print(f"  Output dir     : {OUT_DIR}")
print(f"{'═'*60}")