from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.models.workspace_member import WorkspaceRole
from app.schemas.workspace import InviteCreate, InviteOut, MemberRoleUpdate, WorkspaceCreate, WorkspaceOut
from app.services.workspace_service import (
    DuplicateMemberError,
    InvalidInviteError,
    WorkspaceForbiddenError,
    WorkspaceNotFoundError,
    WorkspaceService,
)


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _raise_workspace_error(exc: ValueError) -> None:
    if isinstance(exc, WorkspaceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (WorkspaceForbiddenError, DuplicateMemberError)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, InvalidInviteError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    return WorkspaceService(db).create(payload, current_user)


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[WorkspaceOut]:
    return WorkspaceService(db).list_for_user(current_user)


@router.post("/invites/{token}/accept", response_model=WorkspaceOut)
def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    try:
        return WorkspaceService(db).accept_invite(token, current_user)
    except ValueError as exc:
        _raise_workspace_error(exc)
    raise AssertionError("unreachable")


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(require_role(WorkspaceRole.VIEWER)),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    try:
        return WorkspaceService(db).get(workspace_id, current_user)
    except ValueError as exc:
        _raise_workspace_error(exc)
    raise AssertionError("unreachable")


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
def rename_workspace(
    workspace_id: UUID,
    payload: WorkspaceCreate,
    current_user: User = Depends(require_role(WorkspaceRole.ADMIN)),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    try:
        return WorkspaceService(db).rename(workspace_id, payload.name, current_user)
    except ValueError as exc:
        _raise_workspace_error(exc)
    raise AssertionError("unreachable")


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(require_role(WorkspaceRole.OWNER)),
    db: Session = Depends(get_db),
) -> Response:
    try:
        WorkspaceService(db).delete(workspace_id, current_user)
    except ValueError as exc:
        _raise_workspace_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{workspace_id}/invites", response_model=InviteOut)
def generate_invite(
    workspace_id: UUID,
    payload: InviteCreate,
    current_user: User = Depends(require_role(WorkspaceRole.ADMIN)),
    db: Session = Depends(get_db),
) -> InviteOut:
    try:
        return WorkspaceService(db).generate_invite(workspace_id, payload, current_user)
    except ValueError as exc:
        _raise_workspace_error(exc)
    raise AssertionError("unreachable")


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceOut)
def change_member_role(
    workspace_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdate,
    current_user: User = Depends(require_role(WorkspaceRole.ADMIN)),
    db: Session = Depends(get_db),
) -> WorkspaceOut:
    try:
        return WorkspaceService(db).change_role(workspace_id, user_id, payload.role, current_user)
    except ValueError as exc:
        _raise_workspace_error(exc)
    raise AssertionError("unreachable")
