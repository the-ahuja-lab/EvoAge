import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Base path ─────────────────────────────────────────────────────────────────
ROOT    = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised/OTHER_SPECIES'
OUT_DIR = ROOT  # each species df saved inside its own folder

OUT_DIR = '/storage/Arushi/090526_EvoAge/kg_formation/orthology_mapping'


# ── Species config ────────────────────────────────────────────────────────────
# species_name : (folder, canonical_species_string, col_name_for_output)
SPECIES_CONFIG = {
    'Celegans'   : ('Celegans',   'Caenorhabditis elegans',  'Celegans_gene'),
    'Drosophila' : ('Drosophila', 'Drosophila melanogaster', 'Droso_gene'),
    'Mouse'      : ('Mouse',      'Mus musculus',            'Mouse_gene'),
    'Yeast'      : ('Yeast',      'Saccharomyces cerevisiae','Yeast_gene'),
    'Zebrafish'  : ('Zebrafish',  'Danio rerio',             'Zebrafish_gene'),
}

# ── Helper: extract unique genes from one CSV ─────────────────────────────────
def extract_genes_from_file(path):
    """
    Read a CSV, collect unique head values where head_type == 'Gene'
    and unique tail values where tail_type == 'Gene'.
    Returns a set of gene IDs.
    """
    try:
        # Read only necessary columns for speed
        usecols = []
        header  = pd.read_csv(path, nrows=0).columns.tolist()

        need = ['head', 'tail', 'head_type', 'tail_type']
        usecols = [c for c in need if c in header]

        if not usecols or 'head_type' not in usecols:
            return set()

        df = pd.read_csv(path, usecols=usecols, low_memory=False)
        genes = set()

        if 'head' in df.columns and 'head_type' in df.columns:
            mask = df['head_type'].str.strip().str.lower() == 'gene'
            genes.update(df.loc[mask, 'head'].dropna().astype(str).unique())

        if 'tail' in df.columns and 'tail_type' in df.columns:
            mask = df['tail_type'].str.strip().str.lower() == 'gene'
            genes.update(df.loc[mask, 'tail'].dropna().astype(str).unique())

        return genes

    except Exception as e:
        tqdm.write(f"    ⚠️  Skipped {os.path.basename(path)}: {e}")
        return set()

# ── Main loop: one df per species ─────────────────────────────────────────────
species_gene_dfs = {}   # { species_name : DataFrame }

for species, (folder, canonical_species, col_name) in SPECIES_CONFIG.items():

    species_dir = os.path.join(ROOT, folder)
    csv_files = [
        f for f in glob.glob(os.path.join(species_dir, '*', '*.csv'))
        if '.ipynb_checkpoints' not in f
        and not os.path.basename(f).startswith('_SUMMARY')
        and 'ortho_1_to_' not in os.path.basename(f)
        and not f.endswith('.bak')
    ]

    print(f"\n{'─'*60}")
    print(f"  {species}  ({len(csv_files)} CSV files)")
    print(f"{'─'*60}")

    all_genes = set()

    for path in tqdm(csv_files, desc=f"  Scanning {species}", unit="file",
                     bar_format="{l_bar}{bar:25}{r_bar}"):
        genes = extract_genes_from_file(path)
        all_genes.update(genes)
        if genes:
            tqdm.write(f"    ✓  {os.path.basename(path):55s}  +{len(genes):,} genes")

    # Build species gene dataframe
    gene_df = pd.DataFrame({
        col_name   : sorted(all_genes),
        'Node_type': 'Gene',
        'species'  : canonical_species,
    })

    species_gene_dfs[species] = gene_df

    # Save
    out_path = os.path.join(OUT_DIR, f'{species}_unique_genes.csv')
    gene_df.to_csv(out_path, index=False)

    print(f"\n  ✅  {species}: {len(gene_df):,} unique genes → {out_path}")

# ── Final summary ─────────────────────────────────────────────────────────────
print(f"\n{'═'*60}")
print("  UNIQUE GENE COUNTS PER SPECIES")
print(f"{'═'*60}")
for species, df in species_gene_dfs.items():
    col = df.columns[0]
    print(f"  {species:<15} {len(df):>8,} unique genes   (col: '{col}')")
print(f"{'═'*60}")

# ── Preview each df ───────────────────────────────────────────────────────────
print("\n  PREVIEW (first 3 rows each):\n")
for species, df in species_gene_dfs.items():
    print(f"  [{species}]")
    print(df.head(3).to_string(index=True))
    print()

# ── Access dataframes in notebook ─────────────────────────────────────────────
# After running this script, use:
#   species_gene_dfs['Yeast']       → Yeast gene df
#   species_gene_dfs['Mouse']       → Mouse gene df
#   species_gene_dfs['Celegans']    → C.elegans gene df
#   species_gene_dfs['Drosophila']  → Drosophila gene df
#   species_gene_dfs['Zebrafish']   → Zebrafish gene df