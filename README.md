# Conversational RAG

A full-stack AI workspace for document-grounded conversations. Upload PDFs, ask questions, and receive answers grounded in your documents — with source citations, retrieval traces, and persistent chat history.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 App Router · React 18 · TypeScript · Tailwind CSS |
| Backend | FastAPI · Pydantic v2 · Python 3.11+ |
| Auth & Database | Supabase (PostgreSQL + Row-Level Security) |
| Vector Store | Pinecone (serverless, `us-east-1`) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Containers | Docker + Docker Compose |
| Package Manager | pnpm (monorepo workspace) |

## Features

- **Authenticated workspace** — sign up, log in, and access your private chat history and documents across sessions
- **Document upload** — drag-and-drop PDFs, TXT, or DOCX files; documents are chunked, embedded, and indexed in Pinecone automatically
- **Conversational RAG** — each query retrieves the most relevant chunks from your document namespace and generates a grounded answer via Groq
- **Citation transparency** — every answer includes source citations with filename, page number, chunk index, and similarity score
- **Retrieval inspector** — view top-k chunks, confidence scores, latency, cache hit status, and LLM usage per query
- **Chat persistence** — messages, documents, and memory summaries are persisted to Supabase; workspace state survives page reloads
- **Seeded demo mode** — four curated document sets (compliance, oracle, research, resume) with pre-seeded chats; no account required
- **Analytics page** — track query volume, average latency, cache hit rate, and retrieval chunk distribution over time
- **Query cache** — identical queries within a TTL window are served from cache, skipping Pinecone and Groq
- **SSE streaming** — token-by-token answer streaming over Server-Sent Events

## Repository Layout

```
conversational-rag/
├── frontend/               # Next.js 14 application
│   ├── app/                # App Router pages (workspace, chat, demo, analytics, auth)
│   ├── components/         # Reusable UI components grouped by feature
│   └── lib/                # API client and session utilities
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── api/            # Route handlers (auth, chat, documents, workspace, demo, metrics, feedback)
│   │   ├── core/           # Config, logging, security
│   │   ├── db/             # Supabase client, Pydantic schemas, repositories
│   │   ├── rag/            # Pinecone retriever, Groq client, prompt builder, citations
│   │   ├── services/       # Business logic (auth, workspace store, retrieval, ingestion, demo, cache, metrics)
│   │   └── workers/        # Background workers (demo reset)
│   └── scripts/            # Developer scripts (lint)
├── supabase/
│   ├── migrations/         # SQL schema (tables, indexes, RLS policies)
│   ├── seed.sql            # Base seed data
│   └── demo_seed.sql       # Demo mode seed data
├── demo_docs/              # Curated PDF sets for demo mode
│   ├── compliance/
│   ├── oracle/
│   ├── research/
│   └── resume/
├── docker/                 # Dockerfiles and docker-compose
├── docs/                   # Architecture, API, database, deployment, demo, evaluation notes
├── package.json            # Monorepo root (pnpm workspace)
└── pnpm-workspace.yaml
```

## Quick Start

### Prerequisites

