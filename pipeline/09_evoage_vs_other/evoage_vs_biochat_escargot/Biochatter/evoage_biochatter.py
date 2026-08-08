"""Ask natural-language questions of the EvoAge Neo4j graph using BioChatter.

BioChatter ships no knowledge graph of its own -- it generates Cypher from a
schema description and runs it against whatever database you point it at. Here
the schema comes from `schema_info.yaml` (produced by generate_schema_info.py
against the live EvoAge graph) and the database is the existing EvoAge Neo4j.

Nothing about the EvoAge stack is modified; this is read-only.

Usage:
    python evoage_biochatter.py "Which genes are associated with Alzheimer disease?"
    python evoage_biochatter.py            # interactive REPL
"""

import os
import re
import sys

import yaml
from dotenv import dotenv_values

from langchain_openai import ChatOpenAI

from biochatter.database_agent import DatabaseAgent
from biochatter.llm_connect import GptConversation, LangChainConversation

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "schema_info.yaml")

# Neo4j credentials are inherited from the EvoAge backend env so there is one
# source of truth for the graph. LLM settings live in this folder's own .env and
# override anything found there, so the benchmark is unaffected by which EvoAge
# tree is currently checked out.
EVOAGE_ENV = os.environ.get("EVOAGE_ENV", "/storage/Arushi/EvoAge-backend_3/Backend/.env")
LOCAL_ENV = os.path.join(HERE, ".env")

_env = {**dotenv_values(EVOAGE_ENV), **dotenv_values(LOCAL_ENV)}


def _cfg(key: str, default: str | None = None) -> str | None:
    value = os.environ.get(key) or _env.get(key) or default
    return value.strip() if isinstance(value, str) else value


MODEL_PROVIDER = _cfg("LLM_PROVIDER", "deepseek")
MODEL_NAME = _cfg("LLM_MODEL", _cfg("DEEPSEEK_MODEL", "deepseek-v4-flash"))
DEEPSEEK_BASE_URL = _cfg("DEEPSEEK_BASE_URL", "https://opencode.ai/zen/go/v1")

# deepseek-v4-flash spends output tokens on internal reasoning before answering,
# so a small budget yields empty content. Disable thinking and leave headroom.
DEEPSEEK_MAX_TOKENS = int(_cfg("DEEPSEEK_MAX_TOKENS", "4096"))


class DeepSeekConversation(GptConversation):
    """GptConversation pointed at the OpenCode proxy, with thinking disabled.

    GptConversation already accepts a base_url, but builds its ChatOpenAI without
    the `extra_body` the proxy needs to suppress reasoning output, and defaults
    its correction model to a GPT model that does not exist there.
    """

    def set_api_key(self, api_key: str, user: str | None = None) -> bool:
        self.user = user
        self.ca_model_name = self.model_name
        common = {
            "openai_api_key": api_key,
            "base_url": self.base_url,
            "temperature": 0,
            "max_tokens": DEEPSEEK_MAX_TOKENS,
            "model_kwargs": {"extra_body": {"thinking": {"type": "disabled"}}},
        }
        self.chat = ChatOpenAI(model_name=self.model_name, **common)
        self.ca_chat = ChatOpenAI(model_name=self.ca_model_name, **common)
        return True


def _api_keys() -> list[str]:
    """Return candidate API keys for the configured provider.

    GEMINI_API_KEY in the EvoAge env is a comma-separated pool, and at least one
    key in it is known-dead, so callers should be prepared to try the next one.
    """
    if MODEL_PROVIDER == "deepseek":
        raw = _cfg("DEEPSEEK_API_KEY") or ""
        env_var = "DEEPSEEK_API_KEY"
    elif MODEL_PROVIDER == "google_genai":
        raw = _cfg("GOOGLE_API_KEY") or _cfg("GEMINI_API_KEY") or ""
        env_var = "GOOGLE_API_KEY"
    elif MODEL_PROVIDER == "openai":
        raw = _cfg("OPENAI_API_KEY") or ""
        env_var = "OPENAI_API_KEY"
    elif MODEL_PROVIDER == "anthropic":
        raw = _cfg("ANTHROPIC_API_KEY") or ""
        env_var = "ANTHROPIC_API_KEY"
    else:
        raise SystemExit(f"unsupported LLM_PROVIDER: {MODEL_PROVIDER}")

    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise SystemExit(
            f"No API key for provider '{MODEL_PROVIDER}'.\n"
            f"Set {env_var} in {LOCAL_ENV}\n"
            f"(checked there, then {EVOAGE_ENV}, then the process environment).",
        )
    _api_keys.env_var = env_var  # type: ignore[attr-defined]
    return keys


