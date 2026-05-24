from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from PyPDF2 import PdfReader
from pinecone import Pinecone

from app.core.config import settings

ROOT_DIR = Path(__file__).resolve().parents[3]
DEMO_DOCS_DIR = ROOT_DIR / 'demo_docs'
INDEX_STATE_FILE = ROOT_DIR / 'backend' / 'demo_index.json'
MANIFEST_FILE = ROOT_DIR / 'backend' / 'demo_ingest_manifest.json'
DEMO_CHATS_FILE = ROOT_DIR / 'backend' / 'demo_chats.json'

NAMESPACE_BY_FOLDER = {
    'oracle': 'demo_oracle',
    'compliance': 'demo_compliance',
    'research': 'demo_research',
    'resume': 'demo_resume'
}

CHAT_SEED_DATA = {
    'demo_oracle': {
        'chat_id': 'oracle-fusion-migration-docs',
        'title': 'Oracle Fusion Migration Docs',
        'namespace': 'demo_oracle',
        'prompts': [
            'Explain Oracle migration',
            'What are implementation users?',
            'Summarize integration workflow'
        ]
    },
    'demo_compliance': {
        'chat_id': 'compliance-handbook',
        'title': 'Compliance Handbook',
        'namespace': 'demo_compliance',
        'prompts': [
            'Explain SOC2',
            'What is ITGC?',
            'Summarize SOX'
        ]
    },
    'demo_research': {
        'chat_id': 'research-papers',
        'title': 'Research Papers',
        'namespace': 'demo_research',
        'prompts': [
            'Compare RAG and Transformers',
            'Explain LoRA',
            'Summarize Attention Is All You Need'
        ]
    },
    'demo_resume': {
        'chat_id': 'resume-job-description-analysis',
        'title': 'Resume + JD Analysis',
        'namespace': 'demo_resume',
        'prompts': [
            'What skills are missing?',
            'How well does resume match JD?'
        ]
    }
}


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    source_path: str
    namespace: str
    text: str
    file_digest: str


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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


def _extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ''
        if text.strip():
            pages.append((page_number, text))
    return pages


@lru_cache(maxsize=1)
def _pinecone_client() -> Pinecone:
    if not settings.pinecone_api_key:
        raise RuntimeError('PINECONE_API_KEY is required for demo ingestion')
    return Pinecone(api_key=settings.pinecone_api_key)


def _ensure_index() -> None:
    """Guard: verify the integrated index exists. Never creates one."""
    client = _pinecone_client()
    index_name = settings.pinecone_index_name
    if not index_name:
        raise RuntimeError('PINECONE_INDEX_NAME is required for demo ingestion')
    if not client.has_index(index_name):
        raise RuntimeError(
            f"Pinecone index '{index_name}' does not exist. "
            "Configure it with llama-text-embed-v2 via configure_index() first."
        )


def _index_state() -> dict[str, bool]:
    state = _load_json(INDEX_STATE_FILE, {})
    return {namespace: bool(state.get(namespace, False)) for namespace in NAMESPACE_BY_FOLDER.values()}


def _manifest() -> dict[str, dict[str, dict[str, Any]]]:
    manifest = _load_json(MANIFEST_FILE, {})
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    for namespace in NAMESPACE_BY_FOLDER.values():
        normalized[namespace] = dict(manifest.get(namespace, {}))
    return normalized


def _discover_files() -> dict[str, list[Path]]:
    discovered: dict[str, list[Path]] = {}
    for folder_name, namespace in NAMESPACE_BY_FOLDER.items():
        folder_path = DEMO_DOCS_DIR / folder_name
        files = []
        if folder_path.exists():
            files = sorted([path for path in folder_path.rglob('*.pdf') if path.is_file()])
        discovered[namespace] = files
    return discovered


def _build_indexed_chunks(namespace: str, pdf_path: Path) -> list[IndexedChunk]:
    digest = _sha256_file(pdf_path)
    source_path = str(pdf_path.relative_to(ROOT_DIR))
    document_name = pdf_path.name
    document_id = _sha256_text(f'{namespace}|{source_path}|{digest}')
    chunks: list[IndexedChunk] = []

    for page_number, page_text in _extract_pdf_pages(pdf_path):
        page_chunks = _chunk_text(page_text)
        for chunk_index, chunk_text in enumerate(page_chunks):
            chunk_id_source = f'{namespace}|{source_path}|{page_number}|{chunk_index}|{digest}'
            chunk_id = _sha256_text(chunk_id_source)
            chunks.append(
                IndexedChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    source_path=source_path,
                    namespace=namespace,
                    text=chunk_text,
                    file_digest=digest
                )
            )
    return chunks


