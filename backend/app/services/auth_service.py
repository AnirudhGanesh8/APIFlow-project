from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parseaddr

import httpx
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_reset_token,
    decode_reset_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import User
from app.repositories.oauth_account_repository import OAuthAccountRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserCreate, UserLogin


class EmailAlreadyExistsError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class InvalidRefreshTokenError(ValueError):
    pass


class InvalidResetTokenError(ValueError):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repository = UserRepository(db)
        self.oauth_account_repository = OAuthAccountRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)

    def signup(self, payload: UserCreate) -> User:
        email = payload.email.lower()
        existing_user = self.user_repository.get_by_email(email)
        if existing_user is not None:
            raise EmailAlreadyExistsError("Email is already registered.")

        user = self.user_repository.create(
            email=email,
            password_hash=hash_password(payload.password),
            name=payload.name,
        )
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, payload: UserLogin) -> User:
        email = payload.email.lower()
        user = self.user_repository.get_by_email(email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password.")
        return user

    def issue_token_pair(self, user: User) -> tuple[str, str]:
        access_token = create_access_token(subject=str(user.id))
        raw_refresh_token = generate_refresh_token()
        refresh_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.refresh_token_repository.create(user_id=user.id, token_hash=refresh_hash, expires_at=expires_at)
        self.db.commit()
        return access_token, raw_refresh_token

    def refresh(self, refresh_token: str) -> tuple[User, str, str]:
        if not refresh_token:
            raise InvalidRefreshTokenError("Refresh token is required.")

        current_hash = hash_token(refresh_token)
        token_row = self.refresh_token_repository.get_by_hash(current_hash)

        if token_row is None:
            raise InvalidRefreshTokenError("Invalid refresh token.")

        if token_row.revoked:
            self.refresh_token_repository.revoke_all_for_user(token_row.user_id)
            self.db.commit()
            raise InvalidRefreshTokenError("Refresh token reuse detected.")

        if token_row.expires_at <= datetime.now(timezone.utc):
            self.refresh_token_repository.revoke_by_hash(current_hash)
            self.db.commit()
            raise InvalidRefreshTokenError("Refresh token expired.")

        user = self.user_repository.get_by_id(token_row.user_id)
        if user is None:
            raise InvalidRefreshTokenError("Invalid refresh token user.")

        self.refresh_token_repository.revoke_by_hash(current_hash)

        access_token = create_access_token(subject=str(user.id))
        new_raw_refresh_token = generate_refresh_token()
        new_hash = hash_token(new_raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.refresh_token_repository.create(user_id=user.id, token_hash=new_hash, expires_at=expires_at)
        self.db.commit()
        return user, access_token, new_raw_refresh_token

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        self.refresh_token_repository.revoke_by_hash(hash_token(refresh_token))
        self.db.commit()

    def upsert_google_user(self, *, provider_user_id: str, email: str, name: str, avatar_url: str | None) -> User:
        oauth = self.oauth_account_repository.get_by_provider_subject("google", provider_user_id)
        if oauth:
            user = self.user_repository.get_by_id(oauth.user_id)
            if user is None:
                raise InvalidCredentialsError("Linked account is missing.")
            return user

        normalized_email = email.lower()
        user = self.user_repository.get_by_email(normalized_email)
        if user is None:
            user = self.user_repository.create(
                email=normalized_email,
                password_hash=None,
                name=name or normalized_email.split("@")[0],
                avatar_url=avatar_url,
            )
            user.is_verified = True
            self.db.flush()

        self.oauth_account_repository.create(user_id=user.id, provider="google", provider_user_id=provider_user_id)
        self.db.commit()
        self.db.refresh(user)
        return user

    def forgot_password(self, email: str) -> str | None:
        user = self.user_repository.get_by_email(email.lower())
        if user is None:
            return None
        return create_reset_token(email=user.email)

    def reset_password(self, token: str, new_password: str) -> None:
        try:
            email = decode_reset_token(token)
        except JWTError as exc:
            raise InvalidResetTokenError("Invalid or expired reset token.") from exc

        user = self.user_repository.get_by_email(email)
        if user is None:
            raise InvalidResetTokenError("Invalid reset token user.")

        user.password_hash = hash_password(new_password)
        self.refresh_token_repository.revoke_all_for_user(user.id)
        self.db.commit()


class EmailService:
    @staticmethod
    def _build_reset_link(token: str) -> str:
        return f"{settings.frontend_url}/reset-password?token={token}"

    @staticmethod
    def _resend_payload(*, to_email: str, reset_link: str) -> dict:
        return {
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": "Reset your APIFlow password",
            "html": (
                "<p>You requested a password reset for APIFlow.</p>"
                f"<p><a href=\"{reset_link}\">Reset password</a></p>"
                "<p>If you did not request this, you can ignore this email.</p>"
            ),
        }

    @staticmethod
    def send_password_reset_email(*, to_email: str, token: str) -> None:
        _, parsed_email = parseaddr(to_email)
        if not parsed_email:
            return

        reset_link = EmailService._build_reset_link(token)

        if not settings.resend_api_key:
            # Local development fallback: keep flow testable without external email setup.
            print(f"[dev-email] Reset link for {parsed_email}: {reset_link}")
            return

        payload = EmailService._resend_payload(to_email=parsed_email, reset_link=reset_link)
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=10.0) as client:
            response = client.post("https://api.resend.com/emails", json=payload, headers=headers)
            response.raise_for_status()

    @staticmethod
    def send_workspace_invite_email(
        *, to_email: str, workspace_name: str, inviter_name: str, role: str, invite_link: str, expires_at: datetime
    ) -> bool:
        _, parsed_email = parseaddr(to_email)
        if not parsed_email:
            return False

        subject = f"You've been invited to join {workspace_name} on APIFlow"
        html = (
            f"<p>{inviter_name} invited you to join <strong>{workspace_name}</strong> on APIFlow.</p>"
            f"<p>Your role will be <strong>{role}</strong>.</p>"
            f'<p><a href="{invite_link}">Accept workspace invite</a></p>'
            f"<p>This invite expires on {expires_at.isoformat()}.</p>"
        )

        if not settings.resend_api_key:
            print(f"[dev-email] Workspace invite for {parsed_email}: {invite_link}")
            return False

        payload = {
            "from": settings.resend_from_email,
            "to": [parsed_email],
            "subject": subject,
            "html": html,
        }
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post("https://api.resend.com/emails", json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            provider_detail = exc.response.text[:500]
            print(
                f"[invite-email-error] Resend rejected workspace invite to {parsed_email} "
                f"with HTTP {exc.response.status_code}: {provider_detail}"
            )
            return False
        except Exception as exc:
            print(f"[invite-email-error] Could not send workspace invite to {parsed_email}: {exc}")
            return False
        return True
