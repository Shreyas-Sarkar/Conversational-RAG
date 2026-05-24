from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any

from app.core.config import settings
from app.rag.memory import summarize_chat_memory

ROOT_DIR = Path(__file__).resolve().parents[3]
WORKSPACE_STATE_FILE = ROOT_DIR / 'backend' / 'workspace_state.json'

DEFAULT_STATE: dict[str, Any] = {
    'users': {},
    'sessions': {},
    'chats': {},
    'messages': {},
    'documents': {},
    'query_cache': {}
}


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


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _new_id() -> str:
    return str(uuid.uuid4())


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except Exception:
        return False


def _cloud_enabled() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key)


def _supabase_request(method: str, path: str, payload: Any | None = None, params: dict[str, object] | None = None) -> Any:
    if not _cloud_enabled():
        raise RuntimeError('Supabase is not configured.')

    url = f"{settings.supabase_url.rstrip('/')}{path}"
    if params:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        if query:
            url = f'{url}?{query}'

    headers = {
        'apikey': settings.supabase_service_role_key,
        'Authorization': f'Bearer {settings.supabase_service_role_key}',
        'Accept': 'application/json'
    }
    data = None
    if payload is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(payload).encode('utf-8')

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode('utf-8')
            return json.loads(body) if body else []
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        raise ValueError(body or exc.reason) from exc


def _select_rows(table: str, filters: dict[str, object] | None = None, order: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, object] = {'select': '*'}
    if filters:
        params.update(filters)
    if order:
        params['order'] = order
    rows = _supabase_request('GET', f'/rest/v1/{table}', params=params)
    return rows if isinstance(rows, list) else []


def _insert_row(table: str, row: dict[str, Any], *, returning: bool = True) -> dict[str, Any]:
    headers_params = 'return=representation' if returning else 'return=minimal'
    result = _supabase_request('POST', f'/rest/v1/{table}', payload=row, params=None)
    return result[0] if isinstance(result, list) and result else row


def _upsert_row(table: str, row: dict[str, Any], conflict: str = 'id', bearer_token: str | None = None) -> dict[str, Any]:
    url_path = f'/rest/v1/{table}?on_conflict={conflict}'
    url = f"{settings.supabase_url.rstrip('/')}{url_path}"
    headers = {
        'apikey': settings.supabase_service_role_key,
        'Authorization': f"Bearer {bearer_token or settings.supabase_service_role_key}",
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Prefer': 'resolution=merge-duplicates,return=representation'
    }
    request = Request(url, data=json.dumps([row]).encode('utf-8'), headers=headers, method='POST')
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode('utf-8')
            payload = json.loads(body) if body else []
            return payload[0] if isinstance(payload, list) and payload else row
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        raise ValueError(body or exc.reason) from exc


def _delete_rows(table: str, filters: dict[str, object]) -> None:
    _supabase_request('DELETE', f'/rest/v1/{table}', params=filters)


def _cloud_user_row(user_id: str) -> dict[str, Any] | None:
    rows = _select_rows('users', {'id': f'eq.{user_id}'})
    return rows[0] if rows else None


def _cloud_chat_row(chat_id: str) -> dict[str, Any] | None:
    if not is_uuid(chat_id):
        return None
    rows = _select_rows('chats', {'id': f'eq.{chat_id}'})
    return rows[0] if rows else None


def _cloud_chats_for_user(user_id: str) -> list[dict[str, Any]]:
    return _select_rows('chats', {'user_id': f'eq.{user_id}'}, order='updated_at.desc')


def _cloud_messages_for_chat(chat_id: str) -> list[dict[str, Any]]:
    if not is_uuid(chat_id):
        return []
    return _select_rows('messages', {'chat_id': f'eq.{chat_id}'}, order='created_at.asc')


def _cloud_documents_for_chat(chat_id: str) -> list[dict[str, Any]]:
    if not is_uuid(chat_id):
        return []
    return _select_rows('documents', {'chat_id': f'eq.{chat_id}'}, order='created_at.asc')


def _cloud_query_cache(chat_id: str, query_hash: str) -> list[dict[str, Any]]:
    if not is_uuid(chat_id):
        return []
    return _select_rows('query_cache', {'chat_id': f'eq.{chat_id}', 'query_hash': f'eq.{query_hash}'}, order='created_at.desc')