_KEYS = _api_keys()
_KEY_INDEX = 0


def conversation_factory():
    """Build the LLM conversation BioChatter uses for query generation."""
    key = _KEYS[_KEY_INDEX]

    if MODEL_PROVIDER == "deepseek":
        conversation = DeepSeekConversation(
            model_name=MODEL_NAME,
            prompts={},
            correct=False,
            base_url=DEEPSEEK_BASE_URL,
        )
        conversation.set_api_key(api_key=key)
        return conversation

    # LangChainConversation reads the key from the environment rather than
    # taking it as an argument, so export the active key before building.
    os.environ[_api_keys.env_var] = key  # type: ignore[attr-defined]
    conversation = LangChainConversation(
        model_name=MODEL_NAME,
        model_provider=MODEL_PROVIDER,
        prompts={},
        correct=False,
    )
    conversation.set_api_key()
    return conversation


# The EvoAge graph has naming conventions BioChatter cannot infer from the
# schema alone: exact-equality matching on `name` misses almost everything,
# because disease names vary in case and punctuation ("Alzheimer Disease" vs
# "Alzheimer's disease"). Appended to every question before query generation.
QUERY_CONVENTIONS = """

Follow these conventions for this specific knowledge graph:
- Entity types mean: Gene = a gene (symbols like APOE, SIRT1, TP53);
  Protein = a protein product; ChemicalEntity = a drug, compound or metabolite,
  NEVER a gene or protein. A gene symbol must always be matched against Gene
  (or Protein) nodes, never against ChemicalEntity.
- When the question names a gene and asks what it relates to, select BOTH the
  Gene entity type and the entity type being asked about.
- Every node has `name` (descriptive, mixed case) and `name_lower` (lowercased).
  Match entities case-insensitively on `name_lower` with CONTAINS, never with
  `=` on `name`. Example: WHERE d.name_lower CONTAINS 'alzheimer'
- Gene and protein symbols (e.g. APOE, TP53) are stored in `id`, not in `name`;
  `name` holds the full descriptive name. Use `id_lower` to match a symbol.
- The graph has 1.2 billion relationships, so always end the query with a LIMIT
  (use LIMIT 25 unless the question asks for a specific number).
- Return human-readable fields (`name`, `id`), not whole nodes.
- Return only the Cypher statement, with no markdown fences or explanation.
"""


