import time

from backend.utils.logging import setup_logging,get_logger
from backend.utils.utilities import run_llm
from backend.utils.prompts import Prompts
from backend.utils.pydantic_models import QueryRoute,QueryState,RetrievalDebug
from backend.graph.retrieval import merge_evidence
from backend.graph.generation import generate_answer,validate_answer
from backend.graph.retrieval import retrieve_graph,retrieve_vector

setup_logging()
logger=get_logger(__name__,service="graph.nodes")

def query_classfn(questions:str)->QueryRoute:
    t0=time.time()
    ans=run_llm(Prompts.GHV_CLASSIFICATION.format(question=questions))
    ans=ans.strip().lower().replace('"','').replace("'","")
    route=QueryRoute.HYBRID  
    if "graph_first" in ans:
        route=QueryRoute.GRAPH_FIRST
    elif "vector_first" in ans:
        route=QueryRoute.VECTOR_FIRST
    elif "hybrid" in ans:
        route=QueryRoute.HYBRID

    elapsed=time.time()-t0
    logger.info("query classified",route=route.value,elapsed_ms=round(elapsed*1000))
    return route

def classify_node(state:QueryState)->dict:
    """
    LangGraph node: classify the query into a retrieval route.
    """
    t=time.time()
    route=query_classfn(state["question"]) #type:ignore
    latency=_lat(state,"classify_ms",t)
    return {
        "route":route.value,
        "latency":latency
    }


def retrieve_graph_node(state:QueryState)->dict:
    """
    LangGraph node: retrieve evidence from knowledge graph.
    """
    t=time.time()
    storage=state["storage"]  #type:ignore
    evidence=retrieve_graph(state["question"], #type:ignore
                            storage,
                            max_results=state.get("max_results",10))
    latency=_lat(state,"graph_retrieval_ms",t)
    return {
        "graph_evidence":evidence,
        "latency":latency
    }


def retrieve_vector_node(state:QueryState)->dict:
    """
    LangGraph node: retrieve evidence from vector store.
    """
    t=time.time()
    storage=state["storage"] #type:ignore
    evidence=retrieve_vector(state["question"], #type:ignore
                             storage,
                             n_results=state.get("max_results",10))
    latency=_lat(state,"vector_retrieval_ms",t)
    return {
        "vector_evidence":evidence,
        "latency":latency
    }


def merge_node(state:QueryState)->dict:
    """
    LangGraph node: merge graph and vector evidence using RRF.
    """
    t=time.time()
    ev_g=state.get("graph_evidence",[])
    ev_v=state.get("vector_evidence",[])
    merged=merge_evidence(ev_g,
                          ev_v,
                          max_results=state.get("max_results",10))
    latency=_lat(state,"merge_ms",t)
    return {
        "merged_evidence":merged,
        "latency":latency
    }



def generate_node(state:QueryState)->dict:
    """
    LangGraph node: generate grounded answer from evidence.
    """
    t=time.time()
    merged=state.get("merged_evidence",[])
    route=QueryRoute(state.get("route","hybrid"))
    response=generate_answer(state["question"],merged,route)  #type:ignore
    latency=_lat(state,"generate_ms",t) 
    return {
        "response":response,
        "latency":latency
    }


def validate_node(state:QueryState)->dict:
    """
    LangGraph node: validate answer quality and attach debug info.
    """
    response=state.get("response")
    if not response:
        return state  #type:ignore
    response=validate_answer(response) 
    latency=dict(state.get("latency",{}))
    latency["total_ms"]=sum(v for k,v in latency.items() if k != "total_ms")
    
    if state.get("include_debug"):
        response.debug=RetrievalDebug(
            query_route=state.get("route",""),
            graph_results_count=len(state.get("graph_evidence",[])),
            vector_results_count=len(state.get("vector_evidence",[])),
            merged_count=len(state.get("merged_evidence",[])),
            latency_ms=latency,
        )
    return {
        "response":response,
        "latency":latency
    }

def route_after_classify(state:QueryState)->str:
    """Conditional edge: route to retrieval strategy based on classification."""
    route=state.get("route","hybrid")
    if route=="graph_first":
        return "retrieve_graph"
    elif route=="vector_first":
        return "retrieve_vector"
    else:
        return "retrieve_both_graph"

def _lat(state,key,t0):
    latency=dict(state.get("latency",{}))
    latency[key]=round((time.time()-t0)*1000)
    return latency




