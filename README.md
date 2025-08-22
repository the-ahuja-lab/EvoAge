# EvoAge-backend

FastAPI service for EvoKG predictions using a bundled (patched) DGL-KE RotatE model.

## Requirements
- Linux/macOS
- **Python 3.11.2**
- NVIDIA GPU(32 GB) + CUDA (recommended). CPU works but is slower.
- `git`, `pip`

## Quick start

```bash
# 1) Clone
git clone git@github.com:the-ahuja-lab/EvoAge-backend.git
cd EvoAge-backend

# 2) Create env and install deps

# Option A: pip + venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt


# 3) Configure environment
cp .env.example .env
# Edit .env and fill in the Variables

# 4) Run the server
bash deploy.sh

# 5) Watch logs
tail -f neo4j_api_logs.log
```

## Required files to exist:
- MODEL_PATH/config.json
- ENT_DICT_PATH, REL_DICT_PATH
- NODE_MAPPINGS_PATH
- Dummy warm-up lists (DGLKE_DUMMY_HEAD_LIST, DGLKE_DUMMY_REL_LIST)

## Run
```bash
bash deploy.sh
```
- API listens at http://0.0.0.0:1026/
- Logs: neo4j_api_logs.log (repo root)

## API (reference)

> Base URL: `http://<host>:1026`  
> Auth: endpoints marked **(auth)** require `Authorization: Bearer <JWT>`  
> Rate limiting: most write/identity endpoints are limited to **10 req/min** via `fastapi-limiter`.

### Auth (`/auth`)
- **POST** `/auth/signup` — Create a new account (blocks common free email domains; validates OpenAI key).
- **POST** `/auth/login` — Exchange username/password for a JWT.

### Users (`/users`)
- **GET** `/users/me` *(auth)* — Fetch the current user’s profile.
- **PUT** `/users/me/query_limits` *(auth)* — Update your own query-limit settings.
- **PUT** `/users/{username}/query_limit_admin` — Admin sets another user’s query limit.
- **POST** `/users/send_welcome_email` — Send a welcome email to a given address.
- **PUT** `/users/me/openai_api_key` *(auth)* — Save/rotate your OpenAI API key.

### Utils (`/utils`)
- **POST** `/utils/validate_openai_key` — Quickly verify if an OpenAI API key is valid.

### Graph / Neo4j
- **GET** `/sample_triples` — Fetch example triples for a relation (fast preview).
- **GET** `/get_nodes_by_label` — List up to 10 nodes of a label with all properties.
- **GET** `/subgraph` — Return a small neighborhood around a starting node.
- **GET** `/search_biological_entities` — Full-text search across entity types (top hits per type).
- **GET** `/entity_relationships` — Get count + sample of related entities (optional relation filter).
- **GET** `/check_relationship` — Check if two entities are connected and by which relation.

### KGE Predictions (DGL-KE)
- **GET** `/predict_tail` — Given head + relation, return top-K candidate tails with scores.
- **GET** `/get_prediction_rank` — For head + relation, report rank/score of a specific tail.

## Vendored DGL-KE (local enhancements)

This project includes a local copy of DGL-KE under `dgl-ke/` with two small, performance-oriented tweaks:

- `dgl-ke/python/dglke/utils.py` — adds in-process caching of `entities.dict` and `relation.dict` to avoid repeated parsing during inference.
- `dgl-ke/python/dglke/models/infer.py` — adds `ScoreInfer.get_rank_score(...)` to return the rank/score of a user-specified tail for a given (head, relation).

## Troubleshooting
- FileNotFoundError → check absolute paths in .env.
- GPU errors → set DGLKE_DEVICE=cpu to verify; confirm CUDA/driver versions if using GPU.
