from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_invite_token, decode_invite_token
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import InviteCreate, InviteOut, MemberOut, WorkspaceCreate, WorkspaceOut


ROLE_RANK = {
    WorkspaceRole.VIEWER: 1,
    WorkspaceRole.MEMBER: 2,
    WorkspaceRole.ADMIN: 3,
    WorkspaceRole.OWNER: 4,
}


class WorkspaceNotFoundError(ValueError):
    pass


class WorkspaceForbiddenError(ValueError):
    pass


class InvalidInviteError(ValueError):
    pass


class DuplicateMemberError(ValueError):
    pass


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workspace_repository = WorkspaceRepository(db)
        self.user_repository = UserRepository(db)

    def _get_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember:
        membership = self.workspace_repository.get_membership(workspace_id=workspace_id, user_id=user_id)
        if membership is None:
            raise WorkspaceForbiddenError("You are not a member of this workspace.")
        return membership

    def _require_role(self, workspace_id: UUID, user_id: UUID, minimum: WorkspaceRole) -> WorkspaceMember:
        membership = self._get_membership(workspace_id, user_id)
        if ROLE_RANK[membership.role] < ROLE_RANK[minimum]:
            raise WorkspaceForbiddenError("You do not have permission to perform this action.")
        return membership

    def require_role_for_dependency(self, workspace_id: UUID, user_id: UUID, minimum: WorkspaceRole) -> WorkspaceMember:
        return self._require_role(workspace_id, user_id, minimum)

    def _get_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError("Workspace not found.")
        return workspace

    def _member_out(self, member: WorkspaceMember) -> MemberOut:
        user = self.user_repository.get_by_id(member.user_id)
        if user is None:
            raise WorkspaceNotFoundError("Workspace member user not found.")
        return MemberOut(
            id=member.id,
            user_id=user.id,
            email=user.email,
            name=user.name,
            role=member.role,
            joined_at=member.joined_at,
        )

    def _workspace_out(self, workspace: Workspace) -> WorkspaceOut:
        return WorkspaceOut(
            id=workspace.id,
            name=workspace.name,
            owner_id=workspace.owner_id,
            created_at=workspace.created_at,
            members=[self._member_out(member) for member in self.workspace_repository.list_members(workspace.id)],
        )

    def create(self, payload: WorkspaceCreate, current_user: User) -> WorkspaceOut:
        workspace = self.workspace_repository.create(name=payload.name.strip(), owner_id=current_user.id)
        self.workspace_repository.add_member(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role=WorkspaceRole.OWNER,
        )
        self.db.commit()
        self.db.refresh(workspace)
        return self._workspace_out(workspace)

    def list_for_user(self, current_user: User) -> list[WorkspaceOut]:
        workspaces = self.workspace_repository.list_for_user(current_user.id)
        return [self._workspace_out(workspace) for workspace in workspaces]

    def get(self, workspace_id: UUID, current_user: User) -> WorkspaceOut:
        self._get_membership(workspace_id, current_user.id)
        return self._workspace_out(self._get_workspace(workspace_id))

    def rename(self, workspace_id: UUID, name: str, current_user: User) -> WorkspaceOut:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        workspace = self.workspace_repository.update_name(self._get_workspace(workspace_id), name.strip())
        self.db.commit()
        return self._workspace_out(workspace)

    def delete(self, workspace_id: UUID, current_user: User) -> None:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.OWNER)
        self._get_workspace(workspace_id)
        self.workspace_repository.delete(workspace_id)
        self.db.commit()

    def generate_invite(self, workspace_id: UUID, payload: InviteCreate, current_user: User) -> InviteOut:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        self._get_workspace(workspace_id)
        if payload.role == WorkspaceRole.OWNER:
            raise WorkspaceForbiddenError("Owner invitations are not allowed.")
        existing_user = self.user_repository.get_by_email(payload.email.lower())
        if existing_user and self.workspace_repository.get_membership(workspace_id=workspace_id, user_id=existing_user.id):
            raise DuplicateMemberError("This user is already a workspace member.")

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.invite_token_expire_days)
        token = create_invite_token(
            workspace_id=str(workspace_id),
            email=payload.email,
            role=payload.role.value,
        )
        return InviteOut(
            invite_token=token,
            invite_link=f"{settings.frontend_url}/accept-invite?token={token}",
            expires_at=expires_at,
        )

    def accept_invite(self, token: str, current_user: User) -> WorkspaceOut:
        try:
            payload = decode_invite_token(token)
            workspace_id = UUID(str(payload["workspace_id"]))
            invited_email = str(payload["sub"]).lower()
            role = WorkspaceRole(str(payload["role"]))
        except (JWTError, KeyError, ValueError) as exc:
            raise InvalidInviteError("Invalid or expired invite link.") from exc

        if current_user.email.lower() != invited_email:
            raise WorkspaceForbiddenError("This invite was issued for a different email address.")
        workspace = self._get_workspace(workspace_id)
        if self.workspace_repository.get_membership(workspace_id=workspace.id, user_id=current_user.id):
            raise DuplicateMemberError("You are already a member of this workspace.")

        self.workspace_repository.add_member(workspace_id=workspace.id, user_id=current_user.id, role=role)
        self.db.commit()
        return self._workspace_out(workspace)

    def change_role(self, workspace_id: UUID, user_id: UUID, role: WorkspaceRole, current_user: User) -> WorkspaceOut:
        actor_membership = self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        workspace = self._get_workspace(workspace_id)
        target_membership = self.workspace_repository.get_membership(workspace_id=workspace_id, user_id=user_id)
        if target_membership is None:
            raise WorkspaceNotFoundError("Workspace member not found.")
        if target_membership.role == WorkspaceRole.OWNER or role == WorkspaceRole.OWNER:
            raise WorkspaceForbiddenError("The workspace owner role cannot be changed.")
        if actor_membership.role != WorkspaceRole.OWNER and target_membership.role == WorkspaceRole.ADMIN:
            raise WorkspaceForbiddenError("Only the owner can change an admin's role.")
        self.workspace_repository.update_member_role(target_membership, role)
        self.db.commit()
        return self._workspace_out(workspace)
