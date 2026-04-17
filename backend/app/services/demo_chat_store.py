from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from app.services.demo_ingest import get_demo_chat_seed_payload
from app.services.workspace_store import _load_json as _workspace_load_json, _save_json as _workspace_save_json

ROOT_DIR = Path(__file__).resolve().parents[3]
CHAT_STATE_FILE = ROOT_DIR / 'backend' / 'demo_chat_state.json'
CHAT_STATE_META_FILE = ROOT_DIR / 'backend' / 'demo_chat_state_meta.json'


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


def _today_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _load_state_meta() -> dict[str, str]:
    return _load_json(CHAT_STATE_META_FILE, {'last_reset_date': _today_key()})


def _save_state_meta(last_reset_date: str) -> None:
    _save_json(CHAT_STATE_META_FILE, {'last_reset_date': last_reset_date})


def _build_seed_messages(chat_id: str) -> list[dict[str, object]]:
    seed_payload = get_demo_chat_seed_payload()
    seed = next((item for item in seed_payload.values() if item.get('chat_id') == chat_id), None)
    if not seed:
        return []

    prompts = seed.get('prompts', [])
    messages: list[dict[str, object]] = []
    for index, prompt in enumerate(prompts[:2], start=1):
        messages.append({'id': f'{chat_id}-seed-user-{index}', 'role': 'user', 'content': prompt, 'sources': []})
        messages.append({'id': f'{chat_id}-seed-assistant-{index}', 'role': 'assistant', 'content': f'Seeded demo response for {seed.get("title", chat_id)}.', 'sources': []})
    return messages


def _cloud_demo_chat_ids() -> list[str]:
    return []


def _cloud_chat_user_id(chat_id: str) -> str | None:
    return None


def _cloud_get_chat_history(chat_id: str) -> list[dict[str, object]]:
    return []


def _cloud_set_chat_history(chat_id: str, messages: list[dict[str, object]]) -> None:
    return


def _cloud_reset_chat_state() -> dict[str, list[dict[str, object]]]:
    return {}


def load_chat_state() -> dict[str, list[dict[str, object]]]:
    meta = _load_state_meta()
    current_day = _today_key()
    if meta.get('last_reset_date') != current_day:
        return reset_chat_state()

    state = _load_json(CHAT_STATE_FILE, {})
    if not state:
        seed_payload = get_demo_chat_seed_payload()
        state = {}
        for seed in seed_payload.values():
            state[seed['chat_id']] = _build_seed_messages(seed['chat_id'])
        _save_json(CHAT_STATE_FILE, state)
        _save_state_meta(current_day)
        return state
    return state


def get_chat_history(chat_id: str) -> list[dict[str, object]]:
    state = load_chat_state()
    if chat_id not in state:
        state[chat_id] = _build_seed_messages(chat_id)
        _save_json(CHAT_STATE_FILE, state)
    return state.get(chat_id, [])


def set_chat_history(chat_id: str, messages: list[dict[str, object]]) -> None:
    state = load_chat_state()
    state[chat_id] = messages
    _save_json(CHAT_STATE_FILE, state)
    _save_state_meta(_today_key())


def append_chat_message(chat_id: str, message: dict[str, object]) -> None:
    messages = get_chat_history(chat_id)
    messages.append(message)
    set_chat_history(chat_id, messages)


def reset_chat_state() -> dict[str, list[dict[str, object]]]:
    seed_payload = get_demo_chat_seed_payload()
    state: dict[str, list[dict[str, object]]] = {}
    for seed in seed_payload.values():
        state[seed['chat_id']] = _build_seed_messages(seed['chat_id'])
    _save_json(CHAT_STATE_FILE, state)
    _save_state_meta(_today_key())
    return state