class EvoAgeDatabaseAgent(DatabaseAgent):
    """DatabaseAgent with a working Neo4j connection.

    biochatter 0.14.2's DatabaseAgent.connect() calls neo4j_utils.Driver with
    `user=`/`password=`, but that class takes `db_user=`/`db_passwd=`. The
    mismatched names are absorbed by its **kwargs, so authentication silently
    fails and the driver drops into offline mode. Also keeps the configured URI
    scheme instead of forcing bolt://.
    """

    @staticmethod
    def _clean_cypher(query: str) -> str:
        """Strip markdown fences the model wraps around generated Cypher.

        BioChatter passes the LLM output to the driver verbatim; deepseek returns
        it inside a ```cypher block, which is a syntax error.
        """
        text = (query or "").strip()
        fenced = re.search(r"```(?:cypher|sql)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fenced:
            text = fenced.group(1)
        return text.strip().strip("`").strip()

    def _generate_query(self, query: str):
        if self.use_reflexion:
            return super()._generate_query(query)
        # Same as the base implementation, but cleans the statement before it
        # reaches the driver rather than after it has already failed.
        cypher = self._clean_cypher(
            self.prompt_engine.generate_query(query + QUERY_CONVENTIONS),
        )
        return cypher, self.driver.query(query=cypher)

    def connect(self) -> None:
        import neo4j_utils as nu

        args = self.connection_args
        uri = args.get("uri") or f"{args.get('host')}:{args.get('port')}"
        if "://" not in uri:
            uri = "bolt://" + uri
        self.driver = nu.Driver(
            db_name=args.get("db_name") or "neo4j",
            db_uri=uri,
            db_user=args.get("user"),
            db_passwd=args.get("password"),
        )


def build_agent() -> DatabaseAgent:
    with open(SCHEMA_PATH) as f:
        schema_info = yaml.safe_load(f)

    uri = _cfg("NEO4J_URI", "neo4j://localhost:7687")
    # DatabaseAgent.connect() assembles "bolt://{host}:{port}" itself, so strip
    # any scheme off the configured URI and hand over the parts.
    hostport = uri.split("://", 1)[-1]
    host, _, port = hostport.partition(":")

    agent = EvoAgeDatabaseAgent(
        model_provider=MODEL_PROVIDER,
        model_name=MODEL_NAME,
        connection_args={
            "uri": uri,
            "host": host,
            "port": port or "7687",
            "user": _cfg("NEO4J_USERNAME", "neo4j"),
            "password": _cfg("NEO4J_PASSWORD"),
            "db_name": _cfg("NEO4J_DATABASE", "neo4j"),
        },
        schema_config_or_info_dict=schema_info,
        conversation_factory=conversation_factory,
        use_reflexion=False,
    )
    agent.connect()
    return agent


def answer(agent: DatabaseAgent, question: str, k: int = 10) -> None:
    """Generate Cypher, run it, and have the LLM phrase the result in prose."""
    global _KEY_INDEX

    documents = None
    for attempt in range(len(_KEYS)):
        try:
            documents = agent.get_query_results(question, k=k)
            break
        except Exception as exc:  # noqa: BLE001 -- any per-key failure should rotate
            # A dead key in the pool must advance the rotation, not abort the run.
            _KEY_INDEX = (_KEY_INDEX + 1) % len(_KEYS)
            if attempt == len(_KEYS) - 1:
                print(f"\n[all {len(_KEYS)} keys failed] {type(exc).__name__}: {exc}")
                return
            print(f"[key {attempt} failed: {type(exc).__name__}] rotating...")

    if not documents:
        print("\nNo results returned from the knowledge graph.")
        return

    cypher = documents[0].metadata.get("cypher_query", "")
    print("\n--- generated Cypher ---")
    print(cypher)
    print("\n--- raw result ---")
    print(documents[0].page_content[:2000])

    conversation = conversation_factory()
    conversation.append_system_message(
        "You are answering a biomedical question using results retrieved from "
        "the EvoAge cross-species aging knowledge graph. Answer concisely and "
        "only from the provided results. If the results are empty, say so.",
    )
    prose, _, _ = conversation.query(
        f"Question: {question}\n\nRetrieved from the knowledge graph:\n{documents[0].page_content}",
    )
    print("\n--- answer ---")
    print(prose)


def main() -> None:
    print(f"EvoAge x BioChatter | provider={MODEL_PROVIDER} model={MODEL_NAME}")
    agent = build_agent()
    print(f"connected to {_cfg('NEO4J_URI')}")

    if len(sys.argv) > 1:
        answer(agent, " ".join(sys.argv[1:]))
        return

    print("Ask a question (empty line or Ctrl-D to quit).")
    while True:
        try:
            question = input("\n> ").strip()
        except EOFError:
            break
        if not question:
            break
        answer(agent, question)


if __name__ == "__main__":
    main()
