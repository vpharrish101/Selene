import os
import json
import langchain_ollama
import regex as re
import functools

from typing import Optional
from dotenv import load_dotenv
from backend.utils.logging import setup_logging,get_logger
from backend.config import Config

load_dotenv()
setup_logging()
logger=get_logger(__name__,service="utils")
_llm=langchain_ollama.ChatOllama(model=Config.MODEL_NAME,
                                 temperature=Config.LLM_TEMPERATURE,
                                  base_url=Config.BASE_URL,)


@functools.lru_cache(maxsize=128)
def run_llm(prompt:str)->str:
    """
    Call Ollama via LangChain ChatOllama. Returns raw text response.
    """
    try:
        response=_llm.invoke(prompt)
        logger.info("llm call success")
        return response.content if response else "" #type:ignore
    except Exception:
        logger.exception("llm call failed")
        return ""
run_llm("capital of france?")

def extract_json(text:str)->Optional[dict|list]:
    """
    Extract JSON from LLM response, handling markdown code blocks and junk.
    """
    match=re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if match: text=match.group(1)

    text=text.strip()
    for attempts in [text,text.rstrip(",")]:
        try: return json.loads(attempts)
        except json.JSONDecodeError as e: 
            logger.exception("json extraction failed, L1",error=str(e))
            continue
    
    for st_chr,end_chr in [("{","}"),("[","]")]:
        start=text.find(st_chr)
        end=text.rfind(end_chr)
        if start!=-1 and end!=-1 and end>start:
            try: return json.loads(text[start:end+1])
            except json.JSONDecodeError as e:
                logger.exception("json extraction failed, L2",error=str(e))
                continue
    logger.warn("None returned from extract_json")
    return None



        

