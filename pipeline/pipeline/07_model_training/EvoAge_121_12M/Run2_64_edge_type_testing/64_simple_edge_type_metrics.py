#!/usr/bin/env python3
import numpy as np
import torch
from typing import Tuple

# ========= HARD-CODED SETTINGS (your request) =========
ENTITY_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Simple/SimplE_Evoage_121_12M_2/Evoage_121_12M_SimplE_entity.npy"

RELATION_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Simple/SimplE_Evoage_121_12M_2/Evoage_121_12M_SimplE_relation.npy"

TRIPLES_PATH     = "/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.txt"
DEVICE = "cuda:1"   # use GPU 1 instead of GPU 0
BATCH_SIZE       = 16384      # --batch
REL_CHUNK        = 8192       # --rel-chunk
# ======================================================

# ---- SimplE config (must match training) ----
# SimplE stores TWO embeddings per entity (head-role, tail-role) and
# TWO embeddings per relation (forward, inverse), each of dim d.
# So entity emb is (E, 2d) and relation emb is (R, 2d), split in half.
# score(h, r, t) = 0.5 * ( <h_head, r_fwd, t_tail> + <t_head, r_inv, h_tail> )
# No gamma/margin — raw score, higher is better.
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
    ent_np = np.load(ent_path).astype(np.float32, copy=False)    # (E, 2d)
    rel_np = np.load(rel_path).astype(np.float32, copy=False)    # (R, 2d)

    if ent_np.ndim != 2 or rel_np.ndim != 2:
        raise ValueError(f"Expected ent (E,2d) and rel (R,2d), got {ent_np.shape}, {rel_np.shape}")
    if ent_np.shape[1] % 2 != 0:
        raise ValueError(f"Entity embedding dim must be even (head|tail halves), got {ent_np.shape[1]}")
    if rel_np.shape[1] != ent_np.shape[1]:
        raise ValueError(
            f"Dim mismatch: relation dim={rel_np.shape[1]} vs entity dim={ent_np.shape[1]}. "
            f"SimplE relation embeddings should match entity embedding dim exactly "
            f"(both store two halves: head/tail for entities, forward/inverse for relations)."
        )

    ent = torch.from_numpy(ent_np).to(device, non_blocking=True)     # (E, 2d)
    rel = torch.from_numpy(rel_np).to(device, non_blocking=True)     # (R, 2d)
    return ent, rel

@torch.no_grad()
def simple_score_all_relations(
    h_head: torch.Tensor,  # (B, d)
    h_tail: torch.Tensor,  # (B, d)
    t_head: torch.Tensor,  # (B, d)
    t_tail: torch.Tensor,  # (B, d)
    r_fwd: torch.Tensor,   # (Rc, d)
    r_inv: torch.Tensor,   # (Rc, d)
) -> torch.Tensor:
    """
    Vectorized SimplE score for a batch of (h, ?, t) against a chunk of relations.
    score(h, r, t) = 0.5 * ( sum(h_head * r_fwd * t_tail) + sum(t_head * r_inv * h_tail) )
    Returns raw scores of shape (B, Rc); higher is better.
    """
    ht_fwd = h_head * t_tail            # (B, d) — independent of relation, precompute once
    ht_inv = t_head * h_tail            # (B, d) — independent of relation, precompute once

    term1 = ht_fwd @ r_fwd.t()          # (B, d) @ (d, Rc) -> (B, Rc)
    term2 = ht_inv @ r_inv.t()          # (B, d) @ (d, Rc) -> (B, Rc)

    return 0.5 * (term1 + term2)        # (B, Rc)

@torch.no_grad()
def evaluate_relation_prediction(
    ent: torch.Tensor, rel: torch.Tensor, triples: torch.Tensor,
    batch_size: int, rel_chunk: int, device: torch.device
):
    """
    Computes Hits@K and MRR for relation prediction (h, ?, t) using SimplE.
    Processes triples in batches, and relations in chunks if needed to limit memory.
    """
    N = triples.shape[0]
    E, two_d = ent.shape
    R, two_d_r = rel.shape
    assert two_d == two_d_r, f"Entity emb dim {two_d} must match relation emb dim {two_d_r}"
    d = two_d // 2

    hits1 = hits3 = hits10 = 0
    mrr_sum = 0.0
    total = 0

    rel_indices = torch.arange(R, device=device)

    # Split relation embeddings once: forward half, inverse half
    r_fwd_all = rel[:, :d]   # (R, d)
    r_inv_all = rel[:, d:]   # (R, d)

    for i in range(0, N, batch_size):
        batch = triples[i:i+batch_size]            # (B, 3)
        B = batch.shape[0]
        h_ids = batch[:, 0]
        r_gt  = batch[:, 1]
        t_ids = batch[:, 2]

        h_full = ent.index_select(0, h_ids)         # (B, 2d)
        t_full = ent.index_select(0, t_ids)         # (B, 2d)

        h_head, h_tail = h_full[:, :d], h_full[:, d:]
        t_head, t_tail = t_full[:, :d], t_full[:, d:]

        # Build scores (B, R) from relation chunks
        scores_chunks = []
        for j in range(0, R, rel_chunk):
            idx = rel_indices[j:j+rel_chunk]            # (Rc,)
            r_fwd_chunk = r_fwd_all.index_select(0, idx)  # (Rc, d)
            r_inv_chunk = r_inv_all.index_select(0, idx)  # (Rc, d)
            scores = simple_score_all_relations(
                h_head, h_tail, t_head, t_tail, r_fwd_chunk, r_inv_chunk
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