from __future__ import annotations

from fastapi import HTTPException,Query,Request,Depends,APIRouter
from backend.utils.pydantic_models import EntityResponse,PathResponse

def _get_storage(request: Request):
    return request.app.state.storage

router=APIRouter()

@router.get("/graph/data")
async def get_full_graph(storage=Depends(_get_storage)):
    """
    Get the entire knowledge graph (nodes and links) for visualization.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")
    return storage.graph.get_full_graph()


@router.get("/graph/entity/{name}",response_model=EntityResponse)
async def get_entity(name: str,
                     storage=Depends(_get_storage)):
    """
    Look up an entity in the knowledge graph and its connections.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")
    node=storage.graph.get_node(name)
    if not node:
        raise HTTPException(status_code=404,detail=f"Entity '{name}' not found")
    connections=storage.graph.get_connections(name)

    return EntityResponse(
        name=node.get("name",name),
        node_type=node.get("node_type","Unknown"),
        properties=node.get("properties",{}),
        connections=connections,
        source_docs=node.get("source_doc_ids",[]),
    )


@router.get("/graph/path",response_model=PathResponse)
async def get_path(
    source: str=Query(...,description="Source entity name"),
    target: str=Query(...,description="Target entity name"),storage=Depends(_get_storage),):

    """
    Find shortest path between two entities in the knowledge graph.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")

    path=storage.graph.shortest_path(source,target)
    edges=storage.graph.get_path_edges(source,target)

    return PathResponse(
        source=source,
        target=target,
        path=path,
        edges=edges,
        exists=len(path)>0,
    )
