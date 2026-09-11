from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User
from app.models.workspace_member import WorkspaceRole
from app.schemas.collection import CollectionCreate, CollectionOut, CollectionUpdate
from app.services.collection_service import CollectionNotFoundError, CollectionService
from app.services.workspace_service import WorkspaceForbiddenError


router = APIRouter(tags=["collections"])


def _raise_collection_error(exc: ValueError) -> None:
    if isinstance(exc, CollectionNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, WorkspaceForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/workspaces/{workspace_id}/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(
    workspace_id: UUID,
    payload: CollectionCreate,
    current_user: User = Depends(require_role(WorkspaceRole.MEMBER)),
    db: Session = Depends(get_db),
) -> CollectionOut:
    try:
        return CollectionService(db).create_collection(workspace_id, payload, current_user)
    except ValueError as exc:
        _raise_collection_error(exc)
    raise AssertionError("unreachable")


@router.get("/workspaces/{workspace_id}/collections", response_model=list[CollectionOut])
def list_collections(
    workspace_id: UUID,
    current_user: User = Depends(require_role(WorkspaceRole.VIEWER)),
    db: Session = Depends(get_db),
) -> list[CollectionOut]:
    try:
        return CollectionService(db).list_collections(workspace_id, current_user)
    except ValueError as exc:
        _raise_collection_error(exc)
    raise AssertionError("unreachable")


@router.get("/collections/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionOut:
    try:
        return CollectionService(db).get_collection(collection_id, current_user)
    except ValueError as exc:
        _raise_collection_error(exc)
    raise AssertionError("unreachable")


@router.patch("/collections/{collection_id}", response_model=CollectionOut)
def rename_collection(
    collection_id: UUID,
    payload: CollectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionOut:
    try:
        return CollectionService(db).rename_collection(collection_id, payload, current_user)
    except ValueError as exc:
        _raise_collection_error(exc)
    raise AssertionError("unreachable")


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        CollectionService(db).delete_collection(collection_id, current_user)
    except ValueError as exc:
        _raise_collection_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)