def _cloud_counts_for_user(user_id: str) -> tuple[int, int, int, int]:
    if not is_uuid(user_id):
        return 0, 0, 0, 0
    chats = _cloud_chats_for_user(user_id)
    chat_ids = [chat['id'] for chat in chats]
    messages = [row for row in _select_rows('messages', {'user_id': f'eq.{user_id}'}) if str(row.get('chat_id')) in chat_ids]
    documents = [row for row in _select_rows('documents', {'user_id': f'eq.{user_id}'}) if str(row.get('chat_id')) in chat_ids]
    cache_entries = [row for row in _select_rows('query_cache', {'user_id': f'eq.{user_id}'}) if str(row.get('chat_id')) in chat_ids]
    return len(chats), len(documents), len(messages), len(cache_entries)


def _normalize_state(raw_state: Any) -> dict[str, Any]:
    state = dict(DEFAULT_STATE)
    if isinstance(raw_state, dict):
        state.update({key: raw_state.get(key, default) for key, default in DEFAULT_STATE.items()})
    for key in ('users', 'sessions', 'chats', 'messages', 'documents', 'query_cache'):
        if not isinstance(state.get(key), dict):
            state[key] = {}
    return state


def load_workspace_state() -> dict[str, Any]:
    if _cloud_enabled():
        # Aggregate Supabase rows into the same shape as the local workspace state
        state: dict[str, Any] = {key: {} if key != 'sessions' else {} for key in DEFAULT_STATE.keys()}

        try:
            users = _select_rows('users', {'select': '*'})
            chats = _select_rows('chats', {'select': '*', 'order': 'created_at.asc'})
            messages = _select_rows('messages', {'select': '*', 'order': 'created_at.asc'})
            documents = _select_rows('documents', {'select': '*', 'order': 'created_at.asc'})
            query_cache = _select_rows('query_cache', {'select': '*'})

            for u in users:
                user_id = str(u.get('id'))
                state['users'][user_id] = dict(u)

            for c in chats:
                chat_id = str(c.get('id'))
                state['chats'][chat_id] = dict(c)

            # messages grouped by chat_id
            for m in messages:
                chat_id = str(m.get('chat_id'))
                state['messages'].setdefault(chat_id, []).append(dict(m))

            # documents grouped by chat_id
            for d in documents:
                chat_id = str(d.get('chat_id'))
                state['documents'].setdefault(chat_id, []).append(dict(d))

            # query_cache keyed by chat_id:query_hash similar to local shape
            for q in query_cache:
                chat_id = str(q.get('chat_id'))
                query_hash = str(q.get('query_hash'))
                state['query_cache'][f'{chat_id}:{query_hash}'] = dict(q)

            return _normalize_state(state)
        except Exception:
            # fall back to empty normalized state on error
            return _normalize_state(DEFAULT_STATE)

    return _normalize_state(_load_json(WORKSPACE_STATE_FILE, DEFAULT_STATE))


def save_workspace_state(state: dict[str, Any]) -> None:
    # When running in cloud mode, do not persist local JSON state.
    if _cloud_enabled():
        return
    _save_json(WORKSPACE_STATE_FILE, _normalize_state(state))


def _serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'is_demo': bool(user.get('is_demo', False)),
        'created_at': user.get('created_at')
    }


def _serialize_chat(chat: dict[str, Any], message_count: int, document_count: int) -> dict[str, Any]:
    return {
        'id': chat['id'],
        'user_id': chat['user_id'],
        'title': chat['title'],
        'pinned': bool(chat.get('pinned', False)),
        'memory_summary': chat.get('memory_summary'),
        'namespace': chat.get('namespace'),
        'is_demo': bool(chat.get('is_demo', False)),
        'created_at': chat.get('created_at'),
        'updated_at': chat.get('updated_at'),
        'message_count': message_count,
        'document_count': document_count
    }


def _serialize_document(document: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': document['id'],
        'chat_id': document['chat_id'],
        'user_id': document['user_id'],
        'display_name': document.get('display_name') or document.get('original_filename') or document['filename'],
        'original_filename': document.get('original_filename') or document['filename'],
        'filename': document['filename'],
        'file_type': document['file_type'],
        'file_size_bytes': int(document.get('file_size_bytes', 0)),
        'status': document.get('status', 'uploaded'),
        'pinecone_namespace': document.get('pinecone_namespace', ''),
        'chunk_count': int(document.get('chunk_count', 0)),
        'error_message': document.get('error_message'),
        'is_demo': bool(document.get('is_demo', False)),
        'created_at': document.get('created_at'),
        'updated_at': document.get('updated_at')
    }


