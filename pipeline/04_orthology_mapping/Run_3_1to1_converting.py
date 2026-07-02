"""
═══════════════════════════════════════════════════════════════════════════════
 ORTHOLOG MAPPING — Convert non-human species genes to human orthologs
 SOURCE: Ensembl BioMart (replaces gProfiler)
═══════════════════════════════════════════════════════════════════════════════
 Mapping rule:
   • input_gene  → initial_alias equivalent  (matched via .str.upper())
   • human_symbol → ortholog symbol
   • human_description → description
   • ortholog_info → copied to head_ortholog_info / tail_ortholog_info
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Base paths ────────────────────────────────────────────────────────────────
ROOT       = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised/OTHER_SPECIES'
BIOMART_DIR = '/storage/Arushi/090526_EvoAge/kg_formation/orthology_mapping/Biomart_ensemble/Human_Ortholog_Mapping_3'

# ── Species config ────────────────────────────────────────────────────────────
# species_key : (folder, original_species_string, BioMart_CSV_path)
SPECIES_CONFIG = {
    'Celegans'   : ('Celegans',   'Caenorhabditis elegans',   'Celegans/Celegans_byType_ortholog_one2one.csv'),
    'Drosophila' : ('Drosophila', 'Drosophila melanogaster',  'Drosophila/Drosophila_byType_ortholog_one2one.csv'),
    'Mouse'      : ('Mouse',      'Mus musculus',             'Mouse/Mouse_byType_ortholog_one2one.csv'),
    'Yeast'      : ('Yeast',      'Saccharomyces cerevisiae', 'Yeast/Yeast_byType_ortholog_one2one.csv'),
    'Zebrafish'  : ('Zebrafish',  'Danio rerio',              'Zebrafish/Zebrafish_byType_ortholog_one2one.csv'),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helper — build ortholog dicts from ONE species' BioMart file
# ═══════════════════════════════════════════════════════════════════════════════
def build_ortholog_dicts(biomart_path, species_key):
    """
    Returns:
      gene2ortho : {input_gene.upper() -> human_symbol}
      gene2desc  : {input_gene.upper() -> human_description}
      gene2info  : {input_gene.upper() -> ortholog_info string}
    Rules:
      • Drop rows where human_symbol is NaN
      • All keys stored UPPERCASED for case-insensitive matching
    """
    bm = pd.read_csv(biomart_path)

    bm['ortholog_info'] = (
        'species: ' + species_key +
        ' ::: original_gene: '        + bm['input_gene'].astype(str) +
        ' ::: orthology_confidence: ' + bm['orthology_confidence'].astype(str) +
        ' ::: perc_identity: '        + bm['perc_id'].astype(str) +
        ' ::: orthology_type: '       + bm['orthology_type'].astype(str)
    )

    # Drop rows with no human symbol
    bm = bm[bm['human_symbol'].notna()].copy()

    # Uppercase the key column for matching
    bm['input_gene_upper'] = bm['input_gene'].astype(str).str.upper()

    # ── first-occurrence drop_duplicates removed ──────────────────────────────

    gene2ortho = dict(zip(bm['input_gene_upper'], bm['human_symbol']))
    gene2desc  = dict(zip(bm['input_gene_upper'], bm['human_description']))
    gene2info  = dict(zip(bm['input_gene_upper'], bm['ortholog_info']))

    return gene2ortho, gene2desc, gene2info


# ═══════════════════════════════════════════════════════════════════════════════
# Helper — map one side (head OR tail) to human orthologs
# ═══════════════════════════════════════════════════════════════════════════════
def map_one_side(df, side, gene2ortho, gene2desc, gene2info, original_species):
    """
    Mutates df in place:
      • df[side]                    → human_symbol where gene is mapped
      • df[f'{side}_detail_name']   → human_description where mapped
      • df[f'{side}_species']       → 'Homo sapiens' where mapped, else original_species
      • df[f'{side}_ortholog_info'] → ortholog_info string where mapped, else pd.NA
    Unmapped genes are left UNCHANGED.
    """
    type_col        = f'{side}_type'
    detail_col      = f'{side}_detail_name'
    species_col     = f'{side}_species'
    ortho_info_col  = f'{side}_ortholog_info'

    # Rows where this side is a Gene
    is_gene = df[type_col].astype(str).str.strip().str.lower() == 'gene'

    # Uppercase lookup keys
    keys = df.loc[is_gene, side].astype(str).str.upper()

    # Which of those actually have an ortholog?
    mapped_mask = is_gene.copy()
    mapped_mask[is_gene] = keys.map(gene2ortho).notna().values

    # Ensure extra columns exist
    for col, default in [(detail_col, pd.NA), (species_col, original_species), (ortho_info_col, pd.NA)]:
        if col not in df.columns:
            df[col] = default

    # Apply mappings only to mapped rows
    mapped_keys = df.loc[mapped_mask, side].astype(str).str.upper()

    df.loc[mapped_mask, side]           = mapped_keys.map(gene2ortho).values
    df.loc[mapped_mask, detail_col]     = mapped_keys.map(gene2desc).values
    df.loc[mapped_mask, species_col]    = 'Homo sapiens'
    df.loc[mapped_mask, ortho_info_col] = mapped_keys.map(gene2info).values

    return int(mapped_mask.sum())


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers — I/O
# ═══════════════════════════════════════════════════════════════════════════════
def get_output_path(src_path):
    root, _ = os.path.splitext(src_path)
    return f"{root}_ortho_1_to_1.csv"

def load_file(path):
    if path.lower().endswith('.parquet'):
        return pd.read_parquet(path)
    return pd.read_csv(path, low_memory=False)

def save_file(df, path):
    df.to_csv(path, index=False)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
overall_log = []

for species, (folder, original_species, biomart_rel_path) in SPECIES_CONFIG.items():

    species_dir  = os.path.join(ROOT, folder)
    biomart_path = os.path.join(BIOMART_DIR, biomart_rel_path)

    print(f"\n{'═'*70}")
    print(f"  {species}   ({original_species})")
    print(f"{'═'*70}")

    if not os.path.exists(biomart_path):
        print(f"  ❌  BioMart file not found: {biomart_path}  — skipping")
        continue

    gene2ortho, gene2desc, gene2info = build_ortholog_dicts(biomart_path, species)
    print(f"  Ortholog map: {len(gene2ortho):,} genes → human (uppercased)\n")

    # Collect triple files
    # files = (
    #     glob.glob(os.path.join(species_dir, '**/*.csv'),     recursive=True) +
    #     glob.glob(os.path.join(species_dir, '**/*.parquet'), recursive=True)
    # )
    files = [
        f for f in glob.glob(os.path.join(species_dir, '*', '*.csv'))
        if '.ipynb_checkpoints' not in f
        and not os.path.basename(f).startswith('_SUMMARY')
        and 'ortho_1_to_' not in os.path.basename(f)
        and not f.endswith('.bak')
    ]
    files = sorted(files)

    for src in tqdm(files, desc=f"  {species}", unit="file",
                    bar_format="{l_bar}{bar:25}{r_bar}"):
        try:
            df = load_file(src)
            df.columns = df.columns.str.lower()

            if 'head_type' not in df.columns or 'tail_type' not in df.columns:
                tqdm.write(f"    ⚠️  no type cols, copied unchanged: {os.path.basename(src)}")
                save_file(df, get_output_path(src))
                continue

            head_has_gene = (df['head_type'].astype(str).str.strip().str.lower() == 'gene').any()
            tail_has_gene = (df['tail_type'].astype(str).str.strip().str.lower() == 'gene').any()

            # Initialise species + ortholog_info cols with defaults
            for col, default in [
                ('head_species',        original_species),
                ('tail_species',        original_species),
                ('head_ortholog_info',  pd.NA),
                ('tail_ortholog_info',  pd.NA),
            ]:
                if col not in df.columns:
                    df[col] = default

            n_head = n_tail = 0
            if head_has_gene:
                n_head = map_one_side(df, 'head', gene2ortho, gene2desc, gene2info, original_species)
            if tail_has_gene:
                n_tail = map_one_side(df, 'tail', gene2ortho, gene2desc, gene2info, original_species)

            out = get_output_path(src)
            save_file(df, out)

            overall_log.append({
                'species'     : species,
                'file'        : os.path.relpath(src, species_dir),
                'rows'        : len(df),
                'head_mapped' : n_head,
                'tail_mapped' : n_tail,
                'output'      : os.path.basename(out),
            })

        except Exception as e:
            tqdm.write(f"    ❌  {os.path.basename(src)}: {e}")
            overall_log.append({
                'species': species, 'file': os.path.relpath(src, species_dir),
                'rows': 0, 'head_mapped': 0, 'tail_mapped': 0, 'output': f'ERROR: {e}',
            })

# ── Final log ─────────────────────────────────────────────────────────────────
log_df   = pd.DataFrame(overall_log)
log_path = os.path.join(ROOT, '_ORTHOLOG_MAPPING_LOG_1_to_1_BioMart.csv')
log_df.to_csv(log_path, index=False)

print(f"\n{'═'*70}")
print(f"  DONE — processed {len(log_df)} files")
print(f"  Log saved → {log_path}")
print(f"{'═'*70}")
print(log_df.to_string(index=False))