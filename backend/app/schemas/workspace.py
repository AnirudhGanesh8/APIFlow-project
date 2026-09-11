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
    id: UUID | None = None
    email: EmailStr | None = None
    role: WorkspaceRole | None = None
    invite_token: str
    invite_link: str
    expires_at: datetime


class InviteCreateResponse(BaseModel):
    invite: InviteOut
    email_sent: bool


class PendingInviteOut(BaseModel):
    id: UUID
    email: EmailStr
    role: WorkspaceRole
    invited_by: UUID
    created_at: datetime
    expires_at: datetime
    status: str = "pending"


class MyInviteOut(BaseModel):
    id: UUID
    workspace_id: UUID
    workspace_name: str
    inviter_name: str
    email: EmailStr
    role: WorkspaceRole
    created_at: datetime
    expires_at: datetime


class MemberRoleUpdate(BaseModel):
    role: WorkspaceRole
