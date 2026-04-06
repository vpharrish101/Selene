import time

from backend.utils.logging import setup_logging,get_logger
from backend.infra.inference import StorageManager
from backend.utils.pydantic_models import QueryResponse,QueryState
from backend.graph.pipeline import query_pipeline


setup_logging()
logger=get_logger(__name__,service="GraphOperations")

def run_query_pipeline(question:str, 
                       storage:StorageManager,
                       max_results:int=10,
                       include_debug:bool=False)->QueryResponse:
    """
    Execute the full query pipeline via LangGraph StateGraph.    
    Pipeline:classify->retrieve (graph/vector/both)->merge->generate->validate
    """
    
    initial_state:QueryState={
        "question":question,
        "max_results":max_results,
        "include_debug":include_debug,
        "route":"",
        "graph_evidence":[],
        "vector_evidence":[],
        "merged_evidence":[],
        "response":None,
        "latency":{},
        "storage":storage,
    }

    # Run the compiled LangGraph pipeline
    final_state=query_pipeline.invoke(initial_state)
    response=final_state.get("response")
    if not response:
        response=QueryResponse(
            answer="Pipeline failed to produce a response.",
            confidence=0.0,
        )

    logger.info("query_pipeline_done", 
                route=final_state.get("route",""),
                confidence=response.confidence, 
                latency=final_state.get("latency",{}))
    return response


def _lat(state,key,t0):
    latency=dict(state.get("latency",{}))
    latency[key]=round((time.time()-t0)*1000)
    return latency


    

