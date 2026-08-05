from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class TripleResponse(BaseModel):
    head: str
    relation: str
    tail: str


class NodeProperties(BaseModel):
    attributes: dict


class NodeConnection(BaseModel):
    relationship_type: str
    target_node: NodeProperties


class SubgraphResponse(BaseModel):
    source_node: NodeProperties
    connections: List[NodeConnection]


class PredictionResult(BaseModel):
    tail_entity: str
    score: float
    properties: Optional[Dict[str, Any]] = None


class PredictionResponse(BaseModel):
    head_entity: str
    relation: str
    predictions: List[PredictionResult]


class PredictionRankResponse(BaseModel):
    head_entity: str
    relation: str
    tail_entity: str
    rank: int
    score: float
    max_score: float


class RelatedEntity(BaseModel):
    entity_properties: dict


class EntityRelationshipsResponse(BaseModel):
    total_relationships: int
    related_entities: List[RelatedEntity]


class RelationCheckResponse(BaseModel):
    exists: bool
    relationship_type: Optional[str] = None


class RankedEntity(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    count: int


class KGAggregateResponse(BaseModel):
    """Ranked neighbour counts, computed over the whole graph.

    Exists so that "which X has the most Y" and "how many Y does X have" are
    answered by an aggregation in the database rather than by sampling a few
    nodes and comparing them, which silently returns the maximum of the sample
    instead of the maximum of the graph.
    """

    source_label: str
    target_label: Optional[str] = None
    relationship_type: Optional[str] = None
    total_ranked: int
    results: List[RankedEntity]


class KGStatisticsResponse(BaseModel):
    """Counts of what the knowledge graph contains.

    Populated from the Neo4j count store, so it is accurate and cheap to compute
    regardless of graph size.
    """

    total_nodes: int
    total_relationships: int
    node_label_count: int
    relationship_type_count: int
    node_counts: Dict[str, int]
    relationship_counts: Dict[str, int]
