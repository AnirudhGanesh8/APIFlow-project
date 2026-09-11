from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.security import create_invite_token, decode_invite_token
from app.models.workspace_member import WorkspaceRole
from app.schemas.workspace import InviteCreate
from app.services.auth_service import EmailService
from app.services.workspace_service import (
    ExpiredInviteError,
    RevokedInviteError,
    WorkspaceForbiddenError,
    WorkspaceService,
)


def user(email: str = "user@example.com"):
    return SimpleNamespace(id=uuid4(), email=email, name="Test User")


def service_with_repositories():
    database = Mock()
    service = WorkspaceService(database)
    service.workspace_repository = Mock()
    service.invite_repository = Mock()
    service.user_repository = Mock()
    return service


def test_non_member_cannot_view_workspace():
    service = service_with_repositories()
    workspace_id = uuid4()
    current_user = user()
    service.workspace_repository.get_membership.return_value = None

    with pytest.raises(WorkspaceForbiddenError, match="not a member"):
        service.get(workspace_id, current_user)

    service.workspace_repository.get_by_id.assert_not_called()


def test_viewer_cannot_generate_invite():
    service = service_with_repositories()
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.VIEWER)

    with pytest.raises(WorkspaceForbiddenError, match="permission"):
        service.generate_invite(uuid4(), InviteCreate(email="new@example.com"), user())


def test_member_cannot_delete_workspace():
    service = service_with_repositories()
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.MEMBER)

    with pytest.raises(WorkspaceForbiddenError, match="permission"):
        service.delete(uuid4(), user())


