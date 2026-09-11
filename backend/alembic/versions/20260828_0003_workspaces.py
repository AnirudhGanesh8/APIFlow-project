"""create workspaces and workspace members tables

Revision ID: 20260828_0003_workspaces
Revises: 20260719_0002_auth_tables
Create Date: 2026-08-28 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260828_0003_workspaces"
down_revision = "20260719_0002_auth_tables"
branch_labels = None
depends_on = None


workspace_role = postgresql.ENUM(
    "owner",
    "admin",
    "member",
    "viewer",
    name="workspace_role",
)
workspace_role_column = postgresql.ENUM(
    "owner",
    "admin",
    "member",
    "viewer",
    name="workspace_role",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"], unique=False)

    workspace_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("role", workspace_role_column, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_user"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"], unique=False)
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
    workspace_role.drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_table("workspaces")
