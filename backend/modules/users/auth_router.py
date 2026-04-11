from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.db import get_db
from modules.users.repository import UserRepository
from modules.users.schemas import AuthResponse, UserCreate, UserLogin, UserRead
from modules.users.service import UserService


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> UserService:
    return UserService(repository=UserRepository(db))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, service: UserService = Depends(_service)) -> UserRead:
    return UserRead.model_validate(service.register(payload))


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, service: UserService = Depends(_service)) -> AuthResponse:
    user, access_token = service.login(payload)
    return AuthResponse(access_token=access_token, user=UserRead.model_validate(user))
