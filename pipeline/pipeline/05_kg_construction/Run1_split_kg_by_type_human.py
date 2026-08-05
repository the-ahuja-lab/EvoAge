import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT      = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge'
SRC_BASE  = os.path.join(ROOT, 'generalised')
AGING_BASE      = os.path.join(ROOT, 'Aging_specific', 'Human')
BIOMEDICAL_BASE = os.path.join(ROOT, 'Biomedical',     'Human')

KG_COL = 'kg_type'

# ── Collect all files (skip OTHER_SPECIES, reports, checkpoints) ──────────────
all_files = (
    glob.glob(os.path.join(SRC_BASE, '**/*.csv'),     recursive=True) +
    glob.glob(os.path.join(SRC_BASE, '**/*.parquet'), recursive=True)
)
all_files = [
    f for f in all_files
    if 'OTHER_SPECIES' not in f
    and '.ipynb_checkpoints' not in f
    and not os.path.basename(f).startswith('_')        # skip _KG_TYPE_CHECK.csv etc.
]
all_files = sorted(all_files)
print(f"Found {len(all_files)} files to split (OTHER_SPECIES excluded)\n")
print(all_files)
# ── Helpers ───────────────────────────────────────────────────────────────────
def find_kg_col(df):
    """Return actual kg_type column name (case-insensitive) or None."""
    match = [c for c in df.columns if c.lower() == KG_COL]
    return match[0] if match else None

def load_file(path):
    return pd.read_parquet(path) if path.lower().endswith('.parquet') \
           else pd.read_csv(path, low_memory=False)

def save_parquet(df, rel_path, base_dir):
    """
    Save df as PARQUET under base_dir, mirroring rel_path but forcing .parquet
    extension (so a source .csv becomes .parquet on output).
    """
    rel_parquet = os.path.splitext(rel_path)[0] + '.parquet'
    out_path = os.path.join(base_dir, rel_parquet)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_parquet(out_path, index=False)
    return out_path

def classify(val):
    """
    Decide which buckets a kg_type value belongs to.
    Returns (is_aging, is_biomedical).
      • 'aging'              → aging only
      • 'generalised'        → biomedical only  (case-insensitive)
      • 'aging::generalised' → BOTH
      • blank / other        → biomedical (default)
    """
    s = str(val).strip().lower()
    is_aging       = 'aging' in s          # matches 'aging' and 'aging::generalised'
    is_biomedical  = ('generalised' in s) or (s == '') or (not is_aging)
    return is_aging, is_biomedical

# ── Main loop ─────────────────────────────────────────────────────────────────
log = []
for src in tqdm(all_files, desc="Splitting", unit="file",
                bar_format="{l_bar}{bar:30}{r_bar}"):
    rel = os.path.relpath(src, SRC_BASE)        # e.g. MUTATION_GENE/ALL_MUTATION_GENE.csv
    try:
        df = load_file(src)
        kg_col = find_kg_col(df)

        if kg_col is None:
            tqdm.write(f"⏭️   {rel}: no kg_type column — skipped")
            log.append({'file': rel, 'aging_rows': 0, 'biomedical_rows': 0,
                        'status': 'no kg_type'})
            continue

        # Build per-row masks
        aging_mask      = df[kg_col].apply(lambda v: classify(v)[0])
        biomedical_mask = df[kg_col].apply(lambda v: classify(v)[1])

        aging_df      = df[aging_mask].copy()
        biomedical_df = df[biomedical_mask].copy()

        # Save into mirrored structure (always as .parquet)
        n_aging = n_bio = 0
        if len(aging_df):
            save_parquet(aging_df, rel, AGING_BASE)
            n_aging = len(aging_df)
        if len(biomedical_df):
            save_parquet(biomedical_df, rel, BIOMEDICAL_BASE)
            n_bio = len(biomedical_df)

        tqdm.write(f"✅  {rel:65s}  aging={n_aging:>8,}  biomedical={n_bio:>8,}")
        log.append({'file': rel, 'total_rows': len(df),
                    'aging_rows': n_aging, 'biomedical_rows': n_bio,
                    'status': 'ok'})

    except Exception as e:
        tqdm.write(f"❌  {rel}: {e}")
        log.append({'file': rel, 'aging_rows': 0, 'biomedical_rows': 0,
                    'status': f'ERROR: {e}'})

# ── Save log ──────────────────────────────────────────────────────────────────
log_df = pd.DataFrame(log)
log_path = os.path.join(ROOT, 'Human_KG_SPLIT_LOG.csv')
log_df.to_csv(log_path, index=False)

print(f"\n{'═'*70}")
print(f"  Files processed   : {len(log_df)}")
print(f"  Total aging rows  : {log_df['aging_rows'].sum():,}")
print(f"  Total biomed rows : {log_df['biomedical_rows'].sum():,}")
print(f"  Aging output      : {AGING_BASE}")
print(f"  Biomedical output : {BIOMEDICAL_BASE}")
print(f"  Log saved         : {log_path}")
print(f"{'═'*70}")