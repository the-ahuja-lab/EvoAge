import re
from typing import Any, Dict, List, Optional
import logging
import unicodedata
from difflib import SequenceMatcher
from fastapi import APIRouter, Depends, HTTPException, Query

from app.utils.database import Neo4jConnection, get_neo4j_connection
from app.utils.schema import (
    EntityRelationshipsResponse,
    KGAggregateResponse,
    KGStatisticsResponse,
    RankedEntity,
    NodeConnection,
    NodeProperties,
    RelatedEntity,
    RelationCheckResponse,
    SubgraphResponse,
    TripleResponse,
)

router = APIRouter()
logger = logging.getLogger("main_server_kge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@router.get(
    "/sample_triples",
    response_model=List[TripleResponse],
    description="Retrieve sample triples based on the relationship type",
    summary="Fetch sample triples",
    response_description="Returns a list of triples with head, relation, and tail",
    operation_id="get_sample_triples",
)
async def get_sample_triples(
    rel_type: str = Query(
        ...,
        description="The relationship type to filter triples. (e.g. GENE_GENE, GENE_DISEASE, GENE_PHENOTYPE)",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Fetch up to 10 sample triples for a given relationship type."""
    query = """
    WITH toLower($relType) AS relationshipType
    CALL apoc.cypher.run(
        "MATCH (h)-[r]->(t)
         WHERE toLower(type(r)) = $relationshipType
         RETURN
             COALESCE(h.id, h.name, id(h)) AS Head,
             type(r) AS Relation,
             COALESCE(t.id, t.name, id(t)) AS Tail
         LIMIT 10",
        {relationshipType: relationshipType}
    ) YIELD value
    RETURN value.Head AS Head, value.Relation AS Relation, value.Tail AS Tail;
    """

    result = db.query(query, parameters={"relType": rel_type})

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No triples found for relationship type '{rel_type}'",
        )

    return [
        TripleResponse(
            head=record["Head"],
            relation=record["Relation"],
            tail=record["Tail"],
        )
        for record in result
    ]


@router.get(
    "/get_nodes_by_label",
    response_model=List[dict],
    description="Retrieve 10 nodes of a given type, returning all their properties.",
    summary="Fetch nodes by label with all properties",
    response_description="Returns a list of up to 10 nodes, each with all its properties.",
    operation_id="get_nodes_by_label",
)
async def get_nodes_by_label(
    label: str = Query(
        ...,
        description="The label of the nodes to retrieve (e.g. Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract)",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    query = f"""
        MATCH (n:{label})
        RETURN properties(n) AS node_properties
        LIMIT 10
    """

    records = db.query(query)
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No nodes found for label '{label}'",
        )
    logger.info(f"Response from get  nodes by label entities:")
    return [record["node_properties"] for record in records]


@router.get(
    "/subgraph",
    description="Retrieve a subgraph of related nodes by specifying the property and value of the start node",
    summary="Get a subgraph of connected nodes based on start node properties",
    response_description="Returns a subgraph of nodes related to the specified node",
    operation_id="get_subgraph",
    response_model=SubgraphResponse,
)
async def get_subgraph(
    property_name: str = Query(
        ...,
        description="Property name of the start node to search for",
    ),
    property_value: str = Query(..., description="Value of the property to search for"),
    node_label: str = Query(
        ..., description="Label of the start node to search for (e.g., Gene, Protein)"
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Retrieve a subgraph of related nodes while limiting the connections to 10."""
    # This is done to optimize the query by removing unnecessary properties
    # Makes the query faster and reduces the data transfer
    ignore_properties_source = ["sequence", "seq", "smiles", "detail", "details"]
    ignore_properties_target = [
        "sequence",
        "seq",
        "smiles",
        "detail",
        "details",
        "description",
    ]

    # Construct the MATCH clause using the provided node_label
    match_clause = (
        f"MATCH (n:{node_label} {{{property_name}: $property_value}})-[r]-(connected)"
    )

    query = f"""
    {match_clause}
    WITH n, r, connected
    RETURN
        apoc.map.removeKeys(properties(n), $ignore_properties_source) AS node_properties,
        collect(apoc.map.fromPairs([
            ['relationship_type', type(r)],
            ['connected_properties', apoc.map.removeKeys(properties(connected), $ignore_properties_target)]
        ]))[0..10] AS connections
    """

    result = db.query(
        query,
        parameters={
            "property_value": property_value,
            "ignore_properties_source": ignore_properties_source,
            "ignore_properties_target": ignore_properties_target,
        },
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Node not found or no connections available",
        )

    # Extract the source node and connections from the query result
    source_node = None
    connections = []
    for record in result:
        if source_node is None:
            source_node = NodeProperties(attributes=record["node_properties"])
        connections.extend(
            [
                NodeConnection(
                    relationship_type=connection["relationship_type"],
                    target_node=NodeProperties(
                        attributes=connection["connected_properties"],
                    ),
                )
                for connection in record["connections"]
            ],
        )
    logger.info(f"Response from get_subgraph: {source_node}")
    return SubgraphResponse(source_node=source_node, connections=connections)


GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau",
    "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
}
GREEK.update({k.upper(): v for k, v in list(GREEK.items())})

DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
APOS = dict.fromkeys(map(ord, "\u2018\u2019\u02bc'"), None)


def normalize(term: str) -> str:
    """β-secretase -> beta-secretase ; Alzheimer's -> Alzheimers"""
    term = unicodedata.normalize("NFKC", term)
    term = term.translate(DASHES).translate(APOS)
    return "".join(GREEK.get(ch, ch) for ch in term).strip()


def tokenize(term: str, max_tokens: int = 200):
    """Returns (raw_tokens, kept_tokens). Keeps numeric tokens: IL-6, p53, CD4."""
    raw = re.findall(r"[A-Za-z0-9]+", normalize(term))
    kept = [t for t in raw if len(t) >= 2 or t.isdigit()][:max_tokens]
    return raw, kept


def _tokset(s: str) -> set:
    return set(re.findall(r"[a-z0-9]+", normalize(s).lower()))


def lexical_score(query: str, cand: Dict[str, Any]) -> float:
    """
    How well does this candidate's name cover the query?
    Penalises candidates carrying words the query never asked for
    (this is what drops 'gamma-secretase complex' for a 'beta' query).
    """
    q = _tokset(query)
    if not q:
        return 0.0

    props = cand.get("properties") or {}
    names = [props.get("name") or "", props.get("id") or ""]
    names += (props.get("alternative_name") or "").split("::")

    best = 0.0
    for n in names:
        c = _tokset(n)
        if not c:
            continue
        jaccard = len(q & c) / len(q | c)
        seq = SequenceMatcher(
            None, " ".join(sorted(q)), " ".join(sorted(c))
        ).ratio()
        best = max(best, 0.6 * jaccard + 0.4 * seq)
    return best


def rerank(query: str, entities: List[Dict], k: int = 5, floor: float = 0.45):
    """Blend Lucene score with lexical coverage, drop the tail, keep top-k."""
    if not entities:
        return entities

    top_luc = max((e.get("lucene_score") or 0.0) for e in entities) or 1.0

    scored = []
    for e in entities:
        lex = lexical_score(query, e)
        final = 0.5 * ((e.get("lucene_score") or 0.0) / top_luc) + 0.5 * lex
        e["lexical_score"] = round(lex, 4)   # keep for logging/tuning
        scored.append((final, lex, e))

    scored.sort(key=lambda x: -x[0])

    keep = [e for _, lex, e in scored if lex >= floor]
    if not keep:                       # never return an empty bucket
        keep = [scored[0][2]]
    return keep[:k]


@router.get(
    "/search_biological_entities",
    response_model=List[Dict[str, Any]],
    description="Search biological entities such as Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name or id",
    summary="Search for biological entities by name or id",
    response_description="Returns a list of entity types with their top 5 matching entities",
    operation_id="search_biological_entities",
)
async def search_biological_entities(
    targetTerm: str = Query(
        ...,
        description="The name or id or the term to search for in biological entities",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Search biological entities by name or id."""
    ignore_properties = ["type", "id_lower", "name_lower"]

    # --- (1) + (2) normalize, then tokenize without killing β / 6 / 1
    raw_tokens, tokens = tokenize(targetTerm)
    if not tokens:
        raise HTTPException(status_code=400, detail="No valid search tokens found.")

    # --- (5) fetch 25, explicitly score-ordered; cut to 5 later in Python
    query = """
    CALL db.index.fulltext.queryNodes("entitySearchIndex", $processed_term)
    YIELD node, score
    WITH labels(node)[0] AS entityType, node, score
    ORDER BY score DESC
    WITH entityType,
         COLLECT({
             properties: apoc.map.removeKeys(properties(node), $ignore_properties),
             lucene_score: score
         })[0..25] AS topEntities
    RETURN entityType, topEntities;
    """

    def run(term: str):
        return db.query(
            query,
            parameters={
                "processed_term": term,
                "ignore_properties": ignore_properties,
            },
        )

    # --- (3) field the AND clause -> excludes iupac_name noise
    and_clause = " AND ".join(
        f"(name:{t} OR id:{t} OR alternative_name:{t})" for t in tokens
    )
    # --- (4) boost exact / glued / alias matches
    phrase = '"' + " ".join(tokens) + '"'
    glued = "".join(raw_tokens)            # betasecretase, IL6, NFkB

    processed_term = (
        f"({and_clause})"
        f" OR name:{phrase}^4"
        f" OR name:{glued}^3"
        f" OR alternative_name:{phrase}^2"
    )
    logger.info(f"[search] '{targetTerm}' -> {processed_term}")
    result = run(processed_term)

    # --- fallback: loose OR (unchanged behaviour, just fielded)
    if not result:
        or_clause = " OR ".join(
            f"(name:{t} OR id:{t} OR alternative_name:{t})" for t in tokens
        )
        logger.info(f"No results with AND. Retrying using OR search: {or_clause}")
        result = run(or_clause)

    # --- ortholog match (separate index, Gene-only) -- e.g. a species-specific
    # symbol like "tep-1" or an Ensembl id that only appears in ortholog_info,
    # not in name/id/alternative_name. Merged into the Gene bucket below.
    ortholog_entities = []
    try:
        ortholog_query = """
        CALL db.index.fulltext.queryNodes("orthologSearchIndex", $processed_term)
        YIELD node, score
        WITH node, score ORDER BY score DESC
        RETURN COLLECT({
            properties: apoc.map.removeKeys(properties(node), $ignore_properties),
            lucene_score: score
        })[0..25] AS topEntities
        """
        ortholog_term = " OR ".join(tokens)
        ortholog_result = db.query(
            ortholog_query,
            parameters={"processed_term": ortholog_term, "ignore_properties": ignore_properties},
        )
        if ortholog_result:
            ortholog_entities = ortholog_result[0]["topEntities"]
    except Exception as e:
        logger.warning(f"ortholog search failed for '{targetTerm}': {e}")

    if not result and not ortholog_entities:
        raise HTTPException(
            status_code=404,
            detail=f"No matching biological entities found for '{targetTerm}'",
        )

    # merge ortholog hits into the Gene bucket, deduping on id
    if ortholog_entities:
        result = [dict(r) for r in result]
        gene_record = next((r for r in result if r["entityType"] == "Gene"), None)
        if gene_record is None:
            gene_record = {"entityType": "Gene", "topEntities": []}
            result.append(gene_record)
        seen_ids = {e["properties"].get("id") for e in gene_record["topEntities"]}
        for e in ortholog_entities:
            eid = e["properties"].get("id")
            if eid not in seen_ids:
                gene_record["topEntities"].append(e)
                seen_ids.add(eid)

    # --- (6) rerank per entity type, then cut to 5
    response = []
    for record in result:
        top = rerank(targetTerm, record["topEntities"], k=5, floor=0.45)
        if top:
            response.append(
                {
                    "entityType": record["entityType"],
                    "topEntities": top,
                }
            )
    return response



# @router.get(
#     "/search_biological_entities",
#     response_model=List[Dict[str, Any]],
#     description="Search biological entities such as Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name or id",
#     summary="Search for biological entities by name or id",
#     response_description="Returns a list of entity types with their top 5 matching entities",
#     operation_id="search_biological_entities",
# )
# async def search_biological_entities(
#     targetTerm: str = Query(
#         ...,
#         description="The name or id or the term to search for in biological entities",
#     ),
#     db: Neo4jConnection = Depends(get_neo4j_connection),
# ):
#     """Search biological entities by name or id."""

#     ignore_properties = ["type", "id_lower", "name_lower"]

#     MAX_TOKENS = 200

#     tokens = [
#         token
#         for token in re.findall(r"\w+", targetTerm)
#         if len(token) >= 2
#     ][:MAX_TOKENS]

#     processed_tokens = []

#     for token in tokens:
#         processed_tokens.append(token)

#     if len(processed_tokens) == 0:
#         raise HTTPException(
#             status_code=400,
#             detail="No valid search tokens found."
#         )

#     query = """
#     CALL db.index.fulltext.queryNodes("entitySearchIndex", $processed_term)
#     YIELD node, score

#     WITH node, score, labels(node) AS entityTypes

#     WITH entityTypes[0] AS entityType,
#          COLLECT({
#              properties: apoc.map.removeKeys(properties(node), $ignore_properties),
#              lucene_score: score
#          }) AS entities

#     WITH entityType, entities[0..5] AS topEntities

#     RETURN entityType, topEntities;
#     """

#     # ==========================================================
#     # First try AND search
#     # ==========================================================

#     processed_term = " AND ".join(processed_tokens)

#     result = db.query(
#         query,
#         parameters={
#             "processed_term": processed_term,
#             "ignore_properties": ignore_properties,
#         },
#     )

#     # ==========================================================
#     # If AND fails, try OR search
#     # ==========================================================

#     if not result:

#         processed_term = " OR ".join(processed_tokens)

#         logger.info(
#             f"No results with AND. Retrying using OR search: {processed_term}"
#         )

#         result = db.query(
#             query,
#             parameters={
#                 "processed_term": processed_term,
#                 "ignore_properties": ignore_properties,
#             },
#         )

#     # ==========================================================
#     # Still nothing
#     # ==========================================================

#     if not result:
#         raise HTTPException(
#             status_code=404,
#             detail=f"No matching biological entities found for '{targetTerm}'",
#         )

#     response = [
#         {
#             "entityType": record["entityType"],
#             "topEntities": record["topEntities"],
#         }
#         for record in result
#     ]

#     return response


@router.get(
    "/entity_relationships",
    response_model=EntityRelationshipsResponse,
    description="Retrieve the count and list of related entities for a specified entity and optionally by relationship type",
    summary="Fetch related entities by entity and optionally relationship type",
    response_description="Returns the count and details of related entities, optionally filtered by relationship type",
    operation_id="get_entity_relationships",
)
async def get_entity_relationships(
    entity_type: str = Query(..., description="The type of entity to search for (e.g., Gene, Protein)"),
    property_name: str = Query(..., description="The property used to identify the entity (e.g., id, name)"),
    property_value: str = Query(..., description="The value of the property for the entity"),
    relationship_type: Optional[str] = Query(None, description="The type of relationship to filter by (optional)"),
    target_label: Optional[str] = Query(None, description="The label of the related entity to filter (optional)"),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Fetch related entities, optionally filter by relationship type and target label."""

    ignore_properties = ["sequence", "seq", "smiles", "detail", "details", "description"]

    if relationship_type:
        # Normalize relationship type and handle possible reverse forms
        rt_lower = relationship_type.lower()
        rt_reverse = check_rev_rel.get(rt_lower) if 'check_rev_rel' in globals() else None  # Optional reverse map
        rt_candidates = [rt_lower]
        if rt_reverse and rt_reverse != rt_lower:
            rt_candidates.append(rt_reverse)

        # Normalize target label if provided
        target_label = target_label.lower() if target_label else None

        query = f"""
        MATCH (e:{entity_type})
        WHERE e.{property_name} = $property_value
        WITH e
        MATCH (e)-[r]-(related)
        WHERE toLower(type(r)) IN $rt_candidates
        AND ($target_label IS NULL OR any(lbl IN labels(related) WHERE toLower(lbl) = $target_label))
        RETURN count(related) AS total_count,
            collect(apoc.map.removeKeys(properties(related), $ignore_properties))[0..20] AS entity_properties

        """

        params = {
            "property_value": property_value,
            "rt_candidates": rt_candidates,
            "target_label": target_label,
            "ignore_properties": ignore_properties,
        }

    else:
        query = f"""
        MATCH (e:{entity_type})--(related)
        WHERE e.{property_name} = $property_value
        RETURN count(related) AS total_count,
               collect(apoc.map.removeKeys(properties(related), $ignore_properties))[0..20] AS entity_properties
        """
        params = {
            "property_value": property_value,
            "ignore_properties": ignore_properties,
        }

    result = db.query(query, parameters=params)

    if not result:
        relationship_message = f" of type '{relationship_type}'" if relationship_type else ""
        raise HTTPException(
            status_code=404,
            detail=f"No relationships{relationship_message} found for {entity_type} with {property_name}='{property_value}'",
        )

    total_count = result[0]["total_count"]
    related_entities = [
        RelatedEntity(entity_properties=entity)
        for entity in result[0]["entity_properties"]
    ]

    return EntityRelationshipsResponse(
        total_relationships=total_count,
        related_entities=related_entities,
    )

@router.get(
    "/kg_aggregate",
    response_model=KGAggregateResponse,
    description=(
        "Rank entities by how many neighbours of a given type they have, computed "
        "across the ENTIRE graph. Use for 'which disease has the most associated "
        "genes', 'top 10 genes by number of biological processes', or 'how many "
        "genes are associated with <entity>' (set entity_name and limit=1)."
    ),
    summary="Rank entities by neighbour count",
    response_description="Entities ordered by neighbour count, highest first",
    operation_id="get_kg_aggregate",
)
async def get_kg_aggregate(
    source_label: str = Query(
        ...,
        description="Label of the entities being ranked (e.g. Disease, Gene, Protein)",
    ),
    target_label: Optional[str] = Query(
        None,
        description="Label of the neighbours being counted (e.g. Gene, BiologicalProcess)",
    ),
    rel_type: Optional[str] = Query(
        None,
        description="Restrict to one relationship type (e.g. Disease_Gene). Omit to count across all.",
    ),
    entity_name: Optional[str] = Query(
        None,
        description="Restrict to entities whose name contains this text, e.g. 'cellular senescence'",
    ),
    direction: str = Query(
        "out",
        pattern="^(out|in|both)$",
        description=(
            "Relationship direction from the ranked entity: 'out' (default), 'in', "
            "or 'both'. Use 'both' only with an explicit rel_type -- it is far slower."
        ),
    ),
    limit: int = Query(10, ge=1, le=100, description="How many entities to return"),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Rank source_label entities by their number of target_label neighbours.

    This is a genuine aggregation over the graph, unlike the sampling endpoints.
    It is therefore materially more expensive: ranking Disease by Gene traverses
    ~13M relationships and takes ~17s. Aggregating over the PMID_* relationship
    types (up to 300M edges) is far slower and should be avoided.
    """
    rel_pattern = f":`{rel_type}`" if rel_type else ""
    target_pattern = f":`{target_label}`" if target_label else ""
    where = "WHERE s.name_lower CONTAINS toLower($entity_name)" if entity_name else ""

    # Direction matters enormously here. An undirected pattern expands every
    # edge incident to the source label -- including PMID_* types with up to
    # 300M edges -- before filtering on the target label. Measured on
    # Disease/Gene: 731s undirected vs 17s directed, for identical results.
    left, right = ("-", "->") if direction == "out" else (
        ("<-", "-") if direction == "in" else ("-", "-")
    )

    query = f"""
        MATCH (s:`{source_label}`){left}[r{rel_pattern}]{right}(t{target_pattern})
        {where}
        WITH s, count(DISTINCT t) AS neighbour_count
        RETURN s.name AS name, s.id AS id, neighbour_count AS count
        ORDER BY neighbour_count DESC
        LIMIT $limit
    """

    try:
        records = db.query(query, parameters={"limit": limit, "entity_name": entity_name})
    except Exception as exc:  # noqa: BLE001 -- surface bad labels as a 400, not a 500
        raise HTTPException(
            status_code=400,
            detail=f"Aggregation failed. Check the label and relationship names. ({exc})",
        )

    if not records:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No '{source_label}' entities found"
                + (f" matching '{entity_name}'" if entity_name else "")
                + (f" connected to '{target_label}'" if target_label else "")
            ),
        )

    logger.info(
        "kg_aggregate: %s -> %s (rel=%s, name=%s) returned %d rows",
        source_label, target_label, rel_type, entity_name, len(records),
    )

    return KGAggregateResponse(
        source_label=source_label,
        target_label=target_label,
        relationship_type=rel_type,
        total_ranked=len(records),
        results=[
            RankedEntity(name=r["name"], id=r["id"], count=int(r["count"]))
            for r in records
        ],
    )


@router.get(
    "/kg_statistics",
    response_model=KGStatisticsResponse,
    description=(
        "Count what the knowledge graph contains: total nodes and relationships, "
        "how many node labels and relationship types exist, and the count for each "
        "individual label and relationship type. Optionally filter to one label "
        "and/or one relationship type."
    ),
    summary="Knowledge graph counts and statistics",
    response_description="Returns totals plus per-label and per-relationship-type counts",
    operation_id="get_kg_statistics",
)
async def get_kg_statistics(
    label: Optional[str] = Query(
        None,
        description="Restrict node_counts to this label (e.g. Gene, Disease, Protein). Omit for all labels.",
    ),
    rel_type: Optional[str] = Query(
        None,
        description="Restrict relationship_counts to this type (e.g. Gene_Disease). Omit for all types.",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Return node/relationship counts for the knowledge graph.

    Uses apoc.meta.stats(), which reads Neo4j's internal count store rather than
    scanning. This matters here: the graph holds ~45M nodes and ~1.2B
    relationships, so a `MATCH (n) RETURN count(n)` would take minutes, while
    this returns in milliseconds.
    """
    result = db.query(
        "CALL apoc.meta.stats() YIELD nodeCount, relCount, labels, relTypesCount "
        "RETURN nodeCount, relCount, labels, relTypesCount"
    )

    if not result:
        raise HTTPException(
            status_code=503,
            detail="Could not read graph statistics. Check that the APOC plugin is installed.",
        )

    record = result[0]
    node_counts = {k: int(v) for k, v in (record["labels"] or {}).items()}
    relationship_counts = {k: int(v) for k, v in (record["relTypesCount"] or {}).items()}

    # Label and type totals are reported before filtering, so the caller still
    # learns how many exist overall even when asking about a single one.
    node_label_count = len(node_counts)
    relationship_type_count = len(relationship_counts)

    if label:
        matched = {k: v for k, v in node_counts.items() if k.lower() == label.lower()}
        if not matched:
            raise HTTPException(
                status_code=404,
                detail=f"No node label '{label}' in the knowledge graph. Available: {sorted(node_counts)}",
            )
        node_counts = matched
        # Asking about one label should not return all 89 relationship counts;
        # drop the other dimension unless it was asked for explicitly.
        if not rel_type:
            relationship_counts = {}

    if rel_type:
        matched = {k: v for k, v in relationship_counts.items() if k.lower() == rel_type.lower()}
        if not matched:
            raise HTTPException(
                status_code=404,
                detail=f"No relationship type '{rel_type}' in the knowledge graph.",
            )
        relationship_counts = matched
        if not label:
            node_counts = {}

    logger.info(
        "kg_statistics: %s nodes, %s relationships (label=%s, rel_type=%s)",
        record["nodeCount"], record["relCount"], label, rel_type,
    )

    return KGStatisticsResponse(
        total_nodes=int(record["nodeCount"]),
        total_relationships=int(record["relCount"]),
        node_label_count=node_label_count,
        relationship_type_count=relationship_type_count,
        node_counts=node_counts,
        relationship_counts=relationship_counts,
    )


## 120726
@router.get(
    "/check_relationship",
    response_model=RelationCheckResponse,
    description="Check if a relationship exists between two entities and return ALL relationship types between them",
    summary="Verify relationship between two entities",
    response_description="Returns whether a relationship exists and every relationship type found",
    operation_id="check_relationship",
)
async def check_relationship(
    entity1_type: str = Query(
        ...,
        description="The type of the first entity (e.g., Gene, Protein)",
    ),
    entity1_property_name: str = Query(
        ...,
        description="The property name to identify the first entity (e.g., id, name)",
    ),
    entity1_property_value: str = Query(
        ...,
        description="The property value to identify the first entity",
    ),
    entity2_type: str = Query(
        ...,
        description="The type of the second entity (e.g., Disease, Protein)",
    ),
    entity2_property_name: str = Query(
        ...,
        description="The property name to identify the second entity (e.g., id, name)",
    ),
    entity2_property_value: str = Query(
        ...,
        description="The property value to identify the second entity",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    ## Return EVERY relationship type between the two entities, not just the first one.
    ## A pair can hold both Gene_Promotes_BiologicalProcess and Gene_Inhibits_BiologicalProcess;
    ## returning result[0] picked one arbitrarily, so callers could not tell the signs apart.
    query = f"""
    MATCH (e1:{entity1_type})-[r]-(e2:{entity2_type})
    WHERE e1.{entity1_property_name} = $entity1_property_value
      AND e2.{entity2_property_name} = $entity2_property_value
    RETURN collect(DISTINCT type(r)) AS relationship_types
    """

    result = db.query(
        query,
        parameters={
            "entity1_property_value": entity1_property_value,
            "entity2_property_value": entity2_property_value,
        },
    )

    # `collect()` always yields exactly one row — an empty list when there is no edge.
    relationship_types = (result[0].get("relationship_types") if result else []) or []

    if not relationship_types:
        return RelationCheckResponse(exists=False)

    return RelationCheckResponse(
        exists=True,
        relationship_type=relationship_types[0],   # kept for back-compat with existing callers
        relationship_types=relationship_types,     # the one the sign check actually uses
    )

# @router.get(
#     "/check_relationship",
#     response_model=RelationCheckResponse,
#     description="Check if a relationship exists between two entities and return the type of relationship",
#     summary="Verify relationship between two entities",
#     response_description="Returns whether a relationship exists and its type",
#     operation_id="check_relationship",
# )
# async def check_relationship(
#     entity1_type: str = Query(
#         ...,
#         description="The type of the first entity (e.g., Gene, Protein)",
#     ),
#     entity1_property_name: str = Query(
#         ...,
#         description="The property name to identify the first entity (e.g., id, name)",
#     ),
#     entity1_property_value: str = Query(
#         ...,
#         description="The property value to identify the first entity",
#     ),
#     entity2_type: str = Query(
#         ...,
#         description="The type of the second entity (e.g., Disease, Protein)",
#     ),
#     entity2_property_name: str = Query(
#         ...,
#         description="The property name to identify the second entity (e.g., id, name)",
#     ),
#     entity2_property_value: str = Query(
#         ...,
#         description="The property value to identify the second entity",
#     ),
#     db: Neo4jConnection = Depends(get_neo4j_connection),
# ):
#     ## Query to check if a relationship exists between the two entities
#     query = f"""
#     MATCH (e1:{entity1_type})-[r]-(e2:{entity2_type})
#     WHERE e1.{entity1_property_name} = $entity1_property_value
#       AND e2.{entity2_property_name} = $entity2_property_value
#     RETURN type(r) AS relationship_type
#     """
    

#     result = db.query(
#         query,
#         parameters={
#             "entity1_property_value": entity1_property_value,
#             "entity2_property_value": entity2_property_value,
#         },
#     )

#     if not result:
#         return RelationCheckResponse(exists=False)

#     # If a relationship exists, return the type
#     return RelationCheckResponse(
#         exists=True,
#         relationship_type=result[0]["relationship_type"],
#     )
