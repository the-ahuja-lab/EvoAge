#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
from tqdm import tqdm
import os
import time


OUTPUT_DIR = '/storage/Arushi/090526_EvoAge/kg_formation/training_3/Shuffled_EvoAge_testing/Store_House/shuffled_test_sets'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load original test set
test_df = pd.read_csv(
    '/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_3/building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.txt',
    sep='\t', header=None, names=['head', 'relation', 'tail']
)

n = len(test_df)
print(f"Test set size: {n}")

# --- Encode entities/relations as integers ---
all_entities = pd.unique(np.concatenate([test_df['head'].values, test_df['tail'].values]))
entity_to_id = {e: i for i, e in enumerate(all_entities)}
all_relations = pd.unique(test_df['relation'].values)
relation_to_id = {r: i for i, r in enumerate(all_relations)}

heads_id = test_df['head'].map(entity_to_id).values.astype(np.int64)
relations_id = test_df['relation'].map(relation_to_id).values.astype(np.int64)
tails_id = test_df['tail'].map(entity_to_id).values.astype(np.int64)

n_entities = len(all_entities)
n_relations = len(all_relations)
print(f"n_entities={n_entities}, n_relations={n_relations}")

def encode_triples(h, r, t, n_entities, n_relations):
    return (h.astype(np.int64) * n_relations + r.astype(np.int64)) * n_entities + t.astype(np.int64)

real_codes = encode_triples(heads_id, relations_id, tails_id, n_entities, n_relations)
real_codes_sorted = np.sort(real_codes)

def is_in_real(codes, real_codes_sorted):
    idx = np.searchsorted(real_codes_sorted, codes)
    idx_clipped = np.clip(idx, 0, len(real_codes_sorted) - 1)
    return real_codes_sorted[idx_clipped] == codes




def shuffle_with_dedup_fast(heads_id, relations_id, tails_id, real_codes_sorted,
                              n_entities, n_relations, seed, max_retries=200, verbose=False):
    rng = np.random.RandomState(seed)
    n = len(heads_id)

    head_perm = rng.permutation(n)
    tail_perm = rng.permutation(n)
    sh_heads = heads_id[head_perm].copy()
    sh_tails = tails_id[tail_perm].copy()

    # Full check ONLY on the first pass (the unavoidable expensive step)
    codes = encode_triples(sh_heads, relations_id, sh_tails, n_entities, n_relations)
    collision_mask = is_in_real(codes, real_codes_sorted)
    bad_idx = np.where(collision_mask)[0]
    if verbose:
        print(f"    retry 0: collisions={len(bad_idx):,}")

    retries = 0
    stale_count = 0
    prev_n_bad = len(bad_idx)

    while len(bad_idx) > 0:
        retries += 1
        if retries > max_retries:
            raise RuntimeError(f"Seed {seed}: unresolved {len(bad_idx)} collisions after {max_retries} retries")

        if len(bad_idx) == prev_n_bad:
            stale_count += 1
        else:
            stale_count = 0
        prev_n_bad = len(bad_idx)

        if stale_count >= 3:
            extra_n = min(n, len(bad_idx) * 20)
            extra_idx = rng.choice(n, size=extra_n, replace=False)
            pool_idx = np.union1d(bad_idx, extra_idx)
            stale_count = 0
        else:
            pool_idx = bad_idx

        sub_head_perm = rng.permutation(len(pool_idx))
        sub_tail_perm = rng.permutation(len(pool_idx))
        sh_heads[pool_idx] = sh_heads[pool_idx][sub_head_perm]
        sh_tails[pool_idx] = sh_tails[pool_idx][sub_tail_perm]

        pool_codes = encode_triples(sh_heads[pool_idx], relations_id[pool_idx], sh_tails[pool_idx],
                                     n_entities, n_relations)
        pool_collision = is_in_real(pool_codes, real_codes_sorted)
        bad_idx = pool_idx[pool_collision]
        if verbose:
            print(f"    retry {retries}: collisions={len(bad_idx):,} pool_size={len(pool_idx):,}")
    final_codes = encode_triples(sh_heads, relations_id, sh_tails, n_entities, n_relations)
    assert not is_in_real(final_codes, real_codes_sorted).any()
    return sh_heads, sh_tails, retries

# Precompute reverse map for decoding ids back to original entity strings
id_to_entity = {i: e for e, i in entity_to_id.items()}
id_to_entity_arr = np.array([id_to_entity[i] for i in range(n_entities)])

relation_values = test_df['relation'].values  # original relation strings, fixed per row

summary = []
pbar = tqdm(range(30), desc="Generating shuffled test sets", unit="shuffle")
for shuffle_id in pbar:
    seed = shuffle_id
    t_start = time.time()

    sh_heads_id, sh_tails_id, retries = shuffle_with_dedup_fast(
        heads_id, relations_id, tails_id, real_codes_sorted,
        n_entities, n_relations, seed=seed, verbose=False
    )

    out_df = pd.DataFrame({
        'head': id_to_entity_arr[sh_heads_id],
        'relation': relation_values,
        'tail': id_to_entity_arr[sh_tails_id]
    })

    out_path = os.path.join(OUTPUT_DIR, f'shuffled_test_{shuffle_id:03d}_seed{seed}.txt')
    out_df.to_csv(out_path, sep='\t', header=False, index=False)

    elapsed = time.time() - t_start
    summary.append({
        'shuffle_id': shuffle_id,
        'seed': seed,
        'retries_needed': retries,
        'elapsed_sec': round(elapsed, 1),
        'output_path': out_path
    })

    pbar.set_postfix({'retries': retries, 'sec': round(elapsed, 1)})

summary_df = pd.DataFrame(summary)
summary_df.to_csv(os.path.join(OUTPUT_DIR, 'shuffle_summary.csv'), index=False)

print("\nAll 30 shuffles complete. Summary saved.")
print(summary_df[['shuffle_id', 'retries_needed', 'elapsed_sec']].describe())
