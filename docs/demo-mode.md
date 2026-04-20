# Demo Mode

## What It Is

Demo mode is a public, unauthenticated workspace that lets visitors explore the full RAG experience without creating an account. It uses four curated document sets pre-indexed in Pinecone and pre-seeded chat histories.

Visit `/demo` from the landing page to enter demo mode.

---

## Document Sets

Demo documents are stored under `demo_docs/` and indexed at startup:

| Set | Namespace | Contents |
|---|---|---|
| `compliance` | `demo/compliance` | Regulatory and policy documents |
| `oracle` | `demo/oracle` | Technical reference material |
| `research` | `demo/research` | Academic papers |
| `resume` | `demo/resume` | Sample professional documents |

Each set has a corresponding pre-seeded chat in the demo workspace with example prompts already answered.

---

## Startup Indexing

When the backend starts, `index_demo_docs()` runs automatically:

1. Reads PDFs from each subdirectory of `demo_docs/`
2. Chunks and embeds each document with Sentence Transformers
3. Upserts chunks into the corresponding Pinecone namespace (e.g., `demo/compliance`)
4. If a namespace is already populated (checked via vector count), indexing is skipped to avoid duplicate entries

This means cold-starting the backend with empty Pinecone namespaces will index all demo docs before serving traffic. Subsequent restarts skip indexing.

---

## Chat State Seeding

Pre-seeded chat histories are stored in `backend/app/data/demo_chats.json`. At startup, `get_demo_chat_seed_payload()` loads this file into memory and makes it available for the `/demo/bootstrap` endpoint.

The seeded chats simulate realistic RAG conversations with example questions and grounded answers covering each document set.

---

## Demo Bootstrap Response

`GET /demo/bootstrap` returns:

```json
{
  "mode": "demo",
  "session": { "token": "demo", "mode": "demo" },
  "seeded_chats": [
    { "id": "demo-compliance", "title": "Compliance Review", "document_count": 2 },
    { "id": "demo-oracle", "title": "Oracle DB Reference", "document_count": 3 },
    { "id": "demo-research", "title": "Research Papers", "document_count": 4 },
    { "id": "demo-resume", "title": "Resume Analysis", "document_count": 1 }
  ],
  "analytics": {
    "queries": 120,
    "avg_latency": 310.0,
    "feedback": 4.2,
    "chunks": 3.8
  }
}
```

The `analytics` snapshot is static for demo mode — it represents illustrative numbers, not live metrics.

---

## Isolation from Authenticated Users

Demo data is fully isolated from authenticated user data:

- Demo chats use string IDs (e.g., `"demo-compliance"`) rather than UUIDs
- The retrieval service checks `get_demo_namespace_for_chat(chat_id)` first; if a demo namespace is found, it is used instead of the user's personal namespace
- Authenticated users never see demo chat history, and demo visitors never see authenticated user data
- The `is_demo` flag on `users`, `chats`, and `documents` tables marks demo records

---

## Reset Cycle

The demo worker (`backend/app/workers/demo_reset_worker.py`) can be triggered on a schedule (e.g., daily via a cron job or Render scheduled job) to restore the demo to its initial state. Each reset run is logged to the `demo_reset_runs` table with outcome status and statistics.

To trigger a reset manually, call the reset endpoint (service-role authenticated) or restart the backend (which re-seeds Pinecone namespaces if they are empty).

---

## Adding New Demo Documents

1. Add PDF files to the appropriate subdirectory under `demo_docs/`
2. Update `backend/app/data/demo_chats.json` to include representative seeded conversations
3. Restart the backend — new documents will be indexed on startup
4. Alternatively, clear the Pinecone namespace first to force a full re-index
