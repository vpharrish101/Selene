from __future__ import annotations

import asyncio
from fastapi import HTTPException, Query, Request,APIRouter,Depends
from backend.utils.pydantic_models import SearchResponse
from backend.graph.retrieval import retrieve_vector,merge_evidence,retrieve_graph

def _get_storage(request: Request):
    return request.app.state.storage

router=APIRouter()


@router.get("/search",response_model=SearchResponse)
async def search(
    q:str=Query(...,description="Search query"),
    mode:str=Query("hybrid",description="Search mode: semantic, lexical, or hybrid"),
    limit:int=Query(10,ge=1,le=50,description="Max results",),
    storage=Depends(_get_storage),):

    """
    Search the knowledge base using semantic, lexical, or hybrid mode.
    """
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    if mode=="hybrid":
        graph_results, semantic, lexical = await asyncio.gather(
            asyncio.to_thread(retrieve_graph, q, storage, 2, limit),
            asyncio.to_thread(retrieve_vector, q, storage, limit, "semantic"),
            asyncio.to_thread(retrieve_vector, q, storage, limit, "lexical")
        )
        results=merge_evidence(graph_results,semantic+lexical,max_results=limit)
    elif mode=="lexical":
        results = await asyncio.to_thread(retrieve_vector, q, storage, limit, "lexical")
    else:
        results = await asyncio.to_thread(retrieve_vector, q, storage, limit, "semantic")

    return SearchResponse(results=results,total=len(results))

