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
          Retrieval Layer
                ↓
       Mem0 Cloud (memory)
                ↓
      LangGraph Orchestrator
                ↓
       gemma4 via Ollama
                ↓
          Final Response
```

**Backend:** FastAPI · LangGraph · Qdrant · Neo4j AuraDB · Mem0 · Redis · PostgreSQL · Celery  
**Frontend:** Next.js 14 · TypeScript · TailwindCSS · React Flow · Monaco Editor · Socket.IO  
**LLM:** `gemma4:latest` via Ollama (local, free)  
**Embeddings:** `qwen3-embedding:4b` via Ollama (local, free, dim=2560)

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker Desktop | 4.x+ | Runs Qdrant, Redis, Postgres |
| Ollama | Latest | Must have `gemma4` and `qwen3-embedding:4b` pulled |
| Node.js | 20+ | For frontend dev |
| Python | 3.12 | For backend dev |

```bash
# Verify Ollama models
ollama list
# Should show: gemma4:latest, qwen3-embedding:4b
```

---

## Quick Start (< 10 minutes)

### 1. Clone & configure

```bash
git clone <repo-url>
cd codebase-intelligence-agent
cp .env.example .env
```

Edit `.env` and fill in:
- `MEM0_API_KEY` — from [app.mem0.ai](https://app.mem0.ai)
- `NEO4J_URI` — AuraDB connection URI (e.g. `neo4j+s://xxxx.databases.neo4j.io`)
- `NEO4J_PASSWORD` — your AuraDB password

### 2. Start infrastructure

```bash
docker compose up qdrant redis postgres -d
```

### 3. Start backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:socket_app --reload
```

### 4. Start Celery worker (separate terminal)

```bash
cd backend
celery -A workers.celery_app worker --loglevel=info
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Verify

```bash
curl http://localhost:8000/health
# → { "status": "ok", "services": { "qdrant": {...}, "neo4j": {...}, ... } }
```

Open **http://localhost:3000** — you should see the three-panel UI with live service health pills in the top bar.

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
