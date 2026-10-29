import os
import re
import shutil
import tempfile
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

from dglke.models.infer import ScoreInfer
from dglke.utils import load_model_config, load_raw_triplet_data

# ============================= CONFIG =============================
MODEL_PATH    = "/path/to/EvoAge/kg_formation/training_3/EvoAge_121_12M/model_output/Rescal/RESCAL_Evoage_121_12M_1"
ENT_DICT_PATH = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/entities_final.dict"
REL_DICT_PATH = "/path/to/EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/relation_final.dict"

INPUT_DIR    = "/path/to/cutoff/output/relation_samples_ALLGT"
MANIFEST_CSV = "/path/to/cutoff/output/relation_samples_ALLGT/gt_manifest.csv"
OUTPUT_DIR   = "/path/to/cutoff/output/relation_samples_ALLGT_output"
LOG_DIR      = "/path/to/cutoff/output/logs"

DEVICE = 0
SFUNC  = "logsigmoid"
SKIP_EXISTING = True
# =================================================================

BATCH_SIZE        = 500_000
MAX_SCORE_PER_REL = None

def _as_path(value, name: str) -> Path:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise RuntimeError(f"{name} is not set (empty/None).")
    return value if isinstance(value, Path) else Path(value)


MODEL_PATH    = _as_path(MODEL_PATH, "MODEL_PATH")
ENT_DICT_PATH = _as_path(ENT_DICT_PATH, "ENT_DICT_PATH")
REL_DICT_PATH = _as_path(REL_DICT_PATH, "REL_DICT_PATH")
INPUT_DIR     = _as_path(INPUT_DIR, "INPUT_DIR")
MANIFEST_CSV  = _as_path(MANIFEST_CSV, "MANIFEST_CSV")
OUTPUT_DIR    = _as_path(OUTPUT_DIR, "OUTPUT_DIR")
LOG_DIR       = _as_path(LOG_DIR, "LOG_DIR")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

errors = []
if not MODEL_PATH.is_dir():
    errors.append(f"MODEL_PATH not a directory: {MODEL_PATH}")
if not INPUT_DIR.is_dir():
    errors.append(f"INPUT_DIR missing: {INPUT_DIR}")
if not MANIFEST_CSV.is_file():
    errors.append(f"MANIFEST_CSV missing: {MANIFEST_CSV}")
if not (MODEL_PATH / "config.json").is_file():
    errors.append(f"Missing config.json at {MODEL_PATH / 'config.json'}")
for name, p in [("ENT_DICT_PATH", ENT_DICT_PATH), ("REL_DICT_PATH", REL_DICT_PATH)]:
    if not p.is_file():
        errors.append(f"{name} not a file: {p}")
if errors:
    raise FileNotFoundError(" | ".join(errors))

