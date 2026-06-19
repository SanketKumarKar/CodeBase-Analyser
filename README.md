# Codebase Intelligence Agent

> A portfolio-grade hybrid-RAG system that lets developers upload or connect a GitHub repository and ask natural-language questions about its architecture, dependencies, and bugs.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.9-purple)](https://qdrant.tech)

---

## Architecture

```
Frontend (Next.js 14 + TypeScript + TailwindCSS)
        ↓ REST + Socket.IO
API Gateway (FastAPI + LangGraph)
        ↓
Repository Ingestion Pipeline (Celery + Redis)
        ↓
Code Parsing (AST for Python · Tree-sitter for JS/TS)
        ↓
 ┌──────────────────────────────┐
 │                              │
 ▼                              ▼
Qdrant                        Neo4j AuraDB
(Vector Semantic Search)    (Code Relationship Graph)
 │                              │
 └──────────────┬───────────────┘
                ↓
# Codebase Intelligence Agent 🧠

A hybrid-RAG system that allows developers to upload GitHub repositories and ask natural-language questions about architecture, dependencies, and bugs.

This system fuses three retrieval modes before generating an answer:
1. **Vector Semantic Search** (Qdrant)
2. **Graph Relationship Traversal** (Neo4j)
3. **Persistent Conversational Memory** (Mem0)

## 🎯 Current Status

**Phase 1-3 are COMPLETE.**

- ✅ **Phase 1: Foundation & Scaffold** — FastAPI backend, Next.js frontend (Three-panel UI layout), Docker Compose infrastructure.
- ✅ **Phase 2: Repository Ingestion** — `POST /repo/upload` accepts GitHub URLs or ZIP files. Celery worker handles cloning, extraction, size validation, and metadata extraction. Live progress via polling/Socket.IO.
- ✅ **Phase 3: Code Parsing Engine** — AST-based Python parser, Tree-sitter JS/TS parser, and coarse fallback parser. Chunks code into functions, classes, and methods.

## 🛠️ Tech Stack

### Infrastructure
- **Embeddings:** `qwen3-embedding:4b` (via local Ollama)
- **LLM:** `gemma4:latest` (via local Ollama)
- **Vector DB:** Qdrant (Docker)
- **Graph DB:** Neo4j AuraDB (Cloud)
- **Memory:** Mem0 (Cloud API)
- **Task Queue:** Celery + Redis (Docker)
- **Database:** PostgreSQL (Docker)

### Backend
- FastAPI + Uvicorn
- SQLAlchemy (Async)
- structlog for structured JSON logging
- Python AST + Tree-sitter for code parsing

### Frontend
- Next.js 14 (App Router)
- React (TypeScript)
- Tailwind CSS
- Axios for API service layer

## 🚀 Local Development Setup

### 1. Prerequisites
- Docker Desktop
- Python 3.12 (via `uv`)
- Node.js (v20+)
- Ollama (running locally with `qwen3-embedding:4b` and `gemma4:latest` installed)

### 2. Environment Variables
Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```
Fill in your Neo4j AuraDB credentials and Mem0 API key.

### 3. Start Infrastructure
```bash
docker compose up qdrant redis postgres -d
```

### 4. Start Backend
```bash
cd backend
uv venv .venv --python 3.12
.venv\Scripts\activate
uv pip install -r requirements.txt
uvicorn main:socket_app --reload
```

### 5. Start Celery Worker
In a new terminal window:
```bash
cd backend
.venv\Scripts\activate
celery -A workers.celery_app worker --loglevel=info
```

### 6. Start Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:3000`.

## 🧪 Testing

The backend includes a comprehensive pytest suite covering the parser, repository service, and health checks.

```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v
```bash
curl http://localhost:8000/health
# → { "status": "ok", "services": { "qdrant": {...}, "neo4j": {...}, ... } }
```


---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Critical ones:

| Variable | Required | Description |
|---|---|---|
| `MEM0_API_KEY` | ✅ | Mem0 cloud API key |
| `NEO4J_URI` | ✅ | AuraDB bolt URI |
| `NEO4J_PASSWORD` | ✅ | AuraDB password |
| `OLLAMA_BASE_URL` | ✅ | Default: `http://localhost:11434` |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service status check |
| POST | `/repo/upload` | Start ingestion job |
| GET | `/repo/status/{job_id}` | Ingestion job status |
| GET | `/repo/graph` | Relationship graph for React Flow |
| POST | `/search/vector` | Raw semantic search |
| POST | `/chat/query` | Main agent endpoint (streamed) |
| GET | `/memory/history` | Memory entries for user/repo |

Interactive docs: **http://localhost:8000/docs**

---

## Build Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Scaffolding & Infra |
| 2 | ⏳ | Repository Ingestion Pipeline |
| 3 | ⏳ | Code Parsing Engine |
| 4 | ⏳ | Embedding + Qdrant Storage |
| 5 | ⏳ | Graph Construction (Neo4j) |
| 6 | ⏳ | Mem0 Memory Layer |
| 7 | ⏳ | Agent Orchestration (LangGraph) |
| 8 | ⏳ | Frontend Integration |
| 9 | ⏳ | Advanced Features |
| 10 | ⏳ | Hardening & Polish |

See [`PROGRESS.md`](PROGRESS.md) for the detailed build log.

---

## Known Limitations

- Single-user for now (`user_id = "default"`) — no auth layer
- Neo4j AuraDB free tier has limited storage (1 GB)
- `gemma4` context window caps large file analysis — chunking mitigates this
- Tree-sitter parsing runs inside Docker (Linux) to avoid Windows build issues

---

## Resume Bullet

> Built an intelligent Codebase Analysis Agent leveraging hybrid RAG architecture with Qdrant, Neo4j, and Mem0 to enable semantic code retrieval, graph-based dependency reasoning, persistent conversational memory, and context-aware repository debugging.
