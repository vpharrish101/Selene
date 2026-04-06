import regex as re

from backend.utils.logging import setup_logging,get_logger
from backend.utils.pydantic_models import DocType,UnifiedDocument,EmailDoc,DocumentDoc,MeetingDoc,TicketDoc,TextChunk,GraphNode
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

setup_logging()
logger=get_logger(__name__,service="extraction")
splitter=RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=50)

def type_detn(Data:dict)->DocType:
    """
    Takes in a dict and returns it's document type, implicitly.
    """
    keys=set(k.lower() for k in Data.keys())
    if "sender" in keys or "recipients" in keys or "thread_id" in keys:
        return DocType.EMAIL
    if "ticket_id" in keys or ("assignee" in keys and "reporter" in keys):
        return DocType.TICKET
    if "participants" in keys or ("action_items" in keys and "decisions" in keys):
        return DocType.MEETING
    if "attendees" in keys and "start_time" in keys:
        return DocType.CALENDAR
    if "title" in keys or "body" in keys or "author" in keys:
        return DocType.DOCUMENT
    
    return DocType.UNKNOWN


def normalize(data:dict,doc_type:DocType)->UnifiedDocument:

    if doc_type==DocType.EMAIL:
        email=EmailDoc(**data)
        return UnifiedDocument(
            doc_type=doc_type,
            title=email.subject,
            author=email.sender,
            timestamp=email.timestamp,
            body=f"From: {email.sender}\nTo: {', '.join(email.recipients)}\n"
                 f"CC: {', '.join(email.cc)}\nSubject: {email.subject}\n\n{email.body}",
            metadata={
                "sender": email.sender,
                "recipients": email.recipients,
                "cc": email.cc,
                "thread_id": email.thread_id,
                "attachments": email.attachments,},
        )
    
    elif doc_type==DocType.MEETING:
        meet=MeetingDoc(**data)
        body_parts=[meet.body or ""]
        if meet.decisions:
            body_parts.append("Decisions: "+"; ".join(meet.decisions))
        if meet.action_items:
            body_parts.append("Action Items: "+"; ".join(meet.action_items))
        if meet.follow_ups:
            body_parts.append("Follow-ups: "+"; ".join(meet.follow_ups))
        return UnifiedDocument(
            doc_type=doc_type,
            title=meet.title,
            body="\n".join(body_parts),
            metadata={
                "participants": meet.participants,
                "decisions": meet.decisions,
                "action_items": meet.action_items,
                "follow_ups": meet.follow_ups,
            },
        )
    
    elif doc_type==DocType.TICKET:
        ticket=TicketDoc(**data)
        return UnifiedDocument(
            doc_type=doc_type,
            title=ticket.summary or f"Ticket {ticket.ticket_id}",
            author=ticket.reporter,
            timestamp=ticket.created_at,
            body=f"Ticket: {ticket.ticket_id}\nReporter: {ticket.reporter}\n"
                 f"Assignee: {ticket.assignee}\nStatus: {ticket.status}\n"
                 f"Priority: {ticket.priority}\nDue: {ticket.due_at}\n\n"
                 f"{ticket.summary}\n{ticket.body}",
            metadata={
                "ticket_id": ticket.ticket_id,
                "reporter": ticket.reporter,
                "assignee": ticket.assignee,
                "status": ticket.status,
                "priority": ticket.priority,
                "due_at": ticket.due_at,
            },
        )
    
    else:
        doc=DocumentDoc(**{k:v for k,v in data.items() if k in DocumentDoc.model_fields})
        return UnifiedDocument(
            doc_type=doc_type if doc_type!=DocType.UNKNOWN else DocType.DOCUMENT,
            title=doc.title,
            author=doc.author,
            timestamp=doc.timestamp,
            body=doc.body,
            metadata={"source_path": doc.source_path},
        )
    

