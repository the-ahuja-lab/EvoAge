# Cross-Species Aging Knowledge Integration into Agentic AI Platform Uncovers Conserved Mechanisms


### Overview
EvoAge is a comprehensive computational framework designed to accelerate discovery in:
- Aging biology  
- Age-related diseases  
- Cross-species comparative research  

It achieves this through a unified **1.04 billion–triples multi-species Knowledge Graph (KG)** built from **48 integrated public biomedical datasets**.

---

### Key Features

#### 🧬 Multi-Species Knowledge Graph
- Integrates 48 heterogeneous biomedical datasets.
- Contains **1.04 billion triples**.
- Reconciles **80,000+ genes** using a **human-centric orthology framework**.

#### 🔮 AI & Machine Learning Integration
- Operationalized using **Knowledge Graph Embedding (KGE)** models.
- Includes an **LLM-assisted agentic interface** for:
  - Link prediction  
  - Hypothesis testing  
  - Biological plausibility assessment  

#### 📈 Performance Highlights
- Significantly outperforms general-purpose LLMs in evaluating biological plausibility.
- Enables high-confidence predictions across species.

---

### Summary
EvoAge provides a robust, AI-driven platform integrating massive biomedical knowledge with cutting-edge ML techniques, enabling transformative insights into aging and age-related diseases.

---

## 📁 Project Structure

The EvoAGE repository is organized into three primary functional components:

| Folder            | Description |
|-------------------|-------------|
| **Backend**       | Contains the core EvoAGE server logic. Handles API requests, manages interactions with Neo4j and Redis, and orchestrates Knowledge Graph Embedding (KGE) and LLM-based query workflows. |
| **Frontend**      | The user-facing application (Streamlit). Provides an interactive interface for natural-language querying, visualization of predictions, and exploration of the EvoAGE Knowledge Graph. |
| **EvoAGE_Training** | Includes all scripts, configurations, and utilities required for training, validating, and optimizing KGE models. Refer to the `README.md` inside this folder for detailed instructions. |



## ⚙️ Backend Prerequisites: Neo4j & Redis Setup

Before using the EvoAge backend or frontend, you must install and configure:

1. Neo4j Graph Database (required for KG queries)

2. Redis Server (required before building or running the EvoAge Docker backend)

This section provides complete setup instructions in clean Markdown format for direct use in your GitHub README.

### 1. Neo4j Setup (required for KG queries)

The EvoAGE backend uses Neo4j as the primary graph database.
Follow the steps below to start Neo4j, configure it, restore a database from a dump, and enable the APOC plugin.

---

#### 1.1 Install,Start & Configure Neo4j

##### Install Neo4j 
```
# Install Java (Neo4j requires Java 17)
sudo apt update
sudo apt install -y openjdk-17-jdk

# Add Neo4j repository
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo "deb https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list

# Install Neo4j
sudo apt install -y neo4j

```
##### Check installed Neo4j version
```bash
neo4j --version
```
##### Set initial password BEFORE first start
```
sudo neo4j-admin dbms set-initial-password <SET_YOUR_NEO4J_PASSWORD>
```

##### Start Neo4j
```
sudo systemctl start neo4j
sudo systemctl status neo4j
```

##### Test login
```
cypher-shell -u neo4j -p <'YOUR_NEO4J_PASSWORD'> "SHOW DATABASES;"
```
---

##### 1.2 Restore Database from a .dump File

Neo4j must be stopped before restoring. You can get EvoAge_neo4j.dump file from https://zenodo.org/records/17711174

```
sudo systemctl stop neo4j
```
```
sudo cp neo4j.dump /var/lib/neo4j/import/
```
```
sudo neo4j-admin database load neo4j \
  --from-path=/var/lib/neo4j/import/ \
  --overwrite-destination=true
```
##### Check graph is built by geting total node count
This command will show total nodes in EvoAge graph
```
cypher-shell -u neo4j -p <'YOUR_neo4j_PASSWORD'> "MATCH (n) RETURN count(n) AS nodeCount;"
```

##### open .conf file
```
sudo nano /etc/neo4j/neo4j.conf
```
##### Add or un-comment these lines:

```
# Enable APOC Core
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*

# Allow file imports (optional)
server.directories.import=import

```

##### Start Neo4j after restoration
```bash
sudo systemctl enable neo4j

sudo systemctl start neo4j

# This will show the working status of neo4j
sudo systemctl status neo4j
```
---

