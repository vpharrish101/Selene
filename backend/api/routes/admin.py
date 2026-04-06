from __future__ import annotations

from fastapi import HTTPException,Request,APIRouter,Depends
from backend.utils.pydantic_models import StatsResponse,UnifiedDocument
from backend.utils.extraction import simple_chunk



def _get_storage(request: Request):
    return request.app.state.storage

router=APIRouter()

@router.post("/reindex")
async def reindex(storage=Depends(_get_storage)):
    """
    Reindex all documents in the vector store from metadata.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")

    docs=storage.metadata.get_all_documents()
    storage.vectors.clear()
    total_chunks=0

    for doc_data in docs:
        doc=UnifiedDocument(**doc_data)
        chunks=simple_chunk(doc.body, 
                            doc.doc_id,
                            metadata={
                                "doc_type": doc.doc_type, 
                                "title": doc.title
                                },
                            )
        storage.vectors.add_chunks(chunks)
        total_chunks+=len(chunks)

    return {
            "status": "ok", 
            "documents_reindexed": len(docs),
            "chunks_indexed": total_chunks
            }


@router.get("/stats",response_model=StatsResponse)
async def stats(storage=Depends(_get_storage)):
    """
    Get system statistics.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")
    return StatsResponse(**storage.stats())


