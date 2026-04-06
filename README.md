# Selene

What it is: A hybrid retrieval system combining graph-based search and semantic vector search, to extract and query data from documents and knowledge graphs.

What it does: It extracts entities and relationships from documents/emails/support tickets (or any data) , stores them in a graph + vector database, and answers coss-domain queries (by referencing both relationships and meanings).

What's unique: Unlike typical GraphRAG systems that rely on LLM-generated graphs, Selene constructs a deterministic, schema-driven graph and uses it for reliable multi-hop relationship reasoning.

## Architecture: -
<img width="711" height="530" alt="image" src="https://github.com/user-attachments/assets/0305bf2d-2e02-46e6-b1c3-3de4534aea67" />


```
# Structure Dynamics: -

The reason I engineered this hybrid retrieval architecture: -

  1. The LLM extraction layer transforms unstructured documents into structured entities and typed relationships, enabling the system
     to operate on explicit knowledge instead of raw text.
  2. The knowledge graph encodes relational structure (e.g., ownership, dependencies, participation), allowing deterministic reasoning
     over how entities are connected.
  3. The vector store captures semantic context from text using embeddings, enabling retrieval based on meaning rather than exact matches.
  4. The query routing layer (LangGraph) classifies each query and dynamically selects the optimal retrieval strategy (graph-first,
     vector-first, or hybrid), improving both accuracy and efficiency.
  5. The fusion layer uses Reciprocal Rank Fusion (RRF) to combine graph-based and semantic results into a single ranked evidence set
     without requiring a learned ranking model.
  6. The answer generation step uses the LLM over retrieved evidence, producing grounded responses with explicit citations and confidence signals.
  7. The result is a unified reasoning system where structure (graph), semantics (vector), and extracted knowledge (LLM) are jointly
     leveraged to answer complex, multi-hop queries.
```
## Features: -

- **Hybrid Graph + Vector Retrieval**  
  Combines knowledge graph traversal (NetworkX) with semantic search (ChromaDB embeddings) for both relational and contextual queries.

- **LLM-Based Structured Extraction**  
  Uses a local LLM (Ollama) to convert raw text into entities, typed relationships, and actions via strict JSON schemas.

- **Deterministic + LLM Hybrid Graph Construction**  
  Builds a reliable “skeleton” graph using Pydantic-validated schemas and metadata parsing, before augmenting it with LLM-extracted semantics to reduce              hallucinated relationships.
  
- **Relationship-Grounded Answer Generation**  
  Constrains LLM generation using graph edges as factual signals, ensuring answers are derived from explicit relationships rather than pure text similarity.

- **Operational Graph Topology (Not Just Knowledge)**  
  Encodes workflows, tasks, deadlines, and dependencies directly into the graph structure (NetworkX), enabling queries around blockers, ownership, and risk.

- **Query-Aware Retrieval Routing (Graph-First Bias)**  
  Uses LangGraph (StateGraph) to classify queries and dynamically route execution (graph-first, vector-first, hybrid) based on intent.

- **Modality-Agnostic Evidence Normalization**  
  Normalizes graph edges and vector-retrieved chunks into a unified `RetrievedEvidence` schema (Pydantic), enabling cross-modal comparison.

- **Algorithmic Fusion via RRF (Pre-LLM)**  
  Applies Reciprocal Rank Fusion (RRF) to merge graph and vector evidence before LLM generation, avoiding prompt-level heuristics.

## UI Snips: -
<tba>

## API Endpoints: -

- `GET /health` - Backend health check
- `POST /ingest` - Ingest raw documents (emails, tickets, meetings, text)
- `POST /query` - Hybrid graph + vector query (main RAG endpoint)
- `GET /search?q=query` - Semantic / lexical / hybrid search over indexed data
- `GET /graph/entity/{name}` - Retrieve entity details and its relationships
- `GET /graph/path?source=A&target=B` - Find shortest path between two entities
- `GET /debug/retrieval?q=query` - Inspect raw graph + vector retrieval outputs
- `GET /debug/graph?entity=name&hops=2` - View multi-hop graph neighborhood
- `GET /stats` - System stats (documents, nodes, edges, chunks)


## Deployment: -

With docker: -
```bash
docker-compose up --build
```

### Manual Setup: -

#### Backend: -
```bash
cd <project_root>
python -m venv .venv
source .venv/bin/activate (Linux/Mac)
.venv\Scripts\activate (Windows)
pip install -r requirements
python -m uvicorn backend.api.app:app --reload --host 0.0.0.0 --port 8000
```
#### Frontend: -
```bash
cd <project_root>/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5000
```


## Configuration: -
The backend is configured via environment variables (see `.env.example`). Key parameters:
- `MODEL_NAME`: The LLM to use (e.g., `qwen2.5:7b-instruct`).
- `BASE_URL`: Ollama host (default: `http://localhost:11434`).
- `MONGO_URI`: MongoDB connection string.

## License
[MIT License](LICENSE) (Placeholder)