#### 1.3 Install APOC Plugin (Required)

##### Stop Neo4j before adding plugins
```bash
sudo systemctl stop neo4j
```

##### Go to Neo4j plugin directory
```bash
cd /var/lib/neo4j/plugins
```

##### Check existing plugins
```bash
ls -l
```

##### Download APOC (example for Neo4j 5.x)
```bash
sudo wget https://github.com/neo4j/apoc/releases/download/5.26.14/apoc-5.26.14-core.jar
```

##### Set correct permissions
```bash
sudo chown neo4j:neo4j apoc-5.26.14-core.jar
```

##### Enable APOC in neo4j.conf
Open:
```bash
sudo nano /etc/neo4j/neo4j.conf
```

Ensure this line exists:
```
dbms.security.procedures.unrestricted=apoc.*
```

##### Restart Neo4j
```bash
sudo systemctl restart neo4j
```

Neo4j + APOC is now ready for the EvoAGE backend.!

## 2. Redis Setup (Required Before Building the Docker Image)

Before running the EvoAGE Docker container, a Redis server must be installed and configured on your system.

The following script installs Redis, enables it as a service, sets a password, and verifies that the setup is correct.

---

### 📌 Redis Installation & Configuration Script

#### **Set your Redis password**
```bash
sudo apt update
```

#### **Install Redis**
```bash
sudo apt install redis-server -y
```

#### **Enable Redis to start automatically**
```bash
sudo systemctl enable redis-server
```

#### **Configure Redis password**
```bash
REDIS_PASSWORD="YOUR_REDIS_PASSWORD_HERE"
sudo sed -i "s/^# requirepass .*/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
```

#### **Restart Redis to apply changes**
```bash
sudo systemctl restart redis-server
```

#### **Test Redis authentication**
```bash
redis-cli
127.0.0.1:6379> AUTH default <YOUR_PASSWORD>
OK
127.0.0.1:6379> PING
PONG
```

#### **Check Redis service status**
```bash
systemctl status redis-server --no-pager
```

Redis setup completed successfully! 🎉

## 3. Frontend Setup (Streamlit UI)

The EvoAge frontend is built using **Streamlit**, providing an interactive interface for exploring the Knowledge Graph, embeddings, and agentic system.  
Follow the steps below to set up and run the frontend locally.

---

### 3.1 Navigate to the Frontend Directory
```bash
cd frontend
```

---

### 3.2 Create and Activate Conda Environment
```bash
conda create -n evoage_frontend python=3.11 -y
conda activate evoage_frontend
```

---

### 3.3 Install Dependencies
Install the required Python packages using `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

### 3.4 Configure Environment Variables
Create a new `.env` file by copying the example template:
```bash
cp .env.example .env
```

Open the file and update the necessary values:
```bash
nano .env
```

Examples of variables to configure:
- Backend API URL   

---

### 3.5 Run the Frontend
Start the Streamlit application using:
```bash
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.enableCORS=false
```

Once running, access the UI at:
```bash
http://localhost:8501
```
If hosting on a remote machine, replace `localhost` with your server’s public IP.

---
## 4. Backend Setup (FastAPI + Gunicorn + DGL-KE)

The EvoAge backend provides REST APIs for querying the Knowledge Graph, running inference using trained KGE models, and interfacing with the frontend.

Follow the steps below to configure and run the backend.

---

### 4.1 Navigate to the Backend Directory
```bash
cd backend
```
---

### 4.2 Configure Environment Variables

Create your .env file based on .env.example:
```bash
cp .env.example .env
```

Edit the file:

```bash
nano .env
```
Fill in the required values:

- Neo4j URI, username, password
- Redis connection details
- Model paths
- API keys

---
### 4.3 Create and Activate Conda Environment
```bash
conda create -n evoage_backend python=3.11 -y
conda activate evoage_backend
```

---

### 4.4 Install Backend Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

Install local DGL-KE:
```bash
pip install -e dgl-ke/python
```
---

### 4.5 Run the Backend Server

Install via Poetry:
```bash
poetry install
```
Run the backend using Gunicorn + Uvicorn worker:
```bash
poetry run gunicorn -w 1 --timeout 300 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:1026
```
Backend will be available at:
```bash
http://localhost:1026
```
Or via remote server:
```bash
http://<SERVER_IP>:1026
