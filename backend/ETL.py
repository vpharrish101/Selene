import time

from backend.utils.extraction import entity_resoln
from backend.utils.logging import setup_logging,get_logger
from backend.utils.utilities import run_llm,extract_json
from backend.utils.prompts import Prompts
from backend.utils.pydantic_models import TextChunk,GraphNode,GraphEdge,ExtractedTriple,NodeType,EdgeType,ExtractedAction,UnifiedDocument,DocType,ExtractionResult
from backend.config import Config

setup_logging()
logger=get_logger(__name__,service="extraction")


def ER_extract(chunk:TextChunk,
               retries:int=Config.ETL_RETRIES)->tuple[list[GraphNode],list[GraphEdge],list[ExtractedTriple]]:
    
    prompt=Prompts.ENTITY_EXTRACTION.format(text=chunk.text[:8000])
    nodes:list[GraphNode]=[]
    edges:list[GraphEdge]=[]
    triples:list[ExtractedTriple]=[]

    for tries in range(retries+1):
        raw=run_llm(prompt)
        if not raw: continue
        parsed=extract_json(raw)
        if not parsed or not isinstance(parsed,dict):
            logger.warning("extraction_parse_failed",attempt=tries,chunk_id=chunk.chunk_id)
            continue 

        for entity in parsed.get("entities",[]):
            if not isinstance(entity,dict) or "name" not in entity:
                continue
            nt=_map_node_type(entity.get("type","Topic"))
            nodes.append(
                GraphNode(
                    name=entity["name"],
                    node_type=nt,
                    properties=entity.get("properties", {}),
                    source_chunk_ids=[chunk.chunk_id],
                    source_doc_ids=[chunk.doc_id],
                    confidence=entity.get("confidence", Config.EXTRACTION_CONFIDENCE),
                )
            )
        
        for rel in parsed.get("relations",[]):
            if not isinstance(rel,dict):
                continue
            if "subject" not in rel or "object" not in rel:
                continue
            et=_map_edge_type(rel.get("predicate","RELATED_TO"))
            conf=float(rel.get("confidence",Config.EXTRACTION_CONFIDENCE))
            edges.append(GraphEdge(
                source=rel["subject"],
                target=rel["object"],
                edge_type=et,
                source_chunk_ids=[chunk.chunk_id],
                confidence=conf,
            ))
            triples.append(ExtractedTriple(
                subject=rel["subject"],
                predicate=et.value,
                object=rel["object"],
                confidence=conf,
                source_chunk_id=chunk.chunk_id,
                source_doc_id=chunk.doc_id,
            ))
        logger.info("extraction_complete",chunk_id=chunk.chunk_id,entities=len(nodes),relations=len(edges))
        if nodes or edges: 
            break
        
    return nodes,edges,triples


def Action_extract(chunk:TextChunk)->list[ExtractedAction]:
    """
    Extract action items and deadlines from chunk blobs.
    """
    prompt=Prompts.ACTION_EXTRACTION.format(text=chunk.text[:8000])
    ans=run_llm(prompt)
    if not ans:
        logger.error("Action Extraction prompt returned none") 
        return []
    parsed=extract_json(ans)
    if not parsed or not isinstance(parsed,dict):
        return []
    actions=[]
    for act in parsed.get("actions",[]):
        if not isinstance(act,dict) or "action" not in act:
            logger.warning("No actions found",chunk_id=chunk.chunk_id)
            continue
        actions.append(
            ExtractedAction(
                action=act["action"],
                assignee=act.get("assignee"),
                deadline=act.get("deadline"),
                source_chunk_id=chunk.chunk_id,
            )
        )
    return actions


