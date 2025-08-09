import numpy as np
import json
import os

MODEL_DIR = "model_output/rotate_wikimedia/RotatE_wikimedia_5"

# Load embeddings
entity_emb = np.load(os.path.join(MODEL_DIR, "wikimedia_RotatE_entity.npy"))
relation_emb = np.load(os.path.join(MODEL_DIR, "wikimedia_RotatE_relation.npy"))

# Load mappings
with open(os.path.join(MODEL_DIR, "entityid2name.json")) as f:
    id2entity = json.load(f)

with open(os.path.join(MODEL_DIR, "relationid2name.json")) as f:
    id2relation = json.load(f)

# Reverse mappings
entity2id = {v: int(k) for k, v in id2entity.items()}
relation2id = {v: int(k) for k, v in id2relation.items()}

# --- USER INPUT ---
head = "neem"
relation = "MedicinalPlant_Disease"
top_k = 10

# --- Get Embeddings ---
h_idx = entity2id[head]
r_idx = relation2id[relation]
h_emb = entity_emb[h_idx]             # shape (512,)
r_emb = relation_emb[r_idx]          # shape (256,)
t_emb = entity_emb                   # shape (956027, 512)

# --- RotatE scoring ---
# Split embeddings into real and imaginary
def split_complex(x):
    return x[..., :x.shape[-1] // 2], x[..., x.shape[-1] // 2:]

h_re, h_im = split_complex(h_emb)          # (256,), (256,)
r_re, r_im = split_complex(r_emb)          # (128,), (128,)
t_re, t_im = split_complex(t_emb)          # (N, 256), (N, 256)

# Now match r_re/r_im to size 256 by duplicating
r_re = np.concatenate([r_re, r_re])
r_im = np.concatenate([r_im, r_im])

# Compute predicted tail embedding
pred_re = h_re * r_re - h_im * r_im
pred_im = h_re * r_im + h_im * r_re

# L2 distance
dist = np.linalg.norm(t_re - pred_re, axis=1) + np.linalg.norm(t_im - pred_im, axis=1)

# Get top-k predicted tail entities
top_k_indices = np.argsort(dist)[:top_k]
top_k_entities = [id2entity[str(i)] for i in top_k_indices]

print(f"\nTop-{top_k} tail predictions for ({head}, {relation}, ?):\n")
for i, ent in enumerate(top_k_entities, 1):
    print(f"{i}. {ent}")
