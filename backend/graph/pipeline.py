from langgraph.graph import StateGraph,END
from typing import TypedDict,Any
from backend.utils.pydantic_models import QueryResponse
from backend.graph.nodes import (
        classify_node,
        retrieve_graph_node,
        retrieve_vector_node,
        merge_node,
        generate_node,
        validate_node,
        route_after_classify)


class QueryState(TypedDict,total=False):
    question: str
    max_results: int
    include_debug: bool
    route: str
    graph_evidence: list
    vector_evidence: list
    merged_evidence: list
    response: QueryResponse|None
    latency: dict[str,float]
    storage: Any


def build_query_graph():
    graph=StateGraph(QueryState)
    
    graph.add_node("classify",classify_node)
    graph.add_node("retrieve_graph",retrieve_graph_node)
    graph.add_node("retrieve_vector",retrieve_vector_node)
    graph.add_node("retrieve_both_graph",retrieve_graph_node)
    graph.add_node("retrieve_both_vector",retrieve_vector_node)
    graph.add_node("retrieve_vector_supplement",retrieve_vector_node)
    graph.add_node("retrieve_graph_supplement",retrieve_graph_node)
    graph.add_node("merge",merge_node)
    graph.add_node("generate",generate_node)
    graph.add_node("validate",validate_node)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "retrieve_graph": "retrieve_graph",
            "retrieve_vector": "retrieve_vector",
            "retrieve_both_graph": "retrieve_both_graph",
        },
    )

    graph.add_edge("retrieve_graph","retrieve_vector_supplement")
    graph.add_edge("retrieve_vector_supplement","merge")

    graph.add_edge("retrieve_vector","retrieve_graph_supplement")
    graph.add_edge("retrieve_graph_supplement","merge")

    graph.add_edge("retrieve_both_graph","retrieve_both_vector")
    graph.add_edge("retrieve_both_vector","merge")

    graph.add_edge("merge","generate")
    graph.add_edge("generate","validate")
    graph.add_edge("validate",END)

    return graph.compile()

query_pipeline=build_query_graph()



