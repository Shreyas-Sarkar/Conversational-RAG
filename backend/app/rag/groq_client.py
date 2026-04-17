from __future__ import annotations

import logging

from groq import Groq

from app.core.config import settings


_groq_client: Groq | None = None
logger = logging.getLogger(__name__)


def _client() -> Groq:
    global _groq_client
    if _groq_client is None:
        if not settings.groq_api_key:
            raise RuntimeError('GROQ_API_KEY is not configured')
        _groq_client = Groq(api_key=settings.groq_api_key)
    return _groq_client


def invoke_groq(final_prompt: str) -> str:
    try:
        response = _client().chat.completions.create(
            model=settings.groq_model_name,
            messages=[
                {'role': 'system', 'content': 'You are a careful enterprise document assistant.'},
                {'role': 'user', 'content': final_prompt},
            ],
            temperature=settings.groq_temperature,
            top_p=settings.groq_top_p,
        )
    except Exception as error:
        logger.exception('Groq request failed')
        return ''

    choices = getattr(response, 'choices', []) or []
    if not choices:
        return ''
    message = getattr(choices[0], 'message', None)
    return str(getattr(message, 'content', '') or '').strip()
