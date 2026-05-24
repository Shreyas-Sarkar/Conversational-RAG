from __future__ import annotations

import hashlib
import io
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from PyPDF2 import PdfReader
from pinecone import Pinecone

from app.core.config import settings

ROOT_DIR = Path(__file__).resolve().parents[3]
UPLOADS_DIR = ROOT_DIR / "backend" / "uploaded_docs"
SUPABASE_STORAGE_BUCKET = "uploaded-docs"
_UPSERT_BATCH = 96  # Pinecone integrated embeddings max batch size


def _chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks: list[str] = []
    start, length = 0, len(cleaned)
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
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _pinecone_client() -> Pinecone:
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is required for uploads")
    return Pinecone(api_key=settings.pinecone_api_key)


def _ensure_index() -> None:
    """Guard: verify the integrated index exists.
    Never creates one — must be pre-configured with llama-text-embed-v2."""
    client = _pinecone_client()
    index_name = settings.pinecone_index_name
    if not index_name:
        raise RuntimeError("PINECONE_INDEX_NAME is required for uploads")
    if not client.has_index(index_name):
        raise RuntimeError(
            f"Pinecone index '{index_name}' does not exist. "
            "Create and configure it with llama-text-embed-v2 via configure_index() first."
        )


def _extract_text(file_bytes: bytes, filename: str, mime_type: str | None) -> str:
    if filename.lower().endswith(".pdf") or (mime_type or "").lower() == "application/pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(
            page_text
            for page_text in (page.extract_text() or "" for page in reader.pages)
            if page_text.strip()
        )
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _store_upload_in_cloud(
    *, user_id: str, chat_id: str, filename: str, file_bytes: bytes
) -> str | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    object_path = f"{user_id}/{chat_id}/{filename}"
    url = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object"
        f"/{SUPABASE_STORAGE_BUCKET}/{quote(object_path, safe='/')}"
    )
    req = Request(
        url,
        data=file_bytes,
        headers={
            "Content-Type": "application/octet-stream",
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30):
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
    pinecone_namespace: str,
) -> dict[str, object]:
    _ensure_index()
    document_id = _sha256_text(
        f"{user_id}|{chat_id}|{filename}|{len(file_bytes)}"
        f"|{hashlib.sha256(file_bytes).hexdigest()}"
    )
    target_dir = UPLOADS_DIR / user_id / chat_id
    target_dir.mkdir(parents=True, exist_ok=True)
    cloud_path = _store_upload_in_cloud(
        user_id=user_id, chat_id=chat_id, filename=filename, file_bytes=file_bytes
    )
    if cloud_path is None:
        (target_dir / filename).write_bytes(file_bytes)

    text = _extract_text(file_bytes, filename, mime_type)
    chunks = _chunk_text(text)
    if not chunks:
        return {
            "document_id": document_id,
            "filename": filename,
            "file_type": (mime_type or filename.rsplit(".", 1)[-1]).lower(),
            "file_size_bytes": len(file_bytes),
            "status": "failed",
            "progress_stage": "failed",
            "stages": ["uploaded", "chunking", "embedding", "indexing", "ready"],
            "chunk_count": 0,
            "error_message": "Unable to extract text from the uploaded file.",
            "pinecone_namespace": pinecone_namespace,
        }

    index = _pinecone_client().Index(settings.pinecone_index_name)
    records = [
        {
            "_id": f"{document_id}:{i}",
            "chunk_text": chunk,        # field_map target — Pinecone embeds this field
            "text": chunk,              # legacy alias kept for retriever fallback
            "document_id": document_id,
            "document_name": filename,
            "page_number": 1,
            "chunk_index": i,
            "source_path": str(target_dir / filename),
            "namespace": pinecone_namespace,
        }
        for i, chunk in enumerate(chunks, start=1)
    ]
    for batch_start in range(0, len(records), _UPSERT_BATCH):
        index.upsert_records(
            namespace=pinecone_namespace,
            records=records[batch_start : batch_start + _UPSERT_BATCH],
        )

    return {
        "document_id": document_id,
        "filename": filename,
        "file_type": (mime_type or filename.rsplit(".", 1)[-1]).lower(),
        "file_size_bytes": len(file_bytes),
        "status": "ready",
        "progress_stage": "ready",
        "stages": ["uploaded", "chunking", "embedding", "indexing", "ready"],
        "chunk_count": len(chunks),
        "error_message": None,
        "pinecone_namespace": pinecone_namespace,
        "storage_path": cloud_path or str(target_dir / filename),
    }
