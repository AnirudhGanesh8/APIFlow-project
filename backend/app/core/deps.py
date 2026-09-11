from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.models.workspace_member import WorkspaceRole
from app.services.workspace_service import WorkspaceForbiddenError, WorkspaceService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        subject = payload.get("sub")
        if not subject:
            raise credentials_exception
        user_id = UUID(str(subject))
    except JWTError as exc:
        raise credentials_exception from exc
    except ValueError as exc:
        raise credentials_exception from exc

    repository = UserRepository(db)
    user = repository.get_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


def require_role(minimum: WorkspaceRole):
    def dependency(
        workspace_id: UUID,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        try:
            WorkspaceService(db).require_role_for_dependency(workspace_id, current_user.id, minimum)
        except WorkspaceForbiddenError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return current_user

    return dependency
