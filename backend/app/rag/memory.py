def summarize_chat_memory(chat_id: str, recent_messages: list[dict[str, object]] | None = None) -> str:
    recent_messages = recent_messages or []
    user_messages = [message['content'] for message in recent_messages if message.get('role') == 'user']
    if not user_messages:
        return ''
    return f"Chat {chat_id} is focused on: {user_messages[-1][:120]}"
