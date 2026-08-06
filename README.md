# Cross-Species Aging Knowledge Integration into Agentic AI Platform Uncovers Conserved Mechanisms


### Overview
EvoAge is a comprehensive computational framework designed to accelerate discovery in:
- Aging biology  
- Age-related diseases  
- Cross-species comparative research  

It achieves this through a unified **1.2 billion–triples multi-species Knowledge Graph (KG)** built from **51 integrated public biomedical datasets**.

---

### Key Features

#### 🧬 Multi-Species Knowledge Graph
- Integrates 13 aging-focused resources, 37 general biomedical resources
- Contains **1.2 billion triples**.
- Reconciles **90,000+ genes** using a **human-centric orthology framework**.

#### 🔮 AI & Machine Learning Integration
- Operationalized using **Knowledge Graph Embedding (KGE)** models.
- Includes an **LLM-assisted agentic interface** for:
  - Link prediction  
  - Hypothesis testing  
  - Biological plausibility assessment  

---

### Summary
EvoAge is an end-to-end framework that bridges multi-species knowledge integration and graph representation learning, powered by a multi-agent hypothesis engine to evaluate complex biological queries with Knowledge Graph–derived evidence.

---

## 📁 Project Structure

The EvoAGE repository is organized into three primary functional components:

| Folder            | Description |
|-------------------|-------------|
| **Backend**       | Contains the core EvoAGE server logic. Handles API requests, manages interactions with Neo4j and Redis, and orchestrates Knowledge Graph Embedding (KGE) and LLM-based query workflows. |
| **Frontend**      | The user-facing application (Streamlit). Provides an interactive interface for natural-language querying, visualization of predictions, and exploration of the EvoAGE Knowledge Graph. |
| **pipeline**      | Includes all scripts, configurations, and utilities required for building the Knowledge Graph, training, validating, and optimizing KGE models, and experiments. Refer to the `README.md` inside this folder for detailed instructions. |

---

# 🖥️ Backend & 🎛️ Frontend Setup

The EvoAge backend (FastAPI + Gunicorn + DGL-KE + Gemini/MedGemma) provides REST APIs for querying the Knowledge Graph and running inference using trained KGE models. The frontend is a **Streamlit** UI for natural-language querying and exploring predictions. Both are set up through the same script flow.

![EvoAge setup command flow](./evoage_setup_flow.svg)

Run every command from the repository root. Do **not** run these scripts with `sudo bash`; run them as a normal user. Scripts that need system-level access call `sudo` internally, and your terminal will ask for the sudo password at that point.

### Quick Command Sequence

```bash
bash scripts/setup.sh --all
bash scripts/download_neo4j_dump.sh

# Fill all required values in Backend/.env and Frontend/.env.
# Choose either USE=gemini or USE=medgemma in Backend/.env.

# Optional local MedGemma path only:
# bash scripts/setup.sh --medgemma
# bash scripts/setup_medgemma.sh

bash scripts/setup_services.sh
bash scripts/setup.sh --check-only
bash scripts/start_app.sh
```

Complete the sections below **in order**:

1. **Python environments and `.env` files** — conda envs and dependencies for backend and frontend.
2. **Neo4j dump** — download and extract the graph dump.
3. **Configuration** — fill both `.env` files, and choose an LLM provider (Gemini or local MedGemma).
4. **Services** — install/configure Redis and Neo4j, then restore the dump.
5. **Final checks** — validate configuration and connectivity.
6. **Start** — launch backend and frontend.

---

## 1. Prepare Python Environments and `.env` Files

```bash
bash scripts/setup.sh --all
```

This creates or checks the backend and frontend conda environments, installs Python dependencies, and creates these files from the templates if they do not already exist:

- `Backend/.env`
- `Frontend/.env`

The first run can print warnings for missing Neo4j, Redis, JWT, model-path, or API-key values. That is expected before the dump, services, and model artifacts are configured.

---

## 2. Download and Extract the Neo4j Dump

```bash
bash scripts/download_neo4j_dump.sh
```

The script downloads the Neo4j dump tarball from the EvoAge Hugging Face dataset:

```text
https://huggingface.co/datasets/gauravahuja77/EvoAge/tree/main
```

Default output:

```text
data/neo4j/neo4j.dump.tar.gz
data/neo4j/neo4j.dump
```

The script uses resumable download flags for `curl` or `wget`. If a resumed download or extraction fails, remove the incomplete file under `data/neo4j/` and rerun the same command.

---

## 3. Fill All Required `.env` Values

After the dump is ready, fill `Backend/.env` and `Frontend/.env` once. `setup_services.sh` uses the service values, and `setup.sh --check-only` verifies the full application configuration before startup.

### 3.1 Database Services

For both local installs and SSH/server installs where Neo4j and Redis run on the same machine as the backend, keep database services private on `localhost`:

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=YOUR_REDIS_PASSWORD
```

### 3.2 Application URLs

Use the server IP or domain only for the backend/frontend app URLs that users open from a browser.

In `Backend/.env`:

```env
API_BASE=http://SERVER_IP_OR_DOMAIN:1026
FRONTEND_URL=http://SERVER_IP_OR_DOMAIN:8501
```

In `Frontend/.env`:

```env
API_BASE_URL=http://SERVER_IP_OR_DOMAIN:1026
```

For local-only testing, use `localhost` for the app URLs too:

```env
API_BASE=http://localhost:1026
FRONTEND_URL=http://localhost:8501
API_BASE_URL=http://localhost:1026
```

Recommended SSH/server connectivity:

```text
User browser
  -> http://SERVER_IP_OR_DOMAIN:8501
  -> Streamlit frontend on the server
  -> http://SERVER_IP_OR_DOMAIN:1026
  -> FastAPI backend on the server
  -> neo4j://localhost:7687
  -> Neo4j on the same server