- Node.js 18+, pnpm 9+
- Python 3.11+
- A [Supabase](https://supabase.com) project with the schema from `supabase/migrations/0001_init.sql`
- A [Pinecone](https://pinecone.io) index named `conversational-rag` (dimension: 384, metric: cosine)
- A [Groq](https://console.groq.com) API key

### 1. Clone and install

```bash
git clone https://github.com/Shreyas-Sarkar/Test-github.git conversational-rag
cd conversational-rag
pnpm install
```

### 2. Configure environment

```bash
# Backend
cp backend/.env.example backend/.env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
#          PINECONE_API_KEY, PINECONE_INDEX_NAME, GROQ_API_KEY

# Frontend
cp frontend/.env.example frontend/.env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_BASE_URL
```

### 3. Apply the database schema

Run `supabase/migrations/0001_init.sql` in your Supabase SQL editor. Optionally run `supabase/seed.sql` and `supabase/demo_seed.sql` for demo data.

### 4. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start the frontend

```bash
# From the repo root
pnpm dev
# or: cd frontend && pnpm dev
```

The frontend runs on `http://localhost:3000` and the backend on `http://localhost:8000`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (admin operations) |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Pinecone index name (default: `conversational-rag`) |
| `PINECONE_CLOUD` | Pinecone cloud provider (default: `aws`) |
| `PINECONE_REGION` | Pinecone region (default: `us-east-1`) |
| `GROQ_API_KEY` | Groq API key |
| `GROQ_MODEL_NAME` | Groq model (default: `llama-3.3-70b-versatile`) |
| `GROQ_TEMPERATURE` | LLM temperature (default: `0.2`) |
| `GROQ_TOP_P` | LLM top-p (default: `0.9`) |
| `EMBEDDING_MODEL_NAME` | Sentence Transformers model (default: `sentence-transformers/all-MiniLM-L6-v2`) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL (default: `http://localhost:8000`) |

## Demo Mode

Visit `/demo` to explore the app without signing up. Demo mode uses four curated document sets pre-indexed in Pinecone:

- **Compliance** — regulatory and policy documents
- **Oracle** — technical reference material
- **Research** — academic papers
- **Resume** — sample professional documents

Demo chats reset on a daily cycle. Demo state is fully isolated from authenticated user data.

## Docker

```bash
cd docker
docker compose up --build
```

This starts both the frontend (port 3000) and backend (port 8000). You still need managed Supabase and Pinecone — the Docker setup does not bundle those services.

## API Overview

The backend exposes a REST API at `http://localhost:8000`. Key endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (Groq, Pinecone, Supabase) |
| `POST` | `/auth/signup` | Create a new account |
| `POST` | `/auth/login` | Log in and receive a session token |
| `GET` | `/workspace/bootstrap` | Load full workspace state for a session |
| `GET` | `/workspace/chats` | List all chats for the authenticated user |
| `POST` | `/workspace/chats` | Create a new chat |
| `GET` | `/workspace/chats/{chat_id}` | Get chat detail with messages and documents |
| `POST` | `/workspace/chats/{chat_id}/documents` | Upload a document to a specific chat |
| `POST` | `/query` | Submit a question and receive an SSE-streamed answer |
| `GET` | `/chat-history` | Retrieve message history for a chat |
| `DELETE` | `/history` | Clear and reset a chat's history |
| `POST` | `/upload` | Upload a document (standalone endpoint) |
| `GET` | `/documents` | List documents for a chat |
| `POST` | `/feedback` | Submit thumbs up/down feedback on a message |
| `GET` | `/metrics` | Retrieve retrieval and usage metrics |

See [`docs/api.md`](docs/api.md) for full request/response schemas.

## Documentation

| Doc | Contents |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, component relationships, data flow |
| [`docs/api.md`](docs/api.md) | Full API reference with request/response shapes |
| [`docs/database.md`](docs/database.md) | Supabase table schemas, indexes, and RLS policy summary |
| [`docs/deployment.md`](docs/deployment.md) | Step-by-step deployment guide (Vercel + Render/Fly) |
| [`docs/demo-mode.md`](docs/demo-mode.md) | Demo mode behaviour, seeding, and reset cycle |
| [`docs/evaluation.md`](docs/evaluation.md) | Metrics tracked and analytics interpretation |
| [`docs/diagrams.md`](docs/diagrams.md) | System architecture diagram |

## Future Work

- Replace remaining local JSON persistence with fully Supabase-backed workspace state
- Add real feedback persistence and ingestion into the analytics pipeline
- Implement CI for lint, typecheck, and backend pytest suite
- Add Pinecone hybrid search (dense + sparse) for improved retrieval precision
- Add multi-document cross-referencing in a single chat namespace
- Release notes and production observability (Sentry, structured logs to a log aggregator)
