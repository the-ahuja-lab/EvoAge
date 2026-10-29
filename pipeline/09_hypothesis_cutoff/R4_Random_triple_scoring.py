import os
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

# ---- RANDOM inputs/outputs (mirror of the GT scorer) ----
INPUT_DIR    = "/path/to/cutoff/output/relation_samples_ALLRANDOM"
MANIFEST_CSV = "/path/to/cutoff/output/relation_samples_ALLRANDOM/rand_manifest.csv"
OUTPUT_DIR   = "/path/to/cutoff/output/relation_samples_ALLRANDOM_output"
LOG_DIR      = "/path/to/cutoff/output/logs"

DEVICE = 0
SFUNC  = "logsigmoid"
SKIP_EXISTING = True

# filename token: GT dump uses _GT_, random dump uses _RAND_
TAG = "RAND"
# =================================================================

BATCH_SIZE        = 500_000
MAX_SCORE_PER_REL = None

# Above this many scored rows, DON'T merge shards into one giant pickle
# (which would rebuild the whole thing in RAM). Instead keep the per-batch
# pickle shards in a per-relation folder. Set to None to always make one pickle.
# None => every relation (incl. the PMID giants) becomes a single .pkl.
# NOTE: the largest relation (~237M rows) will build a ~10-15 GB DataFrame in
# RAM at merge time; fine on a 200 GB box, but that's the peak to be aware of.
PARTS_OUTPUT_THRESHOLD = None

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
    filename=str(Path(LOG_DIR) / f"LOG_inference_ALL{TAG}.log"),
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


