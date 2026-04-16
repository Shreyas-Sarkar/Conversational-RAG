from __future__ import annotations

import hashlib

from app.services.workspace_store import cache_query as store_query_cache, get_cached_query as load_query_cache


def build_query_hash(chat_id: str, message: str, top_k: int, similarity_threshold: float) -> str:
    normalized = f'{chat_id}|{message.strip().lower()}|{top_k}|{similarity_threshold:.4f}'
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def cache_query(
    user_id: str,
    chat_id: str,
    query_hash: str,
    response_text: str,
    sources: list[dict[str, object]],
    ttl_seconds: int = 3600
) -> dict[str, object]:
    return store_query_cache(
        user_id=user_id,
        chat_id=chat_id,
        query_hash=query_hash,
        response_text=response_text,
        sources=sources,
        ttl_seconds=ttl_seconds
    )


def get_cached_query(chat_id: str, query_hash: str) -> dict[str, object] | None:
    return load_query_cache(chat_id, query_hash)
