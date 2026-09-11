from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.workspace_member import WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class MemberOut(BaseModel):
    id: UUID
    user_id: UUID
    email: EmailStr
    name: str
    role: WorkspaceRole
    joined_at: datetime


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    members: list[MemberOut] = Field(default_factory=list)


class InviteCreate(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER


class InviteOut(BaseModel):
    invite_token: str
    invite_link: str
    expires_at: datetime


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole
