# Database

## Overview

All relational data is stored in a Supabase (PostgreSQL) project. The schema is defined in `supabase/migrations/0001_init.sql`. Run this file in the Supabase SQL editor before starting the application. Row-Level Security (RLS) is enabled on every user-facing table.

---

## Tables

### `users`

Stores user profile records mirrored from Supabase Auth.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | References `auth.users(id)` |
| `name` | `text NOT NULL` | Display name |
| `email` | `text UNIQUE NOT NULL` | User email |
| `is_demo` | `boolean` | `true` for demo user records |
| `created_at` | `timestamptz` | Row creation timestamp |

---

### `chats`

A chat is a named conversation thread scoped to a user. Documents are uploaded into chat namespaces.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `user_id` | `uuid FK → users.id` | Owner |
| `title` | `text NOT NULL` | Chat display name |
| `pinned` | `boolean` | Whether pinned in the sidebar |
| `memory_summary` | `text` | Rolling natural-language summary of the conversation |
| `is_demo` | `boolean` | `true` for demo chats |
| `created_at` | `timestamptz` | — |
| `updated_at` | `timestamptz` | Updated by trigger on row change |

**Index**: `(user_id, created_at DESC)` for sidebar listing.

---

### `messages`

Individual messages within a chat. Stores both user and assistant turns.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `chat_id` | `uuid FK → chats.id` | Parent chat |
| `user_id` | `uuid FK → users.id` | Owner |
| `role` | `text CHECK IN ('user', 'assistant', 'system')` | Message role |
| `content` | `text NOT NULL` | Message body |
| `sources` | `jsonb` | Array of `RetrievalSourceRecord` objects attached to assistant turns |
| `latency_ms` | `integer` | End-to-end retrieval latency |
| `token_count` | `integer` | LLM token count (future) |
| `retrieval_count` | `integer` | Number of chunks retrieved |
| `prompt_version` | `text` | Prompt template identifier (for A/B testing) |
| `created_at` | `timestamptz` | — |

**Index**: `(chat_id, created_at DESC)` for history queries.

---

### `documents`

Tracks uploaded files and their Pinecone indexing state.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `chat_id` | `uuid FK → chats.id` | Parent chat |
| `user_id` | `uuid FK → users.id` | Owner |
| `filename` | `text NOT NULL` | File name as uploaded |
| `display_name` | `text` | Optional display override |
| `original_filename` | `text` | Original file name before any normalization |
| `file_type` | `text NOT NULL` | `pdf`, `txt`, or `docx` |
| `file_size_bytes` | `bigint NOT NULL` | Raw file size |
| `status` | `text CHECK IN ('uploaded','chunking','embedding','indexing','ready','failed')` | Processing state |
| `pinecone_namespace` | `text NOT NULL` | Namespace used in Pinecone (`{user_id}/{chat_id}`) |
| `chunk_count` | `integer` | Number of chunks indexed |
| `error_message` | `text` | Error detail if status is `failed` |
| `is_demo` | `boolean` | `true` for demo documents |
| `created_at` / `updated_at` | `timestamptz` | — |

**Index**: `(chat_id, status)` for document panel queries.

---

### `feedback`

Thumbs up/down ratings on individual assistant messages.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `message_id` | `uuid FK → messages.id` | Target message |
| `user_id` | `uuid FK → users.id` | Reviewer |
| `rating` | `integer CHECK IN (-1, 1)` | `1` = positive, `-1` = negative |
| `comment` | `text` | Optional free-text comment |
| `created_at` | `timestamptz` | — |

---

### `query_cache`

Caches retrieval results keyed by a hash of `(chat_id, message, top_k, threshold)`.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `user_id` | `uuid FK → users.id` | Cache entry owner |
| `chat_id` | `uuid FK → chats.id` | Scoped chat |
| `query_hash` | `text NOT NULL` | SHA-256 of query parameters |
| `response_text` | `text NOT NULL` | Cached answer |
| `sources` | `jsonb` | Cached source citations |
| `ttl_expires_at` | `timestamptz NOT NULL` | Cache expiry |
| `created_at` | `timestamptz` | — |

**Index**: `(user_id, chat_id, query_hash)` for cache lookups.

---

### `retrieval_events`

Audit log of every Pinecone retrieval with performance metrics.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `user_id` | `uuid FK → users.id` | — |
| `chat_id` | `uuid FK → chats.id` | — |
| `message_id` | `uuid FK → messages.id` | Associated message (nullable) |
| `top_k` | `integer NOT NULL` | Top-k requested |
| `threshold` | `numeric(3,2) NOT NULL` | Similarity threshold applied |
| `retrieved_chunks` | `integer NOT NULL` | Chunks returned above threshold |
| `latency_ms` | `integer NOT NULL` | Retrieval + LLM latency |
| `tokens` | `integer NOT NULL` | Token count (reserved) |
| `confidence` | `numeric(3,2) NOT NULL` | Max similarity score |
| `created_at` | `timestamptz` | — |

**Index**: `(user_id, created_at DESC)` for analytics queries.

---

### `demo_reset_runs`

Audit log of demo reset operations.

| Column | Type | Description |
|---|---|---|
| `id` | `uuid` PK | Auto-generated UUID |
| `run_at` | `timestamptz` | When the reset ran |
| `chats_reset` | `integer NOT NULL` | Number of demo chats reset |
| `documents_restored` | `integer NOT NULL` | Number of demo documents restored |
| `analytics_restored` | `jsonb` | Snapshot of restored analytics |
| `status` | `text CHECK IN ('started','success','failed')` | Outcome |
| `error_message` | `text` | Error detail if status is `failed` |

---

## Row-Level Security

Every user-facing table has RLS enabled. Policies ensure users can only read and write their own rows. Example for `chats`:

```sql
create policy chats_crud_own on chats
for all using (user_id = auth.uid())
with check (user_id = auth.uid());
```

`demo_reset_runs` has no RLS because it is written by a service-role-key worker only.

---

## Triggers

`updated_at` columns on `chats` and `documents` are automatically updated by the `set_updated_at()` trigger function.

---

## Seed Data

- `supabase/seed.sql` — baseline seed data for development
- `supabase/demo_seed.sql` — demo user records and seeded chat state for the public demo mode

---

## Connection Notes

The backend accesses Supabase via HTTP REST API (no connection pool required). The `SUPABASE_SERVICE_ROLE_KEY` is used only for admin operations (user creation, upsert with service-role privileges). All user-scoped reads and writes use the JWT access token passed in `Authorization: Bearer <token>` headers.
