# Cross-Species Aging Knowledge Integration through a Knowledge-Grounded AI Platform Uncovers Conserved Mechanisms


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
| **pipeline**      | Includes all scripts, configurations, and utilities required for building the Knowledge Graph, training, validating, and optimizing KGE models, and experiments. |
| **docs**          | Source for the EvoAge documentation site, published at [the-ahuja-lab.github.io/EvoAge](https://the-ahuja-lab.github.io/EvoAge/). |

---

## 🐳 Quick Start with Docker (Recommended)

A prebuilt image bundles the backend, frontend, and their Python dependencies, so you can skip the conda setup below. You still need Neo4j and Redis on the host (sections 1 and 2).

```bash
docker pull ahujalab/evoage-project:latest
```

Full run command and environment-variable reference:
**[hub.docker.com/r/ahujalab/evoage-project](https://hub.docker.com/r/ahujalab/evoage-project)**

Continue below for the manual (non-Docker) installation.

---

## 🧰 Prerequisites

| Requirement | Notes |
|---|---|
| **OS** | Ubuntu / Debian. All commands below use `apt` and `systemd`. |
| **Java 17** | Required by Neo4j (installed in section 1). |
| **Conda** | Miniconda or Anaconda, for the Python environments. |
| **Python 3.11** | Created inside the conda environments. |
| **NVIDIA GPU + CUDA** | Required for DGL-KE inference. |
| **Extra GPU memory** | Only if you self-host MedGemma — the 27B model needs roughly 60 GB VRAM (an 80 GB card). Not needed if you use Gemini. |
| **Disk space** | Tens of GB for the Neo4j dump, the restored graph, and model artifacts. |

Run every command from the directory indicated in each section. Do **not** run these steps with `sudo bash`; run them as a normal user and let individual commands call `sudo` where shown.

---

## 1. Neo4j Setup (required for KG queries)

The EvoAGE backend uses Neo4j as the primary graph database.
Follow the steps below to start Neo4j, configure it, restore a database from a dump, and enable the APOC plugin.

---

### 1.1 Install, Start & Configure Neo4j

#### Install Neo4j
```bash
# Install Java (Neo4j requires Java 17)
sudo apt update
sudo apt install -y openjdk-17-jdk

# Add Neo4j repository
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo "deb https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list

# Install Neo4j
sudo apt install -y neo4j
```

#### Check installed Neo4j version
```bash
neo4j --version
```

#### Set initial password BEFORE first start
```bash
sudo neo4j-admin dbms set-initial-password <SET_YOUR_NEO4J_PASSWORD>
```

#### Start Neo4j
```bash
sudo systemctl start neo4j
sudo systemctl status neo4j
```

#### Test login
```bash
cypher-shell -u neo4j -p '<YOUR_NEO4J_PASSWORD>' "SHOW DATABASES;"
```
---

### 1.2 Restore Database from a .dump File

Neo4j must be stopped before restoring. You can get the Neo4j dump file from
https://huggingface.co/datasets/gauravahuja77/EvoAge/tree/main

```bash
sudo systemctl stop neo4j
```

Copy the dump into Neo4j's import directory. If your downloaded file has a different
name, rename it to `neo4j.dump` or adjust the paths below to match:

```bash
sudo cp neo4j.dump /var/lib/neo4j/import/
```

```bash
sudo neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/import/ \
  --overwrite-destination=true
```

#### Check graph is built by getting total node count
This command will show total nodes in EvoAge graph
```bash
cypher-shell -u neo4j -p '<YOUR_NEO4J_PASSWORD>' "MATCH (n) RETURN count(n) AS nodeCount;"
```

#### Open .conf file
```bash
sudo nano /etc/neo4j/neo4j.conf
```

#### Add or un-comment these lines:

```ini
# Enable APOC Core
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*

# Allow file imports (optional)
server.directories.import=import
```

#### Start Neo4j after restoration
```bash
sudo systemctl enable neo4j

sudo systemctl start neo4j

# This will show the working status of neo4j
sudo systemctl status neo4j
```
---

### 1.3 Install APOC Plugin (Required)

#### Stop Neo4j before adding plugins
```bash
sudo systemctl stop neo4j
```

#### Go to Neo4j plugin directory
```bash
cd /var/lib/neo4j/plugins
```

#### Check existing plugins
```bash
ls -l
```

#### Download APOC (example for Neo4j 5.x)
```bash
sudo wget https://github.com/neo4j/apoc/releases/download/5.26.14/apoc-5.26.14-core.jar
```

#### Set correct permissions
```bash
sudo chown neo4j:neo4j apoc-5.26.14-core.jar
```

#### Enable APOC in neo4j.conf
Open:
```bash
sudo nano /etc/neo4j/neo4j.conf
```

Ensure this line exists:
```ini
dbms.security.procedures.unrestricted=apoc.*
```

#### Restart Neo4j
```bash
sudo systemctl restart neo4j
```

Neo4j + APOC is now ready for the EvoAGE backend!

---

## 2. Redis Setup (required for caching and job state)

The EvoAge backend uses Redis for caching and background job state. Install and configure it before starting the backend.

---

### 📌 Redis Installation & Configuration

#### Update package lists
```bash
sudo apt update
```

#### Install Redis
```bash
sudo apt install redis-server -y
```

#### Enable Redis to start automatically
```bash
sudo systemctl enable redis-server
```

#### Configure Redis password
```bash
REDIS_PASSWORD="YOUR_REDIS_PASSWORD_HERE"
sudo sed -i "s/^# requirepass .*/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
```

#### Restart Redis to apply changes
```bash
sudo systemctl restart redis-server
```

#### Test Redis authentication
```bash
redis-cli
127.0.0.1:6379> AUTH default <YOUR_PASSWORD>
OK
127.0.0.1:6379> PING
PONG
```

#### Check Redis service status
```bash
systemctl status redis-server --no-pager
```

Redis setup completed successfully! 🎉

---

## 3. Backend Setup (FastAPI + Gunicorn + DGL-KE + Gemini/MedGemma)

The EvoAge backend provides REST APIs for querying the Knowledge Graph, running inference using trained KGE models, and interfacing with the frontend.

Follow the steps below to configure and run the backend.

---

### 3.1 Navigate to the Backend Directory
```bash
cd Backend
```
---

### 3.2 Create and Activate Conda Environment
```bash
conda create -n evoage_backend python=3.11 -y
conda activate evoage_backend
```

---

### 3.3 Install Backend Dependencies

Install dependencies from `requirements.txt`:
```bash
pip install -r requirements.txt
```

Install local DGL-KE:
```bash
pip install -e dgl-ke/python
```

---

### 3.4 Download DGL-EvoKG Model Artifacts

The trained KGE model and node-mapping files are too large for git, so they are distributed
through the EvoAge Hugging Face dataset:

**https://huggingface.co/datasets/gauravahuja77/EvoAge/tree/main/DGL-EvoKG**

Download them into `Backend/DGL-EvoKG/`, alongside the `Dummy_Input/` and
`HypothesisTesting/` folders already in the repository:

```bash
# from the Backend directory
pip install -U "huggingface_hub[cli]"

hf download gauravahuja77/EvoAge \
  --repo-type dataset \
  --include "DGL-EvoKG/Model/*" "DGL-EvoKG/Node_Mapping/*" \
  --local-dir .
```

The resulting layout should be:

```text
Backend/DGL-EvoKG/
├── Dummy_Input/         # in the repository
├── HypothesisTesting/   # in the repository
├── Model/               # downloaded — trained KGE model, entity/relation dicts
└── Node_Mapping/        # downloaded — node ID mappings
```

The backend checks for these artifacts at startup. Set `ROOT_DIR_PATH` in `.env` to the
directory containing `Model/`, `Node_Mapping/`, and `Dummy_Input/`, and make sure
`MODEL_PATH`, `ENT_DICT_PATH`, `REL_DICT_PATH`, and `NODE_MAPPINGS_PATH` resolve to the
files you just downloaded.

---

### 3.5 Configure Environment Variables

Create your `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

Edit the file:

```bash
nano .env
```

Fill in the required values:

**Database services** — keep these on `localhost` when Neo4j and Redis run on the same machine as the backend:

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_USERNAME=default
REDIS_PASSWORD=YOUR_REDIS_PASSWORD
```

**Application URLs** — use the server IP or domain only for the URLs users open in a browser:

```env
API_BASE=http://SERVER_IP_OR_DOMAIN:1026
FRONTEND_URL=http://SERVER_IP_OR_DOMAIN:8501
```

For local-only testing, use `localhost` for these too.

**Authentication** — required; the backend will not start without a JWT secret:

```env
JWT_SECRET_KEY=YOUR_SECRET_KEY
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Model and data paths** — point these at the artifacts downloaded in section 3.4 (`ROOT_DIR_PATH`, `MODEL_PATH`, `ENT_DICT_PATH`, `REL_DICT_PATH`, `NODE_MAPPINGS_PATH`, `DGLKE_INPUT_DIR`, `DGLKE_DUMMY_HEAD_LIST`, `DGLKE_DUMMY_REL_LIST`, and the hypothesis-testing paths).

```env
DGLKE_DEVICE=0
DGLKE_SFUNC=logsigmoid
DEFAULT_ENTITY_PROP=id
```

**Email settings** (`MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_FROM`, `MAIL_ADMIN_EMAIL`) are needed only for account verification and password-reset features. Use a Gmail **App Password**, not your account password.

See `.env.example` for the complete list with inline comments.

---

### 3.6 Choose Your LLM Provider

The hypothesis pipeline routes every filter / agent / judge call to a single LLM backend, selected by `USE`. Choose one:

**Option A — Gemini (hosted).** No extra setup; skip section 3.7.

```env
USE=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash-lite
```

Comma-separate several keys to rotate between them.

**Option B — MedGemma (local).** Runs on your own GPU; complete section 3.7 first.

```env
USE=medgemma
MEDGEMMA_BASE_URL=http://localhost:30001/v1
MEDGEMMA_MODEL=medgemma-27b-local
```

> **Note:** `GEMINI_API_KEY` must be set even when `USE=medgemma`. The configuration is validated at startup and the backend will not start without it.

---

### 3.7 Running the MedGemma Model (only for `USE=medgemma`)

**Skip this section entirely if you chose Gemini.**

You can download the **MedGemma** 27B model from Hugging Face and deploy it locally using **SGLang**. Create a dedicated Conda environment for serving LLMs with SGLang.

```bash
# Create and activate a new Conda environment
conda create -n sglang python=3.11 -y
conda activate sglang

# Upgrade pip
pip install --upgrade pip

# Install a fixed SGLang version
pip install "sglang[all]==0.5.15.post1"
```
---
#### Model Download

`google/medgemma-27b-text-it` is a gated repository. Accept the licence on the model page with your Hugging Face account, then use a read token:

```bash
hf download google/medgemma-27b-text-it \
  --local-dir ./medgemma-27b-local \
  --token YOUR_HF_READ_TOKEN \
  --max-workers 4
```

---

#### SGLang Server Setup & Deployment

Then run `run_medgemma.sh` which configures the execution environment, sets up log paths, activates the required Conda environment, and launches the MedGemma model using **SGLang** as a background service.
```bash
./run_medgemma.sh
```

#### What the Shell Script Does:

1. **Environment Setup:** Sets temporary directory variables (`TMPDIR`, `TEMP`, `TMP`), CUDA/Triton/Torch cache paths, and library path exports to avoid disk space issues and caching conflicts.
2. **Conda Activation:** Initializes Conda and activates the target environment (`sglang`).
3. **Log Directory Creation:** Automatically creates a `logs/` directory in the current working script location.
4. **Server Launch via SGLang:**
* Launches `sglang.launch_server` in the background using `nohup`.
* Binds to host `0.0.0.0` on port `30001`.
* Allocates `90%` static GPU memory (`--mem-fraction-static 0.9`).
* Sets a maximum context length of `32,000` tokens and a chunked prefill size of `2,048`.
* Configures the schedule policy to `lpm` (Longest Prefix Match).
* Redirects stdout and stderr outputs to `logs/medgemma_port30001.log`.

The model takes several minutes to load. Wait for the server to be ready before starting the backend:

```bash
tail -f logs/medgemma_port30001.log
curl http://localhost:30001/v1/models
```

> **Note:** run `./run_medgemma.sh` in a separate terminal. The model server must stay running the whole time the backend uses `USE=medgemma`.
>
> **GPU note:** SGLang reserves ~90% of its GPU's memory. If the backend loads DGL-KE onto the same GPU, they will contend for memory — on a multi-GPU host, point `DGLKE_DEVICE` at a different GPU than the one SGLang uses.

---

### 3.8 Run the Backend Server

Run the backend using Gunicorn + Uvicorn worker:
```bash
gunicorn -w 1 --timeout 300 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:1026
```
Backend will be available at:
```text
http://localhost:1026
```
Or via remote server:
```text
http://<SERVER_IP>:1026
```

> The backend loads the trained KGE model onto the GPU at startup, which can take several minutes. It is ready once the logs show `Application startup complete.`

---

## 4. Frontend Setup (Streamlit UI)

The EvoAge frontend is built using **Streamlit**, providing an interactive interface for exploring the Knowledge Graph, embeddings, and agentic system.  
Follow the steps below to set up and run the frontend. Start the backend (section 3) first — the UI calls it on every query.

---

### 4.1 Navigate to the Frontend Directory
```bash
cd Frontend
```

---

### 4.2 Create and Activate Conda Environment
```bash
conda create -n evoage_frontend python=3.11 -y
conda activate evoage_frontend
```

---

### 4.3 Install Dependencies
Install the required Python packages using `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

### 4.4 Configure Environment Variables
Create a new `.env` file by copying the example template:
```bash
cp .env.example .env
```

Open the file and update the necessary values:
```bash
nano .env
```

Set the backend API URL to match `API_BASE` from `Backend/.env`:

```env
API_BASE_URL=http://SERVER_IP_OR_DOMAIN:1026
```

Use `http://localhost:1026` for local-only testing.

---

### 4.5 Run the Frontend
Start the Streamlit application using:
```bash
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.enableCORS=false
```

Once running, access the UI at:
```text
http://localhost:8501
```
If hosting on a remote machine, replace `localhost` with your server's public IP.

---

## 📖 Documentation

Full documentation — data collection, KG construction, orthology mapping, model training, and analyses — is published at
**[the-ahuja-lab.github.io/EvoAge](https://the-ahuja-lab.github.io/EvoAge/)**
