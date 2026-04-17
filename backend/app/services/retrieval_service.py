from time import perf_counter
import logging

from app.rag.citations import format_citation
from app.rag.chain import build_rag_prompt
from app.rag.groq_client import invoke_groq
from app.rag.prompts import EMPTY_RETRIEVAL_MESSAGE
from app.rag.retriever import retrieve_from_pinecone
from app.services.cache_service import build_query_hash, cache_query, get_cached_query
from app.services.chat_service import get_persisted_chat_history, make_turn_message_id, persist_chat_turn
from app.services.demo_ingest import get_demo_namespace_for_chat
from app.services.workspace_store import get_chat_namespace, _upsert_row, _cloud_enabled, is_uuid


logger = logging.getLogger(__name__)


def retrieve_context(chat_id: str, message: str, top_k: int, similarity_threshold: float) -> dict[str, object]:
    started_at = perf_counter()
    namespace = get_demo_namespace_for_chat(chat_id) or get_chat_namespace(chat_id) or chat_id
    logger.info('Retrieving response', extra={'chat_id': chat_id, 'namespace': namespace, 'top_k': top_k, 'threshold': similarity_threshold})

    query_hash = build_query_hash(chat_id, message, top_k, similarity_threshold)
    cached_result = get_cached_query(chat_id, query_hash)
    if cached_result:
        cached_latency_ms = int((perf_counter() - started_at) * 1000)
        cached_sources = cached_result.get('sources', [])
        return {
            'chat_id': chat_id,
            'answer': cached_result.get('response_text', EMPTY_RETRIEVAL_MESSAGE),
            'sources': cached_sources,
            'retrieval_count': len(cached_sources),
            'confidence': max((float(source.get('similarity', 0.0)) for source in cached_sources), default=0.0),
            'latency_ms': cached_latency_ms,
            'used_llm': False,
            'namespace': namespace,
            'cache_hit': True
        }

    chunks = retrieve_from_pinecone(namespace=namespace, query=message, top_k=top_k, similarity_threshold=similarity_threshold)
    logger.info('Retrieved chunks', extra={'chat_id': chat_id, 'namespace': namespace, 'chunk_count': len(chunks)})

    if not chunks:
        result = {
            'chat_id': chat_id,
            'answer': EMPTY_RETRIEVAL_MESSAGE,
            'sources': [],
            'retrieval_count': 0,
            'confidence': 0.0,
            'latency_ms': int((perf_counter() - started_at) * 1000),
            'used_llm': False
        }
        persist_chat_turn(
            chat_id,
            {'id': make_turn_message_id(chat_id, 'user', message), 'chat_id': chat_id, 'role': 'user', 'content': message, 'sources': []},
            {'id': make_turn_message_id(chat_id, 'assistant', result['answer']), 'chat_id': chat_id, 'role': 'assistant', 'content': result['answer'], 'sources': []}
        )
        return result

    sources = [format_citation(chunk.__dict__) for chunk in chunks]
    context = '\n\n'.join(
        f"Source {index + 1} | {source['filename']} | page {source['page_number']} | chunk {source['chunk_index']}\n{source['chunk_text']}"
        for index, source in enumerate(sources)
    )
    chat_history_messages = get_persisted_chat_history(chat_id)
    chat_history = '\n'.join(
        f"{message_item.get('role', 'unknown').title()}: {message_item.get('content', '')}"
        for message_item in chat_history_messages
    )

    final_prompt = build_rag_prompt(question=message, context=context, chat_history=chat_history)
    response = invoke_groq(final_prompt)
    used_llm = bool(response.strip())

    if not response.strip():
        response = _build_fallback_answer(message=message, sources=sources)

    confidence = max(source['similarity'] for source in sources)
    latency_ms = int((perf_counter() - started_at) * 1000)
    logger.info('Retrieval complete', extra={'chat_id': chat_id, 'namespace': namespace, 'latency_ms': latency_ms, 'retrieval_count': len(sources), 'used_llm': used_llm})
    result = {
        'chat_id': chat_id,
        'answer': response,
        'sources': sources,
        'retrieval_count': len(sources),
        'confidence': confidence,
        'latency_ms': latency_ms,
        'used_llm': used_llm,
        'namespace': namespace,
        'cache_hit': False
    }
    persist_chat_turn(
        chat_id,
        {'id': make_turn_message_id(chat_id, 'user', message), 'chat_id': chat_id, 'role': 'user', 'content': message, 'sources': []},
        {'id': make_turn_message_id(chat_id, 'assistant', response), 'chat_id': chat_id, 'role': 'assistant', 'content': response, 'sources': sources}
    )
    cache_query(
        user_id=namespace.split('/')[0] if '/' in namespace else chat_id,
        chat_id=chat_id,
        query_hash=query_hash,
        response_text=response,
        sources=sources
    )
    # Persist retrieval event to cloud if enabled
    if _cloud_enabled() and is_uuid(chat_id):
        try:
            _upsert_row(
                'retrieval_events',
                {
                    'user_id': namespace.split('/')[0] if '/' in namespace else chat_id,
                    'chat_id': chat_id,
                    'message_id': None,
                    'top_k': int(top_k),
                    'threshold': float(similarity_threshold),
                    'retrieved_chunks': int(len(sources)),
                    'latency_ms': int(latency_ms),
                    'tokens': int(0),
                    'confidence': float(confidence)
                }
            )
        except Exception:
            logger.exception('Failed to persist retrieval event')
    return result


def _build_fallback_answer(message: str, sources: list[dict[str, object]]) -> str:
    if not sources:
        return 'I could not find relevant information in the indexed documents to answer confidently.'

    lead_source = sources[0]
    snippet = str(lead_source.get('chunk_text', '')).strip()
    if len(snippet) > 320:
        snippet = snippet[:317].rstrip() + '...'

    filename = lead_source.get('filename', 'the document')
    page_number = lead_source.get('page_number', '?')
    return (
        f'Based on {filename} on page {page_number}, the retrieved context suggests: {snippet} '
        f'This is the strongest grounded evidence available for "{message}".'
    )
