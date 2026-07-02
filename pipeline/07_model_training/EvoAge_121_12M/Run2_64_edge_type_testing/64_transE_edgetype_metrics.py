#!/usr/bin/env python3
import numpy as np
import torch
from typing import Tuple

# ========= HARD-CODED SETTINGS (your request) =========
ENTITY_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training/EvoAge_121_12M/model_output/Transe/TransE_Evoage_121_12M_1/Evoage_121_12M_TransE_entity.npy"

RELATION_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training/EvoAge_121_12M/model_output/Transe/TransE_Evoage_121_12M_1/Evoage_121_12M_TransE_relation.npy"

TRIPLES_PATH     = "/storage/Arushi/090526_EvoAge/kg_formation/final_kg__building/building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.txt"
DEVICE = "cuda:1"   # use GPU 1 instead of GPU 0
BATCH_SIZE       = 16384      # --batch
REL_CHUNK        = 8192       # --rel-chunk
# ======================================================

# ---- TransE config (must match training) ----
GAMMA = 12.0      # margin used during training — check your DGL-KE training command (--gamma)
NORM_P = 1        # 1 for L1 distance, 2 for L2 distance — check your training command (-pl / --dist_func)
# Entities and relations are both real-valued, same dim: (E, d) and (R, d).
# score(h, r, t) = gamma - ||h + r - t||_p   (higher is better; 0 distance -> score = gamma)
# -------------------------------------------------

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
    ent_np = np.load(ent_path).astype(np.float32, copy=False)    # (E, d)
    rel_np = np.load(rel_path).astype(np.float32, copy=False)    # (R, d)

    if ent_np.ndim != 2 or rel_np.ndim != 2:
        raise ValueError(f"Expected ent (E,d) and rel (R,d), got {ent_np.shape}, {rel_np.shape}")
    if rel_np.shape[1] != ent_np.shape[1]:
        raise ValueError(
            f"Dim mismatch: relation dim={rel_np.shape[1]} vs entity dim={ent_np.shape[1]}. "
            f"TransE relation embeddings should match entity embedding dim exactly "
            f"(both live in the same real-valued space, unlike RotatE where relation dim "
            f"is half the entity dim)."
        )

    ent = torch.from_numpy(ent_np).to(device, non_blocking=True)     # (E, d)
    rel = torch.from_numpy(rel_np).to(device, non_blocking=True)     # (R, d)
    return ent, rel

@torch.no_grad()
def transe_score_all_relations(
    h_vec: torch.Tensor,   # (B, d)
    t_vec: torch.Tensor,   # (B, d)
    rel_vec: torch.Tensor, # (Rc, d)
    gamma: float,
    norm_p: int,
) -> torch.Tensor:
    """
    Vectorized TransE score for a batch of (h, ?, t) against a chunk of relations.
    score(h, r, t) = gamma - ||h + r - t||_p
    Returns raw scores of shape (B, Rc); higher is better.
    """
    diff = h_vec.unsqueeze(1) + rel_vec.unsqueeze(0) - t_vec.unsqueeze(1)  # (B, Rc, d)
    if norm_p == 1:
        dist = diff.abs().sum(dim=-1)          # (B, Rc)
    elif norm_p == 2:
        dist = diff.pow(2).sum(dim=-1).sqrt()  # (B, Rc)
    else:
        raise ValueError(f"Unsupported norm_p={norm_p}; expected 1 or 2")
    return gamma - dist

@torch.no_grad()
def evaluate_relation_prediction(
    ent: torch.Tensor, rel: torch.Tensor, triples: torch.Tensor,
    batch_size: int, rel_chunk: int, device: torch.device,
    gamma: float, norm_p: int,
):
    """
    Computes Hits@K and MRR for relation prediction (h, ?, t) using TransE.
    Processes triples in batches, and relations in chunks if needed to limit memory.
    """
    N = triples.shape[0]
    E, d = ent.shape
    R, d_r = rel.shape
    assert d_r == d, f"Entity dim {d} must match relation dim {d_r}"

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

        h_vec = ent.index_select(0, h_ids)         # (B, d)
        t_vec = ent.index_select(0, t_ids)         # (B, d)

        # Build scores (B, R) from relation chunks
        scores_chunks = []
        for j in range(0, R, rel_chunk):
            idx = rel_indices[j:j+rel_chunk]            # (Rc,)
            rel_chunk_vec = rel.index_select(0, idx)    # (Rc, d)
            scores = transe_score_all_relations(h_vec, t_vec, rel_chunk_vec, gamma, norm_p)  # (B, Rc)
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
    print(f"🖥️ Device: {device} | batch={BATCH_SIZE} | rel_chunk={REL_CHUNK} | gamma={GAMMA} | norm_p={NORM_P}")

    metrics = evaluate_relation_prediction(
        ent=ent, rel=rel, triples=triples,
        batch_size=BATCH_SIZE, rel_chunk=REL_CHUNK, device=device,
        gamma=GAMMA, norm_p=NORM_P,
    )

    print("\n📊 Final Evaluation on test.txt (head, *, tail)")
    print(f"Total Triples Evaluated: {metrics['total']}")
    print(f"MRR     = {metrics['mrr']:.4f}")
    print(f"Hits@1  = {metrics['hits@1']:.4f}")
    print(f"Hits@3  = {metrics['hits@3']:.4f}")
    print(f"Hits@10 = {metrics['hits@10']:.4f}")

if __name__ == "__main__":
    main()