"""Load the AlzKB sample triples into the throwaway sanity-check Neo4j.

Purpose: run Escargot against the graph shape it was actually built for, to
establish whether the framework works at all before blaming the EvoAge schema.

This writes ONLY to the isolated container on port 7688. It never touches the
EvoAge graph on port 3333.

Source data: KRAGEN/test.csv -- 1000 AlzKB triples. This is a diagnostic
fixture, not a benchmark corpus.

Run:
    python load_alzkb_sample.py
"""

import ast
import csv
import os

from neo4j import GraphDatabase

CSV_PATH = os.environ.get(
    "ALZKB_CSV",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "alzkb_sample.csv"),
)
URI = os.environ.get("ALZKB_URI", "bolt://localhost:7688")
USER = os.environ.get("ALZKB_USER", "neo4j")
PASSWORD = os.environ.get("ALZKB_PASSWORD", "alzkbtest")

# The CSV carries human-readable relationship phrases, but AlzKB's graph uses
# uppercase concatenated type names -- the ones Escargot's cyphergpt.py prompt
# has been trained on. Map to those so the sanity check exercises Escargot's
# real expectations rather than a shape it has never seen.
REL_MAP = {
    "body part over-expresses the gene": "BODYPARTOVEREXPRESSESGENE",
    "body part under-expresses the gene": "BODYPARTUNDEREXPRESSESGENE",
    "gene participates in the biological process": "GENEPARTICIPATESINBIOLOGICALPROCESS",
    "chemical or drug decreases the gene expression": "CHEMICALDECREASESEXPRESSION",
    "chemical or drug increases the gene expression": "CHEMICALINCREASESEXPRESSION",
    "chemical or drug binds the gene": "CHEMICALBINDSGENE",
    "symptom manifestation of the disease": "SYMPTOMMANIFESTATIONOFDISEASE",
    "gene in the pathway": "GENEINPATHWAY",
    "gene interacts with the gene": "GENEINTERACTSWITHGENE",
    "disease localizes to anatomy or body part": "DISEASELOCALIZESTOANATOMY",
    "gene has a molecular function": "GENEHASMOLECULARFUNCTION",
    "gene associated with the cellular component": "GENEASSOCIATEDWITHCELLULARCOMPONENT",
    "gene associated with the disease": "GENEASSOCIATESWITHDISEASE",
    "drug treats the disease": "DRUGTREATSDISEASE",
    "drug in the drug class": "DRUGINCLASS",
}


def normalise(phrase: str) -> str:
    """Fallback for any phrase missing from REL_MAP."""
    return "".join(ch for ch in phrase.upper() if ch.isalnum())


def node_key(label: str, props: dict) -> str:
    """AlzKB identifies genes by symbol and everything else by common name."""
    if label == "Gene":
        return props.get("geneSymbol") or props.get("commonName") or ""
    return props.get("commonName") or ""


def main() -> None:
    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    unmapped: set[str] = set()

    with driver.session() as session:
        # Throwaway database: start clean so repeated runs stay reproducible.
        session.run("MATCH (n) DETACH DELETE n")

        labels = {r["source_label"] for r in rows} | {r["target_label"] for r in rows}
        for label in labels:
            key = "geneSymbol" if label == "Gene" else "commonName"
            session.run(
                f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:`{label}`) REQUIRE n.{key} IS UNIQUE"
            )

        loaded = skipped = 0
        for row in rows:
            try:
                src_props = ast.literal_eval(row["source"])
                tgt_props = ast.literal_eval(row["target"])
            except (ValueError, SyntaxError):
                skipped += 1
                continue

            src_label, tgt_label = row["source_label"], row["target_label"]
            src_key, tgt_key = node_key(src_label, src_props), node_key(tgt_label, tgt_props)
            if not src_key or not tgt_key:
                skipped += 1
                continue

            phrase = row["relationship_type"]
            rel_type = REL_MAP.get(phrase)
            if rel_type is None:
                rel_type = normalise(phrase)
                unmapped.add(phrase)

            src_id = "geneSymbol" if src_label == "Gene" else "commonName"
            tgt_id = "geneSymbol" if tgt_label == "Gene" else "commonName"

            session.run(
                f"""
                MERGE (s:`{src_label}` {{{src_id}: $src_key}})
                SET s += $src_props
                MERGE (t:`{tgt_label}` {{{tgt_id}: $tgt_key}})
                SET t += $tgt_props
                MERGE (s)-[:`{rel_type}`]->(t)
                """,
                src_key=src_key, src_props=src_props,
                tgt_key=tgt_key, tgt_props=tgt_props,
            )
            loaded += 1

        counts = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c ORDER BY c DESC"
        ).data()
        rels = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS c ORDER BY c DESC"
        ).data()

    driver.close()

    print(f"loaded {loaded} triples, skipped {skipped}")
    if unmapped:
        print("relationship phrases not in REL_MAP (normalised instead):")
        for phrase in sorted(unmapped):
            print(f"   {phrase!r} -> {normalise(phrase)}")
    print("\nnodes:")
    for row in counts:
        print(f"   {row['label']:<20} {row['c']}")
    print("\nrelationships:")
    for row in rels:
        print(f"   {row['type']:<40} {row['c']}")


if __name__ == "__main__":
    main()
