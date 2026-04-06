from __future__ import annotations

from fastapi import HTTPException,Query,Request,Depends,APIRouter
from backend.graph.nodes import query_classfn
from backend.graph.retrieval import retrieve_graph,retrieve_vector,merge_evidence

def _get_storage(request: Request):
    return request.app.state.storage

router=APIRouter()

@router.get("/debug/retrieval")
async def debug_retrieval(q:str=Query(...,description="Debug query"),
                          storage=Depends(_get_storage)):
    """
    Debug endpoint showing raw retrieval results from all strategies.
    """
    
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")

    route=query_classfn(q)
    graph_results=retrieve_graph(q,storage)
    vector_results=retrieve_vector(q,storage)
    merged=merge_evidence(graph_results,vector_results)

    return {
        "query": q,
        "classified_route": route.value,
        "graph_results": [e.model_dump() for e in graph_results],
        "vector_results": [e.model_dump() for e in vector_results],
        "merged_results": [e.model_dump() for e in merged],
        "counts": {
            "graph": len(graph_results),
            "vector": len(vector_results),
            "merged": len(merged),
        },
    }


@router.get("/debug/graph")
async def debug_graph(
    entity: str=Query(...,description="Entity to inspect"),
    hops: int=Query(2,ge=1,le=4,description="Max hops for subgraph"),storage=Depends(_get_storage)):
    """
    Debug endpoint showing raw graph neighborhood.
    """

    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")

    node=storage.graph.get_node(entity)
    subgraph=storage.graph.multi_hop(entity,max_hops=hops)
    connections=storage.graph.get_connections(entity)

    return {
        "entity": entity,
        "node": node,
        "connections": connections,
        "subgraph": subgraph,
    }

