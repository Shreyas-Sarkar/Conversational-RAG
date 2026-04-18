from __future__ import annotations

from statistics import mean

from app.services.workspace_store import _cloud_enabled, _select_rows


def _percent(up: int, total: int) -> float:
    return round((up / total) * 100, 2) if total else 0.0


def _cloud_metrics_snapshot() -> dict[str, object]:
    chats = _select_rows('chats', {'select': '*'})
    messages = _select_rows('messages', {'select': '*'})
    feedback_rows = _select_rows('feedback', {'select': '*'})
    cache_rows = _select_rows('query_cache', {'select': '*'})
    retrieval_rows = _select_rows('retrieval_events', {'select': '*'})

    latencies = [float(row.get('latency_ms', 0)) / 1000 for row in retrieval_rows if row.get('latency_ms') is not None]
    query_counts = []
    running_total = 0
    for chat in chats[-5:]:
        running_total += sum(1 for message in messages if str(message.get('chat_id')) == str(chat.get('id')))
        query_counts.append(running_total)

    top_queries = [
        str(row.get('query_hash', ''))[:12] or 'recent query'
        for row in cache_rows[:3]
    ]

    positive = sum(1 for row in feedback_rows if int(row.get('rating', 0)) > 0)
    negative = sum(1 for row in feedback_rows if int(row.get('rating', 0)) < 0)
    total_feedback = positive + negative

    return {
        'avg_latency': round(mean(latencies), 2) if latencies else 0.0,
        'tokens': sum(int(row.get('tokens', 0)) for row in retrieval_rows),
        'queries_per_day': len(cache_rows),
        'retrieved_chunks': sum(int(row.get('retrieved_chunks', 0)) for row in retrieval_rows),
        'feedback_score': round(_percent(positive, total_feedback) / 100, 2) if total_feedback else 0.0,
        'cache_hit_rate': round((sum(1 for row in cache_rows if row.get('response_text')) / len(cache_rows)), 2) if cache_rows else 0.0,
        'retrieval_confidence': round(mean([float(row.get('confidence', 0.0)) for row in retrieval_rows]), 2) if retrieval_rows else 0.0,
        'latency_trend': latencies[-5:] or [0.0],
        'queries_trend': query_counts or [len(cache_rows)],
        'feedback_breakdown': {'up': positive, 'down': negative},
        'top_queries': top_queries or ['No queries yet']
    }


def get_metrics_snapshot() -> dict[str, object]:
    if _cloud_enabled():
        return _cloud_metrics_snapshot()

    return {
        'avg_latency': 1.4,
        'tokens': 1200,
        'queries_per_day': 342,
        'retrieved_chunks': 1320,
        'feedback_score': 0.94,
        'cache_hit_rate': 0.62,
        'retrieval_confidence': 0.89,
        'latency_trend': [1.9, 1.7, 1.6, 1.5, 1.4],
        'queries_trend': [228, 251, 287, 319, 342],
        'feedback_breakdown': {'up': 94, 'down': 6},
        'top_queries': [
            'Explain Oracle migration',
            'Compare two uploaded docs',
            'Show sources used'
        ]
    }
