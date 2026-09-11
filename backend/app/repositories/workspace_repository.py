from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole


class WorkspaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, name: str, owner_id: UUID) -> Workspace:
        workspace = Workspace(name=name, owner_id=owner_id)
        self.db.add(workspace)
        self.db.flush()
        return workspace

    def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        return self.db.scalar(select(Workspace).where(Workspace.id == workspace_id))

    def list_for_user(self, user_id: UUID) -> list[Workspace]:
        statement = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update_name(self, workspace: Workspace, name: str) -> Workspace:
        workspace.name = name
        self.db.flush()
        return workspace

    def delete(self, workspace_id: UUID) -> None:
        self.db.execute(delete(Workspace).where(Workspace.id == workspace_id))

    def add_member(self, *, workspace_id: UUID, user_id: UUID, role: WorkspaceRole) -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self.db.add(member)
        self.db.flush()
        return member

    def get_membership(self, *, workspace_id: UUID, user_id: UUID) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        return self.db.scalar(statement)

    def list_members(self, workspace_id: UUID) -> list[WorkspaceMember]:
        statement = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at)
        )
        return list(self.db.scalars(statement).all())

    def update_member_role(self, member: WorkspaceMember, role: WorkspaceRole) -> WorkspaceMember:
        member.role = role
        self.db.flush()
        return member
