from __future__ import annotations

import asyncio
import mlflow

from backend.graph_orch import run_query_pipeline
from fastapi import HTTPException,Request,Depends,APIRouter
from backend.utils.pydantic_models import QueryRequest,QueryResponse

def _get_storage(request: Request):
    return request.app.state.storage

router=APIRouter()

@router.post("/query",response_model=QueryResponse)
async def query(request: QueryRequest,storage=Depends(_get_storage),):
    """
    Answer a question using hybrid graph + vector retrieval.
    """
    if not storage:
        raise HTTPException(status_code=503,detail="Storage not initialized")
    if not request.question.strip():
        raise HTTPException(status_code=400,detail="Question cannot be empty")

    response = await asyncio.to_thread(
        run_query_pipeline,
        question=request.question,
        storage=storage,
        max_results=request.max_results,
        include_debug=request.include_debug,
    )

    # Log query metrics to MLFlow
    with mlflow.start_run(run_name="query"):
        mlflow.log_params({
            "question": request.question[:250],
            "route": response.debug.query_route if response.debug else "unknown",
            })
        metrics={
            "confidence": response.confidence,
            "citation_count": len(response.citations) if response.citations else 0,
            "evidence_count": len(response.evidence) if response.evidence else 0,
            }
        if response.debug and response.debug.latency_ms:
            for k,v in response.debug.latency_ms.items():
                metrics[f"latency_{k}"]=v
        mlflow.log_metrics(metrics)

    return response

