from app.rag.memory import summarize_chat_memory
from app.services.demo_chat_store import append_chat_message as append_demo_chat_message, get_chat_history as get_demo_chat_history
from app.services.demo_ingest import get_demo_namespace_for_chat
from app.services.workspace_store import append_chat_message as append_workspace_chat_message, get_chat_history as get_workspace_chat_history, get_chat_memory_summary as get_workspace_chat_memory_summary, set_chat_history as set_workspace_chat_history
import uuid


def make_turn_message_id(chat_id: str, role: str, content: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'{chat_id}|{role}|{content}'))


def build_chat_turn(chat_id: str, message: str, answer: str, sources: list[dict[str, object]]) -> dict[str, object]:
    user_message = {
        'id': make_turn_message_id(chat_id, 'user', message),
        'chat_id': chat_id,
        'role': 'user',
        'content': message,
        'sources': []
    }
    assistant_message = {
        'id': make_turn_message_id(chat_id, 'assistant', answer),
        'chat_id': chat_id,
        'role': 'assistant',
        'content': answer,
        'sources': sources
    }
    memory_summary = summarize_chat_memory(chat_id, [user_message, assistant_message])
    return {
        'chat_id': chat_id,
        'user_message': user_message,
        'assistant_message': assistant_message,
        'memory_summary': memory_summary
    }


def create_chat_turn(chat_id: str, message: str, answer: str, sources: list[dict[str, object]]) -> dict[str, object]:
    return build_chat_turn(chat_id, message, answer, sources)


def get_persisted_chat_history(chat_id: str) -> list[dict[str, object]]:
    if get_demo_namespace_for_chat(chat_id):
        return get_demo_chat_history(chat_id)
    return get_workspace_chat_history(chat_id)


def get_chat_memory_summary(chat_id: str) -> str:
    if get_demo_namespace_for_chat(chat_id):
        return f'Chat is focused on {chat_id} guidance.'
    return get_workspace_chat_memory_summary(chat_id)


def persist_chat_turn(chat_id: str, user_message: dict[str, object], assistant_message: dict[str, object]) -> None:
    if get_demo_namespace_for_chat(chat_id):
        append_demo_chat_message(chat_id, user_message)
        append_demo_chat_message(chat_id, assistant_message)
        return

    append_workspace_chat_message(chat_id, user_message)
    append_workspace_chat_message(chat_id, assistant_message)


def replace_chat_history(chat_id: str, messages: list[dict[str, object]]) -> None:
    if get_demo_namespace_for_chat(chat_id):
        from app.services.demo_chat_store import set_chat_history as set_demo_chat_history

        set_demo_chat_history(chat_id, messages)
        return

    set_workspace_chat_history(chat_id, messages)
