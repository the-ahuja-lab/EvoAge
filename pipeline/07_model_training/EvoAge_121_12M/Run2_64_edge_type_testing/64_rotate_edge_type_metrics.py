#!/usr/bin/env python3
import numpy as np
import torch
from typing import Tuple

# ========= HARD-CODED SETTINGS (your request) =========
ENTITY_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Rotate/RotatE_Evoage_121_12M_0/Evoage_121_12M_RotatE_entity.npy"

RELATION_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Rotate/RotatE_Evoage_121_12M_0/Evoage_121_12M_RotatE_relation.npy"

TRIPLES_PATH     = "/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.txt"
DEVICE = "cuda:1"   # use GPU 1 instead of GPU 0
BATCH_SIZE       = 16384      # --batch
REL_CHUNK        = 2048       # --rel-chunk  (lowered from 8192 to cut peak memory ~4x)
# ======================================================

# ---- RotatE config (must match training) ----
GAMMA = 12.0
EMB_INIT = 10.0  # used to convert stored rel emb -> phase
# ---------------------------------------------
#
# MEMORY NOTE vs. the original version:
# The original computed re_hr, im_hr, re_diff, im_diff as 4 separate (B, Rc, d) tensors
# alive at the same time. This version fuses the rotation and the diff-from-tail into
# just 2 (B, Rc, d) buffers using in-place ops (re_part doubles as re_diff, im_part doubles
# as im_diff), roughly halving peak GPU memory for the same REL_CHUNK. REL_CHUNK is also
# lowered as a second lever — drop it further (e.g. 1024, 512) if you still hit OOM.

def load_id_triples(path: str) -> torch.Tensor:
    print("✅ Loading test triples...\n")
    triples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.strip().split()
            if len(p) == 3:
                triples.append(tuple(map(int, p)))
    if not triples:
        raise ValueError("No valid triples found.")
    return torch.tensor(triples, dtype=torch.long)  # (N, 3) [h, r, t]