def SR_extract(doc:UnifiedDocument)->tuple[list[GraphNode],list[GraphEdge]]:
    """
    Extract graph nodes/edges directly from document metadata w/o llm.
    """
    nodes:list[GraphNode]=[]
    edges:list[GraphEdge]=[]
    meta=doc.metadata
    if doc.doc_type==DocType.EMAIL:
        # Document node
        nodes.append(GraphNode(name=doc.title or doc.doc_id,
                                node_type=NodeType.EMAIL,
                                source_doc_ids=[doc.doc_id]))
        email_name=doc.title or doc.doc_id

        # Sender
        if meta.get("sender"):
            nodes.append(GraphNode(name=meta["sender"],
                                    node_type=NodeType.PERSON,
                                    source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=meta["sender"],
                                    target=email_name,
                                    edge_type=EdgeType.SENT_BY,
                                    source_chunk_ids=[],
                                    confidence=1.0))
                        
        # Recipients
        for r in meta.get("recipients",[]):
            nodes.append(GraphNode(name=r, 
                                    node_type=NodeType.PERSON,
                                    source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=email_name, 
                                    target=r,
                                    edge_type=EdgeType.SENT_TO, 
                                    confidence=1.0))
            
        # CC
        for c in meta.get("cc",[]):
            nodes.append(GraphNode(name=c, 
                                    node_type=NodeType.PERSON,
                                    source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=email_name, 
                                    target=c,
                                    edge_type=EdgeType.CC_TO, 
                                    confidence=1.0))
            
    elif doc.doc_type==DocType.MEETING:
        nodes.append(GraphNode(name=doc.title or doc.doc_id,
                                node_type=NodeType.MEETING,
                                source_doc_ids=[doc.doc_id]))
        meeting_name=doc.title or doc.doc_id
        for p in meta.get("participants",[]):
            nodes.append(GraphNode(name=p,
                                    node_type=NodeType.PERSON,
                                    source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=p,
                                    target=meeting_name,
                                    edge_type=EdgeType.PARTICIPATED_IN, 
                                    confidence=1.0))

    elif doc.doc_type==DocType.TICKET:
        ticket_name=meta.get("ticket_id") or doc.title or doc.doc_id
        nodes.append(GraphNode(name=ticket_name, 
                                node_type=NodeType.TICKET,
                                properties={"status":meta.get("status"),
                                            "priority":meta.get("priority"),
                                            "due_at":meta.get("due_at")},
                                source_doc_ids=[doc.doc_id]))
        
        if meta.get("reporter"):
            nodes.append(GraphNode(name=meta["reporter"], 
                                    node_type=NodeType.PERSON,
                                    source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=meta["reporter"], 
                                    target=ticket_name,
                                    edge_type=EdgeType.REPORTED_BY, 
                                    confidence=1.0))
            
        if meta.get("assignee"):
            nodes.append(GraphNode(name=meta["assignee"],
                                    node_type=NodeType.PERSON,
                                    source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=ticket_name, 
                                    target=meta["assignee"],
                                    edge_type=EdgeType.ASSIGNED_TO, 
                                    confidence=1.0))
            
        if meta.get("due_at"): 
            dl_name = f"Deadline:{meta['due_at']}"
            nodes.append(GraphNode(name=dl_name, 
                                   node_type=NodeType.DEADLINE,
                                   properties={"date": meta["due_at"]},
                                   source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=ticket_name, 
                                   target=dl_name,
                                   edge_type=EdgeType.DUE_ON,
                                   confidence=1.0))

    elif doc.doc_type == DocType.DOCUMENT:
        nodes.append(GraphNode(name=doc.title or doc.doc_id,
                               node_type=NodeType.DOCUMENT,
                               source_doc_ids=[doc.doc_id]))
        if doc.author:
            nodes.append(GraphNode(name=doc.author, 
                                   node_type=NodeType.PERSON,
                                   source_doc_ids=[doc.doc_id]))
            edges.append(GraphEdge(source=doc.author, 
                                   target=doc.title or doc.doc_id,
                                   edge_type=EdgeType.OWNS, 
                                   confidence=1.0))

    return nodes,edges
    

