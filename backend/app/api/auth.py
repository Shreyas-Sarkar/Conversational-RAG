from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.schemas import (
    ApiEnvelope,
    LoginResponseData,
    SignupResponseData,
    UserRecord,
)
from app.services.auth_service import login_user, signup_user

router = APIRouter(prefix='/auth', tags=['auth'])


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post('/signup')
def signup(payload: SignupRequest) -> dict[str, object]:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail='Passwords do not match.')

    try:
        user, session, bootstrap_chat = signup_user(name=payload.name, email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ApiEnvelope(
        data=SignupResponseData(
            user=UserRecord(**user),
            session=session,
            bootstrap_chat_id=str(bootstrap_chat.get('id')) if bootstrap_chat.get('id') else None
        ).model_dump()
    ).model_dump()


@router.post('/login')
def login(payload: LoginRequest) -> dict[str, object]:
    try:
        user, session, default_chat = login_user(email=payload.email, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ApiEnvelope(
        data=LoginResponseData(
            user=UserRecord(**user),
            session=session,
            default_chat_ids=[str(default_chat.get('id'))]
        ).model_dump()
    ).model_dump()


@router.post('/demo')
def demo() -> dict[str, object]:
    from app.services.demo_service import build_demo_workspace

    workspace = build_demo_workspace()
    return ApiEnvelope(data={'session': {'mode': 'demo'}, **workspace}).model_dump()
