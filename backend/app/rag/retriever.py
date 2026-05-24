from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pinecone import Pinecone

from app.core.config import settings


@dataclass(frozen=True)
class RetrievalChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    similarity: float
    chunk_text: str


@lru_cache(maxsize=1)
def _pinecone_client() -> Pinecone:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not configured")
    return Pinecone(api_key=settings.pinecone_api_key)


def _query_pinecone(namespace: str, query: str, top_k: int) -> list[dict[str, Any]]:
    client = _pinecone_client()
    index = client.Index(settings.pinecone_index_name)
    response = index.search(
        namespace=namespace,
        inputs={"text": query},
        top_k=top_k,
        fields=[
            "chunk_text",
            "text",
            "document_id",
            "document_name",
            "filename",
            "page_number",
            "chunk_index",
        ],
    )
    hits = response.result.hits if response.result else []
    results = []
    for hit in hits:
        fields = hit.fields or {}
        results.append(
            {
                "chunk_id": str(hit.id),
                "document_id": str(fields.get("document_id", "")),
                # stored as document_name by ingest; filename is the legacy alias
                "filename": str(
                    fields.get("document_name", fields.get("filename", ""))
                ),
                "page_number": int(fields.get("page_number", 0) or 0),
                "chunk_index": int(fields.get("chunk_index", 0) or 0),
                "similarity": float(hit.score or 0.0),
                # chunk_text is canonical; text is the legacy alias
                "chunk_text": str(
                    fields.get("chunk_text", fields.get("text", ""))
                ),
            }
        )
    return results


def retrieve_from_pinecone(
    namespace: str,
    query: str,
    top_k: int,
    similarity_threshold: float,
) -> list[RetrievalChunk]:
    try:
        matches = _query_pinecone(namespace=namespace, query=query, top_k=top_k)
    except Exception:
        return []

    return [
        RetrievalChunk(
            chunk_id=m["chunk_id"],
            document_id=m["document_id"],
            filename=m["filename"],
            page_number=m["page_number"],
            chunk_index=m["chunk_index"],
            similarity=m["similarity"],
            chunk_text=m["chunk_text"],
        )
        for m in matches
        if m["similarity"] >= similarity_threshold
    ]
