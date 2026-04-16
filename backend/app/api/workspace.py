from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.schemas import ApiEnvelope, WorkspaceBootstrapData, WorkspaceChatDetailData, WorkspaceChatSummary
from app.services.auth_service import resolve_session
from app.services.document_ingest_service import ingest_uploaded_document
from app.services.workspace_store import add_document_record, bootstrap_workspace, create_default_chat, get_chat, load_workspace_state, save_workspace_state, list_user_chats

router = APIRouter(prefix='/workspace', tags=['workspace'])
logger = logging.getLogger(__name__)


class CreateChatRequest(BaseModel):
    session_token: str
    title: str | None = None


class UploadDocumentRequest(BaseModel):
    session_token: str
    chat_id: str
    filename: str
    content_base64: str
    mime_type: str | None = None
    size_bytes: int | None = None


@router.get('/bootstrap')
def get_bootstrap(session_token: str) -> dict[str, object]:
    user = resolve_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session token.')

    return ApiEnvelope(data=WorkspaceBootstrapData(**bootstrap_workspace(str(user['id']))).model_dump()).model_dump()


@router.get('/chats')
def get_chats(session_token: str) -> dict[str, object]:
    user = resolve_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session token.')

    chats = list_user_chats(str(user['id']))
    return ApiEnvelope(data={'chats': chats}).model_dump()


@router.post('/chats')
def create_chat(payload: CreateChatRequest) -> dict[str, object]:
    user = resolve_session(payload.session_token)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session token.')

    workspace_state = load_workspace_state()
    chat = create_default_chat(workspace_state, str(user['id']), title=payload.title or 'New chat')
    save_workspace_state(workspace_state)
    return ApiEnvelope(data={'chat': WorkspaceChatSummary(**{
        'id': chat['id'],
        'user_id': chat['user_id'],
        'title': chat['title'],
        'pinned': chat.get('pinned', False),
        'memory_summary': chat.get('memory_summary'),
        'namespace': chat.get('namespace'),
        'is_demo': chat.get('is_demo', False),
        'created_at': chat.get('created_at'),
        'updated_at': chat.get('updated_at'),
        'message_count': 0,
        'document_count': 0
    }).model_dump()}).model_dump()


@router.get('/chats/{chat_id}')
def get_chat_detail(session_token: str, chat_id: str) -> dict[str, object]:
    user = resolve_session(session_token)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session token.')

    detail = get_chat(chat_id)
    if not detail:
        raise HTTPException(status_code=404, detail='Chat not found.')

    return ApiEnvelope(data=WorkspaceChatDetailData(**detail).model_dump()).model_dump()


@router.post('/chats/{chat_id}/documents')
def upload_document(payload: UploadDocumentRequest, chat_id: str) -> dict[str, object]:
    user = resolve_session(payload.session_token)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session token.')

    try:
        file_bytes = base64.b64decode(payload.content_base64.encode('utf-8'))
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Invalid file payload.') from exc

    namespace = f"{str(user['id'])}/{chat_id}"
    try:
        ingest_result = ingest_uploaded_document(
            user_id=str(user['id']),
            chat_id=chat_id,
            filename=payload.filename,
            file_bytes=file_bytes,
            mime_type=payload.mime_type,
            pinecone_namespace=namespace
        )
        add_document_record(
            chat_id=chat_id,
            user_id=str(user['id']),
            filename=payload.filename,
            file_type=str(ingest_result.get('file_type', payload.filename.rsplit('.', 1)[-1])).lower(),
            file_size_bytes=payload.size_bytes or len(file_bytes),
            pinecone_namespace=namespace,
            chunk_count=int(ingest_result.get('chunk_count', 0)),
            status=str(ingest_result.get('status', 'uploaded')),
            error_message=ingest_result.get('error_message')
        )
    except Exception as exc:
        logger.exception('UPLOAD_ERROR type=%s message=%s', type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail='PDF upload failed. See server logs.') from exc

    return ApiEnvelope(data={'upload': ingest_result}).model_dump()
