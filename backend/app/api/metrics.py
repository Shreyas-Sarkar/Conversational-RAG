from fastapi import APIRouter

from app.db.schemas import ApiEnvelope
from app.services.metrics_service import get_metrics_snapshot

router = APIRouter(tags=['metrics'])


@router.get('/metrics')
def metrics() -> dict[str, object]:
    return ApiEnvelope(data=get_metrics_snapshot()).model_dump()
