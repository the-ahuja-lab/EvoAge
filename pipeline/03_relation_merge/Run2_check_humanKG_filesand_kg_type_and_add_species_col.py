import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Base path ─────────────────────────────────────────────────────────────────
BASE = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised'

# ── Collect every csv + parquet, but SKIP the OTHER_SPECIES subtree ───────────
all_files = (
    glob.glob(os.path.join(BASE, '**/*.csv'),     recursive=True) +
    glob.glob(os.path.join(BASE, '**/*.parquet'), recursive=True)
)
all_files = [
    f for f in all_files
    if 'OTHER_SPECIES' not in f
    and '.ipynb_checkpoints' not in f
]
all_files = sorted(all_files)

print(f"Found {len(all_files)} files (OTHER_SPECIES excluded)\n")

# ── Value to write into the new species columns ───────────────────────────────
SPECIES_VALUE = 'Homo sapiens'

# ── Helper: does this file have a kg_type column? (cheap schema/header check) ──
def find_kg_type_col(path):
    """Return the actual kg_type column name (case-insensitive) or None."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.parquet':
        import pyarrow.parquet as pq
        names = pq.read_schema(path).names
    else:
        names = pd.read_csv(path, nrows=0).columns
    match = [c for c in names if c.lower() == 'kg_type']
    return match[0] if match else None

# ── Helper: process one file ──────────────────────────────────────────────────
def process_file(path):
    """
    Returns (has_kg_type, kg_type_values, added_species_cols)

    • If kg_type exists:
        - read full file
        - add head_species / tail_species = 'Homo sapiens' (only if missing)
        - save back in place (same format)
    • If kg_type missing: do nothing, just report.

    Reads kg_type cheaply first; only loads the full file when columns must be added.
    """
    ext = os.path.splitext(path)[1].lower()
    kg_col = find_kg_type_col(path)

    # ── No kg_type → just report, don't touch the file ────────────────────────
    if kg_col is None:
        return (False, None, False)

    # ── Has kg_type → load FULL file so we can add columns and re-save ─────────
    if ext == '.parquet':
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, low_memory=False)

    # Unique kg_type values for the report
    vals = sorted(str(v) for v in df[kg_col].dropna().unique())

    # Add species columns only if not already present (avoid overwriting)
    added = False
    if 'head_species' not in df.columns:
        df['head_species'] = SPECIES_VALUE
        added = True
    if 'tail_species' not in df.columns:
        df['tail_species'] = SPECIES_VALUE
        added = True

    # Save back in place only if we actually added something
    if added:
        if ext == '.parquet':
            df.to_parquet(path, index=False)
        else:
            df.to_csv(path, index=False)

    return (True, vals, added)

# ── Main loop ─────────────────────────────────────────────────────────────────
rows = []
for path in tqdm(all_files, desc="Checking kg_type", unit="file",
                 bar_format="{l_bar}{bar:30}{r_bar}"):
    rel = os.path.relpath(path, BASE)
    try:
        has_col, values, added = process_file(path)
        if has_col:
            tag = "added species cols" if added else "species cols already present"
            tqdm.write(f"✅  {rel}\n        kg_type values: {values}\n        → {tag}")
            rows.append({'file': rel, 'has_kg_type': True,
                         'kg_type_values': ' | '.join(values) if values else '(empty)',
                         'species_cols_added': added})
        else:
            tqdm.write(f"❌  {rel}\n        → NO 'kg_type' column in this file")
            rows.append({'file': rel, 'has_kg_type': False,
                         'kg_type_values': '', 'species_cols_added': False})
    except Exception as e:
        tqdm.write(f"⚠️   {rel}: {e}")
        rows.append({'file': rel, 'has_kg_type': 'ERROR',
                     'kg_type_values': str(e), 'species_cols_added': False})

# ── Summary table + save ──────────────────────────────────────────────────────
result_df = pd.DataFrame(rows)
out_path = os.path.join(BASE, '_KG_TYPE_CHECK.csv')
result_df.to_csv(out_path, index=False)

print(f"\n{'═'*70}")
print(f"  Total files            : {len(result_df)}")
print(f"  With kg_type           : {(result_df['has_kg_type'] == True).sum()}")
print(f"  Without kg_type        : {(result_df['has_kg_type'] == False).sum()}")
print(f"  Species cols added     : {result_df['species_cols_added'].sum()}")
print(f"  Errors                 : {(result_df['has_kg_type'] == 'ERROR').sum()}")
print(f"  Report saved           : {out_path}")
print(f"{'═'*70}")