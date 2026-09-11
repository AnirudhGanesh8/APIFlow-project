"""create persisted workspace invites

Revision ID: 20260911_0004_workspace_invites
Revises: 20260828_0003_workspaces
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260911_0004_workspace_invites"
down_revision = "20260828_0003_workspaces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_invites",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("owner", "admin", "member", "viewer", name="workspace_role", create_type=False),
            nullable=False,
        ),
        sa.Column("invited_by", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_workspace_invites_workspace_id", "workspace_invites", ["workspace_id"], unique=False)
    op.create_index("ix_workspace_invites_email", "workspace_invites", ["email"], unique=False)
    op.create_index("ix_workspace_invites_invited_by", "workspace_invites", ["invited_by"], unique=False)
    op.create_index("ix_workspace_invites_token_hash", "workspace_invites", ["token_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workspace_invites_token_hash", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_invited_by", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_email", table_name="workspace_invites")
    op.drop_index("ix_workspace_invites_workspace_id", table_name="workspace_invites")
    op.drop_table("workspace_invites")