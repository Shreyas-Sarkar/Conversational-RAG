# Evaluation

## What the System Measures

The analytics page and retrieval events table track the following product-level metrics:

| Metric | Source | Description |
|---|---|---|
| **Total queries** | `retrieval_events` | Number of RAG queries submitted |
| **Average latency (ms)** | `retrieval_events.latency_ms` | End-to-end time from query submission to answer |
| **Cache hit rate** | `query_cache` | Fraction of queries served from cache |
| **Average retrieved chunks** | `retrieval_events.retrieved_chunks` | Mean number of Pinecone chunks returned above threshold |
| **Average confidence** | `retrieval_events.confidence` | Mean of the highest cosine similarity score per query |
| **Feedback rating** | `feedback.rating` | Aggregate thumbs up/down; `1` positive, `-1` negative |

---

## Interpreting Metrics

### Latency

- **< 200ms** — cache hit or trivially short retrieval
- **200–600ms** — typical successful Pinecone + Groq call
- **> 800ms** — possible Groq cold start, large document set, or high `top_k`

Reducing `top_k` (default: 4) or raising `similarity_threshold` (default: 0.4) will reduce latency at the cost of recall coverage.

### Cache Hit Rate

A cache hit rate above 20% suggests users are asking repeated questions, which is expected in demo mode. For production workloads, a low cache hit rate is normal (queries are diverse). The TTL can be adjusted in `cache_service.py`.

### Confidence

Confidence reflects the maximum cosine similarity of retrieved chunks, not the quality of the LLM answer. A confidence below 0.5 suggests the query is semantically distant from the indexed documents — the answer may be speculative. A confidence above 0.75 indicates strong document grounding.

### Retrieved Chunks

If `retrieved_chunks` is consistently 0, it means:
- The similarity threshold is too high for the query
- The documents are not properly indexed in Pinecone (check the namespace)
- The embedding model is producing zero-magnitude vectors (environment issue)

If `retrieved_chunks` equals `top_k` on every query, consider raising `top_k` to improve coverage.

---

## RAG-Specific Signals

| Signal | Location | Meaning |
|---|---|---|
| `used_llm` | `QueryResponseData.used_llm` | `true` if Groq was called; `false` if cache hit or empty retrieval fallback |
| `cache_hit` | `QueryResponseData.cache_hit` | `true` if the answer was served from `query_cache` |
| `sources` | `MessageRecord.sources` | Source citations attached to every assistant message |
| `namespace` | `QueryResponseData.namespace` | The Pinecone namespace queried |

---

## Current Implementation Notes

- The analytics page currently aggregates retrieval events stored in Supabase. For demo mode, a static analytics snapshot is served.
- Feedback ratings are stored in the `feedback` table but are not yet aggregated into the analytics dashboard in real time.
- The `token_count` and `prompt_version` columns in `messages` are reserved for future A/B testing of prompt templates.

---

## Future Evaluation Hooks

- **Faithfulness score** — use an LLM judge to assess whether the answer is grounded in the retrieved chunks (RAGAs or custom)
- **Context recall** — measure whether the relevant chunks were actually retrieved (requires ground-truth labels)
- **Answer relevance** — LLM judge on whether the answer addresses the question
- **Latency percentiles** — P50/P95/P99 latency breakdown from `retrieval_events`
- **Retrieval diversity** — track whether retrieved chunks come from multiple pages/documents or cluster on one chunk
- **Prompt A/B testing** — use `prompt_version` to compare answer quality across prompt templates
