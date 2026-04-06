from __future__ import annotations

import os
import structlog

from backend.infra.graph_store import GraphStore
from backend.infra.vector_store import VectorStore
from backend.infra.metadata_store import MetadataStore

logger=structlog.get_logger(__name__)

class StorageManager:
    """
    Unified facade over all three storage backends.
    """

    def __init__(self,
                 base_dir:str="storage",
                 mongo_uri:str="mongodb://localhost:27017",
                 mongo_db:str="graphrag"):
        
        os.makedirs(base_dir,exist_ok=True)
        self.graph=GraphStore(persist_path=os.path.join(base_dir,"graph.json"))
        self.vectors=VectorStore(persist_dir=os.path.join(base_dir,"chroma"))
        self.metadata=MetadataStore(mongo_uri=mongo_uri,db_name=mongo_db)
        logger.info("storage manager initialized",base_dir=base_dir)

    def persist_all(self):
        self.graph.persist()
        logger.info("all_stores_persisted")

    def stats(self)->dict:
        g_stats=self.graph.stats()
        return {
            "total_documents":self.metadata.count_documents(),
            "total_chunks":self.metadata.count_chunks(),
            "total_nodes":g_stats["total_nodes"],
            "total_edges":g_stats["total_edges"],
            "doc_type_counts":self.metadata.doc_type_counts(),
            "node_type_counts":g_stats["node_type_counts"],
            "edge_type_counts":g_stats["edge_type_counts"],
            }

    def clear_all(self):
        self.graph.clear()
        self.vectors.clear()
        self.metadata.clear()
        logger.warning("all_stores_cleared")
