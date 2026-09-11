from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, email: str, password_hash: str | None, name: str, avatar_url: str | None = None) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            name=name,
            avatar_url=avatar_url,
        )
        self.db.add(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)

    def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id)
        return self.db.scalar(statement)
