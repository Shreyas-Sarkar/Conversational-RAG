# System Diagrams

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Browser                                       │
│                                                                         │
│   ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐  │
│   │ Landing │  │ Workspace │  │  Chat   │  │  Demo  │  │Analytics │  │
│   │  Page   │  │  Shell    │  │  View   │  │  Mode  │  │  Page    │  │
│   └─────────┘  └───────────┘  └─────────┘  └────────┘  └──────────┘  │
│                         Next.js 14 App Router                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP / SSE
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                                  │
│                                                                         │
│   ┌──────┐  ┌─────────┐  ┌──────┐  ┌──────┐  ┌────────┐  ┌────────┐  │
│   │ Auth │  │Workspace│  │ Chat │  │ Docs │  │  Demo  │  │Metrics │  │
│   │ API  │  │   API   │  │  API │  │  API │  │   API  │  │   API  │  │
│   └──┬───┘  └────┬────┘  └──┬───┘  └──┬───┘  └───┬────┘  └────────┘  │
│      │           │           │          │           │                    │
│   ┌──┴───────────┴───────────┴──────────┴───────────┴──────────────┐   │
│   │                     Service Layer                                │   │
│   │  AuthService · WorkspaceStore · RetrievalService · DemoIngest  │   │
│   │  DocumentIngestService · ChatService · CacheService · Metrics  │   │
│   └──────────────────────────┬───────────────────────────────────────┘  │
│                               │                                          │
│              ┌────────────────┼─────────────────┐                       │
│              │                │                 │                       │
│              ▼                ▼                 ▼                       │
│        ┌──────────┐   ┌────────────┐   ┌───────────┐                  │
│        │ Supabase │   │  Pinecone  │   │   Groq    │                  │
│        │  (Auth + │   │  (Vector   │   │   (LLM    │                  │
│        │  Postgres│   │   Index)   │   │ Inference)│                  │
│        └──────────┘   └────────────┘   └───────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Query Data Flow

```
User types message
        │
        ▼
POST /query { chat_id, message, top_k=4, threshold=0.4 }
        │
        ▼
  Cache lookup (Supabase query_cache)
        │
   ┌────┴─────┐
   │ HIT      │ MISS
   ▼          ▼
Stream     Encode message
cached     → 384-dim vector
answer     (Sentence Transformers)
   │          │
   │          ▼
   │     Pinecone query
   │     namespace: {user_id}/{chat_id}
   │     top_k=4, cosine similarity
   │          │
   │     Filter by threshold (0.4)
   │          │
   │     Build context block
   │     (Source 1 | file | page | chunk\n text)
   │          │
   │     Append chat history
   │          │
   │     POST to Groq
   │     (llama-3.3-70b-versatile)
   │          │
   │     Stream tokens back
   │          │
   └────►Persist to Supabase
         (user_msg, assistant_msg, retrieval_event, cache_entry)
                │
                ▼
         SSE final event → Frontend
         (answer + sources + metadata)
```

---

## Pinecone Namespace Strategy

```
Pinecone Index: conversational-rag
│
├── {user_id_A}/{chat_id_1}    ← User A, Chat 1 documents
├── {user_id_A}/{chat_id_2}    ← User A, Chat 2 documents
├── {user_id_B}/{chat_id_3}    ← User B, Chat 3 documents
│
├── demo/compliance             ← Demo: compliance docs (seeded at startup)
├── demo/oracle                 ← Demo: oracle reference docs
├── demo/research               ← Demo: academic papers
└── demo/resume                 ← Demo: resume documents
```

Each query is **always scoped** to a single namespace. Users never retrieve chunks from other users' documents.

---

## Document Ingestion Pipeline

```
File upload (base64 JSON)
        │
        ▼
Decode bytes
        │
        ▼
Detect type (PDF / DOCX / TXT)
        │
        ▼
Extract text
  PDF → PyPDF2 page-by-page extraction
  DOCX → paragraph extraction
  TXT → direct read
        │
        ▼
Sentence chunking
  (split by sentence boundary, max chunk size)
        │
        ▼
Embed chunks (Sentence Transformers, all-MiniLM-L6-v2)
  Output: 384-dim float32 vectors
        │
        ▼
Upsert to Pinecone
  namespace = {user_id}/{chat_id}
  metadata: { document_id, filename, page_number, chunk_index, chunk_text }
        │
        ▼
Persist DocumentRecord to Supabase
  status = ready, chunk_count = N
        │
        ▼
Return DocumentUploadResponseData to frontend
```
