from __future__ import annotations

import logging

from app.rag.groq_client import invoke_groq
from app.rag.prompts import RAG_PROMPT_TEMPLATE, RAG_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


def build_rag_prompt(question: str, context: str, chat_history: str) -> str:
    return RAG_PROMPT_TEMPLATE.format(
        system_prompt=RAG_SYSTEM_PROMPT,
        context=context.strip() or 'No retrieved context was available.',
        chat_history=chat_history.strip() or 'No prior conversation history.',
        question=question.strip()
    )


def run_rag_chain(message: str, context: str, chat_history: str = '') -> dict[str, object]:
    final_prompt = build_rag_prompt(question=message, context=context, chat_history=chat_history)
    response = invoke_groq(final_prompt)
    logger.info('Ran legacy RAG chain', extra={'context_length': len(context), 'chat_history_length': len(chat_history), 'response_length': len(response)})
    return {'answer': response, 'sources': []}
