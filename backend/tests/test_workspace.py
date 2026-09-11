from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.security import decode_invite_token
from app.models.workspace_member import WorkspaceRole
from app.schemas.workspace import InviteCreate
from app.services.workspace_service import WorkspaceForbiddenError, WorkspaceService


def user(email: str = "user@example.com"):
    return SimpleNamespace(id=uuid4(), email=email, name="Test User")


def service_with_repositories():
    database = Mock()
    service = WorkspaceService(database)
    service.workspace_repository = Mock()
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

    invite = service.generate_invite(
        workspace_id,
        InviteCreate(email="new@example.com", role=WorkspaceRole.MEMBER),
        user(),
    )

    payload = decode_invite_token(invite.invite_token)
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["sub"] == "new@example.com"
    assert payload["role"] == "member"


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

    from app.core.security import create_invite_token

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