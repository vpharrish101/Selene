from __future__ import annotations
import json
import os
import structlog
import networkx as nx

from typing import Optional
from backend.utils.pydantic_models import GraphNode,GraphEdge

logger=structlog.get_logger(__name__)

class GraphStore:
    """
    In-memory directed graph backed by NetworkX,persisted to JSON.
    """

    def __init__(self,
                 persist_path:str="storage/graph.json"):
        self.persist_path=persist_path
        self.graph=nx.DiGraph()
        self._load()

    def _load(self):
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path,"r",encoding="utf-8") as f:
                    data=json.load(f)
                self.graph=nx.node_link_graph(data,directed=True)
                logger.info("graph_loaded",
                            nodes=self.graph.number_of_nodes(),
                            edges=self.graph.number_of_edges())
            except Exception as e:
                logger.warning("graph_load_failed",error=str(e))
                self.graph=nx.DiGraph()

    def persist(self):
        os.makedirs(os.path.dirname(self.persist_path),exist_ok=True)
        data=nx.node_link_data(self.graph)
        with open(self.persist_path,"w",encoding="utf-8") as f:
            json.dump(data,f,indent=2,default=str)
        logger.info("graph_persisted",
                    nodes=self.graph.number_of_nodes(),
                     edges=self.graph.number_of_edges())


    def add_node(self,node:GraphNode)->str:

        key=self._node_key(node.name)

        if self.graph.has_node(key):
            existing=self.graph.nodes[key]
            existing.setdefault("source_chunk_ids",[])
            existing["source_chunk_ids"].extend(node.source_chunk_ids)
            existing.setdefault("source_doc_ids",[])
            existing["source_doc_ids"].extend(node.source_doc_ids)
            existing["properties"]={**existing.get("properties",{}),**node.properties}
        else:
            self.graph.add_node(key,**{
                "node_id":node.node_id,
                "name":node.name,
                "node_type":node.node_type.value,
                "properties":node.properties,
                "source_chunk_ids":list(node.source_chunk_ids),
                "source_doc_ids":list(node.source_doc_ids),
                "confidence":node.confidence,
                })
            
        return key

    def get_node(self,name:str)->Optional[dict]:

        key=self._node_key(name)
        if self.graph.has_node(key):
            return {**self.graph.nodes[key],"key":key}
        return None

    def find_nodes(self,pattern:str)->list[dict]:
        pattern_l=pattern.lower()
        results=[]
        for n,data in self.graph.nodes(data=True):
            if pattern_l in n.lower() or pattern_l in data.get("name","").lower():
                results.append({**data,"key":n})
        return results

    def add_edge(self,edge:GraphEdge)->str:
        src_key=self._node_key(edge.source)
        tgt_key=self._node_key(edge.target)
        if not self.graph.has_node(src_key):
            self.graph.add_node(src_key,
                                name=edge.source,
                                node_type="Unknown",
                                properties={},source_chunk_ids=[],source_doc_ids=[],confidence=0.5)
        if not self.graph.has_node(tgt_key):
            self.graph.add_node(tgt_key,
                                name=edge.target,
                                node_type="Unknown",
                                properties={},source_chunk_ids=[],source_doc_ids=[],confidence=0.5)
            
        self.graph.add_edge(src_key,tgt_key,**{
            "edge_id":edge.edge_id,
            "edge_type":edge.edge_type.value,
            "properties":edge.properties,
            "source_chunk_ids":list(edge.source_chunk_ids),
            "confidence":edge.confidence,
            })
        
        return edge.edge_id

    def get_connections(self,name:str)->list[dict]:
        key=self._node_key(name)
        conns=[]
        if not self.graph.has_node(key):
            return conns
        
        for _,target,data in self.graph.out_edges(key,data=True):
            conns.append({"direction":"out",
                          "target":target,
                          "target_name":self.graph.nodes[target].get("name",target),**data})
            
        for source,_,data in self.graph.in_edges(key,data=True):
            conns.append({"direction":"in",
                          "source":source,
                          "source_name":self.graph.nodes[source].get("name",source),**data})
        return conns


    def shortest_path(self,source:str,target:str)->list[str]:
        src_key=self._node_key(source)
        tgt_key=self._node_key(target)
        try:
            path=nx.shortest_path(self.graph,src_key,tgt_key)
            return [self.graph.nodes[n].get("name",n) for n in path]
        except (nx.NetworkXNoPath,nx.NodeNotFound):
            return []


    def get_path_edges(self,source:str,target:str)->list[dict]:
        src_key=self._node_key(source)
        tgt_key=self._node_key(target)
        try:
            path=nx.shortest_path(self.graph,src_key,tgt_key)
            edges=[]
            for i in range(len(path) - 1):
                edata=self.graph.edges[path[i],path[i + 1]]
                edges.append({
                    "from":self.graph.nodes[path[i]].get("name",path[i]),
                    "to":self.graph.nodes[path[i + 1]].get("name",path[i + 1]),
                    **edata,
                })
            return edges
        
        except(nx.NetworkXNoPath,nx.NodeNotFound):
            return []

    def get_full_graph(self)->dict:
        """
        Return the entire graph in a format compatible with force-graph.
        """
        nodes_out=[]
        for n,data in self.graph.nodes(data=True):
            nodes_out.append({
                "id":n,
                "name":data.get("name",n),
                "type":data.get("node_type","Unknown").lower(),
                "importance":data.get("confidence",0.5), # Using confidence as a proxy for importance
                **{k:v for k,v in data.items() if k not in ["name","node_type","confidence"]}
            })
            
        links_out=[]
        for u,v,data in self.graph.edges(data=True):
            links_out.append({
                "source":u,
                "target":v,
                "type":data.get("edge_type","Unknown"),
                **{k:v for k,v in data.items() if k not in ["edge_type"]}
            })
            
        return {"nodes":nodes_out,"links":links_out}

    def multi_hop(self,name:str,max_hops:int=2)->dict:
        """
        Return subgraph within max_hops of a node.
        """
        key=self._node_key(name)
        if not self.graph.has_node(key):
            return {"nodes":[],"edges":[]}
        visited=set()
        frontier={key}
        nodes_out=[]
        edges_out=[]
        for _ in range(max_hops):
            next_frontier=set()
            for n in frontier:
                if n in visited:
                    continue
                visited.add(n)
                ndata=self.graph.nodes[n]
                nodes_out.append({**ndata,"key":n})
                for _,tgt,edata in self.graph.out_edges(n,data=True):
                    edges_out.append({"from":ndata.get("name",n),
                                      "to":self.graph.nodes[tgt].get("name",tgt),**edata})
                    next_frontier.add(tgt)
                for src,_,edata in self.graph.in_edges(n,data=True):
                    edges_out.append({"from":self.graph.nodes[src].get("name",src),
                                      "to":ndata.get("name",n),**edata})
                    next_frontier.add(src)
            frontier=next_frontier - visited
        return {"nodes":nodes_out,"edges":edges_out}


    def stats(self)->dict:
        node_types:dict[str,int]={}
        for _,data in self.graph.nodes(data=True):
            nt=data.get("node_type","Unknown")
            node_types[nt]=node_types.get(nt,0)+1
        edge_types:dict[str,int]={}
        for _,_,data in self.graph.edges(data=True):
            et=data.get("edge_type","Unknown")
            edge_types[et]=edge_types.get(et,0)+1
        return {
            "total_nodes":self.graph.number_of_nodes(),
            "total_edges":self.graph.number_of_edges(),
            "node_type_counts":node_types,
            "edge_type_counts":edge_types,
            }

    def clear(self):
        self.graph.clear()

    @staticmethod
    def _node_key(name:str) -> str:
        return name.strip().lower()
