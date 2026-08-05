"""
═══════════════════════════════════════════════════════════════════════════════
 LABEL STANDARDIZATION — fix ID-source typos across all relation-wise files
═══════════════════════════════════════════════════════════════════════════════

 Edits these columns IN PLACE:  head_id_is, tail_id_is, relation
 (only the exact-match values in the MAPPING below are changed; everything
  else is left untouched).

 Safe by design:
   • Only replaces values that EXACTLY equal a key in the mapping
     (so 'Pubchem' → 'PubChem' won't accidentally touch 'Pubchem_Something').
   • Reports per-file how many cells changed.
   • Optionally make a .bak copy before overwriting (BACKUP = True).
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import glob
import shutil
import warnings
import pandas as pd
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Path config ───────────────────────────────────────────────────────────────
ROOT = '/storage/Arushi/090526_EvoAge/kg_formation/processed_data_relation_wise_merge/generalised'

# Set True to scan OTHER_SPECIES as well; False to skip it (Human only)
INCLUDE_OTHER_SPECIES = False

# Set True to write a .bak copy of each modified file before overwriting
BACKUP = False

# ── Columns to clean ──────────────────────────────────────────────────────────
ID_COLS       = ['head_id_is', 'tail_id_is']
RELATION_COLS = ['relation']
# RELATION_COLS = []


# ═══════════════════════════════════════════════════════════════════════════════
# MAPPING — edit / add pairs here.  'wrong value'  :  'correct value'
# ═══════════════════════════════════════════════════════════════════════════════
ID_MAPPING = {
    # ── PubChem variants → Pubchem ──────────────────────────────────────────
    'PubChem'     : 'Pubchem',
    'Pubchem_ID'  : 'Pubchem',
    'PubChem_ID'  : 'Pubchem',

    # ── GO variants → Quick_GO ──────────────────────────────────────────────
    'GO'          : 'Quick_GO',
    'QuickGO'     : 'Quick_GO',
    'Quick_Go'    : 'Quick_GO',

    # ── UBERON variants → UBERON_ID ─────────────────────────────────────────
    'UBERON'      : 'UBERON_ID',

    # ── DOID variants → DOID ────────────────────────────────────────────────
    'DO_ID'       : 'DOID',
    'DOID_ID'     : 'DOID',

    # ── MESH variants → MESH ────────────────────────────────────────────────
    'MESH_ID'     : 'MESH',

    # ── HPO variants → HPO_ID ───────────────────────────────────────────────
    'HPO'         : 'HPO_ID',
    'HP'          : 'HPO_ID',

    # ── Uniprot variants → Uniprot_ID ───────────────────────────────────────
    'UniProt'     : 'Uniprot_ID',
    'Uniprot'     : 'Uniprot_ID',

    # ── Reactome variants → Reactome_ID ─────────────────────────────────────
    'Reactome'    : 'Reactome_ID',

    # ── NCBI variants → NCBI_ID ─────────────────────────────────────────────
    'NCBI'        : 'NCBI_ID',

    # ── SGD typo → fixed ────────────────────────────────────────────────────
    'SGD_SysematicName' : 'SGD_SystematicName',

    # ── empty string → leave as-is is handled separately; uncomment to blank-fix
    # '' : 'Unknown',
}

# Relation-value casing typos → canonical
RELATION_MAPPING = {
    'Gene_inhibits_BiologicalProcess' : 'Gene_Inhibits_BiologicalProcess',
    'Gene_promotes_BiologicalProcess' : 'Gene_Promotes_BiologicalProcess',
    'Gene_Anatomy'                    : 'Gene_AnatomicalEntity',
    'Anatomy_CellularComponent'       : 'AnatomicalEntity_CellularComponent',
}

# ── Collect files ─────────────────────────────────────────────────────────────
all_files = (
    glob.glob(os.path.join(ROOT, '**/*.csv'),     recursive=True) +
    glob.glob(os.path.join(ROOT, '**/*.parquet'), recursive=True)
)
all_files = [
    f for f in all_files
    if '.ipynb_checkpoints' not in f
    and not os.path.basename(f).startswith('_')         # skip _SUMMARY etc.
]
if not INCLUDE_OTHER_SPECIES:
    all_files = [f for f in all_files if 'OTHER_SPECIES' not in f]

all_files = sorted(all_files)
print(f"Scanning {len(all_files)} files "
      f"({'incl.' if INCLUDE_OTHER_SPECIES else 'excl.'} OTHER_SPECIES)\n")

# ── IO helpers ────────────────────────────────────────────────────────────────
def load_file(path):
    return pd.read_parquet(path) if path.lower().endswith('.parquet') \
           else pd.read_csv(path, low_memory=False)

def save_file(df, path):
    if path.lower().endswith('.parquet'):
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)

def find_col(df, name):
    """Case-insensitive column lookup."""
    match = [c for c in df.columns if c.lower() == name.lower()]
    return match[0] if match else None

# ── Main loop ─────────────────────────────────────────────────────────────────
log = []
for path in tqdm(all_files, desc="Cleaning", unit="file",
                 bar_format="{l_bar}{bar:30}{r_bar}"):
    rel = os.path.relpath(path, ROOT)
    try:
        df = load_file(path)
        total_changes = 0
        change_detail = []

        # ── Fix ID-source columns ─────────────────────────────────────────────
        for col_name in ID_COLS:
            col = find_col(df, col_name)
            if col is None:
                continue
            for wrong, correct in ID_MAPPING.items():
                mask = df[col] == wrong
                n = int(mask.sum())
                if n:
                    df.loc[mask, col] = correct
                    total_changes += n
                    change_detail.append(f"{col}: {wrong}->{correct} ({n})")

        # ── Fix relation casing/vocab ─────────────────────────────────────────
        for col_name in RELATION_COLS:
            col = find_col(df, col_name)
            if col is None:
                continue
            for wrong, correct in RELATION_MAPPING.items():
                mask = df[col] == wrong
                n = int(mask.sum())
                if n:
                    df.loc[mask, col] = correct
                    total_changes += n
                    change_detail.append(f"{col}: {wrong}->{correct} ({n})")

        # ── Save only if something changed ────────────────────────────────────
        if total_changes:
            if BACKUP:
                shutil.copy2(path, path + '.bak')
            save_file(df, path)
            tqdm.write(f"✏️   {rel}\n        {'; '.join(change_detail)}")
            log.append({'file': rel, 'cells_changed': total_changes,
                        'detail': '; '.join(change_detail)})
        else:
            log.append({'file': rel, 'cells_changed': 0, 'detail': ''})

    except Exception as e:
        tqdm.write(f"❌  {rel}: {e}")
        log.append({'file': rel, 'cells_changed': -1, 'detail': f'ERROR: {e}'})

# ── Save log ──────────────────────────────────────────────────────────────────
log_df = pd.DataFrame(log)
log_path = os.path.join(ROOT, '_LABEL_CLEANUP_LOG.csv')
log_df.to_csv(log_path, index=False)

changed = log_df[log_df['cells_changed'] > 0]
print(f"\n{'═'*70}")
print(f"  Files scanned   : {len(log_df)}")
print(f"  Files modified  : {len(changed)}")
print(f"  Total cells fixed: {log_df[log_df['cells_changed']>0]['cells_changed'].sum():,}")
print(f"  Backups made    : {'yes (.bak)' if BACKUP else 'no'}")
print(f"  Log saved       : {log_path}")
print(f"{'═'*70}")