FastAPI backend
  -> localhost:6379
  -> Redis on the same server
```

This exposes only the frontend/backend app ports. Neo4j and Redis stay internal unless you intentionally configure them otherwise.

### 3.3 Remaining Backend Values

Also fill these before moving on:

- DGL-EvoKG root/model/data paths
- DGL/DGL-KE input and dummy-list paths
- hypothesis-testing paths
- JWT secret
- email settings if using email or reset-password features

### 3.4 Choose One LLM Provider

**Gemini (hosted):**

```env
USE=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash-lite
```

**MedGemma (local control):**

```env
USE=medgemma
MEDGEMMA_BASE_URL=http://localhost:30001/v1
MEDGEMMA_MODEL=medgemma-27b-local
```

If you use Gemini, skip section 3.5 and continue directly to service setup.

### 3.5 MedGemma Model Setup (SGLang)

Create the separate SGLang environment:

```bash
bash scripts/setup.sh --medgemma
```

Download the MedGemma model:

```bash
conda run -n sglang hf download google/medgemma-27b-text-it \
  --local-dir ./scripts/medgemma-27b-local \
  --token YOUR_HF_READ_TOKEN \
  --max-workers 4
```

Start the local MedGemma server:

```bash
bash scripts/setup_medgemma.sh
```

> **Note:** run `bash scripts/setup_medgemma.sh` in another terminal. The model server can take time to load and must stay running while the backend uses `USE=medgemma`.

### 3.6 DGL-EvoKG Artifacts

The start script checks these artifacts before launching the backend:

- `MODEL_PATH`
- `MODEL_PATH/config.json`
- `ENT_DICT_PATH`
- `REL_DICT_PATH`
- `NODE_MAPPINGS_PATH`
- `DGLKE_DUMMY_HEAD_LIST`
- `DGLKE_DUMMY_REL_LIST`

Download or copy the required DGL-EvoKG artifacts from:

```text
https://huggingface.co/datasets/gauravahuja77/EvoAge/tree/main
```

Then set `ROOT_DIR_PATH` in `Backend/.env` to the directory containing `Model/`, `Node_Mapping/`, and `Dummy_Input/`.

---

## 4. Install/Configure Redis and Neo4j, Then Restore the Dump

```bash
bash scripts/setup_services.sh
```

This script reads service values from `Backend/.env`, syncs app URLs into both `.env` files, installs/configures Redis and Neo4j, installs APOC, restores the graph dump, repairs Neo4j permissions, restarts services, and verifies service connectivity.

It intentionally checks only the values needed for Redis and Neo4j setup. The full `.env` validation happens in the next step.

By default it uses:

```text
data/neo4j/neo4j.dump
```

Use a custom dump path when needed:

```bash
bash scripts/setup_services.sh --dump /path/to/neo4j.dump
```

Useful variants:

```bash
bash scripts/setup_services.sh --skip-neo4j
bash scripts/setup_services.sh --skip-redis
bash scripts/setup_services.sh --dry-run
```

### 4.1 Troubleshooting Neo4j Permissions

If Neo4j starts but queries fail with `AccessDeniedException` under `/var/lib/neo4j/data`, repair ownership manually:

```bash
sudo systemctl stop neo4j
sudo chown -R neo4j:neo4j /var/lib/neo4j/data
sudo chown -R neo4j:neo4j /var/lib/neo4j/plugins
sudo chmod -R u+rwX,g+rX /var/lib/neo4j/data
sudo systemctl start neo4j
```

Then test:

```bash
cypher-shell -a bolt://localhost:7687 -u neo4j -p 'YOUR_NEO4J_PASSWORD' "SHOW DATABASES;"
```

If `/etc/neo4j/neo4j.conf` uses a custom `server.directories.data` or `server.directories.plugins`, run the same ownership commands on those configured paths instead. The script detects those configured paths and fixes them automatically during setup.

---

## 5. Run Final Setup Checks

```bash
bash scripts/setup.sh --check-only
```

This does not reinstall dependencies and does not start the app. It validates required `.env` values, service connectivity, conda environments, imports, and configured URLs.

If backend/frontend URLs are not reachable during `--check-only`, that is expected before the app is started. The next step starts those processes.

---

## 6. Start Backend and Frontend

```bash
bash scripts/start_app.sh
```

This starts the backend and frontend in the background, writes logs/PID files, prints URLs, and checks whether the URLs become reachable.

Runtime defaults:

- Backend printed/checked URL comes from `Frontend/.env` `API_BASE_URL`, then `Backend/.env` `API_BASE`.
- Frontend printed/checked URL comes from `Backend/.env` `FRONTEND_URL`.
- If both localhost and server-IP values exist, the server-IP URL is preferred for display/checks.
- If values are missing/placeholders, fallbacks are `http://localhost:1026` and `http://localhost:8501`.
- If the server-IP URL fails but localhost works, the app is running and the remaining issue is network, firewall, DNS, or port exposure.

Useful commands:

```bash
bash scripts/start_app.sh --restart
bash scripts/start_app.sh --stop
bash scripts/start_app.sh --backend-only
bash scripts/start_app.sh --frontend-only
bash scripts/setup.sh --check-only
```

Once running, access the UI at:

```text
http://localhost:8501
```

If hosting on a remote machine, replace `localhost` with your server's public IP or domain.
