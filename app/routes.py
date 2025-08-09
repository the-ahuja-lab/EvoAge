import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.utils.database import Neo4jConnection, get_neo4j_connection
from app.utils.schema import (
    EntityRelationshipsResponse,
    NodeConnection,
    NodeProperties,
    RelatedEntity,
    RelationCheckResponse,
    SubgraphResponse,
    TripleResponse,
)

router = APIRouter()


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

    return SubgraphResponse(source_node=source_node, connections=connections)


@router.get(
    "/search_biological_entities",
    response_model=List[Dict[str, Any]],
    description="Search biological entities such as Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name or id",
    summary="Search for biological entities by name or id",
    response_description="Returns a list of entity types with their top 3 matching entities",
    operation_id="search_biological_entities",
)
async def search_biological_entities(
    targetTerm: str = Query(
        ...,
        description="The name or id or the term to search for in biological entities",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Search biological entities such as Gene, Protein, Disease, ChemicalEntity, Phenotype, Tissue, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway, Mutation, PMID, Species or PlantExtract by name or id"""
    # List of properties to exclude for optimization
    ignore_properties = ["type", "id_lower", "name_lower"]

    # Minimum length for fuzzy search
    # MIN_LENGTH_FOR_FUZZY_SEARCH = 5

    # Split on non-alphanumeric and apply fuzzy matching
    # Tokenize and filter out short/noisy tokens (length < 2)
    MAX_TOKENS = 200
    tokens = [token for token in re.findall(r"\w+", targetTerm) if len(token) >= 2][
        :MAX_TOKENS
    ]

    processed_tokens = []
    for token in tokens:
        processed_tokens.append(token)

        # currently removing the fuzzy search, but can be added back if needed
        # if len(token) >= MIN_LENGTH_FOR_FUZZY_SEARCH:
        #     processed_tokens.append(f"{token}~1")
        # else:
        #     processed_tokens.append(token)

    # Join with OR to allow partial matches
    processed_term = " AND ".join(processed_tokens)

    query = """
    CALL db.index.fulltext.queryNodes("entitySearchIndex", $processed_term) YIELD node, score
    WITH node, score, labels(node) AS entityTypes
    WITH entityTypes[0] AS entityType,
        COLLECT({properties: apoc.map.removeKeys(properties(node), $ignore_properties), lucene_score: score}) AS entities
    WITH entityType, entities[0..5] AS topEntities
    RETURN entityType, topEntities;
    """

    result = db.query(
        query,
        parameters={
            "processed_term": processed_term,
            "ignore_properties": ignore_properties,
        },
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No matching biological entities found for the term '{processed_term}'",
        )

    response = [
        {"entityType": record["entityType"], "topEntities": record["topEntities"]}
        for record in result
    ]

    return response


@router.get(
    "/entity_relationships",
    response_model=EntityRelationshipsResponse,
    description="Retrieve the count and list of related entities for a specified entity and optionally by relationship type",
    summary="Fetch related entities by entity and optionally relationship type",
    response_description="Returns the count and details of related entities, optionally filtered by relationship type",
    operation_id="get_entity_relationships",
)
async def get_entity_relationships(
    entity_type: str = Query(
        ...,
        description="The type of entity to search for (e.g., Gene, Protein)",
    ),
    property_name: str = Query(
        ...,
        description="The property used to identify the entity (e.g., id, name)",
    ),
    property_value: str = Query(
        ...,
        description="The value of the property for the entity",
    ),
    relationship_type: Optional[str] = Query(
        None,
        description="The type of relationship to filter by (optional)",
    ),
    db: Neo4jConnection = Depends(get_neo4j_connection),
):
    """Fetch related entities, optionally filter by relationship type, and limit details to 20 entities while providing the total count."""
    # List of properties to exclude for optimization
    ignore_properties = [
        "sequence",
        "seq",
        "smiles",
        "detail",
        "details",
        "description",
    ]

    # Define query depending on whether relationship_type is provided
    if relationship_type:
        # Apply LOWER() in the query for case-insensitive relationship matching
        query = f"""
        MATCH (e:{entity_type})-[r]-(related)
        WHERE e.{property_name} = $property_value AND LOWER(type(r)) = LOWER($relationship_type)
        RETURN count(related) AS total_count,
               collect(apoc.map.removeKeys(properties(related), $ignore_properties))[0..20] AS entity_properties
        """
        params = {
            "property_value": property_value,
            "relationship_type": relationship_type,
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

    # Execute the query
    result = db.query(query, parameters=params)

    if not result:
        relationship_message = (
            f" of type '{relationship_type}'" if relationship_type else ""
        )
        raise HTTPException(
            status_code=404,
            detail=f"No relationships{relationship_message} found for {entity_type} with {property_name}='{property_value}'",
        )

    # Extract the total count and related entities
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
    "/check_relationship",
    response_model=RelationCheckResponse,
    description="Check if a relationship exists between two entities and return the type of relationship",
    summary="Verify relationship between two entities",
    response_description="Returns whether a relationship exists and its type",
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
    # Query to check if a relationship exists between the two entities
    query = f"""
    MATCH (e1:{entity1_type})-[r]-(e2:{entity2_type})
    WHERE e1.{entity1_property_name} = $entity1_property_value
      AND e2.{entity2_property_name} = $entity2_property_value
    RETURN type(r) AS relationship_type
    """

    result = db.query(
        query,
        parameters={
            "entity1_property_value": entity1_property_value,
            "entity2_property_value": entity2_property_value,
        },
    )

    if not result:
        return RelationCheckResponse(exists=False)

    # If a relationship exists, return the type
    return RelationCheckResponse(
        exists=True,
        relationship_type=result[0]["relationship_type"],
    )
