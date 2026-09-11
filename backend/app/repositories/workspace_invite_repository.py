from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invite import WorkspaceInvite


class WorkspaceInviteRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **values) -> WorkspaceInvite:
        invite = WorkspaceInvite(**values)
        self.db.add(invite)
        self.db.flush()
        return invite

    def get_by_token_hash(self, token_hash: str) -> WorkspaceInvite | None:
        return self.db.scalar(select(WorkspaceInvite).where(WorkspaceInvite.token_hash == token_hash))

    def get_by_id(self, invite_id: UUID) -> WorkspaceInvite | None:
        return self.db.scalar(select(WorkspaceInvite).where(WorkspaceInvite.id == invite_id))

    def list_pending(self, workspace_id: UUID) -> list[WorkspaceInvite]:
        statement = (
            select(WorkspaceInvite)
            .where(
                WorkspaceInvite.workspace_id == workspace_id,
                WorkspaceInvite.revoked.is_(False),
                WorkspaceInvite.accepted_at.is_(None),
            )
            .order_by(WorkspaceInvite.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_for_workspace(self, workspace_id: UUID) -> list[WorkspaceInvite]:
        statement = (
            select(WorkspaceInvite)
            .where(WorkspaceInvite.workspace_id == workspace_id)
            .order_by(WorkspaceInvite.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_for_email(self, email: str) -> list[tuple[WorkspaceInvite, Workspace, User]]:
        statement = (
            select(WorkspaceInvite, Workspace, User)
            .join(Workspace, Workspace.id == WorkspaceInvite.workspace_id)
            .join(User, User.id == WorkspaceInvite.invited_by)
            .where(
                WorkspaceInvite.email == email,
                WorkspaceInvite.revoked.is_(False),
                WorkspaceInvite.accepted_at.is_(None),
                WorkspaceInvite.declined_at.is_(None),
            )
            .order_by(WorkspaceInvite.created_at.desc())
        )
        return list(self.db.execute(statement).all())

    def revoke(self, invite: WorkspaceInvite) -> WorkspaceInvite:
        invite.revoked = True
        self.db.flush()
        return invite

    def mark_accepted(self, invite: WorkspaceInvite, accepted_at: datetime) -> WorkspaceInvite:
        invite.accepted_at = accepted_at
        self.db.flush()
        return invite

    def mark_declined(self, invite: WorkspaceInvite, declined_at: datetime) -> WorkspaceInvite:
        invite.declined_at = declined_at
        self.db.flush()
        return invite