"""Sanity-check Escargot against the AlzKB sample graph.

Question being answered: does Escargot's framework work at all, or is its
failure on the EvoAge graph caused purely by the wrong schema?

Controls held constant with the failing EvoAge run:
  - same model (ollama qwen2.5:7b)
  - same Escargot version and code (unmodified)
  - same question shape
Only the graph changes -- here it is AlzKB, the shape Escargot was built for.

Unlike the EvoAge ask_question.py, this does NOT hardcode a schema: leaving
node_types/relationship_types empty makes Escargot introspect the graph itself
via get_schema(), which is its native path.

Points at the throwaway container on :7688. Never touches the EvoAge graph.

Run:
    python ask_alzkb.py                       # default question
    python ask_alzkb.py "your question"
"""

import os
import sys

ESCARGOT_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "escargot")
sys.path.insert(0, ESCARGOT_ROOT)

from escargot import Escargot  # noqa: E402

config = {
    "ollama": {
        "model_id": os.environ.get("ALZKB_MODEL", "qwen2.5:7b"),
        "embedding_id": "nomic-embed-text:latest",
        "prompt_token_cost": 0.0,
        "response_token_cost": 0.0,
        "temperature": 0.7,
        "max_tokens": 4096,
        "stop": None,
    },
    # The isolated sanity-check instance, NOT the EvoAge graph on :3333.
    "neo4j": {
        "host": os.environ.get("ALZKB_HOST", "localhost"),
        "port": int(os.environ.get("ALZKB_PORT", "7688")),
        "username": "neo4j",
        "password": "alzkbtest",
    },
}

DEFAULT_QUESTION = "Which biological processes does the gene AGT participate in?"


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION

    print(
        f"\n--- Escargot sanity check ---\n"
        f"model : ollama ({config['ollama']['model_id']})\n"
        f"graph : AlzKB sample at {config['neo4j']['host']}:{config['neo4j']['port']}\n"
    )

    # No node_types/relationship_types -> Escargot introspects the schema itself.
    escargot = Escargot(config, model_name="ollama")

    if escargot.graph_client is None:
        print("FAILED: no graph client -- check the container is running on :7688")
        return

    print("schema Escargot discovered:")
    print("  node types        :", str(escargot.node_types)[:400])
    print("  relationship types:", str(escargot.relationship_types)[:400])

    print(f"\nQuestion: {question}\n")
    response = escargot.ask(question, debug_level=1, answer_type="natural")
    print("\n--- Answer ---")
    print(response)


if __name__ == "__main__":
    main()
