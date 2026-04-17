from fastapi import APIRouter

from app.db.schemas import ApiEnvelope
from app.services.demo_service import build_demo_workspace

router = APIRouter(prefix='/demo', tags=['demo'])


@router.post('/reset')
def reset_demo() -> dict[str, object]:
    return ApiEnvelope(data={'reset': True, 'workspace': build_demo_workspace()}).model_dump()


@router.post('')
def create_demo_session() -> dict[str, object]:
    workspace = build_demo_workspace()
    return ApiEnvelope(data={'session': {'mode': 'demo'}, **workspace}).model_dump()
