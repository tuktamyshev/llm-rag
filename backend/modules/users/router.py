from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import get_db
from modules.users.repository import UserRepository
from modules.users.schemas import AuthResponse, UserCreate, UserLogin, UserRead
from modules.users.service import UserService


router = APIRouter()


def _service(db: Session = Depends(get_db)) -> UserService:
    return UserService(repository=UserRepository(db))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, service: UserService = Depends(_service)) -> UserRead:
    user = service.register(payload)
    return UserRead.model_validate(user)


@router.post("/login", response_model=AuthResponse)
def login_user(payload: UserLogin, service: UserService = Depends(_service)) -> AuthResponse:
    user, access_token = service.login(payload)
    return AuthResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    repository = UserRepository(db)
    user = repository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.get("/", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    repository = UserRepository(db)
    return [UserRead.model_validate(user) for user in repository.list_all()]
