from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

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
def _embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


@lru_cache(maxsize=1)
def _pinecone_client() -> Pinecone:
    if not settings.pinecone_api_key:
        raise RuntimeError('PINECONE_API_KEY is not configured')
    return Pinecone(api_key=settings.pinecone_api_key)


def _query_pinecone(namespace: str, query: str, top_k: int) -> list[dict[str, Any]]:
    client = _pinecone_client()
    index = client.Index(settings.pinecone_index_name)
    vector = _embedding_model().encode([query], normalize_embeddings=True)[0]
    response = index.query(
        namespace=namespace,
        vector=vector.tolist() if hasattr(vector, 'tolist') else list(vector),
        top_k=top_k,
        include_metadata=True
    )

    matches = []
    for match in getattr(response, 'matches', []) or []:
        metadata = getattr(match, 'metadata', None) or {}
        chunk_text = str(metadata.get('chunk_text', metadata.get('text', '')))
        matches.append(
            {
                'chunk_id': str(getattr(match, 'id', '')),
                'document_id': str(metadata.get('document_id', '')),
                'filename': str(metadata.get('document_name', metadata.get('filename', ''))),
                'page_number': int(metadata.get('page_number', 0) or 0),
                'chunk_index': int(metadata.get('chunk_index', 0) or 0),
                'similarity': float(getattr(match, 'score', 0.0) or 0.0),
                'chunk_text': chunk_text
            }
        )
    return matches


def retrieve_from_pinecone(namespace: str, query: str, top_k: int, similarity_threshold: float) -> list[RetrievalChunk]:
    try:
        matches = _query_pinecone(namespace=namespace, query=query, top_k=top_k)
    except Exception:
        return []

    return [
        RetrievalChunk(
            chunk_id=match['chunk_id'],
            document_id=match['document_id'],
            filename=match['filename'],
            page_number=match['page_number'],
            chunk_index=match['chunk_index'],
            similarity=match['similarity'],
            chunk_text=match['chunk_text']
        )
        for match in matches
        if match['similarity'] >= similarity_threshold
    ]
