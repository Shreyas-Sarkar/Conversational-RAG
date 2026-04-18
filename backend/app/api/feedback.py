from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.workspace_store import _cloud_enabled, _upsert_row

router = APIRouter(tags=['feedback'])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int
    comment: str | None = None


@router.post('/feedback')
def feedback(payload: FeedbackRequest) -> dict[str, object]:
    if _cloud_enabled():
        try:
            record = {
                'message_id': payload.message_id,
                'user_id': None,
                'rating': int(payload.rating),
                'comment': payload.comment
            }
            _upsert_row('feedback', record)
            return {'ok': True, 'data': record}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f'Failed to persist feedback: {exc}')

    return {'ok': True, 'data': payload.model_dump()}