def load_embeddings(ent_path: str, rel_path: str, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    ent_np = np.load(ent_path).astype(np.float32, copy=False)    # (E, 2d)
    rel_np = np.load(rel_path).astype(np.float32, copy=False)    # (R, d)

    if ent_np.ndim != 2 or rel_np.ndim != 2:
        raise ValueError(f"Expected ent (E,2d) and rel (R,d), got {ent_np.shape}, {rel_np.shape}")
    if ent_np.shape[1] % 2 != 0:
        raise ValueError(f"Entity embedding dim must be even (real|imag), got {ent_np.shape[1]}")
    if rel_np.shape[1] != ent_np.shape[1] // 2:
        raise ValueError(f"Dim mismatch: relation d={rel_np.shape[1]} vs entity half={ent_np.shape[1]//2}")

    ent = torch.from_numpy(ent_np).to(device, non_blocking=True)     # (E, 2d)
    rel = torch.from_numpy(rel_np).to(device, non_blocking=True)     # (R, d)
    return ent, rel

@torch.no_grad()
def rotate_score_all_relations(
    re_h: torch.Tensor, im_h: torch.Tensor,   # (B, d)
    re_t: torch.Tensor, im_t: torch.Tensor,   # (B, d)
    rel_phase: torch.Tensor,                   # (Rc, d) stored embedding (to be mapped to phase)
    gamma: float,
    emb_init: float,
) -> torch.Tensor:
    """
    Memory-lean RotatE score for a batch of (h, ?, t) against a chunk of relations.
    Fuses rotation + diff-from-tail into 2 (B, Rc, d) buffers (in-place) instead of 4.
    Returns raw scores of shape (B, Rc); higher is better.
    """
    # Convert stored relation embedding to phases in [-pi, pi]
    phase = rel_phase / (emb_init / np.pi)   # (Rc, d)
    re_r = torch.cos(phase)                  # (Rc, d)
    im_r = torch.sin(phase)                  # (Rc, d)

    # re_part starts as re(h ∘ r), then becomes re_diff in-place
    re_part = re_h.unsqueeze(1) * re_r.unsqueeze(0)        # (B, Rc, d)
    re_part -= im_h.unsqueeze(1) * im_r.unsqueeze(0)
    re_part -= re_t.unsqueeze(1)                            # now == re_diff

    # im_part starts as im(h ∘ r), then becomes im_diff in-place
    im_part = re_h.unsqueeze(1) * im_r.unsqueeze(0)         # (B, Rc, d)
    im_part += im_h.unsqueeze(1) * re_r.unsqueeze(0)
    im_part -= im_t.unsqueeze(1)                             # now == im_diff

    dist = re_part.abs_().add_(im_part.abs_()).sum(dim=-1)   # (B, Rc)
    return gamma - dist

@torch.no_grad()
def evaluate_relation_prediction(
    ent: torch.Tensor, rel: torch.Tensor, triples: torch.Tensor,
    batch_size: int, rel_chunk: int, device: torch.device
):
    """
    Computes Hits@K and MRR for relation prediction (h, ?, t) using RotatE.
    Processes triples in batches, and relations in chunks if needed to limit memory.
    """
    N = triples.shape[0]
    E, two_d = ent.shape
    R, d = rel.shape
    assert two_d % 2 == 0 and d == two_d // 2

    hits1 = hits3 = hits10 = 0
    mrr_sum = 0.0
    total = 0

    rel_indices = torch.arange(R, device=device)

    for i in range(0, N, batch_size):
        batch = triples[i:i+batch_size]            # (B, 3)
        B = batch.shape[0]
        h_ids = batch[:, 0]
        r_gt  = batch[:, 1]
        t_ids = batch[:, 2]

        h_vec = ent.index_select(0, h_ids)         # (B, 2d)
        t_vec = ent.index_select(0, t_ids)         # (B, 2d)
        re_h, im_h = h_vec[:, :d], h_vec[:, d:]
        re_t, im_t = t_vec[:, :d], t_vec[:, d:]

        # Build scores (B, R) from relation chunks
        scores_chunks = []
        for j in range(0, R, rel_chunk):
            idx = rel_indices[j:j+rel_chunk]       # (Rc,)
            rel_chunk_phase = rel.index_select(0, idx)  # (Rc, d)
            scores = rotate_score_all_relations(
                re_h, im_h, re_t, im_t, rel_chunk_phase, GAMMA, EMB_INIT
            )  # (B, Rc)
            scores_chunks.append(scores)
        scores_all = torch.cat(scores_chunks, dim=1)    # (B, R)

        gt_scores = scores_all.gather(1, r_gt.view(-1, 1)).squeeze(1)

        # Best-rank tie handling: #strictly greater + 1
        better = (scores_all > gt_scores.unsqueeze(1)).sum(dim=1)  # (B,)
        rank = better.add_(1).to(torch.float32)                    # (B,)

        hits1  += (rank <= 1).sum().item()
        hits3  += (rank <= 3).sum().item()
        hits10 += (rank <= 10).sum().item()
        mrr_sum += (1.0 / rank).sum().item()
        total  += B

    return {
        "total": total,
        "mrr": mrr_sum / total,
        "hits@1": hits1 / total,
        "hits@3": hits3 / total,
        "hits@10": hits10 / total,
    }

def main():
    device = torch.device(DEVICE)
    torch.set_grad_enabled(False)
    torch.set_num_threads(1)  # avoid oversubscription with large batches

    ent, rel = load_embeddings(ENTITY_EMB_PATH, RELATION_EMB_PATH, device)
    triples = load_id_triples(TRIPLES_PATH).to(device, non_blocking=True)

    print(f"📦 Entity emb shape: {tuple(ent.shape)}")
    print(f"📦 Relation emb shape: {tuple(rel.shape)}")
    print(f"🖥️ Device: {device} | batch={BATCH_SIZE} | rel_chunk={REL_CHUNK}")

    metrics = evaluate_relation_prediction(
        ent=ent, rel=rel, triples=triples,
        batch_size=BATCH_SIZE, rel_chunk=REL_CHUNK, device=device
    )

    print("\n📊 Final Evaluation on test.txt (head, *, tail)")
    print(f"Total Triples Evaluated: {metrics['total']}")
    print(f"MRR     = {metrics['mrr']:.4f}")
    print(f"Hits@1  = {metrics['hits@1']:.4f}")
    print(f"Hits@3  = {metrics['hits@3']:.4f}")
    print(f"Hits@10 = {metrics['hits@10']:.4f}")

if __name__ == "__main__":
    main()