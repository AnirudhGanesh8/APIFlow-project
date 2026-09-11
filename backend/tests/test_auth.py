from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_reset_token,
    decode_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.auth_service import AuthService, InvalidRefreshTokenError


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    password = "Password123!"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_contains_user_subject() -> None:
    user_id = str(uuid4())

    token = create_access_token(subject=user_id)

    assert decode_token(token)["sub"] == user_id


def test_reset_token_requires_reset_type() -> None:
    token = create_reset_token(email="USER@example.com")

    assert decode_reset_token(token) == "user@example.com"

    access_token = create_access_token(subject="user@example.com")
    with pytest.raises(JWTError):
        decode_reset_token(access_token)


def test_refresh_rotates_token_and_revoked_reuse_revokes_all() -> None:
    db = Mock()
    user = SimpleNamespace(id=uuid4())
    token_row = SimpleNamespace(
        user_id=user.id,
        token_hash="hashed-token",
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    service = AuthService(db)
    refresh_repository = Mock()
    refresh_repository.get_by_hash.return_value = token_row
    user_repository = Mock()
    user_repository.get_by_id.return_value = user
    service.refresh_token_repository = refresh_repository
    service.user_repository = user_repository

    refreshed_user, access_token, new_refresh_token = service.refresh("raw-token")

    assert refreshed_user is user
    assert access_token
    assert new_refresh_token
    refresh_repository.revoke_by_hash.assert_called_once()
    refresh_repository.create.assert_called_once()

    token_row.revoked = True
    with pytest.raises(InvalidRefreshTokenError, match="reuse detected"):
        service.refresh("raw-token")
    refresh_repository.revoke_all_for_user.assert_called_once_with(user.id)
