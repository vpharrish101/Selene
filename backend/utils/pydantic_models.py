import uuid
from datetime import datetime

from enum import Enum
from typing import Optional,Any,TypedDict
from pydantic import BaseModel,Field

def _uid()->str:
    return str(uuid.uuid4())

# ──────────────────────────────────────────────
# Enumearations
# ──────────────────────────────────────────────

class DocType(str,Enum):
    EMAIL="email"
    DOCUMENT="document"
    MEETING="meeting"
    TICKET="ticket"
    CALENDAR="calendar"
    UNKNOWN="unknown"


class NodeType(str,Enum):
    PERSON="Person"
    ORGANIZATION="Organization"
    PROJECT="Project"
    DOCUMENT="Document"
    EMAIL="Email"
    TICKET="Ticket"
    TASK="Task"
    MEETING="Meeting"
    DEADLINE="Deadline"
    TOPIC="Topic"


class EdgeType(str,Enum):
    SENT_BY="SENT_BY"
    SENT_TO="SENT_TO"
    MENTIONED_IN="MENTIONED_IN"
    RELATED_TO="RELATED_TO"
    ASSIGNED_TO="ASSIGNED_TO"
    OWNS="OWNS"
    DEPENDS_ON="DEPENDS_ON"
    DUE_ON="DUE_ON"
    CREATED_AT="CREATED_AT"
    UPDATED_AT="UPDATED_AT"
    DECIDED_IN="DECIDED_IN"
    ACTION_ITEM_FOR="ACTION_ITEM_FOR"
    FOLLOW_UP_FOR="FOLLOW_UP_FOR"
    SUPPORTS="SUPPORTS"
    CONTRADICTS="CONTRADICTS"
    PARTICIPATED_IN="PARTICIPATED_IN"
    CC_TO="CC_TO"
    REPORTED_BY="REPORTED_BY"
    PART_OF="PART_OF"
    RESPONSIBLE_FOR="RESPONSIBLE_FOR"
    LEADS="LEADS"


class QueryRoute(str,Enum):
    GRAPH_FIRST="graph_first"
    HYBRID="hybrid"
    VECTOR_FIRST="vector_first"


class TicketStatus(str,Enum):
    OPEN="open"
    IN_PROGRESS="in_progress"
    BLOCKED="blocked"
    DONE="done"
    CLOSED="closed"


class TicketPriority(str,Enum):
    LOW="low"
    MEDIUM="medium"
    HIGH="high"
    CRITICAL="critical"


# ──────────────────────────────────────────────
# Raw Document Schemas (input)
# ──────────────────────────────────────────────
class EmailDoc(BaseModel):
    sender: str
    recipients: list[str]=[]
    cc: list[str]=[]
    subject: str=""
    body: str=""
    timestamp: Optional[str]=None
    thread_id: Optional[str]=None
    attachments: list[str]=[]

class DocumentDoc(BaseModel):
    title: str=""
    source_path: Optional[str]=None
    author: Optional[str]=None
    timestamp: Optional[str]=None
    body: str=""

class MeetingDoc(BaseModel):
    title: str=""
    participants: list[str]=[]
    date: Optional[str]=None
    body: str=""
    decisions: list[str]=[]
    action_items: list[str]=[]
    follow_ups: list[str]=[]

class TicketDoc(BaseModel):
    ticket_id: Optional[str]=None
    reporter: Optional[str]=None
    assignee: Optional[str]=None
    status: Optional[str]=None
    priority: Optional[str]=None
    created_at: Optional[str]=None
    due_at: Optional[str]=None
    summary: str=""
    body: str=""


# ──────────────────────────────────────────────
# ETL pipeline specific schemas
# ──────────────────────────────────────────────
class UnifiedDocument(BaseModel):
    doc_id: str=Field(default_factory=_uid)
    doc_type: DocType=DocType.UNKNOWN
    title: str=""
    author: Optional[str]=None
    timestamp: Optional[str]=None
    body: str=""
    metadata: dict[str,Any]={}
    source_file: Optional[str]=None
    ingested_at: str=Field(default_factory=lambda: datetime.utcnow().isoformat())

