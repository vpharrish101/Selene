
class Prompts():
    
    ENTITY_EXTRACTION="""Extract all entities and relationships from the following text.

Return ONLY valid JSON in this exact format:
{{
  "entities": [
    {{"name": "...", "type": "Person|Organization|Project|Document|Email|Ticket|Task|Meeting|Deadline|Topic", "properties": {{}}}}
  ],
  "relations": [
    {{"subject": "...", "predicate": "...", "object": "...", "confidence": 0.8}}
  ]
}}

Available predicates (USE EXACTLY — direction matters):
  Person → LEADS → Project/Team        ("Alice leads the backend team")
  Person → RESPONSIBLE_FOR → Task       ("Frank is responsible for PCI cert")
  Person → ASSIGNED_TO → Task/Ticket    ("Bob is assigned to ATLAS-101")
  Person → OWNS → Project/Document      ("Grace owns the migration plan")
  Task   → DEPENDS_ON → Task            ("sandbox testing depends on PCI cert")
  Entity → PART_OF → Entity             ("API Gateway is part of Project Atlas")
  Entity → RELATED_TO → Entity          (fallback for any other relationship)
  Person → SENT_TO → Person             (emails)
  Person → PARTICIPATED_IN → Meeting
  Entity → MENTIONED_IN → Document
  Task   → DUE_ON → Deadline
  Task   → ACTION_ITEM_FOR → Person
  Entity → SUPPORTS → Entity
  Entity → CONTRADICTS → Entity

Critical rules:
- DIRECTION MATTERS: "Alice leads Project Atlas" → subject=Alice, predicate=LEADS, object=Project Atlas
- Use RESPONSIBLE_FOR when someone owns or is accountable for a task/workstream
- Use LEADS when someone leads a team/project/initiative
- Use OWNS when someone authored or is the owner of a document/artifact
- Extract CONCISE entity names — prefer "PCI compliance" over "PCI compliance certification in progress"
- Do NOT duplicate the same entity with different wordings
- Identify people, organizations, projects, topics, tasks, deadlines
- Set confidence between 0.5 and 1.0
- Do NOT include explanations, only JSON

Text:
{text}

JSON:"""


    ACTION_EXTRACTION="""Extract action items, tasks, and deadlines from the following text.

Return ONLY valid JSON:
{{
  "actions": [
    {{"action": "description of action", "assignee": "person name or null", "deadline": "date string or null"}}
  ]
}}

Text:
{text}

JSON:"""
    
    GHV_CLASSIFICATION="""Classify the following user question into ONE of these categories:

1. "graph_first" — questions about relationships, dependencies, ownership, assignments, 
   who/what is connected to what, paths between entities, organizational structure, 
   what depends on what, who is responsible, what is overdue, what changed.
   Examples: "Who owns X?", "What depends on Y?", "What is the path between A and B?"

2. "vector_first" — questions about content similarity, finding documents about a topic,
   summarization, explanation, or general knowledge questions.
   Examples: "Find documents about X", "Summarize the project", "Explain the decision"

3. "hybrid" — questions that need both relationship context AND content search.
   Examples: "What emails mention the same project as this document?",
   "Show all evidence related to this decision", "What documents support this claim?"

Return ONLY one word: graph_first, vector_first, or hybrid

Question: {question}

Category:"""

    ANSWER = """You are a knowledge assistant. Answer the user's question based ONLY on the 
provided evidence. Be specific, cite sources, and indicate confidence.

EVIDENCE:
{evidence}

QUESTION: {question}

Rules:
- Answer based ONLY on the evidence provided
- Cite specific evidence items by their source (e.g., [Graph: entity_name], [Doc: chunk_id])
- If the evidence is insufficient, say so clearly
- Be concise but thorough
- Include a confidence level (high/medium/low) at the end

ANSWER:"""