_UPSERT_BATCH = 96  # Pinecone integrated embeddings max batch size


def _upsert_namespace(namespace: str, chunks: list[IndexedChunk]) -> int:
    if not chunks:
        return 0

    client = _pinecone_client()
    index = client.Index(settings.pinecone_index_name)

    records = [
        {
            '_id': chunk.chunk_id,
            'chunk_text': chunk.text,        # field_map target — Pinecone embeds this
            'text': chunk.text,              # legacy alias for retriever fallback
            'document_id': chunk.document_id,
            'document_name': chunk.document_name,
            'page_number': chunk.page_number,
            'chunk_index': chunk.chunk_index,
            'source_path': chunk.source_path,
            'namespace': chunk.namespace,
            'file_digest': chunk.file_digest,
        }
        for chunk in chunks
    ]
    for start in range(0, len(records), _UPSERT_BATCH):
        index.upsert_records(
            namespace=namespace,
            records=records[start : start + _UPSERT_BATCH],
        )
    return len(records)


def _write_demo_chat_seed_file() -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for namespace, seed in CHAT_SEED_DATA.items():
        payload[namespace] = {
            'chat_id': seed['chat_id'],
            'title': seed['title'],
            'namespace': seed['namespace'],
            'prompts': seed['prompts']
        }
    _save_json(DEMO_CHATS_FILE, payload)
    return payload


def index_demo_docs(force: bool = False) -> dict[str, Any]:
    """Index demo PDFs once into Pinecone and persist per-namespace state.

    The state file `backend/demo_index.json` stays intentionally simple:
    {"demo_oracle": true, "demo_compliance": true, ...}
    A separate manifest tracks already indexed source files so future additions can be detected
    without re-embedding files that were already ingested.
    """

    if not DEMO_DOCS_DIR.exists():
        return {'status': 'no_demo_docs', 'indexed': {}, 'uploaded': False}

    _ensure_index()

    state = _index_state()
    manifest = _manifest()
    discovered = _discover_files()

    indexed_counts: dict[str, int] = {}
    manifest_changed = False

    for namespace, files in discovered.items():
        namespace_manifest = manifest.setdefault(namespace, {})
        namespace_count = 0
        pending_chunks: list[IndexedChunk] = []

        for pdf_path in files:
            source_path = str(pdf_path.relative_to(ROOT_DIR))
            file_digest = _sha256_file(pdf_path)
            indexed_entry = namespace_manifest.get(source_path)

            if indexed_entry and not force:
                continue

            # Only index once unless force=True. New files get added, existing files are left untouched.
            file_chunks = _build_indexed_chunks(namespace, pdf_path)
            pending_chunks.extend(file_chunks)
            namespace_manifest[source_path] = {
                'file_digest': file_digest,
                'document_name': pdf_path.name,
                'indexed': True,
                'chunk_count': len(file_chunks)
            }
            namespace_count += len(file_chunks)
            manifest_changed = True

        if pending_chunks:
            uploaded = _upsert_namespace(namespace, pending_chunks)
            logging.info('Indexed: %s Chunks: %s Uploaded: success', namespace, uploaded)
        indexed_counts[namespace] = namespace_count
        state[namespace] = True

    _save_json(INDEX_STATE_FILE, state)
    if manifest_changed or not MANIFEST_FILE.exists():
        _save_json(MANIFEST_FILE, manifest)

    _write_demo_chat_seed_file()

    return {
        'status': 'indexed',
        'indexed': indexed_counts,
        'uploaded': True,
        'state_file': str(INDEX_STATE_FILE),
        'manifest_file': str(MANIFEST_FILE)
    }


def get_demo_namespace_for_chat(chat_id: str) -> str | None:
    for namespace, seed in CHAT_SEED_DATA.items():
        if seed['chat_id'] == chat_id:
            return namespace
    if chat_id.startswith('demo_'):
        return chat_id
    return None


def get_demo_chat_seed_payload() -> dict[str, Any]:
    if DEMO_CHATS_FILE.exists():
        return _load_json(DEMO_CHATS_FILE, {})
    return _write_demo_chat_seed_file()
