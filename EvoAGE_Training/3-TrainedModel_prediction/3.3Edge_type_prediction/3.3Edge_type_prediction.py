import numpy as np
import torch
import torch.nn.functional as F
from joblib import Parallel, delayed
import os
from tqdm import tqdm

# Parameters from DGL-KE training config
gamma = 12.0
emb_init = 10.0

def load_id_triples(path):
    print('✅ Loading test triples...\n')
    triples = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 3:
                continue
            h, r, t = map(int, parts)
            triples.append((h, r, t))
    return triples

def rotate_score_logsigmoid(head_emb, rel_emb, tail_emb, gamma: float, emb_init: float) -> float:
    pi = np.pi
    dim = head_emb.shape[-1] // 2
    re_head, im_head = head_emb[:dim], head_emb[dim:]
    re_tail, im_tail = tail_emb[:dim], tail_emb[dim:]

    phase_rel = rel_emb / (emb_init / pi)
    re_rel = torch.cos(phase_rel)
    im_rel = torch.sin(phase_rel)

    re_score = re_head * re_rel - im_head * im_rel
    im_score = re_head * im_rel + im_head * re_rel

    re_diff = re_score - re_tail
    im_diff = im_score - im_tail

    score = torch.stack([re_diff, im_diff], dim=0).norm(dim=0)
    raw_score = gamma - score.sum()
    return F.logsigmoid(raw_score).item()

def evaluate_relation_prediction_from_ids(head_id, tail_id, rel_id_gt, entity_emb, relation_emb, gamma, emb_init):
    head_vec = torch.tensor(entity_emb[head_id], dtype=torch.float32)
    tail_vec = torch.tensor(entity_emb[tail_id], dtype=torch.float32)

    scores = []
    for rel_id, rel_vec_np in enumerate(relation_emb):
        rel_vec = torch.tensor(rel_vec_np, dtype=torch.float32)
        score = rotate_score_logsigmoid(head_vec, rel_vec, tail_vec, gamma, emb_init)
        scores.append((score, rel_id))

    scores_sorted = sorted(scores, key=lambda x: -x[0])  # Higher is better
    ranked_ids = [rid for (_, rid) in scores_sorted]
    rank = ranked_ids.index(rel_id_gt) + 1

    h1 = 1 if rank <= 1 else 0
    h3 = 1 if rank <= 3 else 0
    h10 = 1 if rank <= 10 else 0
    mrr = 1.0 / rank
    return h1, h3, h10, mrr

def eval_single_triple(h, r, t, entity_emb, relation_emb, gamma, emb_init):
    try:
        return evaluate_relation_prediction_from_ids(h, t, r, entity_emb, relation_emb, gamma, emb_init)
    except Exception as e:
        return None  # Skip if error

# Load embeddings
entity_emb = np.load("../../2-DGL_Training/Training_files/entities_final.dict")
relation_emb = np.load("../../2-DGL_Training/Training_files/relation_final.dict")

# Load test triples
triples = load_id_triples("../../2-DGL_Training/Training_files/test_final.txt")

# Parallel execution using n - 5 CPU cores
n_cpus = max(1, os.cpu_count() - 5)
print(f"⚙️ Using {n_cpus} CPU cores...\n")

results = Parallel(n_jobs=n_cpus)(
    delayed(eval_single_triple)(h, r, t, entity_emb, relation_emb, gamma, emb_init)
    for h, r, t in tqdm(triples, desc="🔍 Parallel Evaluation")
)

# Aggregate metrics
metrics = {'hits@1': 0, 'hits@3': 0, 'hits@10': 0, 'mrr': 0}
total = 0

for res in results:
    if res is None:
        continue
    h1, h3, h10, mrr = res
    metrics['hits@1'] += h1
    metrics['hits@3'] += h3
    metrics['hits@10'] += h10
    metrics['mrr'] += mrr
    total += 1

# Final report
print("\n📊 Final Evaluation on test.txt (head, *, tail)")
print(f"Total Triples Evaluated: {total}")
print(f"MRR     = {metrics['mrr'] / total:.4f}")
print(f"Hits@1  = {metrics['hits@1'] / total:.4f}")
print(f"Hits@3  = {metrics['hits@3'] / total:.4f}")
print(f"Hits@10 = {metrics['hits@10'] / total:.4f}")
