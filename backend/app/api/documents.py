import base64
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.schemas import ApiEnvelope, DocumentUploadResponseData
from app.services.auth_service import resolve_session
from app.services.document_ingest_service import ingest_uploaded_document
from app.services.workspace_store import add_document_record, get_chat_namespace, list_documents

router = APIRouter(tags=['documents'])
logger = logging.getLogger(__name__)


class UploadRequest(BaseModel):
    session_token: str
    chat_id: str
    filename: str
    content_base64: str
    mime_type: str | None = None
    size_bytes: int | None = None


@router.post('/upload')
def upload_document(payload: UploadRequest) -> dict[str, object]:
    user = resolve_session(payload.session_token)
    if not user:
        raise HTTPException(status_code=401, detail='Invalid session token.')

    try:
        file_bytes = base64.b64decode(payload.content_base64.encode('utf-8'))
    except Exception as exc:
        raise HTTPException(status_code=400, detail='Invalid file payload.') from exc

    namespace = get_chat_namespace(payload.chat_id) or f"{str(user['id'])}/{payload.chat_id}"
    try:
        ingest_result = ingest_uploaded_document(
            user_id=str(user['id']),
            chat_id=payload.chat_id,
            filename=payload.filename,
            file_bytes=file_bytes,
            mime_type=payload.mime_type,
            pinecone_namespace=namespace
        )
        document = add_document_record(
            chat_id=payload.chat_id,
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

    return ApiEnvelope(
        data=DocumentUploadResponseData(
            document_id=str(document['id']),
            chat_id=payload.chat_id,
            filename=payload.filename,
            status=str(document.get('status', 'uploaded')),
            progress_stage=str(ingest_result.get('progress_stage', 'uploaded')),
            stages=list(ingest_result.get('stages', ['uploaded', 'chunking', 'embedding', 'indexing', 'ready']))
        ).model_dump()
    ).model_dump()


@router.get('/documents')
def documents(chat_id: str) -> dict[str, object]:
    return ApiEnvelope(data={'documents': list_documents(chat_id)}).model_dump()
