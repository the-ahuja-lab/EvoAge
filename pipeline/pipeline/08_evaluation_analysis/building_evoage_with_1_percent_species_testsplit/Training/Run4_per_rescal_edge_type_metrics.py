#!/usr/bin/env python3
import numpy as np
import torch
from typing import Tuple
from datetime import datetime

# ========= HARD-CODED SETTINGS =========
BASE_EMBEDDING_PATH = "/storage/Arushi/090526_EvoAge/kg_formation/training_2/1_per_species_test_EvoAge_121_12M/model_output/Rescal/RESCAL_1_per_Evoage_121_12M_3"
BASE_TRIPLES_PATH   = "/storage/Arushi/090526_EvoAge/kg_formation/final_kg_building_2/building_evoage_with_1_percent_species_testsplit/Store_House"

TEST_SETS = [
    "Celegans.txt",
    "CrossSpecies.txt",
    "Drosophila.txt",
    "Human.txt",
    "Mouse.txt",
    "Yeast.txt",
    "Zebrafish.txt",
]

DEVICE = "cuda:1"   # use GPU 1
BATCH_SIZE = 16384
REL_CHUNK = 8192
# ======================================

def load_id_triples(path: str) -> torch.Tensor:
    """Load ID-based triples from file."""
    triples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.strip().split()
            if len(p) == 3:
                triples.append(tuple(map(int, p)))
    if not triples:
        raise ValueError(f"No valid triples found in {path}")
    return torch.tensor(triples, dtype=torch.long)  # (N, 3) [h, r, t]

