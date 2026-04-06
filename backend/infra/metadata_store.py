from __future__ import annotations
import structlog

from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from backend.utils.pydantic_models import TextChunk,UnifiedDocument
    

logger=structlog.get_logger(__name__)

class MetadataStore:
    """
    MongoDB metadata store for document registry and chunk tracking.
    """

    def __init__(self,
                 mongo_uri:str="mongodb://localhost:27017",
                 db_name:str="graphrag"):
        
        try:
            self.client=MongoClient(mongo_uri,serverSelectionTimeoutMS=3000)
            self.client.admin.command("ping")
            self.db=self.client[db_name]
            self.docs=self.db["documents"]
            self.chunks=self.db["chunks"]
            self.docs.create_index("doc_id",unique=True)
            self.chunks.create_index("chunk_id",unique=True)
            self.chunks.create_index("doc_id")
            logger.info("mongodb_connected",db=db_name)

        except ConnectionFailure:
            logger.error("mongodb connection failed",uri=mongo_uri)
            raise RuntimeError(
                f"Cannot connect to MongoDB at {mongo_uri}. "
                "Ensure MongoDB is running locally."
                )

    def insert_document(self,doc:UnifiedDocument):
        record=doc.model_dump()
        self.docs.update_one({"doc_id":doc.doc_id},{"$set":record},upsert=True)

    def insert_chunks(self,chunks:list[TextChunk]):
        for chunk in chunks:
            record=chunk.model_dump()
            self.chunks.update_one({"chunk_id":chunk.chunk_id},{"$set":record},upsert=True)

    def get_document(self,doc_id:str)->Optional[dict]:
        return self.docs.find_one({"doc_id":doc_id},{"_id":0})

    def get_chunks_for_doc(self,doc_id:str)->list[dict]:
        return list(self.chunks.find({"doc_id":doc_id},{"_id":0}))

    def get_chunk(self,chunk_id:str)->Optional[dict]:
        return self.chunks.find_one({"chunk_id":chunk_id},{"_id":0})

    def get_all_documents(self)->list[dict]:
        return list(self.docs.find({},{"_id":0}))

    def count_documents(self)->int:
        return self.docs.count_documents({})

    def count_chunks(self)->int:
        return self.chunks.count_documents({})

    def doc_type_counts(self)->dict[str,int]:
        pipeline=[
            {"$group":{
                "_id":"$doc_type",
                "count":{
                    "$sum":1}
                    }
                }
        ]
        return {r["_id"]:r["count"] for r in self.docs.aggregate(pipeline)}

    def clear(self):
        self.docs.delete_many({})
        self.chunks.delete_many({})

