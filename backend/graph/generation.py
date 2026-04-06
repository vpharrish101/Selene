import time

from backend.utils.logging import setup_logging,get_logger
from backend.utils.utilities import run_llm
from backend.utils.prompts import Prompts
from backend.utils.pydantic_models import RetrievedEvidence,QueryResponse,QueryRoute

setup_logging()
logger=get_logger(__name__,service="GraphOperations")

def generate_answer(question:str, 
                    evidence:list[RetrievedEvidence],
                    route:QueryRoute)->QueryResponse:
    """
    Generate a grounded answer from merged evidence using LLM.
    """
    t0=time.time()

    if not evidence:
        return QueryResponse(
            answer="I could not find sufficient evidence to answer this question. "
                   "Try ingesting more documents or rephrasing your query.",
            confidence=0.0,
            citations=[],
            evidence=evidence,
        )

    # Format evidence for prompt
    evidence_text=_format_evidence_for_prompt(evidence)
    prompt=Prompts.ANSWER.format(evidence=evidence_text, question=question)

    raw_answer=run_llm(prompt)
    if not raw_answer:
        raw_answer="Failed to generate answer. The LLM did not respond."

    # Extract confidence from answer
    confidence=_extract_confidence(raw_answer)

    # Build citations
    citations=_build_citations(evidence)

    elapsed=time.time()-t0
    logger.info("answer_generated", 
                confidence=confidence, 
                route=route.value,
                elapsed_ms=round(elapsed*1000))

    return QueryResponse(
        answer=raw_answer.strip(),
        confidence=confidence,
        citations=citations,
        evidence=evidence[:10],
        )


def validate_answer(response:QueryResponse)->QueryResponse:
    """
    Validate answer quality and add fallback if confidence is too low.
    """
    if response.confidence<0.3 and response.answer:
        response.answer=(
            "LOW CONFIDENCE ANSWER:\n\n"+response.answer+
            "\n\nNote:This answer has low confidence. The available evidence "
            "may be insufficient. Consider ingesting more relevant documents."
        )
    return response


def _format_evidence_for_prompt(evidence:list[RetrievedEvidence])->str:
    """
    Format evidence list for LLM prompt.
    """
    lines=[]
    for i, ev in enumerate(evidence[:15],1):
        src=ev.source_type.upper()
        sid=ev.source_id[:12] if ev.source_id else "?"
        lines.append(f"[{i}] ({src}:{sid}) {ev.content[:500]}")
    return "\n".join(lines)


def _build_citations(evidence:list[RetrievedEvidence])->list[dict]:
    """
    Build citation objects from evidence.
    """
    citations=[]
    seen=set()
    for ev in evidence:
        key=(ev.source_type, ev.source_id)
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "source_type": ev.source_type,
            "source_id": ev.source_id,
            "doc_id": ev.doc_id,
            "score": round(ev.score, 4),
            "content_preview": ev.content[:100],
        })
    return citations[:10]


def _extract_confidence(answer:str)->float:
    """
    Extract confidence level from answer text.
    """
    answer_lower=answer.lower()
    if "high confidence" in answer_lower or "confidence: high" in answer_lower:
        return 0.9
    elif "medium confidence" in answer_lower or "confidence: medium" in answer_lower:
        return 0.7
    elif "low confidence" in answer_lower or "confidence: low" in answer_lower:
        return 0.4
    elif "insufficient" in answer_lower or "not enough" in answer_lower:
        return 0.2
    return 0.6  # default

