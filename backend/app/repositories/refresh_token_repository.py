from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id, token_hash: str, expires_at) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(token)
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.scalar(statement)

    def revoke_by_hash(self, token_hash: str) -> int:
        statement = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        result = self.db.execute(statement)
        return result.rowcount or 0

    def revoke_all_for_user(self, user_id) -> int:
        statement = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)).values(revoked=True)
        result = self.db.execute(statement)
        return result.rowcount or 0
