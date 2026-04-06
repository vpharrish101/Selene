from __future__ import annotations

import os
import time
import mlflow

from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.infra.inference import StorageManager
from backend.utils.logging import setup_logging,get_logger
from backend.api.routes import ingest,query,graph,search,debug,admin

setup_logging()
logger=get_logger(__name__,service="api")


@asynccontextmanager
async def lifespan(app:FastAPI):

    app.state.storage=StorageManager(
        base_dir=os.environ.get("GRAPHRAG_STORAGE_DIR","storage"),
        mongo_uri=os.environ.get("GRAPHRAG_MONGO_URI","mongodb://localhost:27017"),
        mongo_db=os.environ.get("GRAPHRAG_MONGO_DB","graphrag"),
        )

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI","mlruns"))
    mlflow.set_experiment("Selene")

    logger.info("Initialized from lifespan")

    yield

    app.state.storage.persist_all()
    logger.info("Shutdown from lifespan")


app=FastAPI(title="Selene",
            description=(
                "Graph-Based Retrieval Assistant - ingests data,"
                "builds knowledge graphs,and answers questions using hybrid "
                "graph+vector retrieval with grounded citations."
                ),
            version="1.0.0",
            lifespan=lifespan,)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health(request:Request):
    return {
        "status": "healthy",
        "service": "GraphRAG Assistant",
        "version": "1.0.0",
        "storage_initialized": hasattr(request.app.state,"storage"),
    }


@app.middleware("http")
async def timing_middleware(request:Request,call_next):
    t0=time.time()
    response=await call_next(request)
    elapsed=round((time.time()-t0)*1000,2)
    response.headers["X-Response-Time-ms"]=str(elapsed)
    logger.info("request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed_ms=elapsed)
    return response


app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)
app.include_router(search.router)
app.include_router(debug.router)
app.include_router(admin.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
