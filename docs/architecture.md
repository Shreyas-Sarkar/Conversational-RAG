# Architecture

## System Overview

Conversational RAG is a full-stack application that enables users to upload documents and have grounded AI conversations with them. The system is composed of four distinct layers: a Next.js frontend, a FastAPI backend, Supabase for relational persistence and auth, and Pinecone for vector storage.

```
Browser
  └── Next.js 14 (App Router)
        └── FastAPI Backend (Python 3.11)
              ├── Supabase  (PostgreSQL + Auth)
              └── Pinecone  (Vector Index)
                    └── Groq (LLM inference)
```

## Components

### Frontend — Next.js 14

The frontend is built with the App Router, React Server Components where appropriate, and client components for interactive chat. Tailwind CSS provides styling. The frontend has no direct database access — all state changes go through the FastAPI backend.

Key routes:
- `/` — Landing page with feature overview
- `/auth/login`, `/auth/signup` — Authentication pages
- `/workspace` — Authenticated workspace shell listing all chats
- `/workspace/[chatId]` — Individual chat view with document list and retrieval inspector
- `/workspace/settings` — Profile and settings
- `/demo` — Public demo workspace with pre-seeded chats
- `/analytics` — Metrics dashboard (query volume, latency, cache hit rate)

### Backend — FastAPI

The backend handles all business logic. Routers are organized by feature area:

| Router | Prefix | Responsibility |
|---|---|---|
| `auth` | `/auth` | Signup, login, session resolution |
| `workspace` | `/workspace` | Bootstrap, chat CRUD, document upload per-chat |
| `chat` | `` | Query (SSE), chat history, history clear |
| `documents` | `` | Standalone document upload, document list |
| `demo` | `/demo` | Demo bootstrap, seeded chat state |
| `metrics` | `/metrics` | Retrieval and usage metrics |
| `feedback` | `/feedback` | Thumbs up/down feedback on messages |
| `health` | `/health` | Dependency health check |

### Supabase — Auth + Relational Data

Supabase provides two functions:
1. **Authentication** — email/password sign-up and login via the Supabase Auth API. The backend uses the service role key for admin operations (creating confirmed users) and the anon key for standard auth flows.
2. **Relational persistence** — eight PostgreSQL tables store user profiles, chats, messages, documents, feedback, query cache, retrieval events, and demo reset runs. All tables have Row-Level Security enabled so users can only access their own records.

### Pinecone — Vector Storage

Documents are chunked and embedded with Sentence Transformers (`all-MiniLM-L6-v2`, 384 dimensions) before being indexed in Pinecone. Each user's documents are stored in a namespace of the form `{user_id}/{chat_id}`, so retrieval is always scoped to the correct document set. Demo documents use fixed namespaces seeded at startup.

### Groq — LLM Inference

Retrieved chunks are assembled into a context block and injected into a structured prompt alongside the chat history. Groq's `llama-3.3-70b-versatile` model generates the final answer. If Groq returns an empty response, the backend falls back to a chunk-grounded factual summary to ensure the user always receives a usable answer.

## Data Flow

### Authenticated Query

```
1. User types a message in the workspace chat UI
2. Frontend POSTs { chat_id, message, top_k, similarity_threshold } to POST /query
3. Backend checks the query cache (Supabase query_cache table)
   a. Cache hit → return cached answer immediately, stream as SSE
   b. Cache miss → continue
4. Backend encodes the message with Sentence Transformers → 384-dim vector
5. Pinecone is queried in namespace {user_id}/{chat_id} with top_k and threshold filter
6. Retrieved chunks are ranked by cosine similarity
7. Context block + chat history + system prompt → sent to Groq
8. Groq streams the answer token-by-token
9. Backend persists the user message, assistant message, and retrieval event to Supabase
10. Cache entry is written with TTL
11. Answer + sources + metadata stream back to the frontend over SSE
12. Frontend renders the answer and populates the retrieval inspector panel
```

### Document Upload

```
1. User drops a file onto the upload zone in the workspace
2. Frontend base64-encodes the file and POSTs to POST /upload or POST /workspace/chats/{id}/documents
3. Backend decodes the file and routes it to the ingestion service
4. Ingestion: PDF/DOCX text extraction → sentence chunking → embedding → Pinecone upsert
5. Document record (status, chunk_count, namespace) is persisted to Supabase
6. Frontend receives DocumentUploadResponseData with progress stage and document ID
```

### Authentication Flow

```
1. User submits sign-up form
2. Backend calls Supabase Admin API to create a confirmed user (bypasses email confirmation)
3. Backend upserts the user profile into the public.users table via REST API
4. Backend issues a login request to obtain an access token
5. Token + user ID returned to frontend; stored in sessionStorage
6. Subsequent requests pass the token as session_token; backend resolves it via Supabase Auth
```

## Namespace Strategy

Pinecone namespaces follow the pattern `{user_id}/{chat_id}` for authenticated users. This provides:
- **Isolation**: queries never retrieve chunks from another user's documents
- **Chat-level scoping**: uploading to chat A does not contaminate chat B
- **Demo separation**: demo namespaces use fixed string IDs (`demo/compliance`, `demo/oracle`, etc.) and are never mixed with user data

## Query Cache

The cache key is a SHA-256 hash of `(chat_id, message, top_k, similarity_threshold)`. Cache entries are stored in Supabase with a configurable TTL. A cache hit skips both Pinecone and Groq, returning sub-10ms responses for repeated queries.

## Demo Mode Architecture

On startup, `index_demo_docs()` runs and indexes the four curated PDF sets under `demo_docs/` into their respective Pinecone namespaces. `get_demo_chat_seed_payload()` hydrates the in-memory demo chat state from `backend/app/data/demo_chats.json`. The demo reset worker can be triggered periodically to restore the demo to its initial state.
