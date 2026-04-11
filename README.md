# LLM RAG Platform

API-first RAG platform (modular monolith FastAPI) with:
- backend in `backend/` (`users`, `projects`, `sources`, `ingestion`, `embeddings`, `vectordb`, `rag`, `chat`)
- main frontend (`frontend`)
- external SaaS demo client (`examples/cyber_threat_ui`)
- offline evaluation (`evaluation/ragas`)

## 1) Quick Start (Docker, recommended)

### Prerequisites
- Docker + Docker Compose

### Run full stack
```bash
cp .env.example .env
# set OPENROUTER_API_KEY in .env
docker compose up --build
```

### Services
- Backend API: `http://localhost:8000`
- Main frontend: `http://localhost:3000`
- Postgres: `localhost:5432`
- Qdrant: `http://localhost:6333`

## 2) Local Run (without Docker)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Running Postgres and Qdrant (or keep SQLite fallback + run Qdrant)

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic email-validator qdrant-client psycopg2-binary

cp .env.example .env
export OPENROUTER_API_KEY=your_key
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Main frontend
```bash
cd frontend
npm install
npm run dev
```

### External demo frontend (Cyber Threat UI)
```bash
cd examples/cyber_threat_ui
npm install
npm run dev
```

## 3) API Endpoints (main)

Base URL: `http://localhost:8000/api/v1`

- Users: `/users/*`
- Auth (JWT): `/auth/*`
- Projects: `/projects/*`
- Sources: `/sources/*`
- Ingestion: `/ingestion/*`
- Embeddings: `/embeddings/*`
- Vector DB: `/vectordb/*`
- RAG: `/rag/*`
- Chat: `POST /chat/{project_id}`

### Chat request
`query_embedding` is optional (backend can generate lightweight embedding stub).
```json
{
  "message": "Summarize top phishing risks this week"
}
```

### Chat response
```json
{
  "answer": "...",
  "sources": ["source_id=3, chunk_id=12, score=0.8732"]
}
```

## 4) RAG Logging

RAG requests are stored in `rag_query_logs` with:
- `project_id`
- `question`
- `retrieved_context`
- `answer`

Used for analysis and offline evaluation.

Chat-level logs are also stored in `chat_logs`.

## 5) Offline Evaluation (RAGAS-style)

Run:
```bash
python -m evaluation.ragas.run_eval --dataset path/to/dataset.jsonl
```

JSONL sample:
```json
{"question":"...","contexts":["..."],"ground_truth":"...","answer":"..."}
```

Reported metrics:
- faithfulness
- answer relevancy
- context precision
- context recall

## 6) Handy Make Commands

```bash
make help
make up
make down
make logs
make backend
make frontend
make example
```