def _get_user_by_email(state: dict[str, Any], email: str) -> dict[str, Any] | None:
    normalized = email.strip().lower()
    for user in state['users'].values():
        if str(user.get('email', '')).strip().lower() == normalized:
            return user
    return None


def _get_user_by_session(state: dict[str, Any], session_token: str) -> dict[str, Any] | None:
    user_id = state['sessions'].get(session_token)
    if not user_id:
        return None
    user = state['users'].get(user_id)
    return user if isinstance(user, dict) else None


def create_session(user_id: str) -> dict[str, str]:
    state = load_workspace_state()
    session_token = f'session_{_new_id()}'
    state['sessions'][session_token] = user_id
    save_workspace_state(state)
    return {'token': session_token, 'mode': 'authenticated', 'user_id': user_id}


def get_user_from_session(session_token: str) -> dict[str, Any] | None:
    state = load_workspace_state()
    user = _get_user_by_session(state, session_token)
    return _serialize_user(user) if user else None


def create_default_chat(state: dict[str, Any], user_id: str, title: str = 'My Workspace') -> dict[str, Any]:
    if _cloud_enabled():
        chat_id = _new_id()
        chat = _upsert_row(
            'chats',
            {
                'id': chat_id,
                'user_id': user_id,
                'title': title,
                'pinned': True,
                'memory_summary': 'Upload documents and start asking questions.',
                'namespace': f'{user_id}_{chat_id}',
                'is_demo': False
            }
        )
        return chat

    chat_id = _new_id()
    chat = {
        'id': chat_id,
        'user_id': user_id,
        'title': title,
        'pinned': True,
        'memory_summary': 'Upload documents and start asking questions.',
        'namespace': f'{user_id}_{chat_id}',
        'is_demo': False,
        'created_at': _now_iso(),
        'updated_at': _now_iso()
    }
    state['chats'][chat_id] = chat
    state['messages'][chat_id] = []
    state['documents'][chat_id] = []
    return chat


