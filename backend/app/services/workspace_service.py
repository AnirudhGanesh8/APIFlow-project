from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError
from jose.exceptions import ExpiredSignatureError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_invite_token, decode_invite_token, hash_token
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invite import WorkspaceInvite
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.repositories.workspace_invite_repository import WorkspaceInviteRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    InviteCreate,
    InviteCreateResponse,
    InviteOut,
    MemberOut,
    PendingInviteOut,
    MyInviteOut,
    WorkspaceCreate,
    WorkspaceOut,
)
from app.services.auth_service import EmailService


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


class ExpiredInviteError(InvalidInviteError):
    pass


class RevokedInviteError(InvalidInviteError):
    pass


class AcceptedInviteError(InvalidInviteError):
    pass


class DeclinedInviteError(InvalidInviteError):
    pass


class DuplicateMemberError(ValueError):
    pass


class WorkspaceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.workspace_repository = WorkspaceRepository(db)
        self.invite_repository = WorkspaceInviteRepository(db)
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

    def generate_invite(self, workspace_id: UUID, payload: InviteCreate, current_user: User) -> InviteCreateResponse:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        workspace = self._get_workspace(workspace_id)
        if payload.role == WorkspaceRole.OWNER:
            raise WorkspaceForbiddenError("Owner invitations are not allowed.")
        invited_email = payload.email.lower()
        existing_user = self.user_repository.get_by_email(invited_email)
        if existing_user and self.workspace_repository.get_membership(workspace_id=workspace_id, user_id=existing_user.id):
            raise DuplicateMemberError("This user is already a workspace member.")

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.invite_token_expire_days)
        token = create_invite_token(
            workspace_id=str(workspace_id),
            email=invited_email,
            role=payload.role.value,
        )
        invite = self.invite_repository.create(
            workspace_id=workspace_id,
            email=invited_email,
            role=payload.role,
            invited_by=current_user.id,
            token_hash=hash_token(token),
            expires_at=expires_at,
        )
        self.db.commit()
        self.db.refresh(invite)
        invite_link = f"{settings.frontend_url}/accept-invite?token={token}"
        email_sent = EmailService.send_workspace_invite_email(
            to_email=invited_email,
            workspace_name=workspace.name,
            inviter_name=current_user.name,
            role=payload.role.value,
            invite_link=invite_link,
            expires_at=expires_at,
        )
        return InviteCreateResponse(
            invite=InviteOut(
                id=invite.id,
                email=invite.email,
                role=invite.role,
                invite_token=token,
                invite_link=invite_link,
                expires_at=invite.expires_at,
            ),
            email_sent=email_sent,
        )

    def list_pending_invites(self, workspace_id: UUID, current_user: User) -> list[PendingInviteOut]:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        now = datetime.now(timezone.utc)
        return [
            PendingInviteOut(
                id=invite.id,
                email=invite.email,
                role=invite.role,
                invited_by=invite.invited_by,
                created_at=invite.created_at,
                expires_at=invite.expires_at,
                status=(
                    "accepted" if invite.accepted_at is not None
                    else "declined" if getattr(invite, "declined_at", None) is not None
                    else "revoked" if invite.revoked
                    else "expired" if invite.expires_at <= now
                    else "pending"
                ),
            )
            for invite in self.invite_repository.list_for_workspace(workspace_id)
        ]

    def list_my_invites(self, current_user: User) -> list[MyInviteOut]:
        return [
            MyInviteOut(
                id=invite.id,
                workspace_id=workspace.id,
                workspace_name=workspace.name,
                inviter_name=inviter.name,
                email=invite.email,
                role=invite.role,
                created_at=invite.created_at,
                expires_at=invite.expires_at,
            )
            for invite, workspace, inviter in self.invite_repository.list_for_email(current_user.email.lower())
            if invite.expires_at > datetime.now(timezone.utc)
        ]

    def _validate_active_invite(self, invite: WorkspaceInvite, current_user: User) -> None:
        invited_email = invite.email.lower()
        current_email = current_user.email.lower()
        if current_email != invited_email:
            raise WorkspaceForbiddenError(
                f"This invite was sent to {invited_email}, but you're logged in as {current_email}."
            )
        if invite.revoked:
            raise RevokedInviteError("This invite has been revoked.")
        if getattr(invite, "declined_at", None) is not None:
            raise DeclinedInviteError("This invite has been declined.")
        if invite.accepted_at is not None:
            raise AcceptedInviteError("This invite has already been accepted.")
        if invite.expires_at <= datetime.now(timezone.utc):
            raise ExpiredInviteError("This invite has expired.")

    def _accept_persisted_invite(self, invite: WorkspaceInvite, current_user: User) -> WorkspaceOut:
        self._validate_active_invite(invite, current_user)
        workspace = self._get_workspace(invite.workspace_id)
        if self.workspace_repository.get_membership(workspace_id=workspace.id, user_id=current_user.id):
            raise DuplicateMemberError("You are already a member of this workspace.")
        self.workspace_repository.add_member(workspace_id=workspace.id, user_id=current_user.id, role=invite.role)
        self.invite_repository.mark_accepted(invite, datetime.now(timezone.utc))
        self.db.commit()
        return self._workspace_out(workspace)

    def accept_my_invite(self, invite_id: UUID, current_user: User) -> WorkspaceOut:
        invite = self.invite_repository.get_by_id(invite_id)
        if invite is None:
            raise WorkspaceNotFoundError("Invitation not found.")
        return self._accept_persisted_invite(invite, current_user)

    def decline_my_invite(self, invite_id: UUID, current_user: User) -> None:
        invite = self.invite_repository.get_by_id(invite_id)
        if invite is None:
            raise WorkspaceNotFoundError("Invitation not found.")
        self._validate_active_invite(invite, current_user)
        self.invite_repository.mark_declined(invite, datetime.now(timezone.utc))
        self.db.commit()

    def revoke_invite(self, workspace_id: UUID, invite_id: UUID, current_user: User) -> None:
        self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        invite = self.invite_repository.get_by_id(invite_id)
        if invite is None or invite.workspace_id != workspace_id:
            raise WorkspaceNotFoundError("Invite not found.")
        if invite.accepted_at is not None:
            raise InvalidInviteError("Accepted invites cannot be revoked.")
        if invite.revoked:
            return
        self.invite_repository.revoke(invite)
        self.db.commit()

    def accept_invite(self, token: str, current_user: User) -> WorkspaceOut:
        try:
            payload = decode_invite_token(token)
        except ExpiredSignatureError as exc:
            raise ExpiredInviteError("This invite has expired.") from exc
        except JWTError as exc:
            raise InvalidInviteError("Invalid invite link.") from exc

        try:
            workspace_id = UUID(str(payload["workspace_id"]))
            invited_email = str(payload["sub"]).lower()
            role = WorkspaceRole(str(payload["role"]))
        except (KeyError, ValueError) as exc:
            raise InvalidInviteError("Invalid invite link.") from exc

        current_email = str(current_user.email).lower()
        if current_email != invited_email:
            raise WorkspaceForbiddenError(
                f"This invite was sent to {invited_email}, but you're logged in as {current_email}."
            )

        invite = self.invite_repository.get_by_token_hash(hash_token(token))
        if invite is None or invite.workspace_id != workspace_id or invite.email != invited_email or invite.role != role:
            raise InvalidInviteError("This invite is no longer valid.")
        if invite.role != role:
            raise InvalidInviteError("This invite is no longer valid.")
        return self._accept_persisted_invite(invite, current_user)

    def change_role(self, workspace_id: UUID, user_id: UUID, role: WorkspaceRole, current_user: User) -> WorkspaceOut:
        actor_membership = self._require_role(workspace_id, current_user.id, WorkspaceRole.ADMIN)
        if user_id == current_user.id:
            raise WorkspaceForbiddenError("You cannot change your own role.")
        if role == WorkspaceRole.OWNER:
            raise WorkspaceForbiddenError("The workspace owner role cannot be assigned here.")
        workspace = self._get_workspace(workspace_id)
        target_membership = self.workspace_repository.get_membership(workspace_id=workspace_id, user_id=user_id)
        if target_membership is None:
            raise WorkspaceNotFoundError("Workspace member not found.")
        if target_membership.role == WorkspaceRole.OWNER:
            raise WorkspaceForbiddenError("The workspace owner role cannot be changed.")
        self.workspace_repository.update_member_role(target_membership, role)
        self.db.commit()
        return self._workspace_out(workspace)
