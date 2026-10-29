"""Generate a BioCypher-style schema_info.yaml from the existing EvoAge Neo4j graph.

BioChatter normally reads the schema_info.yaml that BioCypher writes during a KG
build. The EvoAge graph was not built with BioCypher, so we introspect the live
database instead and emit the same structure. BioChatter's BioCypherPromptEngine
only needs `is_schema_info: true` plus per-entry `is_relationship` /
`present_in_knowledge_graph` / `properties` / `source` / `target` keys.

Run:
    python generate_schema_info.py
"""

import os
from collections import defaultdict

import yaml
from dotenv import dotenv_values
from neo4j import GraphDatabase

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.environ.get("EVOAGE_ENV", "/storage/Arushi/EvoAge-backend_3/Backend/.env")
OUT_PATH = os.path.join(HERE, "schema_info.yaml")

# Properties carried by every node that describe plumbing rather than biology.
# Kept in the schema anyway (the LLM may need `id`/`name` to match entities),
# but listed last so the important ones lead.
PROPERTY_ORDER = ["id", "name", "type", "node_species", "source"]

# How many nodes/rels to sample per label to discover its property keys.
SAMPLE_SIZE = 50


def sample_properties(session, cypher: str) -> dict:
    """Return {property_name: type_string} observed in a sample of the graph."""
    props: dict[str, str] = {}
    for record in session.run(cypher):
        for key, value in (record["props"] or {}).items():
            if key not in props:
                props[key] = type(value).__name__
    # stable, readable ordering
    lead = [p for p in PROPERTY_ORDER if p in props]
    rest = sorted(p for p in props if p not in lead)
    return {p: props[p] for p in lead + rest}


def main() -> None:
    env = dotenv_values(ENV_PATH)
    driver = GraphDatabase.driver(
        env["NEO4J_URI"].strip(),
        auth=(env["NEO4J_USERNAME"].strip(), env["NEO4J_PASSWORD"].strip()),
    )

    schema: dict = {"is_schema_info": True}

    with driver.session() as session:
        # Counts come from the store's count-store via APOC -- cheap even at 1.2B
        # triples, unlike a MATCH (n) RETURN count(n).
        stats = session.run("CALL apoc.meta.stats()").single()
        label_counts = stats["labels"] or {}
        rel_counts = stats["relTypesCount"] or {}

        labels = session.run("CALL db.labels()").value()
        rel_types = session.run("CALL db.relationshipTypes()").value()

        # ---- entities ----
        for label in labels:
            props = sample_properties(
                session,
                f"MATCH (n:`{label}`) RETURN properties(n) AS props LIMIT {SAMPLE_SIZE}",
            )
            count = int(label_counts.get(label, 0))
            schema[label] = {
                "represented_as": "node",
                "is_relationship": False,
                "present_in_knowledge_graph": count > 0,
                "preferred_id": "id",
                "input_label": label,
                "count": count,
                "properties": props,
            }

        # ---- relationship endpoints ----
        # db.schema.visualization() gives (source)-[type]->(target) patterns
        # without scanning the data.
        endpoints = defaultdict(lambda: {"source": set(), "target": set()})
        viz = session.run("CALL db.schema.visualization()").single()
        for rel in viz["relationships"]:
            src = list(rel.start_node.labels)
            tgt = list(rel.end_node.labels)
            if src:
                endpoints[rel.type]["source"].add(src[0])
            if tgt:
                endpoints[rel.type]["target"].add(tgt[0])

        # ---- relationships ----
        for rel_type in rel_types:
            props = sample_properties(
                session,
                f"MATCH ()-[r:`{rel_type}`]->() RETURN properties(r) AS props LIMIT {SAMPLE_SIZE}",
            )
            count = int(rel_counts.get(rel_type, 0))
            ends = endpoints.get(rel_type, {"source": set(), "target": set()})

            def collapse(values: set) -> object:
                """A single endpoint stays a string; several become a list."""
                ordered = sorted(values)
                if not ordered:
                    return None
                return ordered[0] if len(ordered) == 1 else ordered

            entry = {
                "represented_as": "edge",
                "is_relationship": True,
                "present_in_knowledge_graph": count > 0,
                # label_as_edge preserves the exact Neo4j type name, so generated
                # Cypher matches the graph even though BioChatter PascalCases keys.
                "label_as_edge": rel_type,
                "input_label": rel_type,
                "count": count,
                "properties": props,
            }
            source = collapse(ends["source"])
            target = collapse(ends["target"])
            if source is not None:
                entry["source"] = source
            if target is not None:
                entry["target"] = target
            schema[rel_type] = entry

    driver.close()

    with open(OUT_PATH, "w") as f:
        yaml.safe_dump(schema, f, sort_keys=False, default_flow_style=False)

    n_ent = sum(1 for k, v in schema.items() if isinstance(v, dict) and not v["is_relationship"])
    n_rel = sum(1 for k, v in schema.items() if isinstance(v, dict) and v["is_relationship"])
    print(f"wrote {OUT_PATH}: {n_ent} entities, {n_rel} relationships")


if __name__ == "__main__":
    main()
