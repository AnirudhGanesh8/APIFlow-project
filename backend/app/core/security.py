from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(password, password_hash)


def create_access_token(*, subject: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_reset_token(*, email: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes or settings.reset_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": email.lower(), "typ": "reset", "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_reset_token(token: str) -> str:
    payload = decode_token(token)
    token_type = payload.get("typ")
    email = payload.get("sub")
    if token_type != "reset" or not email:
        raise JWTError("Invalid reset token")
    return str(email).lower()


def create_invite_token(*, workspace_id: str, email: str, role: str, expires_days: int | None = None) -> str:
    days = expires_days or settings.invite_token_expire_days
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    payload = {
        "sub": email.lower(),
        "workspace_id": workspace_id,
        "role": role,
        "typ": "workspace_invite",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_invite_token(token: str) -> dict:
    payload = decode_token(token)
    if payload.get("typ") != "workspace_invite":
        raise JWTError("Invalid invite token")
    if not payload.get("sub") or not payload.get("workspace_id") or not payload.get("role"):
        raise JWTError("Incomplete invite token")
    return payload
