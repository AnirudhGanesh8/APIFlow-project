from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.collection import Collection


class CollectionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, workspace_id: UUID, name: str, created_by: UUID) -> Collection:
        collection = Collection(workspace_id=workspace_id, name=name, created_by=created_by)
        self.db.add(collection)
        self.db.flush()
        return collection

    def get_by_id(self, collection_id: UUID) -> Collection | None:
        return self.db.scalar(select(Collection).where(Collection.id == collection_id))

    def list_by_workspace(self, workspace_id: UUID) -> list[Collection]:
        statement = (
            select(Collection)
            .where(Collection.workspace_id == workspace_id)
            .order_by(Collection.created_at, Collection.name)
        )
        return list(self.db.scalars(statement).all())

    def update(self, collection: Collection, *, name: str) -> Collection:
        collection.name = name
        self.db.flush()
        return collection

    def delete(self, collection_id: UUID) -> None:
        self.db.execute(delete(Collection).where(Collection.id == collection_id))