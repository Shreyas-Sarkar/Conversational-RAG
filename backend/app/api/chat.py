from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from typing import AsyncIterator

from app.db.schemas import ApiEnvelope, ChatHistoryResponseData, ChatTurnResponseData, QueryResponseData
from app.services.chat_service import build_chat_turn, get_chat_memory_summary, get_persisted_chat_history, replace_chat_history
from app.services.retrieval_service import retrieve_context
from app.services.demo_ingest import get_demo_namespace_for_chat

router = APIRouter(tags=['chat'])


class QueryRequest(BaseModel):
    chat_id: str
    message: str
    top_k: int = 4
    similarity_threshold: float = 0.4


@router.post('/query')
def query(payload: QueryRequest) -> StreamingResponse:
    async def stream_events() -> AsyncIterator[str]:
        retrieval = retrieve_context(
            chat_id=payload.chat_id,
            message=payload.message,
            top_k=payload.top_k,
            similarity_threshold=payload.similarity_threshold
        )
        chat_turn = build_chat_turn(
            chat_id=payload.chat_id,
            message=payload.message,
            answer=retrieval['answer'],
            sources=retrieval['sources']
        )

        payload_data = ChatTurnResponseData(
            chat_id=payload.chat_id,
            user_message_id=chat_turn['user_message']['id'],
            assistant_message_id=chat_turn['assistant_message']['id'],
            answer=retrieval['answer'],
            sources=retrieval['sources'],
            memory_summary=chat_turn['memory_summary'],
            namespace=retrieval.get('namespace'),
            retrieval_count=retrieval.get('retrieval_count', 0),
            confidence=retrieval.get('confidence', 0.0),
            latency_ms=retrieval.get('latency_ms', 0),
            used_llm=retrieval.get('used_llm', False),
            cache_hit=retrieval.get('cache_hit', False)
        ).model_dump()

        for token in payload_data['answer'].split(' '):
            yield f'data: {json.dumps({"type": "token", "value": token})}\n\n'

        yield f'data: {json.dumps({"type": "final", "value": ApiEnvelope(data=payload_data).model_dump()})}\n\n'

    return StreamingResponse(stream_events(), media_type='text/event-stream')


@router.get('/chat-history')
def chat_history(chat_id: str) -> dict[str, object]:
    namespace = get_demo_namespace_for_chat(chat_id)
    messages = get_persisted_chat_history(chat_id)

    response = ApiEnvelope(
        data=ChatHistoryResponseData(
            chat_id=chat_id,
            memory_summary=get_chat_memory_summary(chat_id) or f"Chat is focused on {chat_id} guidance.",
            messages=messages
        ).model_dump()
    )
    return response.model_dump()


@router.delete('/history')
def clear_history(chat_id: str) -> dict[str, object]:
    replace_chat_history(chat_id, [])
    return ApiEnvelope(data={'chat_id': chat_id, 'deleted': True, 'memory_reset': True}).model_dump()