def score_random(relation: str, idx: int) -> bool:
    rel_dir  = INPUT_DIR / relation
    head_f   = rel_dir / f"{relation}_{TAG}_head.list"
    rel_f    = rel_dir / f"{relation}_{TAG}_rel.list"
    tail_f   = rel_dir / f"{relation}_{TAG}_tail.list"
    out_pkl  = OUTPUT_DIR / f"{relation}_{TAG}_SCORE.pkl"
    tmp_pkl  = OUTPUT_DIR / f"{relation}_{TAG}_SCORE.pkl.tmp"
    out_parq = OUTPUT_DIR / f"{relation}_{TAG}_SCORE_parts"

    if SKIP_EXISTING and (out_pkl.is_file() or out_parq.is_dir()):
        tqdm.write(f"  ⏭  {relation}: already scored, skipping")
        return False

    missing = [str(p) for p in (head_f, rel_f, tail_f) if not p.is_file()]
    if missing:
        logging.info("Missing %s files %s in %s (idx %d)", TAG, missing, relation, idx)
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

    # ---- pre-filter + normalize ----
    # The KG's phenotype/miRNA names carry stray whitespace from scraped sources
    # (trailing space 'hsa-miR-103a-3p ', leading+trailing '  caudal fin ... ',
    # internal double-space 'interrenal  angiogenic ...'). DGL-KE's loader does
    # eid_map[line[:-1]] (strips only newline), so these fail to match the dict.
    # GT fix: normalize the names — strip both ends AND collapse internal runs of
    # whitespace to a single space — then match. This matches the dict keys and
    # KEEPS the row (these are real entities), rather than dropping it.
    import re as _re
    _ws = _re.compile(r"\s+")

    def _read_lines(pth):
        with open(pth, "r", encoding="utf-8") as f:
            return [ln.rstrip("\n") for ln in f]

    def _resolve(name: str):
        """EXACT match first, whitespace-normalize only as a FALLBACK.

        Unconditional normalization (what this used to do) merges the 42 entity
        pairs that are distinguished ONLY by whitespace now marked with '_'
        (e.g. 'hsa-miR-103a-3p' vs 'hsa-miR-103a-3p_'), scoring one node with
        the other's embedding. Verbatim-first means a real name always wins and
        normalization only rescues names that would otherwise be dropped.
        Must stay IDENTICAL to R3's rule, or GT and Random get filtered
        asymmetrically and the ROC compares unequal populations.
        """
        if name in ENTITY_KEYS:
            return name
        n = _ws.sub(" ", name).strip()
        return n if n in ENTITY_KEYS else None

    H = _read_lines(head_f); R = _read_lines(rel_f); T = _read_lines(tail_f)
    keep_h, keep_r, keep_t = [], [], []
    n_dropped = 0
    n_normalized = 0
    for h, r, t in zip(H, R, T):
        hn, tn = _resolve(h), _resolve(t)
        if hn is not None and tn is not None:
            if hn != h or tn != t:
                n_normalized += 1
            keep_h.append(hn); keep_r.append(r.strip()); keep_t.append(tn)
        else:
            n_dropped += 1
    if n_normalized:
        logging.info("%s: normalized whitespace in %d/%d triples",
                     relation, n_normalized, len(H))
    if n_dropped:
        logging.info("%s: dropped %d/%d triples still unresolved after normalize",
                     relation, n_dropped, len(H))
        tqdm.write(f"  ⚠  {relation}: normalized {n_normalized:,}, "
                   f"dropped {n_dropped:,} unresolved "
                   f"({100.0*n_dropped/max(len(H),1):.2f}%)")
    if not keep_h:
        tqdm.write(f"  ⚠  {relation}: no resolvable triples, skipping")
        return False

    tmpdir = Path(tempfile.mkdtemp(prefix=f"{relation}_{TAG}_filt_"))
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

        # ---- score in batches, sharding each batch to a pickle part ----
        # Instead of holding every batch DataFrame in RAM and concatenating,
        # we map ids->names PER BATCH and write a small pickle shard. At the
        # end we read the shards back and write the final pickle. This keeps
        # peak memory ~one batch, and a mid-relation crash costs only the
        # current batch (finished shards stay on disk under tmpdir).
        shard_dir = tmpdir / "shards"
        shard_dir.mkdir(parents=True, exist_ok=True)

        n_batches = -(-n_used // BATCH_SIZE)
        total_rows = 0
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
                dfb = pd.DataFrame(rows, columns=["head", "rel", "tail", "score"])
                del rows, raw

                # map ids -> names on this batch only (bounded memory)
                dfb["head"] = dfb["head"].map(lambda x: id2ent[int(x)])
                dfb["rel"]  = dfb["rel"].map(lambda x: id2rel[int(x)])
                dfb["tail"] = dfb["tail"].map(lambda x: id2ent[int(x)])

                dfb.to_pickle(shard_dir / f"shard_{b:05d}.pkl")
                total_rows += len(dfb)
                del dfb

                if n_batches > 1:
                    tqdm.write(f"     {relation}: batch {b+1}/{n_batches} "
                               f"({e:,}/{n_used:,}) shard written")
        except Exception as e:
            logging.info("scoring error: %s in %s (idx %d)", str(e), relation, idx)
            raise RuntimeError(f"scoring failed for {relation}: {e!s}")

        # ---- merge shards -> final output ----
        try:
            shard_files = sorted(shard_dir.glob("shard_*.pkl"))
            if not shard_files:
                raise RuntimeError("no shards produced")

            if PARTS_OUTPUT_THRESHOLD is not None and total_rows > PARTS_OUTPUT_THRESHOLD:
                # huge relation: keep shards as a folder of pickle parts, no giant
                # in-RAM concat and no single giant pickle.
                out_dir = OUTPUT_DIR / f"{relation}_{TAG}_SCORE_parts"
                tmp_dir = OUTPUT_DIR / f"{relation}_{TAG}_SCORE_parts.tmp"
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                tmp_dir.mkdir(parents=True)
                for f in shard_files:
                    shutil.move(str(f), str(tmp_dir / f.name))
                if out_dir.exists():
                    shutil.rmtree(out_dir, ignore_errors=True)
                tmp_dir.replace(out_dir)
                logging.info("%s scored (parts): %s idx=%d rows=%d (%s, dropped %d) -> %s",
                             TAG, relation, idx, total_rows, cap_note, n_dropped, out_dir)
                tqdm.write(f"  ✔  {relation}: {total_rows:,} scored ({cap_note}) "
                           f"-> {out_dir.name}/ ({len(shard_files)} pickle parts)")
                return True

            # normal case: merge to a single pickle
            df = pd.concat((pd.read_pickle(f) for f in shard_files),
                           ignore_index=True)
            df.to_pickle(tmp_pkl)
            tmp_pkl.replace(out_pkl)
            logging.info("%s scored: %s idx=%d rows=%d (%s, dropped %d) -> %s",
                         TAG, relation, idx, len(df), cap_note, n_dropped, out_pkl)
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
          f"relations: {dropped}")

    written, failed = 0, []
    for idx, relation in enumerate(tqdm(relations, desc="scoring", unit="rel")):
        try:
            if score_random(relation, idx):
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