def test_admin_can_generate_member_invite():
    service = service_with_repositories()
    workspace_id = uuid4()
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.ADMIN)
    service.workspace_repository.get_by_id.return_value = SimpleNamespace(
        id=workspace_id,
        name="Test Workspace",
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    service.user_repository.get_by_email.return_value = None
    service.invite_repository.create.return_value = SimpleNamespace(
        id=uuid4(),
        email="new@example.com",
        role=WorkspaceRole.MEMBER,
        expires_at=datetime.now(timezone.utc),
    )
    from unittest.mock import patch

    with patch.object(EmailService, "send_workspace_invite_email", return_value=False):
        invite_response = service.generate_invite(
            workspace_id,
            InviteCreate(email="new@example.com", role=WorkspaceRole.MEMBER),
            user(),
        )

    invite = invite_response.invite

    payload = decode_invite_token(invite.invite_token)
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["sub"] == "new@example.com"
    assert payload["role"] == "member"
    assert invite_response.email_sent is False
    service.invite_repository.create.assert_called_once()


def test_accept_invite_adds_member_with_invited_role():
    service = service_with_repositories()
    workspace_id = uuid4()
    current_user = user("new@example.com")
    service.workspace_repository.get_by_id.return_value = SimpleNamespace(
        id=workspace_id,
        name="Test Workspace",
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    service.workspace_repository.get_membership.return_value = None
    service.workspace_repository.list_members.return_value = []
    service.invite_repository.get_by_token_hash.return_value = SimpleNamespace(
        workspace_id=workspace_id,
        email=current_user.email,
        role=WorkspaceRole.VIEWER,
        revoked=False,
        accepted_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    token = create_invite_token(
        workspace_id=str(workspace_id),
        email=current_user.email,
        role=WorkspaceRole.VIEWER.value,
    )

    service.accept_invite(token, current_user)

    service.workspace_repository.add_member.assert_called_once_with(
        workspace_id=workspace_id,
        user_id=current_user.id,
        role=WorkspaceRole.VIEWER,
    )


def test_accept_invite_rejects_wrong_email_with_specific_message():
    service = service_with_repositories()
    workspace_id = uuid4()
    token = create_invite_token(
        workspace_id=str(workspace_id), email="invited@example.com", role=WorkspaceRole.MEMBER.value
    )

    with pytest.raises(WorkspaceForbiddenError, match="invited@example.com.*logged in as other@example.com"):
        service.accept_invite(token, user("other@example.com"))

    service.invite_repository.get_by_token_hash.assert_not_called()


def test_accept_invite_rejects_expired_token(monkeypatch):
    service = service_with_repositories()
    current_user = user("invited@example.com")

    from jose.exceptions import ExpiredSignatureError

    monkeypatch.setattr(
        "app.services.workspace_service.decode_invite_token",
        Mock(side_effect=ExpiredSignatureError("expired")),
    )

    with pytest.raises(ExpiredInviteError, match="expired"):
        service.accept_invite("expired-token", current_user)


def test_accept_invite_rejects_revoked_persisted_invite():
    service = service_with_repositories()
    workspace_id = uuid4()
    current_user = user("invited@example.com")
    token = create_invite_token(
        workspace_id=str(workspace_id), email=current_user.email, role=WorkspaceRole.MEMBER.value
    )
    service.invite_repository.get_by_token_hash.return_value = SimpleNamespace(
        workspace_id=workspace_id,
        email=current_user.email,
        role=WorkspaceRole.MEMBER,
        revoked=True,
        accepted_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )

    with pytest.raises(RevokedInviteError, match="revoked"):
        service.accept_invite(token, current_user)


def test_accept_invite_marks_persisted_invite_accepted():
    service = service_with_repositories()
    workspace_id = uuid4()
    current_user = user("invited@example.com")
    token = create_invite_token(
        workspace_id=str(workspace_id), email=current_user.email, role=WorkspaceRole.MEMBER.value
    )
    invite = SimpleNamespace(
        workspace_id=workspace_id,
        email=current_user.email,
        role=WorkspaceRole.MEMBER,
        revoked=False,
        accepted_at=None,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    service.invite_repository.get_by_token_hash.return_value = invite
    service.workspace_repository.get_by_id.return_value = SimpleNamespace(
        id=workspace_id,
        name="Test Workspace",
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    service.workspace_repository.get_membership.return_value = None
    service.workspace_repository.list_members.return_value = []

    service.accept_invite(token, current_user)

    service.invite_repository.mark_accepted.assert_called_once()
    service.workspace_repository.add_member.assert_called_once_with(
        workspace_id=workspace_id,
        user_id=current_user.id,
        role=WorkspaceRole.MEMBER,
    )


def test_admin_cannot_change_own_role():
    service = service_with_repositories()
    current_user = user()
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.ADMIN)

    with pytest.raises(WorkspaceForbiddenError, match="cannot change your own role"):
        service.change_role(uuid4(), current_user.id, WorkspaceRole.MEMBER, current_user)


def test_cannot_assign_owner_role():
    service = service_with_repositories()
    current_user = user()
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.ADMIN)

    with pytest.raises(WorkspaceForbiddenError, match="cannot be assigned"):
        service.change_role(uuid4(), uuid4(), WorkspaceRole.OWNER, current_user)


def test_cannot_change_workspace_owner_role():
    service = service_with_repositories()
    current_user = user()
    service.workspace_repository.get_membership.side_effect = [
        SimpleNamespace(role=WorkspaceRole.ADMIN),
        SimpleNamespace(role=WorkspaceRole.OWNER),
    ]

    with pytest.raises(WorkspaceForbiddenError, match="owner role cannot be changed"):
        service.change_role(uuid4(), uuid4(), WorkspaceRole.MEMBER, current_user)


def test_admin_can_change_another_admin_role():
    service = service_with_repositories()
    current_user = user("admin@example.com")
    target_user_id = uuid4()
    service.workspace_repository.get_membership.side_effect = [
        SimpleNamespace(role=WorkspaceRole.ADMIN),
        SimpleNamespace(role=WorkspaceRole.ADMIN),
    ]
    service.workspace_repository.get_by_id.return_value = SimpleNamespace(
        id=uuid4(),
        name="Test Workspace",
        owner_id=uuid4(),
        created_at=datetime.now(timezone.utc),
    )
    service.workspace_repository.list_members.return_value = []

    service.change_role(uuid4(), target_user_id, WorkspaceRole.MEMBER, current_user)

    service.workspace_repository.update_member_role.assert_called_once()