def load_embeddings(ent_path: str, rel_path: str, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
    """Load and validate entity and relation embeddings."""
    ent_np = np.load(ent_path).astype(np.float32, copy=False)    # (E, d)
    rel_np = np.load(rel_path).astype(np.float32, copy=False)    # (R, d*d)

    if ent_np.ndim != 2 or rel_np.ndim != 2:
        raise ValueError(f"Expected ent (E,d) and rel (R,d*d), got {ent_np.shape}, {rel_np.shape}")

    d = ent_np.shape[1]
    if rel_np.shape[1] != d * d:
        raise ValueError(
            f"Dim mismatch: relation flattened dim={rel_np.shape[1]} "
            f"but expected d*d={d*d} for entity dim d={d}. "
            f"Check that embedding paths point to RESCAL model "
            f"(relation matrices stored flattened, not low-rank)."
        )

    ent = torch.from_numpy(ent_np).to(device, non_blocking=True)             # (E, d)
    rel = torch.from_numpy(rel_np).to(device, non_blocking=True)             # (R, d*d)
    rel = rel.view(rel.shape[0], d, d)                                       # (R, d, d)
    return ent, rel

@torch.no_grad()
def rescal_score_all_relations(
    h_vec: torch.Tensor,      # (B, d)
    t_vec: torch.Tensor,      # (B, d)
    rel_mat: torch.Tensor,    # (Rc, d, d)
) -> torch.Tensor:
    """
    Vectorized RESCAL score for a batch of (h, ?, t) against a chunk of relations.
    score(h, r, t) = h^T M_r t
    Returns raw scores of shape (B, Rc); higher is better.
    """
    hM = torch.einsum('bi,rij->rbj', h_vec, rel_mat)       # (Rc, B, d)
    scores = torch.einsum('rbj,bj->rb', hM, t_vec)         # (Rc, B)
    return scores.transpose(0, 1)                          # (B, Rc)

@torch.no_grad()
def evaluate_relation_prediction(
    ent: torch.Tensor, rel: torch.Tensor, triples: torch.Tensor,
    batch_size: int, rel_chunk: int, device: torch.device
):
    """
    Computes Hits@K and MRR for relation prediction (h, ?, t) using RESCAL.
    Processes triples in batches, and relations in chunks if needed to limit memory.
    """
    N = triples.shape[0]
    E, d = ent.shape
    R, d1, d2 = rel.shape
    assert d1 == d2 == d, f"Entity dim {d} must match relation matrix dims {d1}x{d2}"

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
            rel_chunk_mat = rel.index_select(0, idx)    # (Rc, d, d)
            scores = rescal_score_all_relations(h_vec, t_vec, rel_chunk_mat)  # (B, Rc)
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
    torch.set_num_threads(1)

    print("=" * 80)
    print("🧬 RESCAL Relation Prediction Evaluation (Multi-Species)")
    print("=" * 80)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 Embedding base: {BASE_EMBEDDING_PATH}")
    print(f"📍 Triples base:   {BASE_TRIPLES_PATH}")
    print(f"🖥️  Device: {device} | batch={BATCH_SIZE} | rel_chunk={REL_CHUNK}\n")

    # Load embeddings once (same for all test sets)
    ent_path = f"{BASE_EMBEDDING_PATH}/1_per_Evoage_121_12M_RESCAL_entity.npy"
    rel_path = f"{BASE_EMBEDDING_PATH}/1_per_Evoage_121_12M_RESCAL_relation.npy"
    
    print(f"📦 Loading embeddings...")
    ent, rel = load_embeddings(ent_path, rel_path, device)
    print(f"   Entity emb shape: {tuple(ent.shape)}")
    print(f"   Relation emb shape: {tuple(rel.shape)} (R, d, d)\n")

    # Evaluate on each test set
    all_results = {}
    for test_file in TEST_SETS:
        triples_path = f"{BASE_TRIPLES_PATH}/{test_file}"
        test_name = test_file.replace(".txt", "")
        
        try:
            print(f"📊 Evaluating: {test_name}")
            triples = load_id_triples(triples_path)
            triples = triples.to(device, non_blocking=True)
            
            metrics = evaluate_relation_prediction(
                ent=ent, rel=rel, triples=triples,
                batch_size=BATCH_SIZE, rel_chunk=REL_CHUNK, device=device
            )
            
            all_results[test_name] = metrics
            
            print(f"   Total Triples: {metrics['total']}")
            print(f"   MRR     = {metrics['mrr']:.4f}")
            print(f"   Hits@1  = {metrics['hits@1']:.4f}")
            print(f"   Hits@3  = {metrics['hits@3']:.4f}")
            print(f"   Hits@10 = {metrics['hits@10']:.4f}\n")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}\n")
            all_results[test_name] = {"error": str(e)}

    # Summary table
    print("=" * 80)
    print("📋 SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Test Set':<20} {'Total':<10} {'MRR':<10} {'Hits@1':<10} {'Hits@3':<10} {'Hits@10':<10}")
    print("-" * 80)
    
    for test_name in TEST_SETS:
        test_key = test_name.replace(".txt", "")
        if test_key in all_results and "error" not in all_results[test_key]:
            m = all_results[test_key]
            print(f"{test_key:<20} {m['total']:<10} {m['mrr']:<10.4f} {m['hits@1']:<10.4f} {m['hits@3']:<10.4f} {m['hits@10']:<10.4f}")
        else:
            print(f"{test_key:<20} ERROR")
    
    print("=" * 80)
    print(f"⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Save results to CSV
    csv_out = "rescal_1_percent_test_edgeType_results.csv"
    with open(csv_out, "w") as f:
        f.write("TestSet,Metric_type,Total,MRR,Hits@1,Hits@3,Hits@10\n")
        for test_name in TEST_SETS:
            test_key = test_name.replace(".txt", "")
            if test_key in all_results and "error" not in all_results[test_key]:
                m = all_results[test_key]
                f.write(f"{test_key},EdgeType,{m['total']},{m['mrr']:.4f},{m['hits@1']:.4f},{m['hits@3']:.4f},{m['hits@10']:.4f}\n")
            else:
                f.write(f"{test_key},EdgeType,ERROR,,,,,\n")
    
    print(f"✅ Results saved to: {csv_out}\n")

if __name__ == "__main__":
    main()
