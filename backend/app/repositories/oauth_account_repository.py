from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oauth_account import OAuthAccount


class OAuthAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_provider_subject(self, provider: str, provider_user_id: str) -> OAuthAccount | None:
        statement = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
        return self.db.scalar(statement)

    def create(self, *, user_id, provider: str, provider_user_id: str) -> OAuthAccount:
        oauth_account = OAuthAccount(user_id=user_id, provider=provider, provider_user_id=provider_user_id)
        self.db.add(oauth_account)
        return oauth_account