class TextChunk(BaseModel):
    chunk_id: str=Field(default_factory=_uid)
    doc_id: str
    text: str
    chunk_index: int=0
    metadata: dict[str,Any]={}


# ──────────────────────────────────────────────
# Graph schemas
# ──────────────────────────────────────────────
class GraphNode(BaseModel):
    node_id: str=Field(default_factory=_uid)
    name: str
    node_type: NodeType
    properties: dict[str,Any]=Field(default_factory=dict)
    source_chunk_ids: list[str]=Field(default_factory=list)
    source_doc_ids: list[str]=Field(default_factory=list)
    confidence: float=1.0

class GraphEdge(BaseModel):
    edge_id: str=Field(default_factory=_uid)
    source: str          
    target: str         
    edge_type: EdgeType
    properties: dict[str,Any]=Field(default_factory=dict)
    source_chunk_ids: list[str]=Field(default_factory=list)
    confidence: float=1.0

# ──────────────────────────────────────────────
# Extraction Models
# ──────────────────────────────────────────────

class ExtractedTriple(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: float=0.8
    source_chunk_id: Optional[str]=None
    source_doc_id: Optional[str]=None

class ExtractedAction(BaseModel):
    action: str
    assignee: Optional[str]=None
    deadline: Optional[str]=None
    source_chunk_id: Optional[str]=None

class ExtractionResult(BaseModel):
    entities: list[GraphNode]=[]
    edges: list[GraphEdge]=[]
    actions: list[ExtractedAction]=[]
    triples: list[ExtractedTriple]=[]

# ──────────────────────────────────────────────
# Retrieval Models
# ──────────────────────────────────────────────

class RetrievedEvidence(BaseModel):
    content: str
    source_type: str="unknown"      # "graph","vector","lexical"
    source_id: Optional[str]=None
    doc_id: Optional[str]=None
    score: float=0.0
    metadata: dict[str,Any]={}

class RetrievalDebug(BaseModel):
    query_route: str=""
    graph_results_count: int=0
    vector_results_count: int=0
    merged_count: int=0
    latency_ms: dict[str,float]={}



# ──────────────────────────────────────────────
# API Schemas
# ──────────────────────────────────────────────

class IngestRequest(BaseModel):
    doc_type: Optional[str]=None    
    content: Optional[dict[str,Any]]=None
    documents: Optional[list[dict[str,Any]]]=None
    raw_text: Optional[str]=None

class IngestResponse(BaseModel):
    status: str="ok"
    doc_ids: list[str]=[]
    entities_extracted: int=0
    edges_extracted: int=0
    chunks_indexed: int=0
    message: str=""

class QueryRequest(BaseModel):
    question: str
    max_results: int=10
    include_debug: bool=False

class QueryResponse(BaseModel):
    answer: str
    confidence: float=0.0
    citations: list[dict[str,Any]]=[]
    evidence: list[RetrievedEvidence]=[]
    debug: Optional[RetrievalDebug]=None

class EntityResponse(BaseModel):
    name: str
    node_type: str=""
    properties: dict[str,Any]={}
    connections: list[dict[str,Any]]=[]
    source_docs: list[str]=[]

class PathResponse(BaseModel):
    source: str
    target: str
    path: list[str]=[]
    edges: list[dict[str,Any]]=[]
    exists: bool=False

class SearchResponse(BaseModel):
    results: list[RetrievedEvidence]=[]
    total: int=0

class StatsResponse(BaseModel):
    total_documents: int=0
    total_chunks: int=0
    total_nodes: int=0
    total_edges: int=0
    doc_type_counts: dict[str,int]={}
    node_type_counts: dict[str,int]={}
    edge_type_counts: dict[str,int]={}

# ──────────────────────────────────────────────────
# Langgraph state query schema (for GraphOperations)
# ──────────────────────────────────────────────────

class QueryState(TypedDict,total=False):
    """
    State that flows through the LangGraph query pipeline.
    """
    question: str
    max_results: int
    include_debug: bool
    route: str
    graph_evidence: list[RetrievedEvidence]
    vector_evidence: list[RetrievedEvidence]
    merged_evidence: list[RetrievedEvidence]
    response: QueryResponse|None
    latency: dict[str,float]
    storage: Any 