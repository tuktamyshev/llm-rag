import hashlib

from fastapi import HTTPException, status

from modules.users.models import User
from modules.users.repository import UserRepository
from modules.users.schemas import UserCreate, UserLogin
from shared.security import create_jwt


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def register(self, payload: UserCreate) -> User:
        existing = self.repository.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        password_hash = _hash_password(payload.password)
        return self.repository.create(payload=payload, password_hash=password_hash)

    def login(self, payload: UserLogin) -> tuple[User, str]:
        user = self.repository.get_by_email(payload.email)
        if not user or user.password_hash != _hash_password(payload.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = create_jwt(subject=str(user.id))
        return user, token
