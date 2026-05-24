import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.demo import router as demo_router
from app.api.documents import router as documents_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.workspace import router as workspace_router
from app.services.demo_ingest import get_demo_chat_seed_payload, index_demo_docs

from app.core.config import settings

app = FastAPI(title='Conversational-RAG API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        settings.frontend_url
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(demo_router)
app.include_router(documents_router)
app.include_router(feedback_router)
app.include_router(metrics_router)
app.include_router(workspace_router)
app.include_router(health_router)


@app.on_event('startup')
def startup_index_demo():
    try:
        result = index_demo_docs()
        get_demo_chat_seed_payload()
        logging.info('Demo ingest result: %s', result)
    except Exception as exc:
        logging.exception('Demo ingest failed: %s', exc)
