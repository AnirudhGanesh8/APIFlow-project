from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CollectionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime