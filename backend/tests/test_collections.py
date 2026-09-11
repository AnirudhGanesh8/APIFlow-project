from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.workspace_member import WorkspaceRole
from app.schemas.collection import CollectionCreate, CollectionUpdate
from app.services.collection_service import CollectionNotFoundError, CollectionService
from app.services.workspace_service import WorkspaceForbiddenError


def user(email: str = "user@example.com"):
    return SimpleNamespace(id=uuid4(), email=email, name="Test User")


def collection(workspace_id):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Users",
        created_by=uuid4(),
        created_at=now,
        updated_at=now,
    )


def service_with_repositories():
    database = Mock()
    service = CollectionService(database)
    service.collection_repository = Mock()
    service.workspace_repository = Mock()
    return service


@pytest.mark.parametrize("role", [WorkspaceRole.VIEWER, WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER])
def test_members_can_list_collections(role):
    service = service_with_repositories()
    workspace_id = uuid4()
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=role)
    service.collection_repository.list_by_workspace.return_value = [collection(workspace_id)]

    result = service.list_collections(workspace_id, user())

    assert len(result) == 1


@pytest.mark.parametrize("role", [WorkspaceRole.MEMBER, WorkspaceRole.ADMIN, WorkspaceRole.OWNER])
def test_member_and_above_can_create_and_rename(role):
    service = service_with_repositories()
    workspace_id = uuid4()
    current_user = user()
    existing = collection(workspace_id)
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=role)
    service.collection_repository.create.return_value = existing
    service.collection_repository.get_by_id.return_value = existing

    created = service.create_collection(workspace_id, CollectionCreate(name=" Users "), current_user)
    renamed = service.rename_collection(existing.id, CollectionUpdate(name=" Accounts "), current_user)

    assert created.id == existing.id
    assert renamed.id == existing.id
    service.collection_repository.create.assert_called_once_with(
        workspace_id=workspace_id,
        name="Users",
        created_by=current_user.id,
    )
    service.collection_repository.update.assert_called_once_with(existing, name="Accounts")


@pytest.mark.parametrize("role", [WorkspaceRole.ADMIN, WorkspaceRole.OWNER])
def test_admin_and_owner_can_delete(role):
    service = service_with_repositories()
    existing = collection(uuid4())
    service.collection_repository.get_by_id.return_value = existing
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=role)

    service.delete_collection(existing.id, user())

    service.collection_repository.delete.assert_called_once_with(existing.id)


@pytest.mark.parametrize(
    ("operation", "minimum"),
    [
        ("create", WorkspaceRole.MEMBER),
        ("rename", WorkspaceRole.MEMBER),
        ("delete", WorkspaceRole.ADMIN),
    ],
)
def test_viewer_cannot_mutate_collections(operation, minimum):
    service = service_with_repositories()
    workspace_id = uuid4()
    existing = collection(workspace_id)
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.VIEWER)
    service.collection_repository.get_by_id.return_value = existing

    with pytest.raises(WorkspaceForbiddenError, match="permission"):
        if operation == "create":
            service.create_collection(workspace_id, CollectionCreate(name="Users"), user())
        elif operation == "rename":
            service.rename_collection(existing.id, CollectionUpdate(name="Accounts"), user())
        else:
            service.delete_collection(existing.id, user())

    assert minimum in (WorkspaceRole.MEMBER, WorkspaceRole.ADMIN)


def test_member_cannot_delete_collection():
    service = service_with_repositories()
    existing = collection(uuid4())
    service.collection_repository.get_by_id.return_value = existing
    service.workspace_repository.get_membership.return_value = SimpleNamespace(role=WorkspaceRole.MEMBER)

    with pytest.raises(WorkspaceForbiddenError, match="permission"):
        service.delete_collection(existing.id, user())


def test_non_member_cannot_view_or_mutate_collection():
    service = service_with_repositories()
    existing = collection(uuid4())
    service.collection_repository.get_by_id.return_value = existing
    service.workspace_repository.get_membership.return_value = None

    for operation in (
        lambda: service.get_collection(existing.id, user()),
        lambda: service.rename_collection(existing.id, CollectionUpdate(name="Accounts"), user()),
        lambda: service.delete_collection(existing.id, user()),
    ):
        with pytest.raises(CollectionNotFoundError, match="not found"):
            operation()


def test_non_member_cannot_list_or_create_collection():
    service = service_with_repositories()
    service.workspace_repository.get_membership.return_value = None
    workspace_id = uuid4()

    with pytest.raises(WorkspaceForbiddenError, match="not a member"):
        service.list_collections(workspace_id, user())
    with pytest.raises(WorkspaceForbiddenError, match="not a member"):
        service.create_collection(workspace_id, CollectionCreate(name="Users"), user())


def test_missing_collection_returns_clean_not_found():
    service = service_with_repositories()
    service.collection_repository.get_by_id.return_value = None

    with pytest.raises(CollectionNotFoundError, match="not found"):
        service.rename_collection(uuid4(), CollectionUpdate(name="Accounts"), user())
    with pytest.raises(CollectionNotFoundError, match="not found"):
        service.delete_collection(uuid4(), user())


def test_collection_from_workspace_a_is_hidden_from_workspace_b_member():
    service = service_with_repositories()
    workspace_a = uuid4()
    collection_a = collection(workspace_a)
    service.collection_repository.get_by_id.return_value = collection_a
    service.workspace_repository.get_membership.return_value = None
    workspace_b = uuid4()

    assert workspace_b != workspace_a
    for operation in (
        lambda: service.get_collection(collection_a.id, user("b@example.com")),
        lambda: service.rename_collection(collection_a.id, CollectionUpdate(name="Stolen"), user("b@example.com")),
        lambda: service.delete_collection(collection_a.id, user("b@example.com")),
    ):
        with pytest.raises(CollectionNotFoundError, match="not found"):
            operation()
    service.collection_repository.update.assert_not_called()
    service.collection_repository.delete.assert_not_called()