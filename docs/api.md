# API Reference

All endpoints are served from the FastAPI backend at `http://localhost:8000` (or your deployed backend URL). Query responses stream over Server-Sent Events. All authenticated workspace routes require a `session_token` obtained from `/auth/login` or `/auth/signup`.

---

## Health

### `GET /health`

Returns the status of all external dependencies.

**Response**
```json
{
  "ok": true,
  "data": {
    "status": "ok",
    "groq": "ok",
    "pinecone": "ok",
    "supabase": "ok"
  }
}
```

---

## Auth

### `POST /auth/signup`

Create a new user account. Uses the Supabase Admin API to create a confirmed user, then upserts the user profile into `public.users`.

**Request**
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "securepassword"
}
```

**Response**
```json
{
  "ok": true,
  "data": {
    "user": {
      "id": "uuid",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "is_demo": false,
      "created_at": "2026-04-15T10:00:00Z"
    },
    "session": {
      "token": "<supabase_access_token>",
      "mode": "authenticated",
      "user_id": "uuid"
    },
    "bootstrap_chat_id": null
  }
}
```

---

### `POST /auth/login`

Authenticate with email and password. Returns a session token.

**Request**
```json
{
  "email": "jane@example.com",
  "password": "securepassword"
}
```

**Response** — same shape as `/auth/signup`.

---

## Workspace

All workspace routes require `session_token` as a query parameter or in the request body.

### `GET /workspace/bootstrap?session_token=<token>`

Load the full workspace state for the authenticated user: user profile, all chats with message and document counts, and usage metrics.

**Response**
```json
{
  "ok": true,
  "data": {
    "user": { "id": "uuid", "name": "Jane", "email": "jane@example.com", "is_demo": false },
    "chats": [
      {
        "id": "uuid",
        "user_id": "uuid",
        "title": "My first chat",
        "pinned": false,
        "memory_summary": null,
        "namespace": "uuid/uuid",
        "is_demo": false,
        "created_at": "2026-04-15T10:00:00Z",
        "updated_at": "2026-04-15T10:00:00Z",
        "message_count": 4,
        "document_count": 1
      }
    ],
    "metrics": {},
    "default_chat_id": "uuid",
    "profile_menu": []
  }
}
```

---

### `GET /workspace/chats?session_token=<token>`

List all chats for the authenticated user.

**Response** — `{ "ok": true, "data": { "chats": [ WorkspaceChatSummary ] } }`

---

### `POST /workspace/chats`

Create a new chat.

**Request**
```json
{
  "session_token": "<token>",
  "title": "Research session"
}
```

**Response** — `{ "ok": true, "data": { "chat": WorkspaceChatSummary } }`

---

### `GET /workspace/chats/{chat_id}?session_token=<token>`

Get full chat detail: messages and documents.

**Response**
```json
{
  "ok": true,
  "data": {
    "chat": { ...WorkspaceChatSummary },
    "messages": [ { "id": "uuid", "role": "user", "content": "...", "sources": [], "created_at": "..." } ],
    "documents": [ { "id": "uuid", "filename": "report.pdf", "status": "ready", "chunk_count": 42 } ]
  }
}
```

---

### `POST /workspace/chats/{chat_id}/documents`

Upload a document to a specific chat. The file is chunked, embedded, and indexed in Pinecone under the `{user_id}/{chat_id}` namespace.

**Request**
```json
{
  "session_token": "<token>",
  "chat_id": "uuid",
  "filename": "report.pdf",
  "content_base64": "<base64-encoded file bytes>",
  "mime_type": "application/pdf",
  "size_bytes": 102400
}
```

**Response**
```json
{
  "ok": true,
  "data": { "upload": { "status": "ready", "chunk_count": 42, "file_type": "pdf" } }
}
```

---

## Chat

### `POST /query`

Submit a question for retrieval-augmented generation. Response is streamed as Server-Sent Events.

**Request**
```json
{
  "chat_id": "uuid",
  "message": "What are the main risks outlined in the compliance document?",
  "top_k": 4,
  "similarity_threshold": 0.4
}
```

**SSE Event stream**

Token events (one per word):
```
data: {"type": "token", "value": "The"}
data: {"type": "token", "value": "main"}
```

Final event (complete payload):
```
data: {
  "type": "final",
  "value": {
    "ok": true,
    "data": {
      "chat_id": "uuid",
      "answer": "The main risks are...",
      "sources": [
        {
          "chunk_id": "abc123",
          "document_id": "uuid",
          "filename": "compliance.pdf",
          "page_number": 3,
          "chunk_index": 7,
          "similarity": 0.87,
          "chunk_text": "Section 4.2 identifies the following risks..."
        }
      ],
      "retrieval_count": 3,
      "confidence": 0.87,
      "latency_ms": 412,
      "used_llm": true,
      "namespace": "uuid/uuid",
      "cache_hit": false
    }
  }
}
```

---

### `GET /chat-history?chat_id=<uuid>`

Retrieve the full message history for a chat.

**Response**
```json
{
  "ok": true,
  "data": {
    "chat_id": "uuid",
    "memory_summary": "This chat is focused on Q1 compliance review.",
    "messages": [ { "role": "user", "content": "...", "sources": [], "created_at": "..." } ]
  }
}
```

---

### `DELETE /history?chat_id=<uuid>`

Clear and reset a chat's message history.

**Response** — `{ "ok": true, "data": { "chat_id": "uuid", "deleted": true, "memory_reset": true } }`

---

## Documents

### `POST /upload`

Upload a document (standalone endpoint, equivalent to the workspace per-chat upload).

**Request** — same shape as `POST /workspace/chats/{chat_id}/documents`

**Response**
```json
{
  "ok": true,
  "data": {
    "document_id": "uuid",
    "chat_id": "uuid",
    "filename": "report.pdf",
    "status": "ready",
    "progress_stage": "ready",
    "stages": ["uploaded", "chunking", "embedding", "indexing", "ready"]
  }
}
```

---

### `GET /documents?chat_id=<uuid>`

List all documents for a chat.

**Response** — `{ "ok": true, "data": { "documents": [ DocumentRecord ] } }`

---

## Feedback

### `POST /feedback`

Submit thumbs up (`1`) or thumbs down (`-1`) feedback on an assistant message.

**Request**
```json
{
  "message_id": "uuid",
  "user_id": "uuid",
  "rating": 1,
  "comment": "Accurate and well-cited."
}
```

**Response** — `{ "ok": true, "data": { "feedback_id": "uuid" } }`

---

## Metrics

### `GET /metrics?session_token=<token>`

Retrieve aggregated retrieval and usage metrics for the authenticated user.

**Response**
```json
{
  "ok": true,
  "data": {
    "total_queries": 48,
    "avg_latency_ms": 380,
    "cache_hit_rate": 0.21,
    "avg_chunks_retrieved": 3.2,
    "avg_confidence": 0.79
  }
}
```

---

## Demo

### `GET /demo/bootstrap`

Load the demo workspace: seeded chat list and analytics snapshot. No authentication required.

**Response**
```json
{
  "ok": true,
  "data": {
    "mode": "demo",
    "session": { "token": "demo", "mode": "demo" },
    "seeded_chats": [
      { "id": "demo-compliance", "title": "Compliance Review", "document_count": 2, "pinned": false }
    ],
    "analytics": { "queries": 120, "avg_latency": 310.0, "feedback": 4.2, "chunks": 3.8 }
  }
}
```

---

## Error Format

All errors return a standard envelope:

```json
{
  "ok": false,
  "data": {},
  "error": "Invalid session token.",
  "request_id": null
}
```

HTTP status codes:
- `400` — Bad request (malformed payload, invalid file encoding)
- `401` — Unauthorized (missing or invalid session token)
- `404` — Not found (chat or document does not exist)
- `500` — Internal server error (upstream service failure)
