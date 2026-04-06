import time

from backend.infra.inference import StorageManager
from backend.utils.pydantic_models import RetrievedEvidence
from backend.utils.utilities import run_llm
from backend.utils.logging import setup_logging,get_logger
from backend.config import Config

setup_logging()
logger=get_logger(__name__,service="extraction")

def retrieve_graph(question:str,
                   storage:StorageManager,
                   max_hops:int=Config.GRAPH_MAX_HOPS,
                   max_results:int=Config.GRAPH_MAX_RESULTS)->list[RetrievedEvidence]:
    
    """
    Retrieve evidence from the knowledge graph.
        1. Extract entity names from the question
        2. Find matching nodes in the graph
        3. Expand subgraph via multi-hop traversal
        4. Collect edges and connected nodes as evidence
    """

    t0=time.time()
    evidence:list[RetrievedEvidence]=[]

    # Extract key terms to search in graph
    entities=_extract_query_entities(question)

    for entity in entities:
        # Direct node match
        matches=storage.graph.find_nodes(entity)
        for match in matches[:5]:
            evidence.append(RetrievedEvidence(
                content=_format_node_evidence(match),
                source_type="graph",
                source_id=match.get("key",""),
                doc_id=match.get("source_doc_ids",[""])[0] if match.get("source_doc_ids") else None,
                score=match.get("confidence",0.7),
                metadata={"node_type":match.get("node_type",""),
                           "entity":match.get("name","")},))

            # Get connections
            conns=storage.graph.get_connections(match.get("name",""))
            for conn in conns[:10]:
                evidence.append(RetrievedEvidence(
                    content=_format_edge_evidence(conn),
                    source_type="graph",
                    source_id=conn.get("edge_id",""),
                    score=conn.get("confidence",0.6),
                    metadata={"edge_type":conn.get("edge_type",""),
                               "direction":conn.get("direction","")},))

        # Multi-hop expansion for top match
        if matches:
            top_name=matches[0].get("name","")
            subgraph=storage.graph.multi_hop(top_name,max_hops=max_hops)
            for edge in subgraph.get("edges",[])[:max_results]:
                ev=RetrievedEvidence(
                    content=f"{edge.get('from','')} --[{edge.get('edge_type','')}]--> {edge.get('to','')}",
                    source_type="graph",
                    score=edge.get("confidence",0.5),
                    metadata={"hop":"multi","edge_type":edge.get("edge_type","")},)
                # Deduplicate
                if ev.content not in [e.content for e in evidence]:
                    evidence.append(ev)

    elapsed=time.time()-t0
    logger.info("graph_retrieval_done",count=len(evidence),elapsed_ms=round(elapsed * 1000))
    return evidence[:max_results]


def retrieve_vector(question:str,
                    storage:StorageManager,
                    n_results:int=10,
                    mode:str="semantic")->list[RetrievedEvidence]:
    """
    Retrieve evidence from vector store using semantic or lexical search.
    """
    t0=time.time()
    evidence:list[RetrievedEvidence]=[]

    if mode=="lexical":
        results=storage.vectors.search_lexical(question,n_results=n_results)
    else:
        results=storage.vectors.search_semantic(question,n_results=n_results)

    for r in results:
        evidence.append(RetrievedEvidence(
            content=r.get("text",""),
            source_type="vector",
            source_id=r.get("chunk_id",""),
            doc_id=r.get("metadata",{}).get("doc_id"),
            score=r.get("score",0.0),
            metadata=r.get("metadata",{}),
        ))

    elapsed=time.time()-t0
    logger.info("vector_retrieval_done",mode=mode,count=len(evidence),elapsed_ms=round(elapsed*1000))
    return evidence



def merge_evidence(graph_results:list[RetrievedEvidence],
                   vector_results:list[RetrievedEvidence],
                   k:int=Config.RRF_K_PARAM,
                   max_results:int=15)->list[RetrievedEvidence]:
    """
    Merge graph and vector results using Reciprocal Rank Fusion (RRF).
    """
    t0=time.time()

    # Build RRF scores
    scores:dict[str,float]={}
    items:dict[str,RetrievedEvidence]={}

    for rank,ev in enumerate(graph_results):
        content_key=ev.content[:200]  
        scores[content_key]=scores.get(content_key,0)+1.0/(k+rank+1)
        if content_key not in items:
            items[content_key]=ev

    for rank,ev in enumerate(vector_results):
        content_key=ev.content[:200]
        scores[content_key]=scores.get(content_key,0)+1.0/(k+rank+1)
        if content_key not in items:
            items[content_key]=ev

    # Sort by RRF score
    sorted_keys=sorted(scores.keys(),key=lambda x:scores[x],reverse=True)
    merged=[]
    for key in sorted_keys[:max_results]:
        ev=items[key]
        ev.score=scores[key]
        merged.append(ev)

    elapsed=time.time()-t0
    logger.info("evidence_merged",
                graph=len(graph_results),
                vector=len(vector_results),
                merged=len(merged),
                elapsed_ms=round(elapsed*1000))
    
    return merged

import functools

@functools.lru_cache(maxsize=128)
def _extract_query_entities(question:str)->list[str]:
    """
    Extract potential entity names from a question using LLM.
    """
    prompt=(
        "Extract the key entity names (people, projects, tasks, topics, ticket IDs) "
        "from this question. Return ONLY a comma-separated list of names, nothing else.\n\n"
        f"Question: {question}\n\nEntities:"
    )
    
    raw=run_llm(prompt)
    if not raw:
        # Fallback: use significant words
        stop_words={"who", "what", "when", "where", "why", "how", "is", "are", "the",
                      "a", "an", "for", "to", "from", "in", "on", "at", "by", "with",
                      "this", "that", "it", "of", "and", "or", "all", "show", "find",
                      "which", "related", "connected", "responsible", "overdue",
                      "between", "about", "does", "do", "did", "was", "were",
                      "has", "have", "had", "been", "be", "will", "would", "could",
                      "should", "can", "may", "might", "must", "shall"}
        
        words=question.replace("?", "").replace(",", "").split()
        return [w for w in words if w.lower() not in stop_words and len(w) > 2]
    return [e.strip() for e in raw.split(",") if e.strip()]


def _format_node_evidence(node:dict)->str:
    """
    Format a graph node as readable evidence.
    """
    name=node.get("name","Unknown")
    ntype=node.get("node_type","")
    props=node.get("properties",{})
    parts=[f"[{ntype}] {name}"]
    if props:
        prop_strs=[f"{k}={v}" for k, v in props.items() if v]
        if prop_strs:
            parts.append(f"({', '.join(prop_strs)})")
    return " ".join(parts)


def _format_edge_evidence(conn:dict)->str:
    """
    Format a graph edge as readable evidence.
    """
    direction=conn.get("direction","out")
    edge_type=conn.get("edge_type","RELATED_TO")
    if direction=="out":
        return f"--[{edge_type}]--> {conn.get('target_name', conn.get('target', '?'))}"
    else:
        return f"{conn.get('source_name', conn.get('source', '?'))} --[{edge_type}]-->"


