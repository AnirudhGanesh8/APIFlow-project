from uuid import UUID

from sqlalchemy.orm import Session

from app.models.collection import Collection
from app.models.user import User
from app.models.workspace_member import WorkspaceRole
from app.repositories.collection_repository import CollectionRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.collection import CollectionCreate, CollectionOut, CollectionUpdate
from app.services.workspace_service import ROLE_RANK, WorkspaceForbiddenError


class CollectionNotFoundError(ValueError):
    pass


class CollectionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.collection_repository = CollectionRepository(db)
        self.workspace_repository = WorkspaceRepository(db)

    def _require_role(self, workspace_id: UUID, user_id: UUID, minimum: WorkspaceRole) -> None:
        membership = self.workspace_repository.get_membership(workspace_id=workspace_id, user_id=user_id)
        if membership is None:
            raise WorkspaceForbiddenError("You are not a member of this workspace.")
        if ROLE_RANK[membership.role] < ROLE_RANK[minimum]:
            raise WorkspaceForbiddenError("You do not have permission to perform this action.")

    def _get_for_member(self, collection_id: UUID, current_user: User, minimum: WorkspaceRole) -> Collection:
        collection = self.collection_repository.get_by_id(collection_id)
        if collection is None:
            raise CollectionNotFoundError("Collection not found.")
        try:
            self._require_role(collection.workspace_id, current_user.id, minimum)
        except WorkspaceForbiddenError as exc:
            if str(exc) == "You are not a member of this workspace.":
                raise CollectionNotFoundError("Collection not found.") from exc
            raise
        return collection

    @staticmethod
    def _out(collection: Collection) -> CollectionOut:
        return CollectionOut.model_validate(collection)

    def create_collection(self, workspace_id: UUID, data: CollectionCreate, current_user: User) -> CollectionOut:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.MEMBER)
        collection = self.collection_repository.create(
            workspace_id=workspace_id,
            name=data.name.strip(),
            created_by=current_user.id,
        )
        self.db.commit()
        self.db.refresh(collection)
        return self._out(collection)

    def list_collections(self, workspace_id: UUID, current_user: User) -> list[CollectionOut]:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.VIEWER)
        return [self._out(collection) for collection in self.collection_repository.list_by_workspace(workspace_id)]

    def get_collection(self, collection_id: UUID, current_user: User) -> CollectionOut:
        return self._out(self._get_for_member(collection_id, current_user, WorkspaceRole.VIEWER))

    def rename_collection(self, collection_id: UUID, data: CollectionUpdate, current_user: User) -> CollectionOut:
        collection = self._get_for_member(collection_id, current_user, WorkspaceRole.MEMBER)
        self.collection_repository.update(collection, name=data.name.strip())
        self.db.commit()
        self.db.refresh(collection)
        return self._out(collection)

    def delete_collection(self, collection_id: UUID, current_user: User) -> None:
        collection = self._get_for_member(collection_id, current_user, WorkspaceRole.ADMIN)
        self.collection_repository.delete(collection.id)
        self.db.commit()