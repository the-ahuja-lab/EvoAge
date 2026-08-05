"""
# nohup python split_1to1_kg_by_type_otherspecies.py > split_1to1_kg_by_type_otherspecies.log &
═══════════════════════════════════════════════════════════════════════════════
 OTHER SPECIES — KG SPLIT into Aging_specific & Biomedical
═══════════════════════════════════════════════════════════════════════════════
 For each species:
   • Reads only  *_ortho_1_to_1.csv  files
   • Splits rows by kg_type into Aging / Biomedical (same logic as Human)
   • Saves as CSV into:
       Aging_specific/{Species}/...  (mirroring relation subfolder name)
       Biomedical/{Species}/...
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import glob
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge'
SPECIES_ROOT = os.path.join(ROOT, 'generalised', 'OTHER_SPECIES')
AGING_BASE   = os.path.join(ROOT, 'Aging_specific')
BIOMED_BASE  = os.path.join(ROOT, 'Biomedical')

# ── Species config ────────────────────────────────────────────────────────────
SPECIES = {
    'Celegans'   : 'Celegans',
    'Drosophila' : 'Drosophila',
    'Mouse'      : 'Mouse',
    'Yeast'      : 'Yeast',
    'Zebrafish'  : 'Zebrafish',
}

KG_COL = 'kg_type'

# ── Classify kg_type value (same logic as Human split) ────────────────────────
def classify(val):
    s = str(val).strip().lower()
    is_aging      = 'aging' in s
    is_biomedical = ('generalised' in s) or (s == '') or (not is_aging)
    return is_aging, is_biomedical

# ── Helper ────────────────────────────────────────────────────────────────────
def find_kg_col(df):
    match = [c for c in df.columns if c.lower() == KG_COL]
    return match[0] if match else None

# ── Main loop ─────────────────────────────────────────────────────────────────
overall_log = []

for species, folder in SPECIES.items():

    species_dir = os.path.join(SPECIES_ROOT, folder)
    print(f"\n{'═'*70}")
    print(f"  {species}")
    print(f"{'═'*70}")

    # ── Collect ortho_1_to_1 files ────────────────────────────────────────────
    files = sorted([
        f for f in glob.glob(os.path.join(species_dir, '**/*_ortho_1_to_1.csv'), recursive=True)
        if '.ipynb_checkpoints' not in f
    ])
    print(f"  ortho_1_to_1 files found: {len(files)}")

    if not files:
        print(f"  ❌  No files found — skipping")
        continue

    # ── Process each file ─────────────────────────────────────────────────────
    for src in tqdm(files, desc=f"  {species}", unit="file",
                    bar_format="{l_bar}{bar:25}{r_bar}"):
        try:
            df = pd.read_csv(src, low_memory=False)
            kg_col = find_kg_col(df)

            rel_subfolder = os.path.basename(os.path.dirname(src))
            src_filename  = os.path.basename(src)

            if kg_col is None:
                tqdm.write(f"  ⏭️  no kg_type: {src_filename} — skipped")
                overall_log.append({
                    'species': species, 'file': f"{rel_subfolder}/{src_filename}",
                    'total_rows': len(df), 'aging_rows': 0,
                    'biomedical_rows': 0, 'status': 'no kg_type'
                })
                continue

            # ── Split rows ────────────────────────────────────────────────────
            aging_mask      = df[kg_col].apply(lambda v: classify(v)[0])
            biomedical_mask = df[kg_col].apply(lambda v: classify(v)[1])

            aging_df      = df[aging_mask].copy()
            biomedical_df = df[biomedical_mask].copy()

            n_aging = n_bio = 0

            # ── Save Aging ────────────────────────────────────────────────────
            if len(aging_df):
                out_dir = os.path.join(AGING_BASE, species, rel_subfolder)
                os.makedirs(out_dir, exist_ok=True)
                aging_df.to_csv(os.path.join(out_dir, src_filename), index=False)
                n_aging = len(aging_df)

            # ── Save Biomedical ───────────────────────────────────────────────
            if len(biomedical_df):
                out_dir = os.path.join(BIOMED_BASE, species, rel_subfolder)
                os.makedirs(out_dir, exist_ok=True)
                biomedical_df.to_csv(os.path.join(out_dir, src_filename), index=False)
                n_bio = len(biomedical_df)

            tqdm.write(
                f"  ✅  {rel_subfolder}/{src_filename}  "
                f"aging={n_aging:>8,}  biomedical={n_bio:>8,}"
            )
            overall_log.append({
                'species': species, 'file': f"{rel_subfolder}/{src_filename}",
                'total_rows': len(df), 'aging_rows': n_aging,
                'biomedical_rows': n_bio, 'status': 'ok'
            })

        except Exception as e:
            tqdm.write(f"  ❌  {os.path.basename(src)}: {e}")
            overall_log.append({
                'species': species, 'file': os.path.basename(src),
                'total_rows': 0, 'aging_rows': 0,
                'biomedical_rows': 0, 'status': f'ERROR: {e}'
            })

# ── Save log ──────────────────────────────────────════════════════════════────
log_df = pd.DataFrame(overall_log)
log_path = os.path.join(ROOT, '_OTHER_SPECIES_KG_SPLIT_LOG_1to1.csv')
log_df.to_csv(log_path, index=False)

print(f"\n{'═'*70}")
print(f"  DONE")
print(f"  Files processed   : {len(log_df)}")
print(f"  Total aging rows  : {log_df['aging_rows'].sum():,}")
print(f"  Total biomed rows : {log_df['biomedical_rows'].sum():,}")
print(f"  Aging output      : {AGING_BASE}/{{Species}}/")
print(f"  Biomedical output : {BIOMED_BASE}/{{Species}}/")
print(f"  Log saved         : {log_path}")
print(f"{'═'*70}")
print(log_df.to_string(index=False))