def ETL_main(doc:UnifiedDocument,
             chunks:list[TextChunk])->ExtractionResult:
    """
    Run the complete extraction pipeline on a document and its chunks.
    """
    t0=time.time()

    nodes:list[GraphNode]=[]
    edges:list[GraphEdge]=[]
    triples:list[ExtractedTriple]=[]
    actions:list[ExtractedAction]=[]
    
    #1. Manual/Syntactic E/N (edge/node) extraction
    struct_nodes,struct_edges=SR_extract(doc)
    nodes.extend(struct_nodes)
    edges.extend(struct_edges)

    # 1.5 Global Context Generation
    doc_summary = ""
    if doc.body and len(doc.body.strip()) > 50:
        doc_summary = run_llm("Summarize the key entities, people, and structure in one short paragraph:\n\n" + doc.body[:4000])

    # 2. Sematic E/N extraction (Grouped & Filtered)
    valid_chunks = [c for c in chunks if len(c.text.strip()) >= 50]
    grouped_chunks = []
    
    for i in range(0, len(valid_chunks), 3):
        group = valid_chunks[i:i+3]
        combined_text = "\n---\n".join([c.text for c in group])
        if doc_summary:
            combined_text=f"GLOBAL CONTEXT SUMMARY:\n{doc_summary}\n\nLOCAL CHUNK TEXT:\n{combined_text}"
        
        proxy_chunk=TextChunk(
            doc_id=doc.doc_id,
            text=combined_text,
            chunk_index=group[0].chunk_index,
            chunk_id=group[0].chunk_id,
            metadata=group[0].metadata
        )
        grouped_chunks.append(proxy_chunk)

    for chunk in grouped_chunks:
        s_node,s_edge,s_triple=ER_extract(chunk)
        s_action=Action_extract(chunk)

        nodes.extend(s_node)
        edges.extend(s_edge)
        triples.extend(s_triple)
        actions.extend(s_action)

        for action in actions:
            if action.assignee:
                nodes.append(GraphNode(
                    name=action.assignee,
                    node_type=NodeType.PERSON,
                    source_chunk_ids=[chunk.chunk_id], 
                    source_doc_ids=[chunk.doc_id],
                ))
                task_name=action.action[:60]
                nodes.append(GraphNode(
                    name=task_name, 
                    node_type=NodeType.TASK,
                    properties={"deadline":action.deadline},
                    source_chunk_ids=[chunk.chunk_id], 
                    source_doc_ids=[chunk.doc_id],
                ))
                edges.append(GraphEdge(
                    source=task_name, 
                    target=action.assignee,
                    edge_type=EdgeType.ACTION_ITEM_FOR,
                    source_chunk_ids=[chunk.chunk_id], 
                    confidence=0.85,
                ))
                if action.deadline:
                    dl_name=f"Deadline:{action.deadline}"
                    nodes.append(GraphNode(
                        name=dl_name, 
                        node_type=NodeType.DEADLINE,
                        properties={"date":action.deadline},
                        source_chunk_ids=[chunk.chunk_id], 
                        source_doc_ids=[chunk.doc_id],
                    ))
                    edges.append(GraphEdge(
                        source=task_name, 
                        target=dl_name,
                        edge_type=EdgeType.DUE_ON,
                        source_chunk_ids=[chunk.chunk_id], 
                        confidence=0.9,
                    ))
    dedup_nodes=entity_resoln(nodes)
    elapsed=time.time()-t0
    logger.info("Pipeline extracted", 
                doc_id=doc.doc_id,
                entities=len(nodes), 
                edges=len(edges),
                actions=len(actions), 
                elapsed_ms=round(elapsed*1000))
    
    return ExtractionResult(
        entities=nodes,
        edges=edges,
        actions=actions,
        triples=triples
    )



def _map_node_type(raw:str)->NodeType:
    mapping={v.value.lower(): v for v in NodeType}
    return mapping.get(raw.strip().lower(),NodeType.TOPIC)

def _map_edge_type(raw:str)->EdgeType:
    mapping={v.value.lower(): v for v in EdgeType}
    return mapping.get(raw.strip().lower().replace(" ","_"),EdgeType.RELATED_TO)

    