def register_user_record(user_id: str, name: str, email: str, bearer_token: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if _cloud_enabled():
        user = _upsert_row(
            'users',
            {
                'id': user_id,
                'name': name.strip(),
                'email': email.strip().lower(),
                'is_demo': False
            },
            bearer_token=bearer_token
        )
        chats = _cloud_chats_for_user(user_id)
        default_chat = chats[0] if chats else create_default_chat({}, user_id)
        return _serialize_user(user), default_chat

    state = load_workspace_state()
    user = state['users'].get(user_id)
    if not isinstance(user, dict):
        user = {
            'id': user_id,
            'name': name.strip(),
            'email': email.strip().lower(),
            'password_hash': '',
            'is_demo': False,
            'created_at': _now_iso()
        }
        state['users'][user_id] = user
    else:
        user['name'] = name.strip() or str(user.get('name', ''))
        user['email'] = email.strip().lower() or str(user.get('email', '')).lower()
        state['users'][user_id] = user

    chats = [chat for chat in state['chats'].values() if str(chat.get('user_id')) == user_id]
    default_chat = chats[0] if chats else create_default_chat(state, user_id)
    save_workspace_state(state)
    return _serialize_user(user), default_chat


def create_user(name: str, email: str, password: str) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    state = load_workspace_state()
    existing_user = _get_user_by_email(state, email)
    if existing_user:
        raise ValueError('An account with this email already exists.')

    user_id = _new_id()
    user = {
        'id': user_id,
        'name': name.strip(),
        'email': email.strip().lower(),
        'password_hash': _hash_password(password),
        'is_demo': False,
        'created_at': _now_iso()
    }
    state['users'][user_id] = user
    default_chat = create_default_chat(state, user_id)
    save_workspace_state(state)
    session = create_session(user_id)
    return _serialize_user(user), session, default_chat


def authenticate_user(email: str, password: str) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    state = load_workspace_state()
    user = _get_user_by_email(state, email)
    if not user:
        raise ValueError('Invalid email or password.')
    if user.get('password_hash') != _hash_password(password):
        raise ValueError('Invalid email or password.')

    user_id = str(user['id'])
    chats = list_user_chats(user_id)
    if not chats:
        state = load_workspace_state()
        create_default_chat(state, user_id)
        save_workspace_state(state)
        chats = list_user_chats(user_id)

    session = create_session(user_id)
    return _serialize_user(user), session, chats[0]


def list_user_chats(user_id: str) -> list[dict[str, Any]]:
    if _cloud_enabled():
        chats = _cloud_chats_for_user(user_id)
        messages_by_chat: dict[str, int] = {}
        documents_by_chat: dict[str, int] = {}
        for message in _select_rows('messages', {'user_id': f'eq.{user_id}'}, order='created_at.asc'):
            chat_key = str(message.get('chat_id'))
            messages_by_chat[chat_key] = messages_by_chat.get(chat_key, 0) + 1
        for document in _select_rows('documents', {'user_id': f'eq.{user_id}'}, order='created_at.asc'):
            chat_key = str(document.get('chat_id'))
            documents_by_chat[chat_key] = documents_by_chat.get(chat_key, 0) + 1
        serialized = [
            _serialize_chat(chat, messages_by_chat.get(str(chat['id']), 0), documents_by_chat.get(str(chat['id']), 0))
            for chat in chats
        ]
        serialized.sort(key=lambda item: item.get('updated_at') or item.get('created_at') or '', reverse=True)
        return serialized

    state = load_workspace_state()
    chats = []
    for chat in state['chats'].values():
        if str(chat.get('user_id')) != user_id:
            continue
        messages = state['messages'].get(chat['id'], [])
        documents = state['documents'].get(chat['id'], [])
        chats.append(_serialize_chat(chat, len(messages), len(documents)))
    chats.sort(key=lambda item: item.get('updated_at') or item.get('created_at') or '', reverse=True)
    return chats


def get_chat(chat_id: str) -> dict[str, Any] | None:
    if _cloud_enabled():
        chat = _cloud_chat_row(chat_id)
        if not isinstance(chat, dict):
            return None
        messages = _cloud_messages_for_chat(chat_id)
        documents = _cloud_documents_for_chat(chat_id)
        return {
            'chat': _serialize_chat(chat, len(messages), len(documents)),
            'messages': messages,
            'documents': [_serialize_document(document) for document in documents]
        }

    state = load_workspace_state()
    chat = state['chats'].get(chat_id)
    if not isinstance(chat, dict):
        return None
    messages = state['messages'].get(chat_id, [])
    documents = state['documents'].get(chat_id, [])
    return {
        'chat': _serialize_chat(chat, len(messages), len(documents)),
        'messages': messages,
        'documents': [_serialize_document(document) for document in documents]
    }


def get_chat_namespace(chat_id: str) -> str:
    if _cloud_enabled():
        chat = _cloud_chat_row(chat_id)
        if isinstance(chat, dict):
            return str(chat.get('namespace', '') or '').replace('/', '_')
        return ''

    state = load_workspace_state()
    chat = state['chats'].get(chat_id)
    if isinstance(chat, dict):
        return str(chat.get('namespace', '') or '').replace('/', '_')
    return ''


def get_chat_memory_summary(chat_id: str) -> str:
    if _cloud_enabled():
        chat = _cloud_chat_row(chat_id)
        if isinstance(chat, dict):
            return str(chat.get('memory_summary', '') or '')
        return ''

    state = load_workspace_state()
    chat = state['chats'].get(chat_id)
    if isinstance(chat, dict):
        return str(chat.get('memory_summary', '') or '')
    return ''


def get_chat_history(chat_id: str) -> list[dict[str, Any]]:
    if _cloud_enabled() and is_uuid(chat_id):
        return _cloud_messages_for_chat(chat_id)

    state = load_workspace_state()
    messages = state['messages'].get(chat_id, [])
    return list(messages) if isinstance(messages, list) else []


def set_chat_history(chat_id: str, messages: list[dict[str, Any]]) -> None:
    if _cloud_enabled() and is_uuid(chat_id):
        chat = _cloud_chat_row(chat_id)
        if not isinstance(chat, dict):
            return
        _delete_rows('messages', {'chat_id': f'eq.{chat_id}'})
        persisted_messages: list[dict[str, Any]] = []
        for message in messages:
            persisted_message = dict(message)
            persisted_message['chat_id'] = chat_id
            persisted_message['user_id'] = str(chat.get('user_id'))
            persisted_messages.append(persisted_message)
        for message in persisted_messages:
            _upsert_row('messages', message)
        _upsert_row(
            'chats',
            {
                'id': chat_id,
                'user_id': str(chat.get('user_id')),
                'title': str(chat.get('title', 'My Workspace')),
                'pinned': bool(chat.get('pinned', False)),
                'memory_summary': summarize_chat_memory(chat_id, messages[-6:]) or str(chat.get('memory_summary', '')),
                'namespace': str(chat.get('namespace', '')),
                'is_demo': bool(chat.get('is_demo', False))
            }
        )
        return

    state = load_workspace_state()
    state['messages'][chat_id] = list(messages)
    chat = state['chats'].get(chat_id)
    if isinstance(chat, dict):
        chat['memory_summary'] = summarize_chat_memory(chat_id, messages[-6:]) or chat.get('memory_summary', '')
        chat['updated_at'] = _now_iso()
        state['chats'][chat_id] = chat
    save_workspace_state(state)


def append_chat_message(chat_id: str, message: dict[str, Any]) -> None:
    messages = get_chat_history(chat_id)
    messages.append(message)
    set_chat_history(chat_id, messages)


def persist_chat_turn(chat_id: str, user_message: dict[str, Any], assistant_message: dict[str, Any]) -> None:
    append_chat_message(chat_id, user_message)
    append_chat_message(chat_id, assistant_message)


def clear_chat_history(chat_id: str) -> None:
    if _cloud_enabled():
        chat = _cloud_chat_row(chat_id)
        if isinstance(chat, dict):
            _delete_rows('messages', {'chat_id': f'eq.{chat_id}'})
            _upsert_row(
                'chats',
                {
                    'id': chat_id,
                    'user_id': str(chat.get('user_id')),
                    'title': str(chat.get('title', 'My Workspace')),
                    'pinned': bool(chat.get('pinned', False)),
                    'memory_summary': 'Conversation history cleared.',
                    'namespace': str(chat.get('namespace', '')),
                    'is_demo': bool(chat.get('is_demo', False))
                }
            )
        return

    state = load_workspace_state()
    state['messages'][chat_id] = []
    chat = state['chats'].get(chat_id)
    if isinstance(chat, dict):
        chat['memory_summary'] = 'Conversation history cleared.'
        chat['updated_at'] = _now_iso()
        state['chats'][chat_id] = chat
    save_workspace_state(state)


def add_document_record(
    chat_id: str,
    user_id: str,
    filename: str,
    file_type: str,
    file_size_bytes: int,
    pinecone_namespace: str,
    chunk_count: int,
    status: str = 'ready',
    error_message: str | None = None,
    is_demo: bool = False,
    original_filename: str | None = None,
    display_name: str | None = None
) -> dict[str, Any]:
    if _cloud_enabled() and is_uuid(chat_id):
        document = _upsert_row(
            'documents',
            {
                'id': _new_id(),
                'chat_id': chat_id,
                'user_id': user_id,
                'filename': filename,
                'display_name': display_name or original_filename or filename,
                'original_filename': original_filename or filename,
                'file_type': file_type,
                'file_size_bytes': int(file_size_bytes),
                'status': status,
                'pinecone_namespace': pinecone_namespace,
                'chunk_count': int(chunk_count),
                'error_message': error_message,
                'is_demo': is_demo
            }
        )
        return _serialize_document(document)

    state = load_workspace_state()
    document = {
        'id': _new_id(),
        'chat_id': chat_id,
        'user_id': user_id,
        'filename': filename,
        'original_filename': original_filename or filename,
        'display_name': display_name or original_filename or filename,
        'file_type': file_type,
        'file_size_bytes': int(file_size_bytes),
        'status': status,
        'pinecone_namespace': pinecone_namespace,
        'chunk_count': int(chunk_count),
        'error_message': error_message,
        'is_demo': is_demo,
        'created_at': _now_iso(),
        'updated_at': _now_iso()
    }
    state['documents'].setdefault(chat_id, []).append(document)
    chat = state['chats'].get(chat_id)
    if isinstance(chat, dict):
        chat['updated_at'] = _now_iso()
        state['chats'][chat_id] = chat
    save_workspace_state(state)
    return _serialize_document(document)


def list_documents(chat_id: str) -> list[dict[str, Any]]:
    if _cloud_enabled() and is_uuid(chat_id):
        return [_serialize_document(document) for document in _cloud_documents_for_chat(chat_id)]

    state = load_workspace_state()
    documents = state['documents'].get(chat_id, [])
    if not isinstance(documents, list):
        return []
    return [_serialize_document(document) for document in documents]


def cache_query(
    user_id: str,
    chat_id: str,
    query_hash: str,
    response_text: str,
    sources: list[dict[str, Any]],
    ttl_seconds: int = 3600
) -> dict[str, Any]:
    if _cloud_enabled() and is_uuid(chat_id):
        record = _upsert_row(
            'query_cache',
            {
                'id': _new_id(),
                'user_id': user_id,
                'chat_id': chat_id,
                'query_hash': query_hash,
                'response_text': response_text,
                'sources': sources,
                'ttl_expires_at': (_now() + timedelta(seconds=ttl_seconds)).isoformat()
            }
        )
        return record

    state = load_workspace_state()
    record = {
        'id': _new_id(),
        'user_id': user_id,
        'chat_id': chat_id,
        'query_hash': query_hash,
        'response_text': response_text,
        'sources': sources,
        'ttl_expires_at': (_now() + timedelta(seconds=ttl_seconds)).isoformat(),
        'created_at': _now_iso()
    }
    state['query_cache'][f'{chat_id}:{query_hash}'] = record
    save_workspace_state(state)
    return record


def get_cached_query(chat_id: str, query_hash: str) -> dict[str, Any] | None:
    if _cloud_enabled() and is_uuid(chat_id):
        records = _cloud_query_cache(chat_id, query_hash)
        if not records:
            return None
        record = records[0]
        expires_at = record.get('ttl_expires_at')
        if expires_at:
            try:
                if datetime.fromisoformat(str(expires_at)) < _now():
                    _delete_rows('query_cache', {'id': f'eq.{record["id"]}'})
                    return None
            except ValueError:
                return None
        return record

    state = load_workspace_state()
    record = state['query_cache'].get(f'{chat_id}:{query_hash}')
    if not isinstance(record, dict):
        return None
    expires_at = record.get('ttl_expires_at')
    if expires_at:
        try:
            if datetime.fromisoformat(str(expires_at)) < _now():
                state['query_cache'].pop(f'{chat_id}:{query_hash}', None)
                save_workspace_state(state)
                return None
        except ValueError:
            return None
    return record


def get_workspace_metrics(user_id: str) -> dict[str, object]:
    if _cloud_enabled():
        chat_count, document_count, message_count, cache_count = _cloud_counts_for_user(user_id)
        chats = list_user_chats(user_id)
        return {
            'chat_count': chat_count,
            'document_count': document_count,
            'message_count': message_count,
            'cache_entries': cache_count,
            'active_chats': [chat['id'] for chat in chats[:5]],
            'last_updated_at': chats[0]['updated_at'] if chats else None
        }

    chats = list_user_chats(user_id)
    state = load_workspace_state()
    document_count = sum(len(state['documents'].get(chat['id'], [])) for chat in chats)
    message_count = sum(len(state['messages'].get(chat['id'], [])) for chat in chats)
    cache_count = sum(1 for record in state['query_cache'].values() if record.get('user_id') == user_id)
    return {
        'chat_count': len(chats),
        'document_count': document_count,
        'message_count': message_count,
        'cache_entries': cache_count,
        'active_chats': [chat['id'] for chat in chats[:5]],
        'last_updated_at': chats[0]['updated_at'] if chats else None
    }


def bootstrap_workspace(user_id: str) -> dict[str, object]:
    if _cloud_enabled():
        user = _cloud_user_row(user_id)
        if not isinstance(user, dict):
            raise ValueError('User not found.')

        chats = list_user_chats(user_id)
        if not chats:
            create_default_chat({}, user_id)
            chats = list_user_chats(user_id)

        return {
            'user': _serialize_user(user),
            'chats': chats,
            'metrics': get_workspace_metrics(user_id),
            'default_chat_id': chats[0]['id'] if chats else None,
            'profile_menu': [
                {'label': 'Profile settings', 'href': '/workspace/settings'},
                {'label': 'Billing', 'href': '/workspace/settings#billing'},
                {'label': 'Sign out', 'action': 'logout'}
            ]
        }

    state = load_workspace_state()
    user = state['users'].get(user_id)
    if not isinstance(user, dict):
        raise ValueError('User not found.')

    chats = list_user_chats(user_id)
    if not chats:
        state = load_workspace_state()
        create_default_chat(state, user_id)
        save_workspace_state(state)
        chats = list_user_chats(user_id)

    return {
        'user': _serialize_user(user),
        'chats': chats,
        'metrics': get_workspace_metrics(user_id),
        'default_chat_id': chats[0]['id'] if chats else None,
        'profile_menu': [
            {'label': 'Profile settings', 'href': '/workspace/settings'},
            {'label': 'Billing', 'href': '/workspace/settings#billing'},
            {'label': 'Sign out', 'action': 'logout'}
        ]
    }
