from app.db.schemas import DemoAnalyticsSnapshot, SeededChatSummary
from app.services.demo_ingest import get_demo_chat_seed_payload


def build_demo_workspace() -> dict[str, object]:
    seed_payload = get_demo_chat_seed_payload()
    return {
        'workspace': 'demo',
        'status': 'seeded',
        'reset_interval_hours': 24,
        'seeded_chats': [
            SeededChatSummary(id=seed['chat_id'], title=seed['title']).model_dump()
            for seed in seed_payload.values()
        ],
        'analytics': DemoAnalyticsSnapshot(queries=342, avg_latency=1.4, feedback=0.94, chunks=1320).model_dump(),
        'guided_prompts': [prompt for seed in seed_payload.values() for prompt in seed.get('prompts', [])],
        'namespace_map': {seed['chat_id']: seed['namespace'] for seed in seed_payload.values()},
        'tour_steps': [
            'Ask a question',
            'Inspect chunks',
            'View similarity',
            'See citations',
            'Check metrics'
        ]
    }
