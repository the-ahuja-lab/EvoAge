# ESCARGOT Setup & Changes Documentation

This document records all modifications made to the **ESCARGOT** repository to enable execution with a custom **Neo4j Knowledge Graph** and **OpenAI API (`gpt-4o-mini`)**.

---

## 1. Environment & Dependencies Fixed

The following Python dependencies were missing or out-of-sync in the environment and were installed/updated:

- **`pytz` & `pandas`**: Required for data frame operations inside `escargot.memory`.
- **`backoff`**: Required for exponential backoff retries in `chatgpt.py`.
- **`gqlalchemy`**: Interfacing library for Neo4j / Memgraph graph databases.
- **`raphtory`**: Required by ESCARGOT's temporal graph memory.
- **`chromadb`**: Vector database client required by the memory module.
- **`openai`**: OpenAI Python SDK.

---

## 2. Code Changes & Bug Fixes

### A. Model Initializer in `escargot.py`
- **File**: `escargot/escargot.py`
- **Issue**: The original initialization code only checked for `'ollama'` and `'azuregpt'`, throwing an error when initializing with standard OpenAI (`'chatgpt'` or `'openai'`).
- **Fix**: Updated `Escargot.__init__` to instantiate `language_models.ChatGPT` when `'chatgpt'` or `'openai'` is specified in the config.

```python
elif 'chatgpt' in config or 'openai' in config or 'openai' in model_name:
    self.lm = language_models.ChatGPT(config, model_name=model_name)
```

---

### B. Neo4j Authentication in `neo4j.py` & `config.py`
- **File**: `escargot/cypher/neo4j.py` & `agents/config.py`
- **Issue**: `gqlalchemy.Neo4j` client connection was initially initiated without authentication credentials, leading to `Neo.ClientError.Security.Unauthorized`.
- **Fix**:
  1. Updated `agents/config.py` with custom Neo4j endpoint details (`192.168.3.153:3333`, username: `neo4j`, password: `huihuihui`).
  2. Modified `Neo4jClient.__init__` in `neo4j.py` to read `username` and `password` parameters and pass them directly to `gqlalchemy.Neo4j`:

```python
self.username = self.config.get("username", "neo4j")
self.password = self.config.get("password", "")
self.client = Neo4j(host=self.host, port=self.port, username=self.username, password=self.password)
```

---

### C. Added Missing `get_embedding()` in `chatgpt.py`
- **File**: `escargot/language_models/chatgpt.py`
- **Issue**: Calling `escargot.ask()` raised `AttributeError: 'ChatGPT' object has no attribute 'get_embedding'` when writing natural language outputs to memory.
- **Fix**: Added the `embedding_id` property and implemented `get_embedding(self, text_to_embed)` using `OpenAI.embeddings.create()`:

```python
def get_embedding(self, text_to_embed):
    response = self.client.embeddings.create(
        model=self.embedding_id,
        input=text_to_embed
    )
    return response.data[0].embedding
```

---

### D. Fixed Logger Initialization in `chatgpt.py`
- **File**: `escargot/language_models/chatgpt.py`
- **Issue**: `self.logger` was missing from `ChatGPT.__init__`, causing `AttributeError: 'NoneType' object has no attribute 'warning'`.
- **Fix**: Guaranteed logger fallback initialization using `logging.getLogger(__name__)`.

---

## 3. Custom Runner Script Created (`ask_question.py`)

- **File**: `ask_question.py` (in root directory)
- **Usage**:

```bash
export OPENAI_API_KEY="your-openai-api-key"
python ask_question.py "Your question here"
```

- **Execution details**:
  1. Connects to Neo4j instance at `192.168.3.153:3333`.
  2. Extracts graph schema dynamically (`db.schema.visualization()`).
  3. Uses `gpt-4o-mini` to construct a dynamic Graph-of-Thoughts (GoT) plan.
  4. Generates and runs Cypher queries against Neo4j.
  5. Returns a natural language response.
<!-- python ask_question.py "Which of the following binds to the drug Leucovorin? 1. CAD 2. PDS5B 3. SEL1L 4. ABCC2 5. RMI1

?" -->