from app.services.demo_service import build_demo_workspace
from app.services.demo_chat_store import reset_chat_state


def reset_demo_state() -> dict[str, object]:
    reset_chat_state()
    return {
        'status': 'reset',
        'workspace': build_demo_workspace(),
        'next_reset_in_hours': 24,
        'reset_scope': ['messages', 'analytics', 'feedback', 'cache', 'memory'],
        'preserved_scope': ['documents', 'pinecone_vectors', 'demo_ingest_state']
    }