def chunk_text(doc: UnifiedDocument,doc_id:str)->List[TextChunk]:
    chunks=[]
    idx=0

    def add_chunks(text,extra_meta=None):
        nonlocal idx
        def split(text: str)->List[str]:
            if len(text.split())<500: return [text]
            return splitter.split_text(text)

        for part in split(text):
            chunks.append(
                TextChunk(
                    doc_id=doc_id,
                    text=part,
                    chunk_index=idx,
                    metadata={**doc.metadata,**(extra_meta or {})}
                )
            )
            idx+=1

    if doc.doc_type==DocType.MEETING:
        if doc.metadata.get("decisions"):
            add_chunks("Decisions: "+"; ".join(doc.metadata["decisions"]),
                       {"section":"decisions"})
        if doc.metadata.get("action_items"):
            add_chunks("Action Items: "+"; ".join(doc.metadata["action_items"]),
                       {"section":"action_items"})
        if doc.metadata.get("follow_ups"):
            add_chunks("Follow-ups: "+"; ".join(doc.metadata["follow_ups"]),
                       {"section":"follow_ups"})
        if doc.body:
            add_chunks(doc.body,
                       {"section":"body"})

    elif doc.doc_type==DocType.EMAIL:
        add_chunks(doc.title+"\n"+doc.body,{"section":"email"})
    elif doc.doc_type==DocType.TICKET:
        add_chunks(doc.body,{"section":"description"})
    else:
        add_chunks(doc.body,{"section":"general"})
    return chunks

def simple_chunk(text: str, doc_id: str, chunk_size: int = 500,
               overlap: int = 50, metadata: dict | None = None) -> list[TextChunk]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    idx = 0
    chunk_num = 0
    while idx < len(words):
        end = min(idx + chunk_size, len(words))
        chunk_text_content = " ".join(words[idx:end])
        chunks.append(TextChunk(
            doc_id=doc_id,
            text=chunk_text_content,
            chunk_index=chunk_num,
            metadata=metadata or {},
        ))
        chunk_num += 1
        idx += chunk_size - overlap
        if end == len(words):
            break
    return chunks



def entity_resoln(nodes:list[GraphNode])->list[GraphNode]:
    """
    Rule-based entity deduplication before graph insertion.
    Merges nodes with same normalized name, combining source references.
    Also collapses near-duplicates (like 'PCI compliance certification in progress'
        merges into 'PCI compliance certification').
    """
    merged:dict[str,GraphNode]={}
    for node in nodes:
        key=_normalize_name(node.name)
        if key in merged:
            existing=merged[key]
            existing.source_chunk_ids.extend(node.source_chunk_ids)
            existing.source_doc_ids.extend(node.source_doc_ids)
            existing.properties={**existing.properties,**node.properties}
            existing.confidence=max(existing.confidence,node.confidence)
        else:
            merged[key]=node.model_copy(deep=True)

    # Pass 2: fuzzy near-duplicate collapse
    fuzzy_map: dict[str,str]={}
    for exact_key in merged:
        fk=_normalize_name_fuzzy(exact_key)
        if fk in fuzzy_map and fuzzy_map[fk]!=exact_key:
            canon_key=fuzzy_map[fk]
            canon=merged[canon_key]
            dup=merged[exact_key]
            canon.source_chunk_ids.extend(dup.source_chunk_ids)
            canon.source_doc_ids.extend(dup.source_doc_ids)
            canon.properties={**canon.properties,**dup.properties}
            canon.confidence=max(canon.confidence,dup.confidence)
            merged[exact_key]=None   #type:ignore

        else:
            if fk in fuzzy_map:
                existing_key=fuzzy_map[fk]
                if len(exact_key)<len(existing_key):
                    canon=merged[exact_key]
                    dup=merged[existing_key]
                    canon.source_chunk_ids.extend(dup.source_chunk_ids)
                    canon.source_doc_ids.extend(dup.source_doc_ids)
                    canon.confidence=max(canon.confidence,dup.confidence)
                    merged[existing_key]=None #type:ignore
                    fuzzy_map[fk]=exact_key
            else:
                fuzzy_map[fk]=exact_key

    return [n for n in merged.values() if n is not None]


def _normalize_name(name:str)->str:
    """
    Normalize entity name for deduplication.
    """
    name=name.strip().lower()
    name=re.sub(r"\s+"," ",name)
    for prefix in ["dr.","mr.","mrs.","ms.","prof."]:
        if name.startswith(prefix):
            name=name[len(prefix):].strip()
    return name


def _normalize_name_fuzzy(name:str)->str:
    """
    Aggressive normalization for near-duplicate collapsing.
    Strips trailing qualifiers like 'in progress', 'certification', 'process'.
    """
    base= _normalize_name(name)
    # Strip common trailing status/qualifier phrases
    for suffix in [" in progress"," certification"," process"," complete"," completed"," pending"," status"," update"," review",]:
        if base.endswith(suffix) and len(base)>len(suffix)+3:
            base=base[:-len(suffix)].strip()
    return base