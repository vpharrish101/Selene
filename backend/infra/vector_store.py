from __future__ import annotations

import structlog

from backend.utils.pydantic_models import TextChunk
logger=structlog.get_logger(__name__)

class VectorStore:
    """
    ChromaDB persistent vector store for text chunks.
    """

    def __init__(self,
                 persist_dir:str="storage/chroma",
                 collection_name:str="graphrag_chunks"):
        
        import chromadb

        self.client=chromadb.PersistentClient(path=persist_dir)
        self.collection=self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space":"cosine"},
            )
        self._embedder=None
        logger.info("vector_store_init",
                    persist_dir=persist_dir,
                    count=self.collection.count())

    @property
    def embedder(self):
        if self._embedder is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embedder=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            logger.info("embedder_loaded",model="all-MiniLM-L6-v2")
        return self._embedder

    def add_chunks(self,chunks:list[TextChunk]):

        if not chunks:
            return
        
        texts=[c.text for c in chunks]
        ids=[c.chunk_id for c in chunks]
        metadatas=[self._sanitize_metadata({"doc_id":c.doc_id,"chunk_index":c.chunk_index,
                    **c.metadata}) for c in chunks]
        
        embeddings=self.embedder.embed_documents(texts)
        self.collection.upsert(ids=ids,documents=texts,embeddings=embeddings,metadatas=metadatas,) #type:ignore
        logger.info("chunks_indexed",count=len(chunks))

    @staticmethod
    def _sanitize_metadata(meta:dict)->dict:
        """
        Convert list/dict values to strings for ChromaDB compatibility.
        """
        clean={}
        for k,v in meta.items():
            if isinstance(v,list):
                clean[k]=",".join(str(i) for i in v)
            elif isinstance(v,dict):
                clean[k]=str(v)
            elif isinstance(v,(str,int,float,bool)) or v is None:
                clean[k]=v
            else:
                clean[k]=str(v)
        return clean

    def search_semantic(self,
                        query:str,
                        n_results:int=10)->list[dict]:
        
        emb=[self.embedder.embed_query(query)]
        results=self.collection.query(
            query_embeddings=emb,n_results=n_results,#type:ignore
            include=["documents","metadatas","distances"],
            )
        
        return self._format_results(results) #type:ignore

    def search_lexical(self,
                       query:str,
                       n_results:int=10)->list[dict]:
        
        results=self.collection.query(
            query_texts=[query],n_results=n_results,
            include=["documents","metadatas","distances"],
            )
        
        return self._format_results(results) #type:ignore

    def count(self)->int:
        return self.collection.count()

    def clear(self):
        # Delete and recreate collection
        name=self.collection.name
        meta=self.collection.metadata
        self.client.delete_collection(name)
        self.collection=self.client.get_or_create_collection(name=name,metadata=meta)

    @staticmethod
    def _format_results(raw:dict) -> list[dict]:
        out=[]
        if not raw or not raw.get("ids"):
            return out
        for i,cid in enumerate(raw["ids"][0]):
            out.append({
                "chunk_id":cid,
                "text":raw["documents"][0][i] if raw.get("documents") else "",
                "metadata":raw["metadatas"][0][i] if raw.get("metadatas") else {},
                "distance":raw["distances"][0][i] if raw.get("distances") else 0.0,
                "score":1.0 - (raw["distances"][0][i] if raw.get("distances") else 0.0),
                })
        return out
