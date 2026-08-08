"""Escargot against the EvoAge knowledge graph, on DeepSeek.

Model parity with the BioChatter benchmark: same graph, same
deepseek-v4-flash, so the framework is the only variable.

Why the schema is supplied explicitly
-------------------------------------
Escargot's get_schema() derives node properties from `dict(node)['indexes']`,
i.e. only INDEXED properties. On the EvoAge graph that yields a single
comma-joined string from the fulltext index
(`'name,id,iupac_name,alternative_name'`) applied to every label -- and it never
mentions `name_lower` / `id_lower`, which are the properties that actually make
matching work. Left to guess, the model falls back to the AlzKB conventions
baked into Escargot's cyphergpt.py prompt examples (`geneSymbol`, `commonName`),
which do not exist here.

Verified on the AlzKB sanity graph: Escargot's planning and Cypher generation
work correctly when the schema is right, so this supplies the real one.

Run:
    python ask_evoage.py "Which genes are associated with Alzheimer disease?"
    python ask_evoage.py                    # default question
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ESCARGOT_ROOT = os.path.join(os.path.dirname(HERE), "escargot")
sys.path.insert(0, ESCARGOT_ROOT)
sys.path.insert(0, HERE)

import deepseek_lm  # noqa: E402

BIOCHATTER_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Biochatter", ".env")

NODE_TYPES = (
    "Gene, Protein, ChemicalEntity, Disease, Phenotype, BiologicalProcess, "
    "MolecularFunction, CellularComponent, AnatomicalEntity, Tissue, Pathway, "
    "Mutation, Mirna, PlantSpecies, Species, PMID"
)

# The relationship types actually present in the graph, most useful first.
RELATIONSHIP_TYPES = ", ".join([
    "Disease_Gene", "Gene_Disease", "Gene_BiologicalProcess",
    "BiologicalProcess_Protein", "Protein_BiologicalProcess",
    "Gene_MolecularFunction", "MolecularFunction_Protein",
    "Gene_ChemicalEntity", "ChemicalEntity_Gene", "Protein_ChemicalEntity",
    "Gene_Phenotype", "Disease_Phenotype", "Protein_Phenotype",
    "Phenotype_Protein", "Phenotype_BiologicalProcess",
    "Gene_AnatomicalEntity", "AnatomicalEntity_Gene", "Disease_AnatomicalEntity",
    "Disease_Pathway", "Pathway_Gene", "Pathway_Pathway",
    "Protein_Protein", "Disease_Disease", "BiologicalProcess_BiologicalProcess",
    "Protein_CellularComponent", "CellularComponent_Gene",
    "ChemicalEntity_BiologicalProcess", "ChemicalEntity_Tissue",
    "Gene_Promotes_BiologicalProcess", "Gene_Inhibits_BiologicalProcess",
    "Gene_PositivelyAssociatedWith_BiologicalProcess",
    "Gene_NotAssociatedWith_BiologicalProcess",
    "ChemicalEntity_Inhibits_BiologicalProcess",
    "ChemicalEntity_NegativelyAssociatedWith_BiologicalProcess",
    "Mutation_Gene", "Mutation_Protein", "Mirna_Gene",
    "PMID_Disease", "PMID_Protein", "PMID_ChemicalEntity",
])

# Supplied verbatim to the Cypher generator, replacing Escargot's
# index-derived guess.
SCHEMA = """Node properties are the following:
Every node has these properties: ['id', 'name', 'name_lower', 'id_lower', 'type', 'node_species']
Node name: 'Gene', Node properties: ['id', 'name', 'name_lower', 'id_lower', 'node_species', 'ortholog_info']
Node name: 'Protein', Node properties: ['id', 'name', 'name_lower', 'id_lower', 'node_species']
Node name: 'Disease', Node properties: ['id', 'name', 'name_lower', 'id_lower']
Node name: 'ChemicalEntity', Node properties: ['id', 'name', 'name_lower', 'id_lower', 'smiles', 'iupac_name', 'alternative_name']
Node name: 'BiologicalProcess', Node properties: ['id', 'name', 'name_lower', 'id_lower']
Node name: 'MolecularFunction', Node properties: ['id', 'name', 'name_lower', 'id_lower']
Node name: 'CellularComponent', Node properties: ['id', 'name', 'name_lower', 'id_lower']
Node name: 'Phenotype', Node properties: ['id', 'name', 'name_lower', 'id_lower']
Node name: 'AnatomicalEntity', Node properties: ['id', 'name', 'name_lower', 'id_lower']
Node name: 'Pathway', Node properties: ['id', 'name', 'name_lower', 'id_lower']

IMPORTANT conventions for this database:
- Gene and Protein SYMBOLS (e.g. APOE, SIRT1, TP53) are stored in the 'id'
  property, NOT in 'name'. The 'name' property holds the full descriptive name
  (e.g. 'ATP binding cassette subfamily A member 1').
- There is NO 'geneSymbol' property and NO 'commonName' property in this
  database. Never use them.
- Match entity names case-insensitively using CONTAINS on 'name_lower', never
  with = on 'name'. Names vary in case and punctuation, e.g. both
  'Alzheimer Disease' and \"Alzheimer's disease\" exist.
  Example: WHERE d.name_lower CONTAINS 'alzheimer'
- To match a gene symbol use 'id_lower', e.g. WHERE g.id_lower = 'sirt1'
- ChemicalEntity means a drug, compound or metabolite, never a gene or protein.
- The graph has 1.2 billion relationships, so queries that LIST entities must
  end with a LIMIT (use LIMIT 25 unless a specific number is requested).
