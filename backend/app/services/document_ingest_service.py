from __future__ import annotations

import hashlib
import io
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from PyPDF2 import PdfReader
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from app.core.config import settings

ROOT_DIR = Path(__file__).resolve().parents[3]
UPLOADS_DIR = ROOT_DIR / 'backend' / 'uploaded_docs'
SUPABASE_STORAGE_BUCKET = 'uploaded-docs'


def _chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    cleaned = ' '.join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - chunk_overlap, start + 1)
    return chunks


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


@lru_cache(maxsize=1)
def _embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


@lru_cache(maxsize=1)
def _pinecone_client() -> Pinecone:
    if not settings.pinecone_api_key:
        raise RuntimeError('PINECONE_API_KEY is required for uploads')
    return Pinecone(api_key=settings.pinecone_api_key)


def _ensure_index() -> None:
    client = _pinecone_client()
    index_name = settings.pinecone_index_name
    if not index_name:
        raise RuntimeError('PINECONE_INDEX_NAME is required for uploads')
    if client.has_index(index_name):
        return
    client.create_index(
        name=index_name,
        dimension=384,
        metric='cosine',
        spec=ServerlessSpec(cloud=settings.pinecone_cloud or 'aws', region=settings.pinecone_region or 'us-east-1')
    )


def _extract_text(file_bytes: bytes, filename: str, mime_type: str | None) -> str:
    lowered_name = filename.lower()
    lowered_mime = (mime_type or '').lower()

    if lowered_name.endswith('.pdf') or lowered_mime == 'application/pdf':
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or '' for page in reader.pages]
        return '\n'.join(page for page in pages if page.strip())

    try:
        return file_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return ''


def _store_upload_in_cloud(*, user_id: str, chat_id: str, filename: str, file_bytes: bytes) -> str | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None

    object_path = f'{user_id}/{chat_id}/{filename}'
    encoded_object_path = quote(object_path, safe='/')
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{encoded_object_path}"
    request = Request(
        url,
        data=file_bytes,
        headers={
            'Content-Type': 'application/octet-stream',
            'apikey': settings.supabase_service_role_key,
            'Authorization': f'Bearer {settings.supabase_service_role_key}',
            'x-upsert': 'true'
        },
        method='POST'
    )
    try:
        with urlopen(request, timeout=30):
            return object_path
    except HTTPError:
        return None


def ingest_uploaded_document(
    *,
    user_id: str,
    chat_id: str,
    filename: str,
    file_bytes: bytes,
    mime_type: str | None = None,
    pinecone_namespace: str
) -> dict[str, object]:
    _ensure_index()
    document_id = _sha256_text(f'{user_id}|{chat_id}|{filename}|{len(file_bytes)}|{hashlib.sha256(file_bytes).hexdigest()}')
    target_dir = UPLOADS_DIR / user_id / chat_id
    target_dir.mkdir(parents=True, exist_ok=True)
    cloud_path = _store_upload_in_cloud(user_id=user_id, chat_id=chat_id, filename=filename, file_bytes=file_bytes)
    if cloud_path is None:
        (target_dir / filename).write_bytes(file_bytes)

    text = _extract_text(file_bytes, filename, mime_type)
    chunks = _chunk_text(text)
    if not chunks:
        return {
            'document_id': document_id,
            'filename': filename,
            'file_type': (mime_type or filename.rsplit('.', 1)[-1]).lower(),
            'file_size_bytes': len(file_bytes),
            'status': 'failed',
            'progress_stage': 'failed',
            'stages': ['uploaded', 'chunking', 'embedding', 'indexing', 'ready'],
            'chunk_count': 0,
            'error_message': 'Unable to extract text from the uploaded file.',
            'pinecone_namespace': pinecone_namespace
        }

    model = _embedding_model()
    vectors = model.encode(chunks, show_progress_bar=False, normalize_embeddings=True)
    index = _pinecone_client().Index(settings.pinecone_index_name)

    upsert_payload = []
    for chunk_index, (chunk_text, vector) in enumerate(zip(chunks, vectors), start=1):
        upsert_payload.append(
            {
                'id': f'{document_id}:{chunk_index}',
                'values': vector.tolist() if hasattr(vector, 'tolist') else list(vector),
                'metadata': {
                    'document_id': document_id,
                    'document_name': filename,
                    'page_number': 1,
                    'chunk_index': chunk_index,
                    'source_path': str(target_dir / filename),
                    'namespace': pinecone_namespace,
                    'chunk_text': chunk_text,
                    'text': chunk_text
                }
            }
        )

    index.upsert(vectors=upsert_payload, namespace=pinecone_namespace)
    return {
        'document_id': document_id,
        'filename': filename,
        'file_type': (mime_type or filename.rsplit('.', 1)[-1]).lower(),
        'file_size_bytes': len(file_bytes),
        'status': 'ready',
        'progress_stage': 'ready',
        'stages': ['uploaded', 'chunking', 'embedding', 'indexing', 'ready'],
        'chunk_count': len(chunks),
        'error_message': None,
        'pinecone_namespace': pinecone_namespace,
        'storage_path': cloud_path or str(target_dir / filename)
    }
