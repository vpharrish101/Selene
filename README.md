# Selene: Knowledge Graph RAG Assistant

Selene is a high-performance Knowledge Graph Augmented Retrieval (GraphRAG) assistant. It combines vector-based retrieval with structural knowledge graph insights to provide more grounded and context-aware answers.

## Architecture

- **Backend**: FastAPI (Python), LangGraph, ChromaDB (Vector Store), MongoDB (Metadata Store).
- **Frontend**: React, Vite, Framer Motion, Tailwind CSS.
- **AI**: Integration with Ollama/LLMs for extraction and retrieval reasoning.

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
- [Ollama](https://ollama.com/) (running on the host for LLM services)

### Running with Docker

The easiest way to start Selene is using Docker Compose:

```bash
docker-compose up --build
```

- **Frontend**: [http://localhost:80](http://localhost:80)
- **Backend API**: [http://localhost:8000](http://localhost:8000)

### Manual Setup

#### Backend

1. Navigate to `backend/`
2. Create a virtual environment: `python -m venv .venv`
3. Install dependencies: `pip install -r ../requirements.txt`
4. Copy `.env.example` to `.env` and fill in your settings.
5. Run the server: `uvicorn backend.api.app:app --reload`

#### Frontend

1. Navigate to `frontend/`
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`

## Configuration

The backend is configured via environment variables (see `.env.example`). Key parameters:

- `MODEL_NAME`: The LLM to use (e.g., `qwen2.5:7b-instruct`).
- `BASE_URL`: Ollama host (default: `http://localhost:11434`).
- `MONGO_URI`: MongoDB connection string.

## License

[MIT License](LICENSE) (Placeholder)
