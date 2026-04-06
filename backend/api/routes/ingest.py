from __future__ import annotations

import mlflow

from typing import Any
from fastapi import HTTPException,Request,Depends,APIRouter
from backend.ETL import ETL_main
from backend.utils.logging import setup_logging,get_logger
from backend.utils.pydantic_models import IngestRequest,IngestResponse,DocType
from backend.utils.extraction import type_detn,normalize,chunk_text

setup_logging()
logger=get_logger(__name__,service="extraction")

def _get_storage(request: Request):
    return request.app.state.storage

router=APIRouter()

@router.post("/ingest",response_model=IngestResponse)

async def ingest(request:IngestRequest,
                 storage=Depends(_get_storage),):
    """
    Ingest documents into the knowledge graph and vector store.
    
    Accepts single document via 'content' or batch via 'documents'.
    Auto-detects document type if not specified.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")

    documents_to_process: list[dict[str,Any]]=[]

    if request.documents:
        documents_to_process.extend(request.documents)
    elif request.content:
        documents_to_process.append(request.content)
    elif request.raw_text:
        documents_to_process.append({"body": request.raw_text,"title": "Raw Text Input"})
    else:
        raise HTTPException(status_code=400,detail="Provide 'content','documents',or 'raw_text'")

    all_doc_ids: list[str]=[]
    total_entities=0
    total_edges=0
    total_chunks=0

    for raw_doc in documents_to_process:
        try:
            #1. Detect type
            doc_type=DocType(request.doc_type) if request.doc_type else type_detn(raw_doc)

            #2. Normalize
            unified=normalize(raw_doc,doc_type)
            all_doc_ids.append(unified.doc_id)

            #3. Store metadata
            storage.metadata.insert_document(unified)

            #4. Chunk
            chunks=chunk_text(unified,unified.doc_id,)
            storage.metadata.insert_chunks(chunks)
            total_chunks+=len(chunks)

            #5. Index in vector store
            storage.vectors.add_chunks(chunks)

            #6. Extract entities & relations
            extraction=ETL_main(unified,chunks)

            #7. Populate graph
            for node in extraction.entities:
                storage.graph.add_node(node)
                total_entities+=1
            for edge in extraction.edges:
                storage.graph.add_edge(edge)
                total_edges+=1

            logger.info("document_ingested",
                        doc_id=unified.doc_id,
                        doc_type=doc_type.value,
                        chunks=len(chunks),
                        entities=len(extraction.entities),
                        edges=len(extraction.edges))

        except Exception as e:
            logger.error("ingest_failed",error=str(e),raw_doc_keys=list(raw_doc.keys()))
            raise HTTPException(status_code=422,detail=f"Failed to ingest document: {e}")

    storage.graph.persist()

    with mlflow.start_run(run_name=f"ingest_{len(all_doc_ids)}_docs"):
        mlflow.log_params({
            "doc_type": request.doc_type or "auto",
            "doc_count": len(all_doc_ids),
            })
        mlflow.log_metrics({
            "entities_extracted": total_entities,
            "edges_extracted": total_edges,
            "chunks_indexed": total_chunks,
            })

    return IngestResponse(
        status="ok",
        doc_ids=all_doc_ids,
        entities_extracted=total_entities,
        edges_extracted=total_edges,
        chunks_indexed=total_chunks,
        message=f"Ingested {len(all_doc_ids)} document(s) successfully.",
        )