logging.basicConfig(
    filename=str(Path(LOG_DIR) / "LOG_inference_ALLGT.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def non_empty_line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _load_entity_keys(emap_path: Path) -> set:
    """Entity NAMES = second field of 'id<TAB>name', even when numeric
    (PubChem CIDs like 5281243). Never infer name-vs-id by digit-ness."""
    keys = set()
    with open(emap_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                keys.add(parts[1])   # name, verbatim
    return keys


# ---- load model + entity keys once ----
try:
    config = load_model_config(str(MODEL_PATH / "config.json"))
except Exception as e:
    raise RuntimeError(f"Failed to load model config: {e!s}")

try:
    infer = ScoreInfer(device=DEVICE, config=config, model_path=MODEL_PATH, sfunc=SFUNC)
    infer.load_model()
except Exception as e:
    logging.info("Loading on GPU failed: %s", str(e))
    raise RuntimeError(f"Cannot initialize inference model: {e!s}")

ENTITY_KEYS = _load_entity_keys(ENT_DICT_PATH)
logging.info("loaded %d entity keys for pre-filtering", len(ENTITY_KEYS))
print(f"Loaded {len(ENTITY_KEYS):,} entity keys for pre-filtering")


def score_gt(relation: str, idx: int) -> bool:
    rel_dir  = INPUT_DIR / relation
    head_f   = rel_dir / f"{relation}_GT_head.list"
    rel_f    = rel_dir / f"{relation}_GT_rel.list"
    tail_f   = rel_dir / f"{relation}_GT_tail.list"
    out_pkl  = OUTPUT_DIR / f"{relation}_GT_SCORE.pkl"
    tmp_pkl  = OUTPUT_DIR / f"{relation}_GT_SCORE.pkl.tmp"

    if SKIP_EXISTING and out_pkl.is_file():
        tqdm.write(f"  ⏭  {relation}: already scored, skipping")
        return False

    missing = [str(p) for p in (head_f, rel_f, tail_f) if not p.is_file()]
    if missing:
        logging.info("Missing GT files %s in %s (idx %d)", missing, relation, idx)
        tqdm.write(f"  ⚠  {relation}: missing files {missing}")
        return False

    nh, nr, nt = (non_empty_line_count(head_f),
                  non_empty_line_count(rel_f),
                  non_empty_line_count(tail_f))
    if nh == 0 or not (nh == nr == nt):
        logging.info("Row mismatch/empty h=%d r=%d t=%d in %s (idx %d)",
                     nh, nr, nt, relation, idx)
        tqdm.write(f"  ⚠  {relation}: row mismatch/empty (h={nh} r={nr} t={nt})")
        return False

    def _read_lines(pth):
        with open(pth, "r", encoding="utf-8") as f:
            return [ln.rstrip("\n") for ln in f]

    _ws = re.compile(r"\s+")

    def _resolve(name):
        """verbatim -> normalized -> None"""
        if name in ENTITY_KEYS:
            return name
        n = _ws.sub(" ", name).strip()
        return n if n in ENTITY_KEYS else None

    H = _read_lines(head_f); R = _read_lines(rel_f); T = _read_lines(tail_f)
    keep_h, keep_r, keep_t, n_dropped, n_normalized = [], [], [], 0, 0
    for h, r, t in zip(H, R, T):
        hn, tn = _resolve(h), _resolve(t)
        if hn is not None and tn is not None:
            if hn != h or tn != t:
                n_normalized += 1
            keep_h.append(hn); keep_r.append(r.strip()); keep_t.append(tn)
        else:
            n_dropped += 1
    if n_normalized:
        logging.info("%s: resolved %d/%d triples only after whitespace-normalize",
                     relation, n_normalized, len(H))
        tqdm.write(f"  ℹ  {relation}: normalized {n_normalized:,} dirty names")
    if n_dropped:
        logging.info("%s: dropped %d/%d triples with unresolved head/tail names",
                     relation, n_dropped, len(H))
        tqdm.write(f"  ⚠  {relation}: skipped {n_dropped:,} unresolved-name triples "
                   f"({100.0*n_dropped/max(len(H),1):.2f}%)")
    if not keep_h:
        tqdm.write(f"  ⚠  {relation}: no resolvable triples, skipping")
        return False

    tmpdir = Path(tempfile.mkdtemp(prefix=f"{relation}_filt_"))
    try:
        fh_f = tmpdir / "head.list"; fr_f = tmpdir / "rel.list"; ft_f = tmpdir / "tail.list"
        fh_f.write_text("\n".join(keep_h) + "\n")
        fr_f.write_text("\n".join(keep_r) + "\n")
        ft_f.write_text("\n".join(keep_t) + "\n")
        del H, R, T, keep_h, keep_r, keep_t

        # ---- load ids from the FILTERED files ----
        try:
            head_ids, rel_ids, tail_ids, id2ent, id2rel = load_raw_triplet_data(
                head_f=str(fh_f), rel_f=str(fr_f), tail_f=str(ft_f),
                emap_f=str(ENT_DICT_PATH), rmap_f=str(REL_DICT_PATH),
            )
        except Exception as e:
            logging.info("load_raw_triplet_data error: %s in %s (idx %d)", str(e), relation, idx)
            raise RuntimeError(f"load_raw_triplet_data failed for {relation}: {e!s}")

        head_ids = np.asarray(head_ids)
        rel_ids  = np.asarray(rel_ids)
        tail_ids = np.asarray(tail_ids)
        n_total  = len(head_ids)

        # ---- optional cap (None = score all) ----
        if MAX_SCORE_PER_REL is not None and n_total > MAX_SCORE_PER_REL:
            rng = np.random.default_rng(42)
            sel = rng.choice(n_total, size=MAX_SCORE_PER_REL, replace=False)
            sel.sort()
            head_ids, rel_ids, tail_ids = head_ids[sel], rel_ids[sel], tail_ids[sel]
            n_used = MAX_SCORE_PER_REL
            cap_note = f"sampled {MAX_SCORE_PER_REL:,} of {n_total:,}"
        else:
            n_used = n_total
            cap_note = f"all {n_total:,}"

        # ---- score in batches ----
        n_batches = -(-n_used // BATCH_SIZE)
        frames = []
        try:
            for b in range(n_batches):
                s = b * BATCH_SIZE
                e = min((b + 1) * BATCH_SIZE, n_used)
                h_b = head_ids[s:e].tolist()
                r_b = rel_ids[s:e].tolist()
                t_b = tail_ids[s:e].tolist()

                raw = infer.topK_no_sort(head=h_b, rel=r_b, tail=t_b,
                                         exec_mode="triplet_wise")
                rows = [(int(h), int(r), int(t), float(sc))
                        for h_a, r_a, t_a, s_a in raw
                        for h, r, t, sc in zip(h_a, r_a, t_a, s_a)]
                frames.append(pd.DataFrame(rows, columns=["head", "rel", "tail", "score"]))

                if n_batches > 1:
                    tqdm.write(f"     {relation}: batch {b+1}/{n_batches} ({e:,}/{n_used:,})")
        except Exception as e:
            logging.info("scoring error: %s in %s (idx %d)", str(e), relation, idx)
            raise RuntimeError(f"scoring failed for {relation}: {e!s}")

        try:
            df_ids = pd.concat(frames, ignore_index=True)
            del frames
            df = df_ids.assign(
                head=df_ids["head"].map(lambda x: id2ent[int(x)]),
                rel =df_ids["rel"].map(lambda x: id2rel[int(x)]),
                tail=df_ids["tail"].map(lambda x: id2ent[int(x)]),
            )
            df.to_pickle(tmp_pkl)
            tmp_pkl.replace(out_pkl)
            logging.info("GT scored: %s idx=%d rows=%d (%s, dropped %d) -> %s",
                         relation, idx, len(df), cap_note, n_dropped, out_pkl)
            tqdm.write(f"  ✔  {relation}: {len(df):,} scored ({cap_note}) -> {out_pkl.name}")
            return True
        except Exception as e:
            if tmp_pkl.exists():
                tmp_pkl.unlink()
            logging.info("score-processing error: %s in %s (idx %d)", str(e), relation, idx)
            raise RuntimeError(f"score processing failed for {relation}: {e!s}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    man = pd.read_csv(MANIFEST_CSV)

    # SKIP_PREFIXES = ("PMID_",)
    # SKIP_EXACT    = {"Species_AssociatedWith"}
    SKIP_PREFIXES = ()
    SKIP_EXACT    = {"Species_AssociatedWith"}

    before = len(man)
    rel_col = man["relation"].astype(str)
    keep_mask = ~rel_col.str.startswith(SKIP_PREFIXES) & ~rel_col.isin(SKIP_EXACT)
    dropped = man.loc[~keep_mask, "relation"].tolist()
    man = man.loc[keep_mask]

    relations = man["relation"].astype(str).tolist()
    print(f"Manifest: {before} relations, "
          f"scoring {len(relations)} after skipping {len(dropped)} "
          f"provenance relations: {dropped}")

    written, failed = 0, []
    for idx, relation in enumerate(tqdm(relations, desc="scoring", unit="rel")):
        try:
            if score_gt(relation, idx):
                written += 1
        except Exception as e:
            failed.append(relation)
            logging.info("RELATION FAILED (skipped): %s -- %s", relation, str(e))
            tqdm.write(f"  ✗  {relation}: FAILED ({e}) -- skipping, will retry on rerun")
            continue

    print(f"\n✅ Done. Scored {written} relations. "
          f"Failed/skipped: {len(failed)} -> {failed}. Output -> {OUTPUT_DIR}")
    if failed:
        print("Rerun to retry failed relations (completed ones are skipped).")


if __name__ == "__main__":
    main()
