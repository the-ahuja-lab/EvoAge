#!/usr/bin/env python3
import numpy as np
import torch
from typing import Tuple

# ========= HARD-CODED SETTINGS (your request) =========
ENTITY_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Complex/ComplEx_Evoage_121_12M_1/Evoage_121_12M_ComplEx_entity.npy"

RELATION_EMB_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/EvoAge_121_12M/model_output/Complex/ComplEx_Evoage_121_12M_1/Evoage_121_12M_ComplEx_relation.npy"

TRIPLES_PATH     = "/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_kg_new/Store_House/EvoAge_1to1_KG_test.txt"
DEVICE = "cuda:0"   # use GPU 1 instead of GPU 0
BATCH_SIZE       = 16384      # --batch
REL_CHUNK        = 8192       # --rel-chunk
# ======================================================

# ---- ComplEx config (must match training) ----
# ComplEx uses complex-valued embeddings stored as (E, 2d) and (R, 2d):
#   First d dimensions = real part
#   Last d dimensions = imaginary part
# score(h, r, t) = Re( <h_conj, r, t> )
#   where h_conj is element-wise complex conjugate of h
# No gamma/margin — raw score, higher is better.
# --------------------------------------------------

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
        raise ValueError(f"Entity embedding dim must be even (real|imag halves), got {ent_np.shape[1]}")
    if rel_np.shape[1] != ent_np.shape[1]:
        raise ValueError(
            f"Dim mismatch: relation dim={rel_np.shape[1]} vs entity dim={ent_np.shape[1]}. "
            f"ComplEx relation embeddings should match entity embedding dim exactly "
            f"(both store real|imag halves: first d dims = real, last d = imaginary)."
        )

    ent = torch.from_numpy(ent_np).to(device, non_blocking=True)     # (E, 2d)
    rel = torch.from_numpy(rel_np).to(device, non_blocking=True)     # (R, 2d)
    return ent, rel

@torch.no_grad()
def complex_score_all_relations(
    re_h: torch.Tensor,   # (B, d)
    im_h: torch.Tensor,   # (B, d)
    re_t: torch.Tensor,   # (B, d)
    im_t: torch.Tensor,   # (B, d)
    re_r: torch.Tensor,   # (Rc, d)
    im_r: torch.Tensor,   # (Rc, d)
) -> torch.Tensor:
    """
    Vectorized ComplEx score for a batch of (h, ?, t) against a chunk of relations.
    
    score(h, r, t) = Re( <h_conj, r, t> )
                   = sum_i [ h_re[i]*r_re[i]*t_re[i] 
                           + h_re[i]*r_im[i]*t_im[i]
                           + h_im[i]*r_im[i]*t_re[i] 
                           - h_im[i]*r_re[i]*t_im[i] ]
    
    The four terms arise from:
      (h_re - i*h_im) * (r_re + i*r_im) * (t_re + i*t_im) -> take real part
    
    Returns raw scores of shape (B, Rc); higher is better.
    """
    # h_re * r_re * t_re
    term1 = torch.einsum('bd,rd,bd->br', re_h, re_r, re_t)  # (B, Rc)
    
    # h_re * r_im * t_im
    term2 = torch.einsum('bd,rd,bd->br', re_h, im_r, im_t)  # (B, Rc)
    
    # h_im * r_im * t_re
    term3 = torch.einsum('bd,rd,bd->br', im_h, im_r, re_t)  # (B, Rc)
    
    # - h_im * r_re * t_im
    term4 = torch.einsum('bd,rd,bd->br', im_h, re_r, im_t)  # (B, Rc)
    
    return term1 + term2 + term3 - term4  # (B, Rc)

@torch.no_grad()
def evaluate_relation_prediction(
    ent: torch.Tensor, rel: torch.Tensor, triples: torch.Tensor,
    batch_size: int, rel_chunk: int, device: torch.device
):
    """
    Computes Hits@K and MRR for relation prediction (h, ?, t) using ComplEx.
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

    # Split relation embeddings once: real half, imaginary half
    re_r_all = rel[:, :d]   # (R, d)
    im_r_all = rel[:, d:]   # (R, d)

    for i in range(0, N, batch_size):
        batch = triples[i:i+batch_size]            # (B, 3)
        B = batch.shape[0]
        h_ids = batch[:, 0]
        r_gt  = batch[:, 1]
        t_ids = batch[:, 2]

        h_full = ent.index_select(0, h_ids)         # (B, 2d)
        t_full = ent.index_select(0, t_ids)         # (B, 2d)

        re_h, im_h = h_full[:, :d], h_full[:, d:]
        re_t, im_t = t_full[:, :d], t_full[:, d:]

        # Build scores (B, R) from relation chunks
        scores_chunks = []
        for j in range(0, R, rel_chunk):
            idx = rel_indices[j:j+rel_chunk]            # (Rc,)
            re_r_chunk = re_r_all.index_select(0, idx)  # (Rc, d)
            im_r_chunk = im_r_all.index_select(0, idx)  # (Rc, d)
            scores = complex_score_all_relations(
                re_h, im_h, re_t, im_t, re_r_chunk, im_r_chunk
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