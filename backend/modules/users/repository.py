from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.users.models import User
from modules.users.schemas import UserCreate


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def list_all(self) -> list[User]:
        stmt = select(User).order_by(User.id)
        return list(self.db.scalars(stmt).all())

    def create(self, payload: UserCreate, password_hash: str) -> User:
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=password_hash,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, full_name: str) -> User:
        user.full_name = full_name
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()