- NEVER put a LIMIT on an aggregate. For "how many" questions use count() and
  return the count itself, e.g. MATCH (d:Disease) RETURN count(d) AS n --
  adding LIMIT 25 there would count only 25 rows and give a wrong answer.
- Return readable fields such as name and id, not whole nodes.
- ALWAYS alias every returned field with AS, using a simple lowercase
  identifier: RETURN bp.name AS process, not RETURN bp.name. Unaliased returns
  produce dotted column keys like 'bp.name' which break downstream processing.
- Output ONLY the Cypher statement. No preamble, no explanation, no markdown
  fences. A reply beginning with anything other than MATCH, CALL, WITH, RETURN
  or UNWIND is a syntax error.

The relationships are the following:
(:Disease)-[:Disease_Gene]-(:Gene)
(:Gene)-[:Gene_Disease]-(:Disease)
(:Gene)-[:Gene_BiologicalProcess]-(:BiologicalProcess)
(:Gene)-[:Gene_MolecularFunction]-(:MolecularFunction)
(:Gene)-[:Gene_ChemicalEntity]-(:ChemicalEntity)
(:Gene)-[:Gene_Phenotype]-(:Phenotype)
(:Gene)-[:Gene_AnatomicalEntity]-(:AnatomicalEntity)
(:Protein)-[:Protein_Protein]-(:Protein)
(:Protein)-[:Protein_BiologicalProcess]-(:BiologicalProcess)
(:Protein)-[:Protein_Disease]-(:Disease)
(:Protein)-[:Protein_CellularComponent]-(:CellularComponent)
(:Disease)-[:Disease_Phenotype]-(:Phenotype)
(:Disease)-[:Disease_Pathway]-(:Pathway)
(:Disease)-[:Disease_AnatomicalEntity]-(:AnatomicalEntity)
(:Disease)-[:Disease_Disease]-(:Disease)
(:Pathway)-[:Pathway_Gene]-(:Gene)
(:Mutation)-[:Mutation_Gene]-(:Gene)
(:Mirna)-[:Mirna_Gene]-(:Gene)
(:ChemicalEntity)-[:ChemicalEntity_BiologicalProcess]-(:BiologicalProcess)"""

DEFAULT_QUESTION = "Which genes are associated with Alzheimer disease?"


import re  # noqa: E402

# Anchors that unambiguously open a Cypher statement. WITH and RETURN are
# deliberately EXCLUDED: "with" and "return" are ordinary English words that
# appear constantly in the model's preamble ("...associated with the protein
# TBK1:"). Anchoring on them slices mid-sentence and leaves prose glued to the
# front of otherwise valid Cypher, turning a good query into a syntax error.
_CYPHER_START = re.compile(r"\b(OPTIONAL\s+MATCH|MATCH|CALL|UNWIND)\b", re.IGNORECASE)
# Fallback for a statement that genuinely opens with WITH/RETURN -- honoured
# only at the start of a line, where prose would not place it.
_CYPHER_START_LINE = re.compile(r"^[ \t]*(WITH|RETURN)\b", re.IGNORECASE | re.MULTILINE)


def clean_cypher(text: str) -> str:
    """Strip prose the model writes before the Cypher.

    Escargot removes markdown fences but not preambles like "Based on the schema
    and instructions, here is the Cypher query:", which make the statement a
    syntax error. Equivalent to the cleaning applied on the BioChatter side, so
    neither tool is penalised for the same formatting habit.
    """
    statement = (text or "").strip()
    fenced = re.search(r"```(?:cypher|sql)?\s*([\s\S]*?)```", statement, re.IGNORECASE)
    if fenced:
        statement = fenced.group(1).strip()

    match = _CYPHER_START.search(statement)
    if match is None:
        match = _CYPHER_START_LINE.search(statement)
    if match and match.start() > 0:
        statement = statement[match.start():]
    return statement.strip().strip("`").strip()


def install_cypher_cleaner(escargot):
    """Clean generated Cypher before it reaches the driver."""
    client = escargot.graph_client.client
    original = client.execute_and_fetch

    def execute_and_fetch(query, *args, **kwargs):
        return original(clean_cypher(query), *args, **kwargs)

    client.execute_and_fetch = execute_and_fetch
    return escargot


def build_escargot():
    """Construct Escargot on DeepSeek with the correct EvoAge schema."""
    deepseek_lm.install()
    from escargot import Escargot

    from dotenv import dotenv_values

    env = dotenv_values(os.environ.get("EVOAGE_BIOCHATTER_ENV", BIOCHATTER_ENV))
    uri = (env.get("NEO4J_URI") or "neo4j://192.168.3.153:3333").strip()
    hostport = uri.split("://", 1)[-1]
    host, _, port = hostport.partition(":")

    config = deepseek_lm.build_config({
        "host": host,
        "port": int(port or 7687),
        "username": (env.get("NEO4J_USERNAME") or "neo4j").strip(),
        "password": (env.get("NEO4J_PASSWORD") or "").strip(),
    })

    escargot = Escargot(
        config,
        model_name="chatgpt",
        node_types=NODE_TYPES,
        relationship_types=RELATIONSHIP_TYPES,
    )
    if escargot.graph_client is None:
        raise SystemExit("no graph client -- check Neo4j credentials and reachability")
    escargot.graph_client.schema = SCHEMA
    install_cypher_cleaner(escargot)
    return escargot


def main() -> None:
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_QUESTION
    escargot = build_escargot()
    print(f"\nEscargot | model={deepseek_lm.DEEPSEEK_MODEL} | graph=EvoAge")
    print(f"Question: {question}\n")
    print("--- Answer ---")
    print(escargot.ask(question, debug_level=1, answer_type="natural", memory_name="evoage"))


if __name__ == "__main__":
    main()
