"""
═══════════════════════════════════════════════════════════════════════════════
 ORTHOLOG MAPPING — 1-to-MANY
 SOURCE: Ensembl BioMart (replaces gProfiler)
═══════════════════════════════════════════════════════════════════════════════
 Mapping rule:
   • input_gene (uppercased) → LIST of human_symbol  (1 or many)
   • A single triple row explodes into N rows if head gene has N orthologs
   • If BOTH sides are genes: N × M rows (cartesian product)
   • ortholog_info built per row, then grouped into list → exploded alongside
   • Unmapped genes kept as-is (1 row, original value)
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Base paths ────────────────────────────────────────────────────────────────
ROOT        = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised/OTHER_SPECIES'
BIOMART_DIR = '/storage/Arushi/090526_EvoAge/kg_formation/orthology_mapping/Biomart_ensemble/Human_Ortholog_Mapping_3'

# ── Species config ────────────────────────────────────────────────────────────
SPECIES_CONFIG = {
    'Celegans'   : ('Celegans',   'Caenorhabditis elegans',   'Celegans/Celegans_byType_ortholog_one2one_plus_one2many.csv'),
    'Drosophila' : ('Drosophila', 'Drosophila melanogaster',  'Drosophila/Drosophila_byType_ortholog_one2one_plus_one2many.csv'),
    'Mouse'      : ('Mouse',      'Mus musculus',             'Mouse/Mouse_byType_ortholog_one2one_plus_one2many.csv'),
    'Yeast'      : ('Yeast',      'Saccharomyces cerevisiae', 'Yeast/Yeast_byType_ortholog_one2one_plus_one2many.csv'),
    'Zebrafish'  : ('Zebrafish',  'Danio rerio',              'Zebrafish/Zebrafish_byType_ortholog_one2one_plus_one2many.csv'),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helper — build 1-to-MANY ortholog dicts from ONE species' BioMart file
# ═══════════════════════════════════════════════════════════════════════════════
def build_ortholog_dicts_121_12M(biomart_path, species_key):
    """
    Returns:
      gene2orthos : {input_gene.upper() -> [human_symbol, ...]}   (list, length >= 1)
      gene2descs  : {input_gene.upper() -> [human_description, ...]}
      gene2infos  : {input_gene.upper() -> [ortholog_info, ...]}

    Rules:
      • Drop rows where human_symbol is NaN
      • Drop exact (input_gene, human_symbol) duplicates
      • Group ALL orthologs per uppercased input_gene into lists
        (preserves BioMart row order)
    """
    bm = pd.read_csv(biomart_path)

    # Build ortholog_info per row
    bm['ortholog_info'] = (
        'species: ' + species_key +
        ' ::: original_gene: '        + bm['input_gene'].astype(str) +
        ' ::: orthology_confidence: ' + bm['orthology_confidence'].astype(str) +
        ' ::: perc_identity: '        + bm['perc_id'].astype(str) +
        ' ::: orthology_type: '       + bm['orthology_type'].astype(str)
    )

    # Drop rows with no human symbol
    bm = bm[bm['human_symbol'].notna()].copy()

    # Uppercase key for matching
    bm['input_gene_upper'] = bm['input_gene'].astype(str).str.upper()

    # Drop exact duplicates (same source gene → same human symbol listed twice)
    bm = bm.drop_duplicates(subset=['input_gene_upper', 'human_symbol'], keep='first')

    # Group into lists per source gene
    gene2orthos = bm.groupby('input_gene_upper')['human_symbol'].apply(list).to_dict()
    gene2descs  = bm.groupby('input_gene_upper')['human_description'].apply(list).to_dict()
    gene2infos  = bm.groupby('input_gene_upper')['ortholog_info'].apply(list).to_dict()

    return gene2orthos, gene2descs, gene2infos


# ═══════════════════════════════════════════════════════════════════════════════
# Helper — explode ONE side (head OR tail) into ortholog lists
# ═══════════════════════════════════════════════════════════════════════════════
def explode_side(df, side, gene2orthos, gene2descs, gene2infos, original_species):
    """
    For each row:
      - gene + mapped     → lists of [orthologs], [descriptions], [infos]
      - gene + NOT mapped → [original_value], [pd.NA], [pd.NA]
      - not a gene        → [original_value], [pd.NA], [pd.NA]

    Explodes all three list columns together (aligned), so each ortholog
    gets its own description and ortholog_info on the same row.

    Sets {side}_species = 'Homo sapiens' only for mapped gene rows.
    """
    type_col       = f'{side}_type'
    species_col    = f'{side}_species'
    detail_col     = f'{side}_detail_name'
    info_col       = f'{side}_ortholog_info'

    # Temp list columns
    list_col_node  = f'_{side}_orthos'
    list_col_desc  = f'_{side}_descs'
    list_col_info  = f'_{side}_infos'

    is_gene = df[type_col].astype(str).str.strip().str.lower() == 'gene'

    # Default: single-element lists (no explosion)
    df[list_col_node] = df[side].apply(lambda v: [v])
    df[list_col_desc] = [[pd.NA]] * len(df)
    df[list_col_info] = [[pd.NA]] * len(df)

    # For gene rows: look up lists; fall back to [original] if no mapping
    def lookup_node(val):
        return gene2orthos.get(str(val).upper(), [val])

    def lookup_desc(val):
        return gene2descs.get(str(val).upper(), [pd.NA])

    def lookup_info(val):
        return gene2infos.get(str(val).upper(), [pd.NA])

    df.loc[is_gene, list_col_node] = df.loc[is_gene, side].apply(lookup_node)
    df.loc[is_gene, list_col_desc] = df.loc[is_gene, side].apply(lookup_desc)
    df.loc[is_gene, list_col_info] = df.loc[is_gene, side].apply(lookup_info)

    # Track which gene rows actually mapped (for species labelling)
    mapped_keys = set(gene2orthos.keys())
    was_mapped  = is_gene & df[side].astype(str).str.upper().isin(mapped_keys)
    df['_was_mapped_' + side] = was_mapped

    # ── Explode all three list cols together (aligned) ────────────────────────
    df = df.explode([list_col_node, list_col_desc, list_col_info], ignore_index=True)

    # Write back from temp cols
    df[side] = df[list_col_node]

    if detail_col not in df.columns:
        df[detail_col] = pd.NA
    df.loc[df['_was_mapped_' + side], detail_col] = df.loc[df['_was_mapped_' + side], list_col_desc]

    if info_col not in df.columns:
        df[info_col] = pd.NA
    df.loc[df['_was_mapped_' + side], info_col] = df.loc[df['_was_mapped_' + side], list_col_info]

    # Species
    if species_col not in df.columns:
        df[species_col] = original_species
    df.loc[df['_was_mapped_' + side], species_col] = 'Homo sapiens'

    # Drop temp list cols
    df.drop(columns=[list_col_node, list_col_desc, list_col_info], inplace=True)

    return df


# ── I/O helpers ───────────────────────────────────────────────────────────────
def get_output_path(src_path):
    root, _ = os.path.splitext(src_path)
    return f"{root}_ortho_1_to_one2one_plus_one2many.csv"

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
    print(f"  {species}   ({original_species})   [1-to-MANY]")
    print(f"{'═'*70}")

    if not os.path.exists(biomart_path):
        print(f"  ❌  BioMart file not found: {biomart_path}  — skipping")
        continue

    gene2orthos, gene2descs, gene2infos = build_ortholog_dicts_121_12M(biomart_path, species)
    multi = sum(1 for v in gene2orthos.values() if len(v) > 1)
    print(f"  Ortholog map: {len(gene2orthos):,} genes "
          f"({multi:,} have >1 ortholog → will explode)\n")

    # Collect triple files — one level deep only
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
                tqdm.write(f"    ⚠️  no type cols, skipped: {os.path.basename(src)}")
                continue

            head_has_gene = (df['head_type'].astype(str).str.strip().str.lower() == 'gene').any()
            tail_has_gene = (df['tail_type'].astype(str).str.strip().str.lower() == 'gene').any()

            rows_before = len(df)

            # No gene nodes → save as-is with species cols added
            if not head_has_gene and not tail_has_gene:
                for col, default in [
                    ('head_species',       original_species),
                    ('tail_species',       original_species),
                    ('head_ortholog_info', pd.NA),
                    ('tail_ortholog_info', pd.NA),
                ]:
                    if col not in df.columns:
                        df[col] = default
                out = get_output_path(src)
                save_file(df, out)
                overall_log.append({
                    'species'    : species,
                    'file'       : os.path.relpath(src, species_dir),
                    'rows_before': rows_before,
                    'rows_after' : rows_before,
                    'expanded_by': 0,
                    'output'     : os.path.basename(out),
                })
                continue

            # ── Explode head first, then tail (gives N×M cartesian product) ──
            if head_has_gene:
                df = explode_side(df, 'head', gene2orthos, gene2descs, gene2infos, original_species)
            else:
                df['head_species']       = original_species
                df['head_ortholog_info'] = pd.NA

            if tail_has_gene:
                df = explode_side(df, 'tail', gene2orthos, gene2descs, gene2infos, original_species)
            else:
                df['tail_species']       = original_species
                df['tail_ortholog_info'] = pd.NA

            # Drop internal flag columns
            df.drop(columns=[c for c in df.columns if c.startswith('_was_mapped_')],
                    inplace=True, errors='ignore')

            rows_after = len(df)
            out = get_output_path(src)
            save_file(df, out)

            overall_log.append({
                'species'    : species,
                'file'       : os.path.relpath(src, species_dir),
                'rows_before': rows_before,
                'rows_after' : rows_after,
                'expanded_by': rows_after - rows_before,
                'output'     : os.path.basename(out),
            })

        except Exception as e:
            tqdm.write(f"    ❌  {os.path.basename(src)}: {e}")
            overall_log.append({
                'species': species, 'file': os.path.relpath(src, species_dir),
                'rows_before': 0, 'rows_after': 0, 'expanded_by': 0,
                'output': f'ERROR: {e}',
            })

# ── Final log ─────────────────────────────────────────────────────────────────
log_df   = pd.DataFrame(overall_log)
log_path = os.path.join(ROOT, '_ORTHOLOG_MAPPING_LOG_1_to_many_BioMart.csv')
log_df.to_csv(log_path, index=False)

print(f"\n{'═'*70}")
print(f"  DONE (1-to-many) — processed {len(log_df)} files")
print(f"  Log saved → {log_path}")
print(f"{'═'*70}")
print(log_df.to_string(index=False))