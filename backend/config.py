import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Settings
    MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b-instruct")
    BASE_URL = os.getenv("BASE_URL", "http://localhost:11434")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.07"))

    # Extraction Settings 
    ETL_RETRIES = int(os.getenv("ETL_RETRIES", "2"))
    EXTRACTION_CONFIDENCE = float(os.getenv("EXTRACTION_CONFIDENCE", "0.8"))

    # Retrieval Settings
    GRAPH_MAX_HOPS = int(os.getenv("GRAPH_MAX_HOPS", "2"))
    GRAPH_MAX_RESULTS = int(os.getenv("GRAPH_MAX_RESULTS", "20"))
    RRF_K_PARAM = int(os.getenv("RRF_K_PARAM", "60"))
