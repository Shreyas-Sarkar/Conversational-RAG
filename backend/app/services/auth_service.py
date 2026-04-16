from __future__ import annotations

import json
import logging
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.core.config import settings
from app.services.workspace_store import authenticate_user, create_user, get_user_from_session
from app.services.workspace_store import create_session, create_default_chat, register_user_record, _select_rows


logger = logging.getLogger(__name__)


def _supabase_enabled() -> bool:
    return bool(settings.supabase_url and settings.supabase_anon_key)


def _supabase_request(path: str, payload: dict[str, object], *, bearer_token: str | None = None) -> dict[str, object]:
    url = f"{settings.supabase_url.rstrip('/')}" + path
    token = bearer_token or settings.supabase_anon_key
    request = Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'apikey': settings.supabase_anon_key,
            'Authorization': f'Bearer {token}'
        },
        method='POST'
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        raise ValueError(body or exc.reason) from exc


def _supabase_auth_user(bearer_token: str) -> dict[str, object] | None:
    if not settings.supabase_url:
        return None

    request = Request(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={
            'apikey': settings.supabase_anon_key,
            'Authorization': f'Bearer {bearer_token}'
        },
        method='GET'
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError:
        return None


def _extract_access_token(response: dict[str, object]) -> str:
    access_token = str(response.get('access_token') or '')
    if access_token:
        return access_token

    session = response.get('session')
    if isinstance(session, dict):
        access_token = str(session.get('access_token') or '')
        if access_token:
            return access_token

    raise ValueError('Supabase did not return an access token.')


def _supabase_rest_upsert_user(user_id: str, name: str, email: str, bearer_token: str | None = None) -> None:
    if not (settings.supabase_service_role_key or bearer_token):
        return

    url = f"{settings.supabase_url.rstrip('/')}" + '/rest/v1/users?on_conflict=id'
    request = Request(
        url,
        data=json.dumps([{'id': user_id, 'name': name, 'email': email, 'is_demo': False}]).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'apikey': settings.supabase_service_role_key,
            'Authorization': f"Bearer {bearer_token or settings.supabase_service_role_key}",
            'Prefer': 'resolution=merge-duplicates,return=representation'
        },
        method='POST'
    )
    try:
        with urlopen(request, timeout=20):
            return
    except HTTPError:
        return


def _verify_user_persisted(user_id: str) -> dict[str, object]:
    last_error: Exception | None = None
    for _ in range(3):
        try:
            rows = _select_rows('users', {'id': f'eq.{user_id}'})
            if rows:
                logger.info('USER UPSERT: PASS user_id=%s', user_id)
                return rows[0]
        except Exception as exc:
            last_error = exc
        time.sleep(0.4)

    logger.error('USER UPSERT: FAIL user_id=%s error=%s', user_id, last_error)
    raise RuntimeError('Failed to create user profile')


def _create_default_chat_with_retry(user_id: str) -> dict[str, object]:
    last_error: Exception | None = None
    for _ in range(5):
        try:
            chat = create_default_chat({}, user_id)
            logger.info('CHAT CREATE: PASS user_id=%s chat_id=%s', user_id, chat.get('id'))
            return chat
        except Exception as exc:
            last_error = exc
            message = str(exc)
            if 'chats_user_id_fkey' not in message and '23503' not in message:
                break
            time.sleep(0.4)

    logger.error('CHAT CREATE: FAIL user_id=%s error=%s', user_id, last_error)
    raise RuntimeError('Failed to create default chat')


def _supabase_admin_create_user(name: str, email: str, password: str) -> dict[str, object] | None:
    if not settings.supabase_service_role_key:
        return None

    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users"
    request = Request(
        url,
        data=json.dumps({
            'email': email,
            'password': password,
            'email_confirm': True,
            'user_metadata': {'name': name}
        }).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'apikey': settings.supabase_service_role_key,
            'Authorization': f'Bearer {settings.supabase_service_role_key}'
        },
        method='POST'
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        body = exc.read().decode('utf-8') if exc.fp else ''
        raise ValueError(body or exc.reason) from exc


def bootstrap_user(email: str) -> dict[str, str]:
    return {'email': email, 'status': 'stub'}


def signup_user(name: str, email: str, password: str) -> tuple[dict[str, object], dict[str, str], dict[str, object]]:
    if _supabase_enabled():
        response = _supabase_admin_create_user(name, email, password) if settings.supabase_service_role_key else None
        if response is None:
            response = _supabase_request('/auth/v1/signup', {
                'email': email,
                'password': password,
                'data': {'name': name}
            })
        if response is not None:
            user_payload = response.get('user') or response or {}
            user_id = str(user_payload.get('id', ''))
            if user_id:
                access_token = str(response.get('access_token') or '')
                if not access_token:
                    login_response = _supabase_request('/auth/v1/token?grant_type=password', {
                        'email': email,
                        'password': password
                    })
                    access_token = _extract_access_token(login_response)
                _supabase_rest_upsert_user(user_id, name, email)
                verified_user = _verify_user_persisted(user_id)
                logger.info('CHAT CREATE: SKIPPED signup user_id=%s (login will create first chat if needed)', user_id)
                session = {'token': access_token, 'mode': 'authenticated', 'user_id': user_id}
                return {
                    'id': str(verified_user.get('id', user_id)),
                    'name': str(verified_user.get('name', name)),
                    'email': str(verified_user.get('email', email)),
                    'is_demo': bool(verified_user.get('is_demo', False)),
                    'created_at': verified_user.get('created_at')
                }, session, {'id': None}

    return create_user(name=name, email=email, password=password)


def login_user(email: str, password: str) -> tuple[dict[str, object], dict[str, str], dict[str, object]]:
    if _supabase_enabled():
        response = _supabase_request('/auth/v1/token?grant_type=password', {
            'email': email,
            'password': password
        })
        user_payload = response.get('user') or {}
        user_id = str(user_payload.get('id', ''))
        user_email = str(user_payload.get('email') or email)
        user_name = str((user_payload.get('user_metadata') or {}).get('name') or user_payload.get('name') or user_email.split('@')[0])
        if user_id:
            access_token = _extract_access_token(response)
            _supabase_rest_upsert_user(user_id, user_name, user_email, bearer_token=access_token)
            user, default_chat = register_user_record(user_id, user_name, user_email, bearer_token=access_token)
            session = {'token': access_token, 'mode': 'authenticated', 'user_id': user_id}
            return user, session, default_chat

    return authenticate_user(email=email, password=password)


def resolve_session(session_token: str) -> dict[str, object] | None:
    if _supabase_enabled():
        auth_user = _supabase_auth_user(session_token)
        if isinstance(auth_user, dict):
            user_id = str(auth_user.get('id', ''))
            email = str(auth_user.get('email') or '')
            user_name = str((auth_user.get('user_metadata') or {}).get('name') or auth_user.get('name') or email.split('@')[0])
            if user_id:
                return {
                    'id': user_id,
                    'name': user_name,
                    'email': email,
                    'is_demo': False,
                    'created_at': auth_user.get('created_at')
                }

    return get_user_from_session(session_token)
